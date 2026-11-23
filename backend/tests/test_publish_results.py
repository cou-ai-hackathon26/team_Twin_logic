"""Scoring helpers used to publish the evaluation, and the Benchmark API's evidence block."""

import json
from types import SimpleNamespace

from app import config
from app.api import routes
from scripts.publish_results import counts, metrics, paired


def test_counts_match_scoring_rules():
    # not-reached words are ignored; unsure is never an error
    tp, fp, fn, hc, un, w = counts(["misread", "correct", "unsure", "skipped", "correct"],
                                   ["misread", "misread", "correct", "correct", "not_reached"])
    assert (tp, fp, fn, hc, un, w) == (1, 1, 1, 2, 1, 4)
    m = metrics([(tp, fp, fn, hc, un, w)])
    assert m["recall"] == 0.5 and m["precision"] == 0.5 and m["false_alarm"] == 0.5 and m["unsure_rate"] == 0.25


def test_paired_bootstrap_detects_a_clear_difference():
    better = [(9, 0, 1, 50, 2, 60)] * 30   # recall 0.9
    worse = [(3, 0, 7, 50, 2, 60)] * 30    # recall 0.3
    d = paired(better, worse)
    assert round(d["recall"]["diff"], 2) == 0.6 and d["recall"]["excludes_zero"]
    same = paired(better, better)
    assert same["recall"]["diff"] == 0 and not same["recall"]["excludes_zero"]


def test_benchmark_api_adds_published_evidence(tmp_path, monkeypatch):
    local, published = tmp_path / "local", tmp_path / "published"
    published.mkdir()
    (published / "benchmark_latest.json").write_text(json.dumps(
        {"label": "FLEURS bn_in test speakers, first 100 recordings", "recordings": 100,
         "per_recording": [{"id": "x"}]}), encoding="utf-8")
    (published / "robustness.json").write_text(json.dumps({"robustness": {"childlike": {"recordings": 100}}}),
                                               encoding="utf-8")
    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(reports_dir=local))
    monkeypatch.setattr(config, "RESULTS_DIR", published)
    out = routes.benchmark_report()
    assert out["available"] and out["recordings"] == 100
    assert "per_recording" not in out
    assert out["evidence"]["robustness"]["childlike"]["recordings"] == 100
