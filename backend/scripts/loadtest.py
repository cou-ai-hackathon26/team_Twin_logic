"""Load test: many children hand in a reading at the same moment. How long until every one is marked?

Runs against a PoraBondhu server that is already running LOCALLY (never the hosted demo), e.g.

    set PB_METRICS_ENABLED=true& set PB_MAX_UPLOADS_PER_10MIN=0& set PB_MARKING_WORKERS=1
    set PB_DATABASE_URL=sqlite:///C:/temp/pb_loadtest.db
    python -m uvicorn app.main:app --port 8200
    python -m scripts.loadtest --url http://127.0.0.1:8200 --burst 10 25 50 --server-pid <pid>

Audio: real Bangla speech from Google FLEURS (adult readers, CC BY 4.0; the recordings already used by
the evaluation). Each recording gets a temporary passage with its own text so it is marked like a real
reading. Everything the test creates (passages, readings, audio) is deleted at the end.

Output: results/loadtest_<workers>w.json with, per burst size: wall time until all marked, readings
per hour, p50/p95 time from upload to marks, queue wait, marking time, failures, refused uploads, and
server CPU / memory (Windows, sampled every second when --server-pid is given).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx

from app.config import RESULTS_DIR, BACKEND_DIR

MANIFEST = BACKEND_DIR / "data" / "eval_fleurs" / "recordings.csv"


def pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 2)


class Sampler(threading.Thread):
    """Samples CPU % (of all cores) and working-set memory of the server process every second."""

    def __init__(self, pid: int):
        super().__init__(daemon=True)
        self.pid, self.stop, self.cpu, self.mem = pid, threading.Event(), [], []

    def _read(self) -> tuple[float, float] | None:
        cmd = f"$p=Get-Process -Id {self.pid}; \"$($p.CPU) $($p.WorkingSet64)\""
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                                 timeout=10).stdout.split()
            return float(out[0]), float(out[1]) / 2**20
        except Exception:  # noqa: BLE001
            return None

    def run(self) -> None:
        import os

        cores = os.cpu_count() or 1
        prev, t_prev = self._read(), time.perf_counter()
        while not self.stop.wait(1.0):
            cur, t = self._read(), time.perf_counter()
            if cur and prev:
                self.cpu.append(100 * (cur[0] - prev[0]) / (t - t_prev) / cores)
                self.mem.append(cur[1])
            prev, t_prev = cur, t


def run_burst(c: httpx.Client, base: str, recs: list[dict], sid: int, n: int, pid: int | None) -> dict:
    jobs = [recs[i % len(recs)] for i in range(n)]
    sampler = Sampler(pid) if pid else None
    if sampler:
        sampler.start()
    t0 = time.perf_counter()

    def upload(rec: dict) -> dict:
        t_up = time.perf_counter()
        with open(rec["audio"], "rb") as f:
            r = c.post(f"{base}/api/readings", data={"student_id": sid, "passage_id": rec["pid"]},
                       files={"audio": ("r.wav", f.read(), "audio/wav")})
        return {"t_up": t_up, "code": r.status_code, "id": r.json().get("id") if r.status_code == 202 else None}

    with ThreadPoolExecutor(max_workers=min(n, 16)) as ex:
        ups = list(ex.map(upload, jobs))

    pending = {u["id"]: u for u in ups if u["id"]}
    results: dict[int, dict] = {}
    deadline = time.perf_counter() + 60 * 30
    while pending and time.perf_counter() < deadline:
        for rid in list(pending):
            r = c.get(f"{base}/api/readings/{rid}").json()
            if r["status"] in ("done", "failed", "rejected"):
                u = pending.pop(rid)
                results[rid] = {"status": r["status"], "latency": time.perf_counter() - u["t_up"],
                                "marking": (r.get("processing_ms") or 0) / 1000, "audio": r.get("duration_sec") or 0}
        time.sleep(0.5)
    wall = time.perf_counter() - t0
    if sampler:
        sampler.stop.set()
        sampler.join()

    done = [v for v in results.values() if v["status"] == "done"]
    lat = [v["latency"] for v in done]
    mark = [v["marking"] for v in done]
    audio = sum(v["audio"] for v in done)
    out = {
        "burst": n,
        "accepted": sum(1 for u in ups if u["code"] == 202),
        "refused_busy_503": sum(1 for u in ups if u["code"] == 503),
        "other_errors": sum(1 for u in ups if u["code"] not in (202, 503)),
        "done": len(done),
        "failed_or_rejected": len(results) - len(done),
        "rejected_by_audio_check": sum(1 for v in results.values() if v["status"] == "rejected"),
        "unfinished": len(pending),
        "wall_seconds": round(wall, 1),
        "readings_per_hour": round(len(done) / wall * 3600) if wall else None,
        "audio_seconds_marked": round(audio, 1),
        "audio_seconds_per_wall_second": round(audio / wall, 2) if wall else None,
        "latency_upload_to_marks_s": {"p50": pct(lat, .5), "p95": pct(lat, .95), "max": pct(lat, 1)},
        "marking_time_per_reading_s": {"p50": pct(mark, .5), "p95": pct(mark, .95),
                                       "mean": round(statistics.mean(mark), 2) if mark else None},
        "ids": list(results) + list(pending),
    }
    if sampler and sampler.cpu:
        out["server_cpu_percent_all_cores"] = {"mean": round(statistics.mean(sampler.cpu), 1),
                                               "max": round(max(sampler.cpu), 1)}
        out["server_memory_mb"] = {"max": round(max(sampler.mem)), "mean": round(statistics.mean(sampler.mem))}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8200")
    ap.add_argument("--burst", type=int, nargs="+", default=[10, 25, 50])
    ap.add_argument("--recordings", type=int, default=10, help="distinct FLEURS test recordings to cycle through")
    ap.add_argument("--server-pid", type=int)
    ap.add_argument("--login", default="teacher")
    ap.add_argument("--password", default="teacher123")
    args = ap.parse_args()
    if not args.url.startswith(("http://127.0.0.1", "http://localhost")):
        raise SystemExit("Load tests run against a local server only.")

    rows = [r for r in csv.DictReader(open(MANIFEST, encoding="utf-8")) if r["split"] == "test"]
    rows = [r for r in rows if r["condition"] == "clean"][: args.recordings]
    base = args.url.rstrip("/")
    c = httpx.Client(timeout=120, headers={"Origin": base})
    assert c.post(f"{base}/api/auth/login", json={"username": args.login, "password": args.password}).status_code == 200
    system = c.get(f"{base}/api/system").json()
    metrics_text = c.get(f"{base}/metrics").text
    workers = next((int(float(line.split()[1])) for line in metrics_text.splitlines() if line.startswith("pb_workers ")), None)

    cls = c.post(f"{base}/api/classrooms", json={"name": "Load test (temporary)", "grade": 3}).json()
    c.post(f"{base}/api/classrooms/{cls['id']}/students/bulk", json={"count": 1})
    sid = c.get(f"{base}/api/classrooms/{cls['id']}").json()["students"][0]["id"]
    recs = []
    for i, r in enumerate(rows):
        p = c.post(f"{base}/api/passages", json={"title": f"loadtest {i}", "grade": 3, "language": "bn",
                                                 "text": r["human_transcript"]}).json()
        recs.append({"audio": r["audio"], "pid": p["id"]})

    # warm-up: load the model once so burst 1 is not charged for it
    for rid in run_burst(c, base, recs, sid, 1, None)["ids"]:
        c.delete(f"{base}/api/readings/{rid}")

    report = {"generated": datetime.now().isoformat(timespec="seconds"), "server": base, "workers": workers,
              "machine": "author's laptop (8 logical cores, 16 GB RAM, Windows 10), server and load generator on the same machine",
              "audio": f"{len(recs)} real FLEURS bn_in test recordings (adult speech), cycled",
              "ctc_backend": system.get("ctc_backend") or system.get("models"), "bursts": []}
    try:
        for n in args.burst:
            print(f"burst {n} ...", flush=True)
            res = run_burst(c, base, recs, sid, n, args.server_pid)
            for rid in res.pop("ids"):
                c.delete(f"{base}/api/readings/{rid}")
            print(json.dumps(res, ensure_ascii=False), flush=True)
            report["bursts"].append(res)
    finally:
        for r in recs:
            c.delete(f"{base}/api/passages/{r['pid']}")
        c.delete(f"{base}/api/classrooms/{cls['id']}")
    out = RESULTS_DIR / f"loadtest_{workers}w.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
