"""Tracing distribuído com OpenTelemetry.

A configuração segue as variáveis padrão do SDK (OTEL_EXPORTER_OTLP_ENDPOINT,
OTEL_TRACES_SAMPLER, OTEL_TRACES_SAMPLER_ARG, OTEL_RESOURCE_ATTRIBUTES...), de modo
que o mesmo binário funciona no Compose e no Kubernetes mudando apenas o ambiente.
O contexto é propagado entre serviços pelo header W3C `traceparent`.
"""

import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

log = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, service: str, version: str) -> None:
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):  # o provider global só pode ser definido uma vez
        resource = Resource.create(
            {
                "service.name": os.getenv("OTEL_SERVICE_NAME", service),
                "service.version": version,
                "service.namespace": "loja-veloz",
                "deployment.environment.name": os.getenv("APP_ENV", "local"),
            }
        )
        provider = TracerProvider(resource=resource)  # sampler lido de OTEL_TRACES_SAMPLER
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider, excluded_urls="health/.*,metrics")
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(tracer_provider=provider, enable_commenter=True)
    except ImportError:  # serviços sem banco não instalam o instrumentador
        pass
    log.info("telemetria inicializada", extra={"otlp": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")})
