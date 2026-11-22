from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class StatusReserva(StrEnum):
    RESERVADA = "RESERVADA"
    BAIXADA = "BAIXADA"  # pagamento aprovado: item sai definitivamente do estoque
    LIBERADA = "LIBERADA"  # compensação: itens voltam a ficar disponíveis


class Produto(BaseModel):
    sku: str
    nome: str
    preco: Decimal
    disponivel: int


class ItemSolicitado(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantidade: int = Field(gt=0, le=100)


class NovaReserva(BaseModel):
    pedido_id: str = Field(min_length=1, max_length=64)
    itens: list[ItemSolicitado] = Field(min_length=1, max_length=50)


class ItemReservado(BaseModel):
    sku: str
    nome: str
    quantidade: int
    preco_unitario: Decimal
    subtotal: Decimal


class Reserva(BaseModel):
    pedido_id: str
    status: StatusReserva
    itens: list[ItemReservado]
    total: Decimal


def consolidar(itens: list[ItemSolicitado]) -> dict[str, int]:
    """Soma quantidades de SKUs repetidos e devolve em ordem determinística."""
    total: dict[str, int] = {}
    for item in itens:
        total[item.sku] = total.get(item.sku, 0) + item.quantidade
    return dict(sorted(total.items()))
