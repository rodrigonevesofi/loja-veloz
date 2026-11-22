import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import InMemoryRepository


@pytest.fixture
def client():
    with TestClient(create_app(InMemoryRepository())) as c:
        yield c


def reservar(client, pedido_id="p1", itens=None):
    itens = itens or [{"sku": "SKU-001", "quantidade": 2}]
    return client.post("/reservas", json={"pedido_id": pedido_id, "itens": itens})


def disponivel(client, sku="SKU-001"):
    return client.get(f"/produtos/{sku}").json()["disponivel"]


def test_health_e_metricas(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json() == {"status": "ok"}
    client.get("/produtos")
    linhas = [
        line
        for line in client.get("/metrics").text.splitlines()
        if line.startswith("http_requests_total{") and 'route="/produtos"' in line
    ]
    assert linhas and 'service="estoque"' in linhas[0] and 'status="200"' in linhas[0]


def test_lista_catalogo(client):
    produtos = client.get("/produtos").json()
    assert len(produtos) == 5
    assert produtos[0]["sku"] == "SKU-001"


def test_reserva_debita_estoque_e_calcula_total(client):
    antes = disponivel(client)
    resp = reservar(client, itens=[{"sku": "SKU-001", "quantidade": 1}, {"sku": "SKU-001", "quantidade": 1}])
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "RESERVADA"
    assert body["itens"][0]["quantidade"] == 2  # SKUs repetidos são consolidados
    assert body["total"] == "159.80"
    assert disponivel(client) == antes - 2


def test_reserva_e_idempotente(client):
    antes = disponivel(client)
    reservar(client)
    reservar(client)
    assert disponivel(client) == antes - 2


def test_estoque_insuficiente_retorna_409(client):
    resp = reservar(client, itens=[{"sku": "SKU-005", "quantidade": 51}])
    assert resp.status_code == 409
    assert resp.json()["detail"]["faltantes"] == {"SKU-005": 51}


def test_produto_inexistente_retorna_404(client):
    assert reservar(client, itens=[{"sku": "NAO-EXISTE", "quantidade": 1}]).status_code == 404


def test_liberar_devolve_itens(client):
    antes = disponivel(client)
    reservar(client)
    resp = client.post("/reservas/p1/liberar")
    assert resp.json()["status"] == "LIBERADA"
    assert disponivel(client) == antes
    # idempotente
    assert client.post("/reservas/p1/liberar").status_code == 200
    assert disponivel(client) == antes


def test_confirmar_e_depois_liberar_e_invalido(client):
    reservar(client)
    assert client.post("/reservas/p1/confirmar").json()["status"] == "BAIXADA"
    assert client.post("/reservas/p1/liberar").status_code == 409


def test_validacao_de_entrada(client):
    assert reservar(client, itens=[{"sku": "SKU-001", "quantidade": 0}]).status_code == 422
    assert client.post("/reservas/xyz/confirmar").status_code == 404
