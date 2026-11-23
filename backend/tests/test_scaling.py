"""Scaling safeguards: Prometheus metrics (off by default) and the marking-queue limit."""

from tests.test_api import FakeRecognizer, wav_bytes, wait_done  # noqa: F401  (sets up the temp data dir)
from tests.test_api import client  # noqa: F401  (fixture)
from app import metrics
from app.config import get_settings
from app.services import readings as svc


def _class3_student_and_passage(c):
    cls = next(x for x in c.get("/api/classrooms").json() if x["name"] == "Class 3")
    sid = c.get(f"/api/classrooms/{cls['id']}").json()["students"][0]["id"]
    pid = next(p["id"] for p in c.get("/api/passages").json() if p["language"] == "bn")
    return sid, pid


def test_metrics_off_by_default(client):  # noqa: F811
    assert get_settings().metrics_enabled is False
    assert client.get("/metrics").status_code == 404


def test_metrics_count_readings_without_personal_data(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(get_settings(), "metrics_enabled", True)
    metrics.reset()
    c = client
    sid, pid = _class3_student_and_passage(c)
    words = next(p for p in c.get("/api/passages").json() if p["id"] == pid)["text"].replace("।", "").split()
    monkeypatch.setattr(svc, "get_ctc", lambda: FakeRecognizer(words))  # fast and deterministic
    r = c.post("/api/readings", data={"student_id": sid, "passage_id": pid},
               files={"audio": ("a.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 202
    assert wait_done(c, r.json()["id"], timeout=60)["status"] == "done"
    text = c.get("/metrics").text
    assert "# TYPE pb_marking_seconds histogram" in text
    assert 'pb_readings_total{status="done"} 1' in text
    assert "pb_marking_seconds_count 1" in text
    assert 'pb_http_requests_total{method="POST",route="/api/readings",status="2xx"}' in text
    assert "pb_workers 1" in text and "pb_queue_limit" in text
    st = c.get(f"/api/students/{sid}").json()
    student_name = st.get("display_name") or st.get("code")
    assert student_name not in text  # counts and timings only


def test_full_queue_refuses_upload_politely(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(get_settings(), "max_queue", 1)
    monkeypatch.setattr(svc, "_waiting", 1)  # pretend one reading is already waiting
    sid, pid = _class3_student_and_passage(client)
    r = client.post("/api/readings", data={"student_id": sid, "passage_id": pid},
                    files={"audio": ("a.wav", wav_bytes(), "audio/wav")})
    assert r.status_code == 503 and r.headers["retry-after"] == "60"
    assert "busy" in r.json()["detail"]
