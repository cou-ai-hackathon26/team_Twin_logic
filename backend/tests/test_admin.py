"""Roles: admin creates teachers, teachers create students' logins, each sees only what they should."""

from fastapi.testclient import TestClient

from tests.test_api import client  # noqa: F401  (sets up the temp data dir and the teacher login)
from app.main import app


def _login(username, password, role=None):
    c = TestClient(app)
    c.__enter__()
    body = {"username": username, "password": password}
    if role:
        body["role"] = role
    r = c.post("/api/auth/login", json=body)
    assert r.status_code == 200, r.text
    return c


def test_admin_teacher_student_chain(client):  # noqa: F811
    admin = _login("admin", "admin123", role="teacher")  # admins use the Teacher tab
    assert admin.get("/api/auth/me").json()["role"] == "admin"
    # only the admin can manage teachers
    assert client.get("/api/admin/teachers").status_code == 403
    r = admin.post("/api/admin/teachers", json={"username": "rina.t", "display_name": "Rina", "password": "rina-pass1"})
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    assert admin.post("/api/admin/teachers", json={"username": "rina.t", "password": "rina-pass1"}).status_code == 409
    assert admin.post("/api/admin/teachers", json={"username": "x", "password": "short"}).status_code == 422

    # the new teacher creates a class, a student and the student's login
    t = _login("rina.t", "rina-pass1", role="teacher")
    cid = t.post("/api/classrooms", json={"name": "Rina 3A", "grade": 3}).json()["id"]
    sid = t.post(f"/api/classrooms/{cid}/students", json={"code": "R1"}).json()["id"]
    assert t.put(f"/api/students/{sid}/account", json={"username": "rina3a01", "password": "kid-pass1"}).status_code == 200
    s = _login("rina3a01", "kid-pass1", role="student")
    assert s.get("/api/auth/me").json()["student"]["id"] == sid
    assert s.get("/api/admin/teachers").status_code == 403

    # the demo teacher cannot see Rina's class; the admin sees every class
    assert "Rina 3A" not in [c["name"] for c in client.get("/api/classrooms").json()]
    assert "Rina 3A" in [c["name"] for c in admin.get("/api/classrooms").json()]
    listed = {u["username"]: u for u in admin.get("/api/admin/teachers").json()}
    assert listed["rina.t"]["classes"] == 1 and listed["admin"]["role"] == "admin"

    # password reset logs the teacher out; removing the teacher keeps the class, now shared
    assert admin.put(f"/api/admin/teachers/{tid}/password", json={"password": "new-pass-99"}).status_code == 204
    assert t.get("/api/auth/me").status_code == 401
    assert admin.delete(f"/api/admin/teachers/{tid}").status_code == 204
    assert "Rina 3A" in [c["name"] for c in client.get("/api/classrooms").json()]
    # the shared demo teacher is protected on the demo server
    demo_id = next(u["id"] for u in admin.get("/api/admin/teachers").json() if u["username"] == "teacher")
    assert admin.delete(f"/api/admin/teachers/{demo_id}").status_code == 403
    for c in (admin, t, s):
        c.__exit__(None, None, None)


def test_demo_reset_removes_visitor_teachers(client):  # noqa: F811
    admin = _login("admin", "admin123")
    admin.post("/api/admin/teachers", json={"username": "visitor1", "password": "visitor-pass1"})
    client.post("/api/demo/reset")
    names = [u["username"] for u in admin.get("/api/admin/teachers").json()]
    assert "visitor1" not in names and "teacher" in names and "admin" in names
    admin.__exit__(None, None, None)
