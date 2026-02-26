"""FastAPI app and API routing structure (base path /api/v1)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.auth import AuthMiddleware
from src.api.config import get_settings
from src.api.rate_limit import RateLimitMiddleware
from src.api.routes import documents
from src.observability.logging import configure_logging
from src.observability.telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    setup_telemetry(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    yield
    # shutdown if needed


app = FastAPI(
    title="Document Upload and RAG API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware: auth sets request.state.owner_id; rate limit uses it
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

# API v1 (base path /api/v1)
app.include_router(documents.router, prefix="/api/v1")
