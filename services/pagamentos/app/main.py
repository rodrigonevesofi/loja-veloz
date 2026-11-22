"""Serviço de Pagamentos: autoriza a cobrança de um pedido no provedor externo.

É stateless (12-Factor, fator VI): não guarda estado entre requisições, então
escala horizontalmente sem coordenação. A idempotência é garantida pela chave
`pedido_id` repassada ao provedor.
"""

import logging
from decimal import Decimal
from enum import StrEnum

from fastapi import FastAPI, HTTPException
from prometheus_client import Counter
from pydantic import BaseModel, Field

from app.provider import ProvedorIndisponivel, ProvedorSimulado
from veloz_common import create_base_app, env_float, env_int

SERVICE = "pagamentos"
log = logging.getLogger(SERVICE)
PAGAMENTOS = Counter("pagamentos_total", "Pagamentos por resultado", ["resultado"])


class StatusPagamento(StrEnum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class NovoPagamento(BaseModel):
    pedido_id: str = Field(min_length=1, max_length=64)
    cliente_id: str = Field(min_length=1, max_length=64)
    valor: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class Pagamento(BaseModel):
    pedido_id: str
    transacao_id: str
    status: StatusPagamento
    valor: Decimal
    motivo: str | None = None


def create_app(provedor: ProvedorSimulado | None = None) -> FastAPI:
    app = create_base_app(SERVICE)
    app.state.provedor = provedor or ProvedorSimulado(
        latencia_ms=env_int("PAYMENT_PROVIDER_LATENCY_MS", 150),
        taxa_falha=env_float("PAYMENT_PROVIDER_FAILURE_RATE", 0.0),
        limite_aprovacao=Decimal(str(env_float("PAYMENT_APPROVAL_LIMIT", 5000))),
    )

    @app.post("/pagamentos", response_model=Pagamento, status_code=201)
    async def cobrar(body: NovoPagamento):
        try:
            aut = await app.state.provedor.autorizar(body.pedido_id, body.valor)
        except ProvedorIndisponivel:
            PAGAMENTOS.labels("erro_provedor").inc()
            log.warning("provedor indisponível", extra={"pedido_id": body.pedido_id})
            raise HTTPException(502, "provedor de pagamento indisponível") from None
        status = StatusPagamento.APROVADO if aut.aprovado else StatusPagamento.RECUSADO
        PAGAMENTOS.labels(status.value.lower()).inc()
        log.info("pagamento processado", extra={"pedido_id": body.pedido_id, "status": status})
        return Pagamento(
            pedido_id=body.pedido_id,
            transacao_id=aut.transacao_id,
            status=status,
            valor=body.valor,
            motivo=aut.motivo,
        )

    return app


app = create_app()
