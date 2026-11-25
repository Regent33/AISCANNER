"""Review queue API: low-confidence items listed, accept / edit score, bounds checked."""
from app import db


def seed(client):
    tid = client.post("/api/tests", json={"name": "T"}).json()["id"]
    client.post(f"/api/tests/{tid}/key", json={"text": "1 | mcq | B | 1 | q1\n2 | written | lava | 1 | q2"})
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    c = db.connect()
    pid = c.execute("INSERT INTO paper(batch_id, student_ref, status, flags) VALUES (?, 'S-0001', 'graded', '[\"id_unreadable\"]')",
                    (bid,)).lastrowid
    qids = [r[0] for r in c.execute("SELECT id FROM question WHERE test_id=? ORDER BY number", (tid,))]
    rows = [(pid, qids[0], "B", 1, 1, 0.95, 0), (pid, qids[1], "lav", 1, 1, 0.55, 1)]
    for paper, q, ans, ok, score, conf, review in rows:
        c.execute("INSERT INTO response(paper_id, question_id, normalized_answer, is_correct, score, confidence,"
                  " needs_review, final_score) VALUES (?,?,?,?,?,?,?,?)", (paper, q, ans, ok, score, conf, review, score))
    return bid, pid


def test_queue_lists_low_confidence_and_identity(client):
    bid, pid = seed(client)
    q = client.get(f"/api/batches/{bid}/review").json()
    assert q["total"] == 2
    assert [i["kind"] for i in q["items"]] == ["identity", "response"]
    assert q["items"][1]["confidence"] == 0.55 and q["items"][1]["question"] == 2


def test_accept_edit_and_bounds(client):
    bid, pid = seed(client)
    rid = client.get(f"/api/batches/{bid}/review").json()["items"][1]["response_id"]
    assert client.patch(f"/api/responses/{rid}", json={"final_score": 2}).status_code == 422  # above max_points
    r = client.patch(f"/api/responses/{rid}", json={"final_score": 0}).json()
    assert r["reviewed"] == 1 and r["final_score"] == 0
    assert client.get(f"/api/batches/{bid}/review").json()["total"] == 1  # only identity left
    assert client.get(f"/api/batches/{bid}/review", params={"status": "reviewed"}).json()["total"] == 1


def test_identity_fix_assigns_ref(client):
    bid, pid = seed(client)
    p = client.patch(f"/api/papers/{pid}", json={"student_id": "123456", "year": "7", "section": "Rizal"}).json()
    assert p["student_id_local"] == "123456" and p["student_ref"].startswith("S-") and "id_reviewed" in p["flags"]
    assert (p["student_year_local"], p["student_section_local"]) == ("7", "Rizal")
    p = client.patch(f"/api/papers/{pid}", json={"student_id": "123456"}).json()  # omitted fields are kept
    assert (p["student_year_local"], p["student_section_local"]) == ("7", "Rizal")
    assert client.get(f"/api/batches/{bid}/review").json()["total"] == 1


def test_pagination(client):
    bid, _ = seed(client)
    q = client.get(f"/api/batches/{bid}/review", params={"page_size": 1, "page": 2}).json()
    assert q["total"] == 2 and len(q["items"]) == 1 and q["items"][0]["kind"] == "response"
