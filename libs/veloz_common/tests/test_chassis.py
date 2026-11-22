import json
import logging

from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider

from veloz_common import create_base_app
from veloz_common.logging import JsonFormatter


async def nunca_pronto(_app) -> bool:
    return False


def test_health_ready_reflete_dependencias():
    app = create_base_app("teste", readiness=nunca_pronto)
    with TestClient(app) as c:
        assert c.get("/health/live").status_code == 200
        assert c.get("/health/ready").status_code == 503


def test_request_id_e_propagado():
    app = create_base_app("teste")
    with TestClient(app) as c:
        assert c.get("/health/live", headers={"x-request-id": "abc"}).headers["x-request-id"] == "abc"
        assert len(c.get("/health/live").headers["x-request-id"]) == 32


def test_log_json_com_trace_id(monkeypatch):
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)  # o CI desliga o SDK por padrão
    tracer = TracerProvider().get_tracer("t")
    record = logging.makeLogRecord({"msg": "oi", "levelname": "INFO", "name": "x", "pedido_id": "p1"})
    with tracer.start_as_current_span("span"):
        linha = json.loads(JsonFormatter("teste").format(record))
    assert linha["service"] == "teste"
    assert linha["pedido_id"] == "p1"
    assert len(linha["trace_id"]) == 32
