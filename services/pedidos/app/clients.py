"""Clientes HTTP para Estoque e Pagamentos.

O httpx é instrumentado pelo OpenTelemetry, então cada chamada vira um span filho
e o header `traceparent` é injetado automaticamente (tracing distribuído).
"""

from decimal import Decimal

import httpx

from app.models import Item


class DependenciaIndisponivel(Exception):
    """Timeout, erro de conexão ou 5xx de um serviço dependente."""


class EstoqueInsuficiente(Exception):
    def __init__(self, faltantes: dict[str, int]) -> None:
        super().__init__(f"estoque insuficiente: {faltantes}")
        self.faltantes = faltantes


class ProdutoInexistente(Exception):
    pass


async def _post(http: httpx.AsyncClient, url: str, json: dict | None = None) -> httpx.Response:
    try:
        resp = await http.post(url, json=json)
    except httpx.HTTPError as e:
        raise DependenciaIndisponivel(f"{url}: {e.__class__.__name__}") from e
    if resp.status_code >= 500:
        raise DependenciaIndisponivel(f"{url}: HTTP {resp.status_code}")
    return resp


class EstoqueClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self.http, self.base = http, base_url.rstrip("/")

    async def reservar(self, pedido_id: str, itens: list[Item]) -> dict:
        resp = await _post(
            self.http,
            f"{self.base}/reservas",
            {"pedido_id": pedido_id, "itens": [i.model_dump() for i in itens]},
        )
        if resp.status_code == 409:
            raise EstoqueInsuficiente(resp.json()["detail"].get("faltantes", {}))
        if resp.status_code == 404:
            raise ProdutoInexistente(resp.json().get("detail"))
        resp.raise_for_status()
        return resp.json()

    async def confirmar(self, pedido_id: str) -> None:
        (await _post(self.http, f"{self.base}/reservas/{pedido_id}/confirmar")).raise_for_status()

    async def liberar(self, pedido_id: str) -> None:
        resp = await _post(self.http, f"{self.base}/reservas/{pedido_id}/liberar")
        if resp.status_code != 404:  # nada reservado = nada a compensar
            resp.raise_for_status()


class PagamentosClient:
    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self.http, self.base = http, base_url.rstrip("/")

    async def cobrar(self, pedido_id: str, cliente_id: str, valor: Decimal) -> dict:
        resp = await _post(
            self.http,
            f"{self.base}/pagamentos",
            {"pedido_id": pedido_id, "cliente_id": cliente_id, "valor": str(valor)},
        )
        resp.raise_for_status()
        return resp.json()
