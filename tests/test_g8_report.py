"""Report logic: exact aggregation, topic mapping on the question bank, keyless keys, provisional flag, PDF sections."""
import json

import pymupdf as fitz

import generate as gen
from app import analysis, db
from app.report_pdf import SECTIONS
from content import TESTS


def test_aggregate_exact():
    qs = [{"id": 1, "number": 1, "max_points": 1, "topic_code": "A"}, {"id": 2, "number": 2, "max_points": 2, "topic_code": "B"},
          {"id": 3, "number": 3, "max_points": 1, "topic_code": "B"}]
    rs = [{"question_id": 1, "final_score": 1, "normalized_answer": "B", "is_correct": 1},
          {"question_id": 1, "final_score": 0, "normalized_answer": "C", "is_correct": 0},
          {"question_id": 2, "final_score": 1, "normalized_answer": "x", "is_correct": 0},   # partial credit
          {"question_id": 2, "final_score": 2, "normalized_answer": "y", "is_correct": 1},
          {"question_id": 3, "final_score": None, "normalized_answer": None, "is_correct": None}]  # ungraded: excluded
    qrows, trows = analysis.aggregate(qs, rs)
    assert [(r["number"], r["miss_rate"], r["common_wrong"]) for r in qrows] == [(1, 0.5, "C"), (2, 0.25, "x"), (3, None, None)]
    assert [(t["code"], t["miss_rate"], t["points_missed"], t["points_possible"]) for t in trows] == [("A", 0.5, 1, 2), ("B", 0.25, 1, 4)]


def test_lexical_mapping_on_question_bank():
    ok = n = 0
    for t in TESTS:
        tt = gen.test_truth(t)
        m = analysis.lexical_topic_map([{"number": q.number, "text": q.text} for q in tt.questions],
                                       [x.model_dump() for x in tt.topics])
        ok += sum(m[q.number][0] == q.topic for q in tt.questions)
        n += len(tt.questions)
    assert ok / n >= 0.90, ok / n


def seed(client, key):
    tid = client.post("/api/tests", json={"name": "Quiz", "subject": "Sci"}).json()["id"]
    client.post(f"/api/tests/{tid}/key", json={"text": key})
    client.post(f"/api/tests/{tid}/syllabus", json={"text": "PL | Plant life | roots, leaves, water\nSP | Space | planets, Sun, Moon"})
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    c = db.connect()
    qids = {r[1]: r[0] for r in c.execute("SELECT id, number FROM question WHERE test_id=?", (tid,))}
    return tid, bid, c, qids


def add_paper(c, bid, qids, answers, name="Maya Silva", sid="123456", review=()):
    pid = c.execute("INSERT INTO paper(batch_id, student_ref, student_name_local, student_id_local, status, flags)"
                    " VALUES (?, 'S-0001', ?, ?, 'graded', '[]')", (bid, name, sid)).lastrowid
    for num, (ans, score) in answers.items():
        c.execute("INSERT INTO response(paper_id, question_id, normalized_answer, is_correct, score, final_score, confidence,"
                  " needs_review) VALUES (?,?,?,?,?,?,0.9,?)", (pid, qids[num], ans, None if score is None else int(score > 0),
                                                              score, score, int(num in review)))


def test_report_ranks_topics_and_is_provisional_until_reviewed(client):
    tid, bid, c, qids = seed(client, "1 | mcq | B | 1 | Which part of a plant takes in water? (A) Leaves (B) Roots\n"
                                     "2 | mcq | C | 1 | Which planet is closest to the Sun? (A) Mars (B) Venus (C) Mercury")
    add_paper(c, bid, qids, {1: ("A", 0), 2: ("C", 1)}, review=(1,))
    add_paper(c, bid, qids, {1: ("A", 0), 2: ("B", 0)}, name="Leo Kim", sid="654321")
    r = client.get(f"/api/tests/{tid}/report").json()
    assert [(t["code"], t["miss_rate"]) for t in r["topics"]] == [("PL", 1.0), ("SP", 0.5)]
    assert r["provisional"] and r["pending_review"] == 1 and r["papers"] == 2
    assert r["questions"][0]["common_wrong"] == "A" and r["reteach"][0]["code"] == "PL" and r["reteach"][0]["activities"]
    rid = c.execute("SELECT id FROM response WHERE needs_review=1").fetchone()[0]
    client.patch(f"/api/responses/{rid}", json={"final_score": 1})  # teacher overrides the AI
    r = client.get(f"/api/tests/{tid}/report").json()
    assert not r["provisional"] and r["topics"][0]["miss_rate"] == 0.5


def test_keyless_question_gets_unverified_key(client):
    tid, bid, c, qids = seed(client, "1 | mcq | | 1 | Which part of a plant takes in water? (A) Leaves (B) Roots")
    for ans in ("B", "B", "A"):
        add_paper(c, bid, qids, {1: (ans, None)})
    r = client.get(f"/api/tests/{tid}/report").json()
    q = r["questions"][0]
    assert (q["correct_answer"], q["key_source"]) == ("B", "ai") and abs(q["miss_rate"] - 1 / 3) < 1e-9
    assert r["topics"][0]["unverified"] is True


def test_pdf_has_four_sections_and_no_student_identity(client):
    tid, bid, c, qids = seed(client, "1 | mcq | B | 1 | Which part of a plant takes in water? (A) Leaves (B) Roots")
    add_paper(c, bid, qids, {1: ("A", 0)}, name="Maya Silva", sid="123456")
    r = client.get(f"/api/tests/{tid}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    text = "".join(p.get_text() for p in fitz.open(stream=r.content, filetype="pdf"))
    assert all(s in text for s in SECTIONS), text[:500]
    assert "Maya" not in text and "Silva" not in text and "123456" not in text and "S-0001" not in text
    json.dumps(client.get(f"/api/tests/{tid}/report").json())  # report JSON serialises


def test_redaction_block_is_not_an_answer_box():
    import numpy as np
    from app import grading, printable, vision
    img = np.full((vision.H, vision.W), 250, np.uint8)
    region = vision.region_px(printable.IDENTITY_REGION["box"])
    x0, y0, x1, y1 = region
    img[y0 - 6:y1 + 6, x0 - 6:x1 + 6] = 0  # redaction fill a little larger than the region, as after a skewed scan
    assert grading.detect_items(img, [region]) == []
