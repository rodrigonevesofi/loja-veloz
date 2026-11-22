"""Fábrica de aplicação FastAPI com observabilidade e health checks embutidos."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from veloz_common.config import env
from veloz_common.logging import configure_logging
from veloz_common.metrics import HTTP_IN_FLIGHT, HTTP_LATENCY, HTTP_REQUESTS, render_latest
from veloz_common.telemetry import setup_telemetry

ReadinessCheck = Callable[[FastAPI], Awaitable[bool]]


def create_base_app(
    service: str,
    *,
    readiness: ReadinessCheck | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    version = env("APP_VERSION", "dev")
    configure_logging(service, env("LOG_LEVEL", "INFO"))
    log = logging.getLogger(service)

    app = FastAPI(title=f"Loja Veloz - {service}", version=version, lifespan=lifespan)
    app.state.service = service

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        HTTP_IN_FLIGHT.labels(service).inc()
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - start
            HTTP_IN_FLIGHT.labels(service).dec()
            route = getattr(request.scope.get("route"), "path", "unmatched")
            if not route.startswith(("/health", "/metrics")):
                HTTP_REQUESTS.labels(service, request.method, route, str(status)).inc()
                HTTP_LATENCY.labels(service, request.method, route).observe(elapsed)
                log.info(
                    "request",
                    extra={
                        "method": request.method,
                        "route": route,
                        "status": status,
                        "duration_ms": round(elapsed * 1000, 2),
                        "request_id": request_id,
                    },
                )

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict:
        # Liveness só verifica o próprio processo: dependências NUNCA entram aqui,
        # senão uma queda do banco reiniciaria todos os pods em cascata.
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> Response:
        ok = True
        if readiness is not None:
            try:
                ok = await readiness(app)
            except Exception:  # noqa: BLE001
                log.exception("readiness falhou")
                ok = False
        return JSONResponse({"status": "ok" if ok else "unavailable"}, status_code=200 if ok else 503)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        body, content_type = render_latest()
        return Response(body, media_type=content_type)

    setup_telemetry(app, service, version)
    return app
