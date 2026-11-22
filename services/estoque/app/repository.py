"""Persistência do estoque.

Duas implementações com a mesma semântica:
- PostgresRepository: produção, com SELECT ... FOR UPDATE para evitar overselling
  quando várias réplicas reservam o mesmo SKU ao mesmo tempo;
- InMemoryRepository: testes e STORAGE=memory (demo sem banco).
"""

import asyncio
from decimal import Decimal
from typing import Protocol

from app.models import ItemReservado, Produto, Reserva, StatusReserva


class EstoqueInsuficiente(Exception):
    def __init__(self, faltantes: dict[str, int]) -> None:
        super().__init__(f"estoque insuficiente: {faltantes}")
        self.faltantes = faltantes


class ProdutoNaoEncontrado(Exception):
    pass


class ReservaNaoEncontrada(Exception):
    pass


class TransicaoInvalida(Exception):
    pass


SEED: list[tuple[str, str, Decimal, int]] = [
    ("SKU-001", "Camiseta Veloz", Decimal("79.90"), 500),
    ("SKU-002", "Tênis Runner", Decimal("349.90"), 200),
    ("SKU-003", "Boné Classic", Decimal("59.90"), 1000),
    ("SKU-004", "Mochila Urbana", Decimal("199.90"), 150),
    ("SKU-005", "Smartwatch Fit", Decimal("899.00"), 50),
]


class Repository(Protocol):
    async def ping(self) -> bool: ...
    async def listar_produtos(self) -> list[Produto]: ...
    async def obter_produto(self, sku: str) -> Produto: ...
    async def reservar(self, pedido_id: str, itens: dict[str, int]) -> Reserva: ...
    async def confirmar(self, pedido_id: str) -> Reserva: ...
    async def liberar(self, pedido_id: str) -> Reserva: ...
    async def close(self) -> None: ...


def _montar_reserva(pedido_id: str, status: StatusReserva, linhas: list[tuple]) -> Reserva:
    itens = [
        ItemReservado(sku=s, nome=n, quantidade=q, preco_unitario=p, subtotal=p * q) for s, n, q, p in linhas
    ]
    return Reserva(
        pedido_id=pedido_id,
        status=status,
        itens=itens,
        total=sum((i.subtotal for i in itens), Decimal("0")),
    )


def _proximo_status(atual: StatusReserva, alvo: StatusReserva) -> bool:
    """Máquina de estados da reserva. Retorna False se já está no alvo (idempotente)."""
    if atual == alvo:
        return False
    if atual != StatusReserva.RESERVADA:
        raise TransicaoInvalida(f"reserva {atual} não pode ir para {alvo}")
    return True


