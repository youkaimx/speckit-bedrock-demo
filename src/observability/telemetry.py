"""OpenTelemetry: metrics, traces, OTLP export."""

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(
    service_name: str = "document-rag-api",
    otlp_endpoint: str | None = None,
) -> None:
    """Configure OpenTelemetry tracer; OTLP export if endpoint set."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otlp_endpoint)
            exporter = OTLPSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            pass
    trace.set_tracer_provider(provider)
