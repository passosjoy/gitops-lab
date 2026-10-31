"""Camada de observabilidade da Oficina de Lanternagem e Pintura do Rasta.

Stack self-hosted:
  * Métricas  -> prometheus_client (endpoint /metrics)
  * Traces    -> OpenTelemetry SDK -> OTLP HTTP -> Collector -> Tempo
  * Logs      -> JSON no stdout, correlacionado por trace_id/span_id
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import resource
import socket
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from flask import g, request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

try:  # suporte a gunicorn com múltiplos workers
    from prometheus_client import multiprocess as prom_multiprocess
except ImportError:  # pragma: no cover
    prom_multiprocess = None

SERVICE = os.getenv("OTEL_SERVICE_NAME", "oficina-lanternagem-do-rasta")
ENV = os.getenv("APP_ENV", "lab")
VERSION = os.getenv("APP_VERSION", "v1.0.0")
FAULT_MODE = os.getenv("FAULT_MODE", "none").strip().lower()
FAULT_RATE = float(os.getenv("FAULT_RATE", "1.0"))
DB_LATENCY_SECONDS = float(os.getenv("DB_LATENCY_SECONDS", "2.5"))
SLI_LATENCY_THRESHOLD_MS = float(os.getenv("SLI_LATENCY_THRESHOLD_MS", "500"))
LAB_ENABLED = os.getenv("ENABLE_LAB_ENDPOINTS", "false").lower() == "true"
LAB_TOKEN = os.getenv("LAB_TOKEN", "")
POD_NAME = os.getenv("POD_NAME", "")
NODE_NAME = os.getenv("NODE_NAME", "")
OTLP_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "http://otel-collector.observability.svc.cluster.local:4318",
).rstrip("/")

BASE_TAGS = {
    "service": SERVICE,
    "env": ENV,
    "version": VERSION,
}

EXCLUDED_ENDPOINTS = {"metrics", "health", "ready", "live", "static"}
_RESERVED_LOG_KEYS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}

_tracer = trace.get_tracer(__name__)
_tracing_initialized = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname.lower()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": level,
            "status": _level_to_status(level),
            "message": record.getMessage(),
            "logger": record.name,
            "service": SERVICE,
            "env": ENV,
            "version": VERSION,
            "host": socket.gethostname(),
        }

        if POD_NAME:
            payload["pod_name"] = POD_NAME
        if NODE_NAME:
            payload["node_name"] = NODE_NAME

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_KEYS or key.startswith("_"):
                continue
            if key in ("exc_info", "stack_info"):
                continue
            payload[key] = value

        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            payload["trace_id"] = format(span_context.trace_id, "032x")
            payload["span_id"] = format(span_context.span_id, "016x")

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["error.kind"] = exc_type.__name__ if exc_type else "Exception"
            payload["error.message"] = str(exc_value) if exc_value else ""
            payload["error.stack"] = self.formatException(record.exc_info)[:16000]

        return json.dumps(payload, default=str, ensure_ascii=False)


def _level_to_status(level: str) -> str:
    if level in ("critical", "fatal", "error"):
        return "error"
    if level == "warning":
        return "warn"
    if level == "debug":
        return "debug"
    return "info"


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for noisy in ("opentelemetry", "urllib3", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    for name in ("gunicorn.error", "gunicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False


def init_tracing(app=None) -> None:
    """Configura o TracerProvider OTLP e instrumenta o Flask."""
    global _tracing_initialized
    if _tracing_initialized:
        if app is not None:
            FlaskInstrumentor().instrument_app(app)
        return

    resource = Resource.create(
        {
            "service.name": SERVICE,
            "deployment.environment": ENV,
            "service.version": VERSION,
            "service.instance.id": POD_NAME or socket.gethostname(),
        }
    )

    provider = TracerProvider(resource=resource)
    span_endpoint = OTLP_ENDPOINT
    if not span_endpoint.endswith("/v1/traces"):
        span_endpoint = f"{span_endpoint}/v1/traces"
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=span_endpoint, timeout=5))
    )

    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())

    if app is not None:
        FlaskInstrumentor().instrument_app(
            app,
            excluded_urls=os.getenv(
                "OTEL_PYTHON_FLASK_EXCLUDED_URLS", "metrics,health,ready,live"
            ),
        )

    logging.getLogger(__name__).info(
        "OpenTelemetry configurado", extra={"otlp_endpoint": span_endpoint}
    )
    _tracing_initialized = True


def traced(span_name: str) -> Callable:
    """Decorator que cria um span OTel em volta da função."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with _tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Métricas Prometheus
# ---------------------------------------------------------------------------

_metric_lock = threading.Lock()
_metrics: dict[tuple[str, str, tuple[str, ...]], Any] = {}
_DEFAULT_BUCKETS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


def _sanitize_metric_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")


def _tags(extra: dict[str, Any] | None = None) -> dict[str, str]:
    tags = dict(BASE_TAGS)
    for key, value in (extra or {}).items():
        if value is None:
            continue
        tags[str(key)] = str(value).replace(",", "_").replace("\n", "_")[:120]
    return tags


