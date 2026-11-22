"""Testes do serviço de Pedidos com Estoque e Pagamentos simulados via httpx.MockTransport."""

import json
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import InMemoryRepository

PRECOS = {"SKU-001": Decimal("79.90"), "SKU-002": Decimal("349.90")}


class Dependencias:
    """Simula os serviços Estoque e Pagamentos e registra as chamadas recebidas."""

    def __init__(self) -> None:
        self.disponivel = {"SKU-001": 10, "SKU-002": 1}
        self.pagamento = "APROVADO"
        self.pagamentos_fora = False
        self.chamadas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        self.chamadas.append(f"{host}{path}")
        if host == "pagamentos":
            if self.pagamentos_fora:
                raise httpx.ConnectError("connection refused", request=request)
            body = json.loads(request.content)
            return httpx.Response(
                201,
                json={
                    "pedido_id": body["pedido_id"],
                    "transacao_id": "tx-1",
                    "status": self.pagamento,
                    "valor": body["valor"],
                    "motivo": None if self.pagamento == "APROVADO" else "limite",
                },
            )
        if path == "/reservas":
            itens = json.loads(request.content)["itens"]
            faltantes = {
                i["sku"]: i["quantidade"] for i in itens if self.disponivel[i["sku"]] < i["quantidade"]
            }
            if faltantes:
                return httpx.Response(
                    409, json={"detail": {"erro": "estoque_insuficiente", "faltantes": faltantes}}
                )
            total = sum(PRECOS[i["sku"]] * i["quantidade"] for i in itens)
            return httpx.Response(201, json={"status": "RESERVADA", "total": str(total), "itens": []})
        return httpx.Response(200, json={"status": "ok"})


@pytest.fixture
def deps():
    return Dependencias()


@pytest.fixture
def client(deps):
    http = httpx.AsyncClient(transport=httpx.MockTransport(deps))
    with TestClient(create_app(InMemoryRepository(), http)) as c:
        yield c


def criar(client, itens=None, chave=None):
    headers = {"Idempotency-Key": chave} if chave else {}
    itens = itens or [{"sku": "SKU-001", "quantidade": 2}]
    return client.post("/pedidos", json={"cliente_id": "cli-1", "itens": itens}, headers=headers)


def test_fluxo_feliz_confirma_pedido(client, deps):
    resp = criar(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "CONFIRMADO"
    assert body["total"] == "159.80"
    assert body["transacao_id"] == "tx-1"
    assert resp.headers["location"] == f"/pedidos/{body['id']}"
    assert deps.chamadas == [
        "estoque/reservas",
        "pagamentos/pagamentos",
        f"estoque/reservas/{body['id']}/confirmar",
    ]


def test_estoque_insuficiente_rejeita_sem_cobrar(client, deps):
    body = criar(client, itens=[{"sku": "SKU-002", "quantidade": 5}]).json()
    assert body["status"] == "REJEITADO"
    assert "SKU-002" in body["motivo"]
    assert not any(c.startswith("pagamentos") for c in deps.chamadas)


def test_pagamento_recusado_compensa_reserva(client, deps):
    deps.pagamento = "RECUSADO"
    body = criar(client).json()
    assert body["status"] == "PAGAMENTO_RECUSADO"
    assert deps.chamadas[-1] == f"estoque/reservas/{body['id']}/liberar"


def test_pagamentos_indisponivel_marca_falha_e_compensa(client, deps):
    deps.pagamentos_fora = True
    body = criar(client).json()
    assert body["status"] == "FALHA"
    assert "pagamento indisponível" in body["motivo"]
    assert deps.chamadas[-1] == f"estoque/reservas/{body['id']}/liberar"


def test_idempotency_key_evita_pedido_duplicado(client, deps):
    primeiro = criar(client, chave="abc-123")
    segundo = criar(client, chave="abc-123")
    assert primeiro.status_code == 201 and segundo.status_code == 200
    assert primeiro.json()["id"] == segundo.json()["id"]
    assert deps.chamadas.count("estoque/reservas") == 1


def test_consulta_e_listagem(client):
    pid = criar(client).json()["id"]
    assert client.get(f"/pedidos/{pid}").json()["status"] == "CONFIRMADO"
    assert [p["id"] for p in client.get("/pedidos", params={"cliente_id": "cli-1"}).json()] == [pid]
    assert client.get("/pedidos/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.get("/pedidos/nao-e-uuid").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"cliente_id": "c", "itens": []},
        {"cliente_id": "", "itens": [{"sku": "A", "quantidade": 1}]},
        {"cliente_id": "c", "itens": [{"sku": "A", "quantidade": 0}]},
    ],
)
def test_validacao(client, payload):
    assert client.post("/pedidos", json=payload).status_code == 422
