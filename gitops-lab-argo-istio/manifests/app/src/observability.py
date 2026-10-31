"""Camada de observabilidade da Oficina de Lanternagem e Pintura do Rasta."""

from __future__ import annotations

import json
import logging
import os
import random
import resource
import socket
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from datadog.dogstatsd.base import DogStatsd
from ddtrace import tracer
from flask import g, request

SERVICE = os.getenv("DD_SERVICE", "oficina-lanternagem-do-rasta")
ENV = os.getenv("DD_ENV", "lab")
VERSION = os.getenv("DD_VERSION", "v1.0.0")
FAULT_MODE = os.getenv("FAULT_MODE", "none").strip().lower()
FAULT_RATE = float(os.getenv("FAULT_RATE", "1.0"))
DB_LATENCY_SECONDS = float(os.getenv("DB_LATENCY_SECONDS", "2.5"))
SLI_LATENCY_THRESHOLD_MS = float(os.getenv("SLI_LATENCY_THRESHOLD_MS", "500"))
LAB_ENABLED = os.getenv("ENABLE_LAB_ENDPOINTS", "false").lower() == "true"
LAB_TOKEN = os.getenv("LAB_TOKEN", "")
POD_NAME = os.getenv("POD_NAME", "")
NODE_NAME = os.getenv("NODE_NAME", "")

BASE_TAGS = [
    f"service:{SERVICE}",
    f"env:{ENV}",
    f"version:{VERSION}",
]

EXCLUDED_ENDPOINTS = {"metrics", "health", "ready", "live", "static"}
_TRACE_ID_KEYS = ("dd.trace_id", "dd.span_id")
_RESERVED_LOG_KEYS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}


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
            if key in ("dd", "exc_info", "stack_info"):
                continue
            payload[key] = value

        dd = getattr(record, "dd", None)
        trace_id = getattr(dd, "trace_id", None)
        span_id = getattr(dd, "span_id", None)
        if trace_id is None or span_id is None:
            span = tracer.current_span()
            if span is not None:
                trace_id = trace_id or span.trace_id
                span_id = span_id or span.span_id
        if trace_id:
            payload["dd.trace_id"] = str(trace_id)
        if span_id:
            payload["dd.span_id"] = str(span_id)

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

    for noisy in ("ddtrace", "datadog", "urllib3", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    for name in ("gunicorn.error", "gunicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False


_statsd: DogStatsd | None = None


def init_metrics() -> None:
    global _statsd
    host = os.getenv("DD_AGENT_HOST", "localhost")
    port = int(os.getenv("DD_DOGSTATSD_PORT", "8125"))
    try:
        _statsd = DogStatsd(host=host, port=port, use_default_route=False)
    except Exception:
        _statsd = None
        logging.getLogger(__name__).warning(
            "Falha ao inicializar DogStatsD; métricas customizadas serão perdidas.",
            exc_info=True,
        )


def _tags(extra: dict[str, Any] | None = None) -> list[str]:
    tags = list(BASE_TAGS)
    for key, value in (extra or {}).items():
        if value is None:
            continue
        safe = str(value).replace(",", "_").replace("\n", "_")[:120]
        tags.append(f"{key}:{safe}")
    return tags


def incr(metric: str, extra_tags: dict[str, Any] | None = None, value: int = 1) -> None:
    if _statsd is not None:
        _statsd.increment(metric, value=value, tags=_tags(extra_tags))


def gauge(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    if _statsd is not None:
        _statsd.gauge(metric, value, tags=_tags(extra_tags))


def histogram(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    if _statsd is not None:
        _statsd.histogram(metric, value, tags=_tags(extra_tags))


def distribution(metric: str, value: float, extra_tags: dict[str, Any] | None = None) -> None:
    if _statsd is not None:
        try:
            _statsd.distribution(metric, value, tags=_tags(extra_tags))
        except Exception:
            histogram(metric, value, extra_tags)


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
            rss = rss_mb()
            gauge("oficina.fault.rss_mb", rss, {"fault_mode": FAULT_MODE})


def _cpu_burn() -> None:
    while True:
        acc = 0
        for i in range(2_000_000):
            acc = (acc + i * i) % 1_000_003


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
    span = tracer.current_span()
    if span is None:
        return
    span.error = 1
    span.set_tag("error.type", type(exc).__name__)
    span.set_tag("error.message", str(exc)[:500])
    span.set_tag("error.stack", "".join(traceback.format_exception(exc))[:16000])
    span.set_tag("fault_mode", FAULT_MODE)