def _metric(kind: str, name: str, tags: dict[str, str]):
    base = _sanitize_metric_name(name)
    if kind == "counter" and not base.endswith("_total"):
        base += "_total"
    if (
        kind == "histogram"
        and "duration" in base
        and not base.endswith(("_seconds", "_milliseconds"))
    ):
        base += "_milliseconds"

    labelnames = tuple(sorted(tags))
    key = (kind, base, labelnames)

    with _metric_lock:
        metric = _metrics.get(key)
        if metric is None:
            if kind == "counter":
                metric = Counter(base, f"{name} (counter)", labelnames)
            elif kind == "gauge":
                metric = Gauge(
                    base,
                    f"{name} (gauge)",
                    labelnames,
                    multiprocess_mode="max",
                )
            else:
                metric = Histogram(
                    base,
                    f"{name} (histogram)",
                    labelnames,
                    buckets=_DEFAULT_BUCKETS,
                )
            _metrics[key] = metric
    return metric, labelnames


def _observe(kind: str, metric: str, value: float, extra_tags=None) -> None:
    tags = _tags(extra_tags)
    try:
        instance, labelnames = _metric(kind, metric, tags)
        labels = instance.labels(*[tags[name] for name in labelnames])
        if kind == "counter":
            labels.inc(value)
        elif kind == "gauge":
            labels.set(value)
        else:
            labels.observe(value)
    except Exception:  # métrica nunca deve derrubar a requisição
        logging.getLogger(__name__).debug(
            "Falha ao registrar métrica %s", metric, exc_info=True
        )


def init_metrics() -> None:
    """Compatibilidade: as métricas são registradas sob demanda."""
    logging.getLogger(__name__).debug("Métricas Prometheus habilitadas em /metrics")


def incr(metric: str, extra_tags: dict[str, Any] | None = None, value: int = 1) -> None:
    _observe("counter", metric, value, extra_tags)


def gauge(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    _observe("gauge", metric, value, extra_tags)


def histogram(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    _observe("histogram", metric, value, extra_tags)


def distribution(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    histogram(metric, value, extra_tags)


def render_metrics() -> bytes:
    """Renderiza /metrics respeitando o modo multiprocess do gunicorn."""
    if os.getenv("PROMETHEUS_MULTIPROC_DIR") and prom_multiprocess is not None:
        registry = CollectorRegistry()
        prom_multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest(REGISTRY)


# ---------------------------------------------------------------------------
# Laboratório (fault injection)
# ---------------------------------------------------------------------------

def fault_active(mode: str) -> bool:
    return FAULT_MODE == mode and random.random() < FAULT_RATE


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def start_background_faults() -> None:
    logger = logging.getLogger(__name__)
    if FAULT_MODE == "memory_leak":
        logger.warning("FAULT_MODE=memory_leak ativo.", extra={"fault_mode": FAULT_MODE})
        threading.Thread(target=_memory_leak, name="lab-memory-leak", daemon=True).start()
    elif FAULT_MODE == "cpu_burn":
        logger.warning("FAULT_MODE=cpu_burn ativo.", extra={"fault_mode": FAULT_MODE})
        threading.Thread(target=_cpu_burn, name="lab-cpu-burn", daemon=True).start()


def _memory_leak() -> None:
    chunks: list[bytes] = []
    while True:
        chunks.append(b"x" * (8 * 1024 * 1024))
        time.sleep(1)
        if len(chunks) % 5 == 0:
            gauge("oficina.fault.rss_mb", rss_mb(), {"fault_mode": FAULT_MODE})


def _cpu_burn() -> None:
    while True:
        acc = 0
        for i in range(2_000_000):
            acc = (acc + i * i) % 1_000_003


# ---------------------------------------------------------------------------
# Hooks Flask
# ---------------------------------------------------------------------------

def before_request() -> None:
    g.request_started_at = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    g.fault_mode = FAULT_MODE


def after_request(response):
    request_id = getattr(g, "request_id", str(uuid.uuid4()))
    response.headers["X-Request-ID"] = request_id

    if request.endpoint in EXCLUDED_ENDPOINTS or request.path.startswith("/lab/"):
        return response

    started = getattr(g, "request_started_at", time.perf_counter())
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    status_class = f"{response.status_code // 100}xx"
    endpoint = request.endpoint or "unknown"
    route = getattr(request.url_rule, "rule", request.path)
    tags = {
        "endpoint": endpoint,
        "route": route,
        "method": request.method,
        "status_class": status_class,
        "fault_mode": FAULT_MODE,
    }

    incr("oficina.http.requests.total", tags)
    histogram("oficina.http.request.duration", duration_ms, {"endpoint": endpoint})
    if response.status_code < 500:
        incr("oficina.http.requests.good", tags)
    else:
        incr("oficina.http.errors", tags)
    if duration_ms <= SLI_LATENCY_THRESHOLD_MS:
        incr("oficina.http.requests.fast", tags)

    level = logging.INFO
    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400:
        level = logging.WARNING

    logging.getLogger("app.access").log(
        level,
        "http_request",
        extra={
            "http.method": request.method,
            "http.route": route,
            "http.path": request.path,
            "http.status_code": response.status_code,
            "duration_ms": duration_ms,
            "request_id": request_id,
            "fault_mode": FAULT_MODE,
        },
    )
    return response


def tag_current_span_error(exc: BaseException) -> None:
    span = trace.get_current_span()
    context = span.get_span_context()
    if context is None or not context.is_valid:
        return
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)[:500]))
    span.set_attribute("error.type", type(exc).__name__)
    span.set_attribute("error.message", str(exc)[:500])
    span.set_attribute("fault_mode", FAULT_MODE)
