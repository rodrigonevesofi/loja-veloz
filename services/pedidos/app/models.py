from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class StatusPedido(StrEnum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    REJEITADO = "REJEITADO"  # estoque insuficiente / produto inexistente
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    FALHA = "FALHA"  # dependência indisponível; reserva compensada


class Item(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantidade: int = Field(gt=0, le=100)


class NovoPedido(BaseModel):
    cliente_id: str = Field(min_length=1, max_length=64)
    itens: list[Item] = Field(min_length=1, max_length=50)


def agora() -> datetime:
    return datetime.now(UTC)


class Pedido(BaseModel):
    id: str
    cliente_id: str
    status: StatusPedido
    itens: list[Item]
    total: Decimal | None = None
    motivo: str | None = None
    transacao_id: str | None = None
    criado_em: datetime = Field(default_factory=agora)
    atualizado_em: datetime = Field(default_factory=agora)