class InMemoryRepository:
    def __init__(self) -> None:
        self._produtos = {s: Produto(sku=s, nome=n, preco=p, disponivel=d) for s, n, p, d in SEED}
        self._reservas: dict[str, tuple[StatusReserva, dict[str, int]]] = {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    async def listar_produtos(self) -> list[Produto]:
        return [p.model_copy() for p in self._produtos.values()]

    async def obter_produto(self, sku: str) -> Produto:
        if sku not in self._produtos:
            raise ProdutoNaoEncontrado(sku)
        return self._produtos[sku].model_copy()

    def _reserva(self, pedido_id: str) -> Reserva:
        status, itens = self._reservas[pedido_id]
        linhas = [(s, self._produtos[s].nome, q, self._produtos[s].preco) for s, q in itens.items()]
        return _montar_reserva(pedido_id, status, linhas)

    async def reservar(self, pedido_id: str, itens: dict[str, int]) -> Reserva:
        async with self._lock:
            if pedido_id in self._reservas:
                return self._reserva(pedido_id)
            for sku in itens:
                if sku not in self._produtos:
                    raise ProdutoNaoEncontrado(sku)
            faltantes = {s: q for s, q in itens.items() if self._produtos[s].disponivel < q}
            if faltantes:
                raise EstoqueInsuficiente(faltantes)
            for sku, qtd in itens.items():
                self._produtos[sku].disponivel -= qtd
            self._reservas[pedido_id] = (StatusReserva.RESERVADA, dict(itens))
            return self._reserva(pedido_id)

    async def _transicionar(self, pedido_id: str, alvo: StatusReserva) -> Reserva:
        async with self._lock:
            if pedido_id not in self._reservas:
                raise ReservaNaoEncontrada(pedido_id)
            atual, itens = self._reservas[pedido_id]
            if _proximo_status(atual, alvo):
                if alvo == StatusReserva.LIBERADA:
                    for sku, qtd in itens.items():
                        self._produtos[sku].disponivel += qtd
                self._reservas[pedido_id] = (alvo, itens)
            return self._reserva(pedido_id)

    async def confirmar(self, pedido_id: str) -> Reserva:
        return await self._transicionar(pedido_id, StatusReserva.BAIXADA)

    async def liberar(self, pedido_id: str) -> Reserva:
        return await self._transicionar(pedido_id, StatusReserva.LIBERADA)

    async def close(self) -> None:
        return None


SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    sku         TEXT PRIMARY KEY,
    nome        TEXT NOT NULL,
    preco       NUMERIC(12, 2) NOT NULL CHECK (preco >= 0),
    disponivel  INTEGER NOT NULL CHECK (disponivel >= 0)
);
CREATE TABLE IF NOT EXISTS reservas (
    pedido_id   TEXT NOT NULL,
    sku         TEXT NOT NULL REFERENCES produtos (sku),
    quantidade  INTEGER NOT NULL CHECK (quantidade > 0),
    status      TEXT NOT NULL,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pedido_id, sku)
);
"""

_SELECT_RESERVA = """
SELECT r.sku, p.nome, r.quantidade, p.preco, r.status
FROM reservas r JOIN produtos p ON p.sku = r.sku
WHERE r.pedido_id = %s ORDER BY r.sku
"""


class PostgresRepository:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        from psycopg_pool import AsyncConnectionPool

        self._pool = AsyncConnectionPool(dsn, min_size=min_size, max_size=max_size, open=False)

    async def open(self, seed: bool = True) -> None:
        await self._pool.open(wait=True, timeout=30)
        async with self._pool.connection() as conn, conn.transaction():
            # advisory lock: várias réplicas sobem juntas e só uma aplica o schema/seed
            await conn.execute("SELECT pg_advisory_xact_lock(4201)")
            await conn.execute(SCHEMA)
            if seed:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        "INSERT INTO produtos (sku, nome, preco, disponivel) VALUES (%s, %s, %s, %s)"
                        " ON CONFLICT (sku) DO NOTHING",
                        SEED,
                    )

    async def close(self) -> None:
        await self._pool.close()

    async def ping(self) -> bool:
        async with self._pool.connection(timeout=2) as conn:
            await conn.execute("SELECT 1")
        return True

    async def listar_produtos(self) -> list[Produto]:
        async with self._pool.connection() as conn:
            cur = await conn.execute("SELECT sku, nome, preco, disponivel FROM produtos ORDER BY sku")
            return [Produto(sku=s, nome=n, preco=p, disponivel=d) for s, n, p, d in await cur.fetchall()]

    async def obter_produto(self, sku: str) -> Produto:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "SELECT sku, nome, preco, disponivel FROM produtos WHERE sku = %s", (sku,)
            )
            row = await cur.fetchone()
        if row is None:
            raise ProdutoNaoEncontrado(sku)
        return Produto(sku=row[0], nome=row[1], preco=row[2], disponivel=row[3])

    @staticmethod
    async def _ler(conn, pedido_id: str) -> Reserva | None:
        cur = await conn.execute(_SELECT_RESERVA, (pedido_id,))
        rows = await cur.fetchall()
        if not rows:
            return None
        return _montar_reserva(pedido_id, StatusReserva(rows[0][4]), [r[:4] for r in rows])

    async def reservar(self, pedido_id: str, itens: dict[str, int]) -> Reserva:
        async with self._pool.connection() as conn, conn.transaction():
            existente = await self._ler(conn, pedido_id)
            if existente:  # idempotência: retry do serviço de pedidos não reserva duas vezes
                return existente
            # trava as linhas em ordem de SKU para evitar deadlock entre transações
            cur = await conn.execute(
                "SELECT sku, disponivel FROM produtos WHERE sku = ANY(%s) ORDER BY sku FOR UPDATE",
                (list(itens),),
            )
            disponivel = dict(await cur.fetchall())
            for sku in itens:
                if sku not in disponivel:
                    raise ProdutoNaoEncontrado(sku)
            faltantes = {s: q for s, q in itens.items() if disponivel[s] < q}
            if faltantes:
                raise EstoqueInsuficiente(faltantes)
            async with conn.cursor() as c:
                await c.executemany(
                    "UPDATE produtos SET disponivel = disponivel - %s WHERE sku = %s",
                    [(q, s) for s, q in itens.items()],
                )
                await c.executemany(
                    "INSERT INTO reservas (pedido_id, sku, quantidade, status) VALUES (%s, %s, %s, %s)",
                    [(pedido_id, s, q, StatusReserva.RESERVADA.value) for s, q in itens.items()],
                )
            return await self._ler(conn, pedido_id)

    async def _transicionar(self, pedido_id: str, alvo: StatusReserva) -> Reserva:
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute("SELECT 1 FROM reservas WHERE pedido_id = %s FOR UPDATE", (pedido_id,))
            atual = await self._ler(conn, pedido_id)
            if atual is None:
                raise ReservaNaoEncontrada(pedido_id)
            if _proximo_status(atual.status, alvo):
                if alvo == StatusReserva.LIBERADA:
                    async with conn.cursor() as c:
                        await c.executemany(
                            "UPDATE produtos SET disponivel = disponivel + %s WHERE sku = %s",
                            [(i.quantidade, i.sku) for i in atual.itens],
                        )
                await conn.execute(
                    "UPDATE reservas SET status = %s WHERE pedido_id = %s", (alvo.value, pedido_id)
                )
            return await self._ler(conn, pedido_id)

    async def confirmar(self, pedido_id: str) -> Reserva:
        return await self._transicionar(pedido_id, StatusReserva.BAIXADA)

    async def liberar(self, pedido_id: str) -> Reserva:
        return await self._transicionar(pedido_id, StatusReserva.LIBERADA)
