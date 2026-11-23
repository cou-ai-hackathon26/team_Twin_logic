import json
from types import SimpleNamespace

from app import config
from app.api import routes


def _write_report(path, label, recordings):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"label": label, "recordings": recordings}), encoding="utf-8")


def test_benchmark_hides_synthetic_only_report(tmp_path, monkeypatch):
    local = tmp_path / "local"
    published = tmp_path / "published"
    _write_report(local / "benchmark_latest.json", "SYNTHETIC TTS SMOKE TEST - not a result", 24)
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(reports_dir=local))
    monkeypatch.setattr(config, "RESULTS_DIR", published)

    result = routes.benchmark_report()

    assert result["available"] is False
    assert "Only synthetic" in result["reason"]


def test_benchmark_selects_published_real_report_over_local_synthetic(tmp_path, monkeypatch):
    local = tmp_path / "local"
    published = tmp_path / "published"
    _write_report(local / "benchmark_latest.json", "SYNTHETIC TTS SMOKE TEST - not a result", 24)
    _write_report(published / "benchmark_latest.json", "FLEURS adult speech; simulated text-side errors; n=10", 10)
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(reports_dir=local))
    monkeypatch.setattr(config, "RESULTS_DIR", published)

    result = routes.benchmark_report()

    assert result["available"] is True
    assert result["recordings"] == 10
    assert result["label"].startswith("FLEURS adult speech")
