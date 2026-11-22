"""Persistência de pedidos (database-per-service: só este serviço acessa o banco `pedidos`)."""

import asyncio
from decimal import Decimal
from typing import Protocol

from app.models import Item, Pedido, StatusPedido, agora


class Repository(Protocol):
    async def ping(self) -> bool: ...
    async def inserir(self, pedido: Pedido, chave: str | None) -> Pedido | None: ...
    async def por_chave(self, chave: str) -> Pedido | None: ...
    async def obter(self, pedido_id: str) -> Pedido | None: ...
    async def listar(self, cliente_id: str, limite: int) -> list[Pedido]: ...
    async def atualizar(
        self,
        pedido_id: str,
        status: StatusPedido,
        *,
        total: Decimal | None = None,
        motivo: str | None = None,
        transacao_id: str | None = None,
    ) -> Pedido: ...
    async def close(self) -> None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self._pedidos: dict[str, Pedido] = {}
        self._chaves: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def ping(self) -> bool:
        return True

    async def inserir(self, pedido: Pedido, chave: str | None) -> Pedido | None:
        async with self._lock:
            if chave and chave in self._chaves:
                return None
            self._pedidos[pedido.id] = pedido.model_copy()
            if chave:
                self._chaves[chave] = pedido.id
            return pedido

    async def por_chave(self, chave: str) -> Pedido | None:
        pid = self._chaves.get(chave)
        return await self.obter(pid) if pid else None

    async def obter(self, pedido_id: str) -> Pedido | None:
        p = self._pedidos.get(pedido_id)
        return p.model_copy() if p else None

    async def listar(self, cliente_id: str, limite: int) -> list[Pedido]:
        itens = [p for p in self._pedidos.values() if p.cliente_id == cliente_id]
        return sorted(itens, key=lambda p: p.criado_em, reverse=True)[:limite]

    async def atualizar(self, pedido_id, status, *, total=None, motivo=None, transacao_id=None):
        async with self._lock:
            p = self._pedidos[pedido_id]
            p.status = status
            p.total = total if total is not None else p.total
            p.motivo = motivo
            p.transacao_id = transacao_id or p.transacao_id
            p.atualizado_em = agora()
            return p.model_copy()

    async def close(self) -> None:
        return None


SCHEMA = """
CREATE TABLE IF NOT EXISTS pedidos (
    id               UUID PRIMARY KEY,
    cliente_id       TEXT NOT NULL,
    status           TEXT NOT NULL,
    itens            JSONB NOT NULL,
    total            NUMERIC(12, 2),
    motivo           TEXT,
    transacao_id     TEXT,
    idempotency_key  TEXT UNIQUE,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos (cliente_id, criado_em DESC);
"""

_COLS = "id::text, cliente_id, status, itens, total, motivo, transacao_id, criado_em, atualizado_em"


def _row(r) -> Pedido:
    return Pedido(
        id=r[0],
        cliente_id=r[1],
        status=StatusPedido(r[2]),
        itens=[Item(**i) for i in r[3]],
        total=r[4],
        motivo=r[5],
        transacao_id=r[6],
        criado_em=r[7],
        atualizado_em=r[8],
    )


class PostgresRepository:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        from psycopg_pool import AsyncConnectionPool

        self._pool = AsyncConnectionPool(dsn, min_size=min_size, max_size=max_size, open=False)

    async def open(self) -> None:
        await self._pool.open(wait=True, timeout=30)
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(4202)")
            await conn.execute(SCHEMA)

    async def close(self) -> None:
        await self._pool.close()

    async def ping(self) -> bool:
        async with self._pool.connection(timeout=2) as conn:
            await conn.execute("SELECT 1")
        return True

    async def inserir(self, pedido: Pedido, chave: str | None) -> Pedido | None:
        from psycopg.types.json import Jsonb

        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO pedidos (id, cliente_id, status, itens, idempotency_key)"
                " VALUES (%s, %s, %s, %s, %s) ON CONFLICT (idempotency_key) DO NOTHING"
                f" RETURNING {_COLS}",
                (
                    pedido.id,
                    pedido.cliente_id,
                    pedido.status.value,
                    Jsonb([i.model_dump() for i in pedido.itens]),
                    chave,
                ),
            )
            row = await cur.fetchone()
        return _row(row) if row else None

    async def _one(self, where: str, arg) -> Pedido | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM pedidos WHERE {where}", (arg,))
            row = await cur.fetchone()
        return _row(row) if row else None

    async def por_chave(self, chave: str) -> Pedido | None:
        return await self._one("idempotency_key = %s", chave)

    async def obter(self, pedido_id: str) -> Pedido | None:
        return await self._one("id = %s", pedido_id)

    async def listar(self, cliente_id: str, limite: int) -> list[Pedido]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM pedidos WHERE cliente_id = %s ORDER BY criado_em DESC LIMIT %s",
                (cliente_id, limite),
            )
            return [_row(r) for r in await cur.fetchall()]

    async def atualizar(self, pedido_id, status, *, total=None, motivo=None, transacao_id=None):
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE pedidos SET status = %s, total = COALESCE(%s, total), motivo = %s,"
                " transacao_id = COALESCE(%s, transacao_id), atualizado_em = now()"
                f" WHERE id = %s RETURNING {_COLS}",
                (status.value, total, motivo, transacao_id, pedido_id),
            )
            return _row(await cur.fetchone())
