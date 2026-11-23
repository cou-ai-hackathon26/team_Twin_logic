"""Prometheus metrics in plain text format, with no extra dependency.

Off by default (PB_METRICS_ENABLED=false), so the hosted demo is unchanged. Enabled for local load
tests and the optional Prometheus + Grafana stack in monitoring/ (docker-compose.monitoring.yml).
Only counts and timings are exported: no names, no text, no audio.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()

# reading-marking histogram buckets (seconds)
_BUCKETS = (1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610)

_counters: dict[tuple[str, tuple], float] = {}
_gauges: dict[str, float] = {"pb_queue_waiting": 0, "pb_workers_busy": 0}
_hist: dict[str, dict] = {}
_HELP = {
    "pb_readings_total": ("counter", "Readings finished by the marking worker, by final status"),
    "pb_readings_rejected_queue_full_total": ("counter", "Uploads refused because the marking queue was full"),
    "pb_audio_seconds_total": ("counter", "Seconds of reading audio marked"),
    "pb_http_requests_total": ("counter", "HTTP requests by method, route group and status class"),
    "pb_queue_waiting": ("gauge", "Readings waiting in the marking queue"),
    "pb_workers_busy": ("gauge", "Marking workers busy right now"),
    "pb_workers": ("gauge", "Marking workers configured"),
    "pb_queue_limit": ("gauge", "Maximum readings allowed to wait"),
    "pb_marking_seconds": ("histogram", "Time to mark one reading (model + alignment), seconds"),
    "pb_queue_wait_seconds": ("histogram", "Time a reading waited in the queue before marking, seconds"),
    "pb_http_request_seconds": ("histogram", "HTTP request latency, seconds"),
}
_started = time.time()


def inc(name: str, value: float = 1.0, **labels: str) -> None:
    key = (name, tuple(sorted(labels.items())))
    with _lock:
        _counters[key] = _counters.get(key, 0.0) + value


def gauge_add(name: str, delta: float) -> None:
    with _lock:
        _gauges[name] = _gauges.get(name, 0.0) + delta


def gauge_set(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


def observe(name: str, seconds: float) -> None:
    with _lock:
        h = _hist.setdefault(name, {"buckets": [0] * len(_BUCKETS), "sum": 0.0, "count": 0})
        for i, b in enumerate(_BUCKETS):
            if seconds <= b:
                h["buckets"][i] += 1
        h["sum"] += seconds
        h["count"] += 1


def reset() -> None:
    with _lock:
        _counters.clear()
        _hist.clear()
        _gauges.update({"pb_queue_waiting": 0, "pb_workers_busy": 0})


def snapshot() -> dict:
    """Plain dict (used by the load-test report and tests)."""
    with _lock:
        return {
            "counters": {f"{n}{dict(l) if l else ''}": v for (n, l), v in _counters.items()},
            "gauges": dict(_gauges),
            "histograms": {k: {"count": v["count"], "sum": round(v["sum"], 3)} for k, v in _hist.items()},
        }


def _fmt_labels(labels: tuple) -> str:
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""


def render() -> str:
    lines: list[str] = []
    with _lock:
        names = sorted({n for n, _ in _counters} | set(_gauges) | set(_hist))
        for name in names:
            kind, help_ = _HELP.get(name, ("gauge", name))
            lines += [f"# HELP {name} {help_}", f"# TYPE {name} {kind}"]
            if kind == "counter":
                for (n, labels), v in sorted(_counters.items()):
                    if n == name:
                        lines.append(f"{name}{_fmt_labels(labels)} {v:g}")
            elif kind == "histogram":
                h = _hist[name]
                for b, c in zip(_BUCKETS, h["buckets"]):
                    lines.append(f'{name}_bucket{{le="{b}"}} {c}')
                lines += [f'{name}_bucket{{le="+Inf"}} {h["count"]}', f"{name}_sum {h['sum']:.4f}",
                          f"{name}_count {h['count']}"]
            else:
                lines.append(f"{name} {_gauges[name]:g}")
        lines += ["# HELP pb_uptime_seconds Seconds since the server started", "# TYPE pb_uptime_seconds gauge",
                  f"pb_uptime_seconds {time.time() - _started:.0f}"]
    return "\n".join(lines) + "\n"
