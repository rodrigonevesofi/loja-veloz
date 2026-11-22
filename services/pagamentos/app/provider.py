"""Adaptador do provedor de pagamentos externo (gateway de cartão/PIX).

No MVP o provedor é simulado, mas com os comportamentos que importam para a
operação: latência variável, falhas intermitentes (HTTP 5xx do provedor) e
recusa por regra de negócio. Isso permite exercitar timeouts, compensação e
alertas sem depender de um sandbox externo. Trocar pelo provedor real significa
implementar outra classe com o mesmo método `autorizar`.
"""

import asyncio
import random
import uuid
from dataclasses import dataclass
from decimal import Decimal

from opentelemetry import trace

tracer = trace.get_tracer(__name__)
NAMESPACE = uuid.UUID("7d0c7a4e-1f5b-4c38-9a59-6f3e1f5f0b11")


class ProvedorIndisponivel(Exception):
    pass


@dataclass(frozen=True)
class Autorizacao:
    aprovado: bool
    transacao_id: str
    motivo: str | None = None


@dataclass
class ProvedorSimulado:
    latencia_ms: int = 150
    taxa_falha: float = 0.0
    limite_aprovacao: Decimal = Decimal("5000")

    async def autorizar(self, pedido_id: str, valor: Decimal) -> Autorizacao:
        with tracer.start_as_current_span("provedor.autorizar") as span:
            span.set_attribute("pagamento.valor", float(valor))
            if self.latencia_ms:
                await asyncio.sleep(random.uniform(0.5, 1.5) * self.latencia_ms / 1000)
            if random.random() < self.taxa_falha:
                span.set_attribute("error", True)
                raise ProvedorIndisponivel("provedor retornou 503")
            # chave de idempotência = pedido_id: retries geram a mesma transação
            transacao = str(uuid.uuid5(NAMESPACE, pedido_id))
            if valor > self.limite_aprovacao:
                return Autorizacao(False, transacao, "limite de crédito excedido")
            return Autorizacao(True, transacao)
