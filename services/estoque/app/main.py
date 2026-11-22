"""Serviço de Estoque: catálogo, reserva, baixa e liberação de itens."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_client import Counter

from app.models import NovaReserva, Produto, Reserva, consolidar
from app.repository import (
    EstoqueInsuficiente,
    InMemoryRepository,
    PostgresRepository,
    ProdutoNaoEncontrado,
    Repository,
    ReservaNaoEncontrada,
    TransicaoInvalida,
)
from veloz_common import create_base_app, env

SERVICE = "estoque"
log = logging.getLogger(SERVICE)

RESERVAS = Counter("estoque_reservas_total", "Reservas de estoque por resultado", ["resultado"])


def create_app(repo: Repository | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if repo is not None:
            app.state.repo = repo
        elif env("STORAGE", "postgres") == "memory":
            app.state.repo = InMemoryRepository()
        else:
            pg = PostgresRepository(env("DATABASE_URL", required=True))
            await pg.open(seed=env("SEED_CATALOG", "true") == "true")
            app.state.repo = pg
        yield
        await app.state.repo.close()

    async def readiness(app: FastAPI) -> bool:
        return await app.state.repo.ping()

    app = create_base_app(SERVICE, readiness=readiness, lifespan=lifespan)

    def r() -> Repository:
        return app.state.repo

    @app.get("/produtos", response_model=list[Produto])
    async def listar_produtos():
        return await r().listar_produtos()

    @app.get("/produtos/{sku}", response_model=Produto)
    async def obter_produto(sku: str):
        try:
            return await r().obter_produto(sku)
        except ProdutoNaoEncontrado:
            raise HTTPException(404, f"produto {sku} não encontrado") from None

    @app.post("/reservas", response_model=Reserva, status_code=201)
    async def reservar(body: NovaReserva):
        try:
            reserva = await r().reservar(body.pedido_id, consolidar(body.itens))
        except ProdutoNaoEncontrado as e:
            RESERVAS.labels("produto_inexistente").inc()
            raise HTTPException(404, f"produto {e} não encontrado") from None
        except EstoqueInsuficiente as e:
            RESERVAS.labels("insuficiente").inc()
            raise HTTPException(409, {"erro": "estoque_insuficiente", "faltantes": e.faltantes}) from None
        RESERVAS.labels("reservado").inc()
        log.info("reserva criada", extra={"pedido_id": body.pedido_id, "total": str(reserva.total)})
        return reserva

    @app.post("/reservas/{pedido_id}/confirmar", response_model=Reserva)
    async def confirmar(pedido_id: str):
        return await _transicao(r().confirmar, pedido_id, "baixado")

    @app.post("/reservas/{pedido_id}/liberar", response_model=Reserva)
    async def liberar(pedido_id: str):
        return await _transicao(r().liberar, pedido_id, "liberado")

    async def _transicao(fn, pedido_id: str, rotulo: str) -> Reserva:
        try:
            reserva = await fn(pedido_id)
        except ReservaNaoEncontrada:
            raise HTTPException(404, f"reserva do pedido {pedido_id} não encontrada") from None
        except TransicaoInvalida as e:
            raise HTTPException(409, str(e)) from None
        RESERVAS.labels(rotulo).inc()
        return reserva

    return app


app = create_app()
