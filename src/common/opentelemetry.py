import logging
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor  # type: ignore
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore

logger = logging.getLogger(__name__)


def setup_opentelemetry(service_name: str, app: FastAPI) -> None:
    logger.info("Setting up instrumentation...")

    resource = Resource(attributes={SERVICE_NAME: service_name})
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(exporter)
    trace_provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)  # type: ignore
    logger.info("FastAPI Instrumentation enabled.")

    OpenAIInstrumentor().instrument()
    logger.info("OpenAI Instrumentation enabled.")
