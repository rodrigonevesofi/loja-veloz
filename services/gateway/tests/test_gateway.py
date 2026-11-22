import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


class Upstream:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.falha: Exception | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.falha:
            raise self.falha
        if request.method == "POST":
            return httpx.Response(201, json={"id": "p1"}, headers={"location": "/pedidos/p1"})
        return httpx.Response(200, json={"ok": True, "path": request.url.path})


@pytest.fixture
def upstream():
    return Upstream()


@pytest.fixture
def client(upstream):
    with TestClient(create_app(httpx.AsyncClient(transport=httpx.MockTransport(upstream)))) as c:
        yield c


def test_roteia_produtos_para_estoque(client, upstream):
    resp = client.get("/api/produtos/SKU-001")
    assert resp.status_code == 200
    req = upstream.requests[0]
    assert (req.url.host, req.url.path) == ("estoque", "/produtos/SKU-001")


def test_repasse_de_query_headers_e_location(client, upstream):
    resp = client.post(
        "/api/pedidos", json={"x": 1}, headers={"Idempotency-Key": "k1", "Cookie": "segredo=1"}
    )
    assert resp.status_code == 201
    assert resp.headers["location"] == "/api/pedidos/p1"
    req = upstream.requests[0]
    assert req.headers["idempotency-key"] == "k1"
    assert "cookie" not in req.headers  # só headers da allowlist chegam ao serviço interno
    assert req.headers["x-request-id"] == resp.headers["x-request-id"]
    client.get("/api/pedidos", params={"cliente_id": "c1"})
    assert upstream.requests[1].url.params["cliente_id"] == "c1"


def test_recurso_desconhecido(client):
    assert client.get("/api/admin").status_code == 404


@pytest.mark.parametrize(
    ("erro", "status"),
    [(httpx.ReadTimeout("t"), 504), (httpx.ConnectError("c"), 503)],
)
def test_falhas_do_upstream(client, upstream, erro, status):
    upstream.falha = erro
    assert client.get("/api/produtos").status_code == status
