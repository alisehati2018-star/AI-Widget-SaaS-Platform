"""Observability (Phase F): a tiny in-process metrics registry + OTel tracing.

Dependency-free metrics: counters + latency summaries rendered in the Prometheus
text exposition format at ``/metrics``. Tracing uses the OpenTelemetry SDK
(already a dependency); the OTLP exporter is import-guarded so the absence of the
exporter package (or a collector) never breaks startup.
"""

from __future__ import annotations

import threading
from collections import defaultdict

from .logging import get_logger

log = get_logger("obs")

_VERSION = "0.1.0"


def _labels_key(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(labels.items()))


class Metrics:
    """Minimal Prometheus-compatible registry (counters + latency summaries)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        # name -> labelset -> (sum, count)
        self._summaries: dict[str, dict[tuple, list[float]]] = defaultdict(
            lambda: defaultdict(lambda: [0.0, 0.0])
        )

    def inc(self, name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name][_labels_key(labels or {})] += value

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._gauges[name][_labels_key(labels or {})] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            cell = self._summaries[name][_labels_key(labels or {})]
            cell[0] += value
            cell[1] += 1.0

    def render(self) -> str:
        lines: list[str] = [
            "# HELP vitrin_build_info Build info.",
            "# TYPE vitrin_build_info gauge",
            f'vitrin_build_info{{version="{_VERSION}"}} 1',
        ]
        with self._lock:
            for name, series in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                for key, val in series.items():
                    lines.append(f"{name}{_fmt_labels(key)} {val:g}")
            for name, gseries in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                for key, val in gseries.items():
                    lines.append(f"{name}{_fmt_labels(key)} {val:g}")
            for name, sumseries in self._summaries.items():
                lines.append(f"# TYPE {name} summary")
                for key, cell in sumseries.items():
                    lines.append(f"{name}_sum{_fmt_labels(key)} {cell[0]:g}")
                    lines.append(f"{name}_count{_fmt_labels(key)} {cell[1]:g}")
        return "\n".join(lines) + "\n"


def _fmt_labels(key: tuple[tuple[str, str], ...]) -> str:
    if not key:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in key)
    return "{" + inner + "}"


# Process-wide registry.
metrics = Metrics()


def setup_telemetry(app, settings) -> None:
    """Instrument the FastAPI app for tracing (best-effort; never breaks boot)."""
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider(resource=Resource.create({"service.name": settings.service_name}))
        exporter = None
        if settings.otel_endpoint:
            try:  # OTLP exporter is optional (separate package).
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
            except Exception:  # noqa: BLE001
                log.warning("otel.otlp_unavailable", endpoint=settings.otel_endpoint)
        if exporter is None and settings.otel_console:
            exporter = ConsoleSpanExporter()
        if exporter is not None:
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("otel.instrumented", exporter=type(exporter).__name__ if exporter else "none")
    except Exception as exc:  # noqa: BLE001 - observability must never break the app
        log.warning("otel.setup_failed", error=str(exc))
