"""Saga orquestrada de criação de pedido.

    PENDENTE -> reservar estoque -> cobrar pagamento -> baixar estoque -> CONFIRMADO
                     |                    |
                     |                    +-- recusado/erro -> liberar estoque (compensação)
                     +-- insuficiente -> REJEITADO

Sem transação distribuída (2PC): cada passo é local ao serviço dono do dado e
falhas são desfeitas por ações compensatórias idempotentes.
"""

import logging
from decimal import Decimal
from uuid import uuid4

from opentelemetry import trace
from prometheus_client import Counter, Histogram

from app.clients import (
    DependenciaIndisponivel,
    EstoqueClient,
    EstoqueInsuficiente,
    PagamentosClient,
    ProdutoInexistente,
)
from app.models import NovoPedido, Pedido, StatusPedido
from app.repository import Repository

log = logging.getLogger("pedidos.saga")
tracer = trace.get_tracer(__name__)

PEDIDOS = Counter("pedidos_total", "Pedidos finalizados por status", ["status"])
RECEITA = Counter("pedidos_receita_reais_total", "Valor de pedidos confirmados (R$)")
SAGA_DURACAO = Histogram(
    "pedidos_saga_duration_seconds",
    "Duração da saga de criação de pedido",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)


class Saga:
    def __init__(self, repo: Repository, estoque: EstoqueClient, pagamentos: PagamentosClient):
        self.repo, self.estoque, self.pagamentos = repo, estoque, pagamentos

    async def criar(self, req: NovoPedido, chave: str | None) -> tuple[Pedido, bool]:
        """Retorna (pedido, criado_agora). Reenvios com a mesma Idempotency-Key não duplicam."""
        if chave and (existente := await self.repo.por_chave(chave)):
            return existente, False
        pedido = Pedido(
            id=str(uuid4()), cliente_id=req.cliente_id, status=StatusPedido.PENDENTE, itens=req.itens
        )
        if await self.repo.inserir(pedido, chave) is None:  # corrida entre dois reenvios
            return await self.repo.por_chave(chave), False

        with SAGA_DURACAO.time(), tracer.start_as_current_span("saga.criar_pedido") as span:
            span.set_attribute("pedido.id", pedido.id)
            final = await self._executar(pedido)
            span.set_attribute("pedido.status", final.status.value)
        PEDIDOS.labels(final.status.value).inc()
        if final.status == StatusPedido.CONFIRMADO and final.total:
            RECEITA.inc(float(final.total))
        log.info("pedido finalizado", extra={"pedido_id": final.id, "status": final.status.value})
        return final, True

    async def _executar(self, p: Pedido) -> Pedido:
        try:
            reserva = await self.estoque.reservar(p.id, p.itens)
        except EstoqueInsuficiente as e:
            return await self._fim(p, StatusPedido.REJEITADO, motivo=f"estoque insuficiente: {e.faltantes}")
        except ProdutoInexistente as e:
            return await self._fim(p, StatusPedido.REJEITADO, motivo=f"produto inexistente: {e}")
        except DependenciaIndisponivel as e:
            await self._compensar(p.id)  # a reserva pode ter sido gravada antes do timeout
            return await self._fim(p, StatusPedido.FALHA, motivo=f"estoque indisponível ({e})")

        total = Decimal(str(reserva["total"]))
        try:
            pag = await self.pagamentos.cobrar(p.id, p.cliente_id, total)
        except DependenciaIndisponivel as e:
            await self._compensar(p.id)
            return await self._fim(p, StatusPedido.FALHA, total=total, motivo=f"pagamento indisponível ({e})")

        if pag["status"] != "APROVADO":
            await self._compensar(p.id)
            return await self._fim(
                p,
                StatusPedido.PAGAMENTO_RECUSADO,
                total=total,
                motivo=pag.get("motivo"),
                transacao_id=pag["transacao_id"],
            )

        try:
            await self.estoque.confirmar(p.id)
        except DependenciaIndisponivel:
            # pagamento já aprovado: o pedido é confirmado e a baixa fica pendente
            # para reconciliação (a reserva continua segurando o item).
            log.error("baixa de estoque pendente", extra={"pedido_id": p.id})
        return await self._fim(p, StatusPedido.CONFIRMADO, total=total, transacao_id=pag["transacao_id"])

    async def _compensar(self, pedido_id: str) -> None:
        with tracer.start_as_current_span("saga.compensar"):
            try:
                await self.estoque.liberar(pedido_id)
            except Exception:  # noqa: BLE001 - compensação é best-effort, reconciliação cobre o resto
                log.exception("falha ao liberar reserva", extra={"pedido_id": pedido_id})

    async def _fim(self, p: Pedido, status: StatusPedido, **campos) -> Pedido:
        return await self.repo.atualizar(p.id, status, **campos)
