"""API Gateway: ponto único de entrada HTTP.

Responsabilidades: roteamento por prefixo (/api/<recurso>), timeout por rota,
propagação de X-Request-ID/traceparent e isolamento dos serviços internos (que não
são expostos fora do cluster). Autenticação e rate limiting ficam no Ingress/mesh.
"""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from veloz_common import create_base_app, env, env_float

SERVICE = "gateway"
log = logging.getLogger(SERVICE)

# headers repassados ao serviço interno (o traceparent é injetado pelo OpenTelemetry)
FORWARD_HEADERS = ("content-type", "accept", "idempotency-key", "authorization")
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


def rotas() -> dict[str, str]:
    """recurso público -> URL base do serviço interno (configurável por ambiente)."""
    pedidos = env("PEDIDOS_URL", "http://pedidos:8000")
    estoque = env("ESTOQUE_URL", "http://estoque:8000")
    return {"pedidos": f"{pedidos}/pedidos", "produtos": f"{estoque}/produtos"}


def create_app(http: httpx.AsyncClient | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = http or httpx.AsyncClient(
            timeout=httpx.Timeout(env_float("HTTP_TIMEOUT_SECONDS", 10.0), connect=1.0),
            transport=httpx.AsyncHTTPTransport(retries=2),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
        app.state.http = client
        yield
        await client.aclose()

    app = create_base_app(SERVICE, lifespan=lifespan)
    app.state.rotas = rotas()

    @app.get("/")
    async def index() -> dict:
        return {"servico": "Loja Veloz API Gateway", "recursos": sorted(app.state.rotas)}

    @app.api_route("/api/{recurso}", methods=METHODS)
    @app.api_route("/api/{recurso}/{resto:path}", methods=METHODS)
    async def proxy(recurso: str, request: Request, resto: str = "") -> Response:
        base = app.state.rotas.get(recurso)
        if base is None:
            return JSONResponse({"detail": f"recurso '{recurso}' não existe"}, status_code=404)
        url = f"{base}/{resto}" if resto else base
        headers = {k: v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS}
        headers["x-request-id"] = request.state.request_id
        try:
            upstream = await app.state.http.request(
                request.method,
                url,
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
        except httpx.TimeoutException:
            log.warning("timeout no upstream", extra={"upstream": recurso})
            return JSONResponse({"detail": "serviço demorou para responder"}, status_code=504)
        except httpx.HTTPError as e:
            log.warning("upstream indisponível", extra={"upstream": recurso, "erro": str(e)})
            return JSONResponse({"detail": "serviço indisponível"}, status_code=503)
        passthrough = {k: v for k, v in upstream.headers.items() if k.lower() in ("content-type", "location")}
        if "location" in passthrough:
            passthrough["location"] = f"/api{passthrough['location']}"
        return Response(upstream.content, status_code=upstream.status_code, headers=passthrough)

    return app


app = create_app()
