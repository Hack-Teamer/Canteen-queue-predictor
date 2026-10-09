from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from app.api.v1.router import api_router
from app.api.v1.ws import ws_router
from app.core.config import settings
from app.core.exceptions import (
    QueueSenseException,
    generic_exception_handler,
    queuesense_exception_handler,
)
from app.core.logging import logger, request_id_ctx
from app.core.redis import close_redis_client, get_redis_client

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "queuesense_http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "queuesense_http_request_duration_seconds",
    "HTTP Request Latency in Seconds",
    ["method", "endpoint"],
)
PREDICTION_LATENCY = Histogram(
    "queuesense_prediction_latency_seconds",
    "Wait-time prediction latency in seconds",
)
FALLBACK_COUNT = Counter(
    "queuesense_prediction_fallback_total",
    "Count of fallback baseline predictions used",
)
ACTIVE_ORDERS_GAUGE = Gauge(
    "queuesense_active_orders",
    "Current number of active online orders",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} in {settings.ENVIRONMENT} mode")
    try:
        await get_redis_client()
        logger.info("Redis client connected")
    except Exception as e:
        logger.warning(f"Initial Redis connection warning: {e}")

    yield

    # Shutdown
    await close_redis_client()
    logger.info(f"Shutdown {settings.PROJECT_NAME} complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID & Logging Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response: Response = await call_next(request)
        duration = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = req_id

        # Track Prometheus metrics
        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response
    finally:
        request_id_ctx.reset(token)


# Exception Handlers
app.add_exception_handler(QueueSenseException, queuesense_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Mount Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix="/ws", tags=["websockets"])


# Prometheus metrics endpoint
@app.get(settings.PROMETHEUS_METRICS_PATH, include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
