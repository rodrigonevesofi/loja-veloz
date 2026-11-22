"""Serviço de Pedidos: cria e consulta pedidos, orquestrando Estoque e Pagamentos."""

import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Response

from app.clients import EstoqueClient, PagamentosClient
from app.models import NovoPedido, Pedido
from app.repository import InMemoryRepository, PostgresRepository, Repository
from app.saga import Saga
from veloz_common import create_base_app, env, env_float

SERVICE = "pedidos"


def create_app(repo: Repository | None = None, http: httpx.AsyncClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if repo is not None:
            app.state.repo = repo
        elif env("STORAGE", "postgres") == "memory":
            app.state.repo = InMemoryRepository()
        else:
            pg = PostgresRepository(env("DATABASE_URL", required=True))
            await pg.open()
            app.state.repo = pg
        timeout = env_float("HTTP_TIMEOUT_SECONDS", 3.0)
        # retries=2 só repete falhas de CONEXÃO (seguro); nunca reenvia um POST já recebido.
        client = http or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=1.0),
            transport=httpx.AsyncHTTPTransport(retries=2),
        )
        app.state.saga = Saga(
            app.state.repo,
            EstoqueClient(client, env("ESTOQUE_URL", "http://estoque:8000")),
            PagamentosClient(client, env("PAGAMENTOS_URL", "http://pagamentos:8000")),
        )
        yield
        await client.aclose()
        await app.state.repo.close()

    async def readiness(app: FastAPI) -> bool:
        return await app.state.repo.ping()

    app = create_base_app(SERVICE, readiness=readiness, lifespan=lifespan)

    @app.post("/pedidos", response_model=Pedido, status_code=201)
    async def criar_pedido(
        body: NovoPedido,
        response: Response,
        idempotency_key: str | None = Header(default=None, max_length=128),
    ):
        pedido, criado = await app.state.saga.criar(body, idempotency_key)
        if not criado:
            response.status_code = 200
        response.headers["Location"] = f"/pedidos/{pedido.id}"
        return pedido

    @app.get("/pedidos/{pedido_id}", response_model=Pedido)
    async def obter_pedido(pedido_id: str):
        try:
            uuid.UUID(pedido_id)
        except ValueError:
            raise HTTPException(404, "pedido não encontrado") from None
        pedido = await app.state.repo.obter(pedido_id)
        if pedido is None:
            raise HTTPException(404, "pedido não encontrado")
        return pedido

    @app.get("/pedidos", response_model=list[Pedido])
    async def listar_pedidos(cliente_id: str, limite: int = Query(20, ge=1, le=100)):
        return await app.state.repo.listar(cliente_id, limite)

    return app


app = create_app()
