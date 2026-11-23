"""Schools and the district summary: counts only, small groups hidden, officers never see children."""

import json

from sqlalchemy import select

from tests.test_admin import _login
from tests.test_api import client  # noqa: F401  (sets up the temp data dir and the teacher login)
from app.db import SessionLocal
from app.models import Classroom, School
from app.seed.demo import DEMO_SCHOOLS, NICKNAMES
from app.services import district


def _summary(officer):
    r = officer.get("/api/district/summary")
    assert r.status_code == 200, r.text
    return r.json()


def test_district_officer_sees_counts_only(client):  # noqa: F811
    officer = _login("district", "district123", role="teacher")  # staff use the Teacher tab
    assert officer.get("/api/auth/me").json()["role"] == "district"
    data = _summary(officer)
    names = [s["name"] for s in data["schools"]]
    for n, _ in DEMO_SCHOOLS:
        assert n in names
    a = next(s for s in data["schools"] if s["name"] == "Demo School A")
    assert not a["hidden"] and a["assessed"] >= district.MIN_GROUP and a["median_wcpm"]
    assert a["weakest"] and a["weakest"][0]["practice"], "weak units link to passages that practise them"
    assert data["totals"]["simulated_readings"] > 0  # demo data is labelled as simulated

    # no child-level data anywhere in the summary
    text = json.dumps(data, ensure_ascii=False)
    assert "Roll 0" not in text
    assert not any(n in text for n in NICKNAMES)

    # an officer can open nothing about classes, children, readings or recordings
    cid = client.get("/api/classrooms").json()[0]["id"]
    sid = client.get(f"/api/classrooms/{cid}").json()["students"][0]["id"]
    rid = client.get("/api/readings").json()[0]["id"]
    for url in ["/api/classrooms", f"/api/classrooms/{cid}", f"/api/students/{sid}", "/api/readings",
                f"/api/readings/{rid}", f"/api/readings/{rid}/audio", "/api/admin/teachers", "/api/admin/schools",
                "/api/my/overview", f"/api/classrooms/{cid}/export.csv"]:
        assert officer.get(url).status_code in (403, 404), url
    # teachers and students cannot open the district view
    assert client.get("/api/district/summary").status_code == 403

    csv = officer.get("/api/district/summary.csv")
    assert csv.status_code == 200 and "Demo School A" in csv.text and "error_rate" in csv.text


def test_summary_matches_hand_count(client):  # noqa: F811
    officer = _login("district", "district123", role="teacher")
    c_row = next(s for s in _summary(officer)["schools"] if s["name"] == "Demo School C")
    with SessionLocal() as db:
        sch = db.scalar(select(School).where(School.name == "Demo School C"))
        classes = db.scalars(select(Classroom).where(Classroom.school_id == sch.id)).all()
        kids = [st for c in classes for st in c.students if st.active]
        reviewed = [[r for r in st.readings if r.reviewed and r.status == "done"
                     and not (r.passage and r.passage.language == "en")] for st in kids]
    assert c_row["children"] == len(kids)
    assert c_row["assessed"] == sum(1 for rs in reviewed if rs)
    if not c_row["hidden"]:
        assert c_row["reviewed_readings"] == sum(len(rs) for rs in reviewed)


def test_small_groups_are_hidden():
    assert district._cell({"errors": 3, "opportunities": 10, "children": 4, "children_with_errors": 2})["hidden"]
    shown = district._cell({"errors": 3, "opportunities": 10, "children": 5, "children_with_errors": 2})
    assert not shown["hidden"] and shown["error_rate"] == 0.3


def test_admin_manages_schools_and_teachers_follow(client):  # noqa: F811
    admin = _login("admin", "admin123", role="teacher")
    r = admin.post("/api/admin/schools", json={"name": "Tiny School", "upazila": "U", "district": "D"})
    assert r.status_code == 201, r.text
    school_id = r.json()["id"]
    assert admin.post("/api/admin/schools", json={"name": "Tiny School"}).status_code == 409

    # a teacher created without a school works exactly as before
    assert admin.post("/api/admin/teachers", json={"username": "tina.t", "password": "tina-pass1"}).status_code == 201
    t = _login("tina.t", "tina-pass1", role="teacher")
    cid = t.post("/api/classrooms", json={"name": "Tina 2B", "grade": 2}).json()["id"]
    t.post(f"/api/classrooms/{cid}/students/bulk", json={"count": 3})
    assert t.get(f"/api/classrooms/{cid}").status_code == 200
    schools = admin.get("/api/admin/schools").json()
    assert cid in [c["id"] for c in schools["unassigned_classes"]]

    # putting the teacher in a school moves their classes; a school with < 5 assessed children is hidden
    uid = next(u["id"] for u in admin.get("/api/admin/teachers").json() if u["username"] == "tina.t")
    assert admin.put(f"/api/admin/teachers/{uid}/school", json={"school_id": school_id}).json()["school_id"] == school_id
    tiny = next(s for s in admin.get("/api/admin/schools").json()["schools"] if s["id"] == school_id)
    assert [c["id"] for c in tiny["classes"]] == [cid] and tiny["children"] == 3
    row = next(s for s in _summary(admin)["schools"] if s["id"] == school_id)
    assert row["hidden"] and "weakest" not in row and "median_wcpm" not in row
    # new classes of a teacher in a school join that school
    cid2 = t.post("/api/classrooms", json={"name": "Tina 3B", "grade": 3}).json()["id"]
    assert cid2 in [c["id"] for c in next(s for s in admin.get("/api/admin/schools").json()["schools"]
                                          if s["id"] == school_id)["classes"]]

    # the admin can create a district officer account, who cannot manage anything
    r = admin.post("/api/admin/teachers", json={"username": "dpeo.x", "password": "dpeo-pass1", "role": "district"})
    assert r.status_code == 201 and r.json()["role"] == "district"
    o = _login("dpeo.x", "dpeo-pass1", role="teacher")
    assert o.get("/api/district/summary").status_code == 200
    assert o.post("/api/admin/schools", json={"name": "Nope"}).status_code == 403

    # demo reset removes visitor schools and accounts, keeps the demo schools and district login
    assert admin.post("/api/demo/reset").status_code == 200
    names = [s["name"] for s in admin.get("/api/admin/schools").json()["schools"]]
    assert "Tiny School" not in names and all(n in names for n, _ in DEMO_SCHOOLS)
    _login("district", "district123", role="teacher")
