from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.provider import ProvedorSimulado


def make_client(**kwargs):
    return TestClient(create_app(ProvedorSimulado(latencia_ms=0, **kwargs)))


def pagar(client, valor="100.00", pedido_id="p1"):
    return client.post("/pagamentos", json={"pedido_id": pedido_id, "cliente_id": "c1", "valor": valor})


def test_aprova_dentro_do_limite():
    resp = pagar(make_client())
    assert resp.status_code == 201
    assert resp.json()["status"] == "APROVADO"


def test_recusa_acima_do_limite():
    body = pagar(make_client(limite_aprovacao=Decimal("50")), valor="51.00").json()
    assert body["status"] == "RECUSADO"
    assert "limite" in body["motivo"]


def test_transacao_e_idempotente_por_pedido():
    client = make_client()
    assert pagar(client).json()["transacao_id"] == pagar(client).json()["transacao_id"]
    assert pagar(client).json()["transacao_id"] != pagar(client, pedido_id="p2").json()["transacao_id"]


def test_falha_do_provedor_vira_502():
    assert pagar(make_client(taxa_falha=1.0)).status_code == 502


@pytest.mark.parametrize("valor", ["0", "-1", "10.123"])
def test_valor_invalido(valor):
    assert pagar(make_client(), valor=valor).status_code == 422
