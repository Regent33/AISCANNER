"""Teacher report: topic mapping (once per test), keyless keys, miss rates per question and topic, reteach, PDF."""
import json

from fastapi import APIRouter
from fastapi.responses import Response

from . import analysis, db, grading, providers
from .web import get_or_404

router = APIRouter()
TOP_WEAK = 3


def ensure_topics(c, tid, prov):
    """Map every question to a syllabus topic once; a new syllabus clears the mapping and it runs again."""
    qs = db.rows(c.execute("SELECT * FROM question WHERE test_id=? ORDER BY number", (tid,)))
    topics = db.rows(c.execute("SELECT * FROM syllabus_topic WHERE test_id=?", (tid,)))
    if not topics or all(q["topic_id"] for q in qs):
        return
    mapping = prov.map_topics([{"number": q["number"], "text": q["text"]} for q in qs],
                              [{"code": t["code"], "title": t["title"], "description": t["description"]} for t in topics])
    ids = {t["code"]: t["id"] for t in topics}
    for q in qs:
        code, conf = mapping.get(q["number"], (None, 0.0))
        c.execute("UPDATE question SET topic_id=?, topic_confidence=? WHERE id=?", (ids.get(code), conf, q["id"]))


def ensure_keys(c, tid, prov):
    """Questions without a key get one from the AI (or, offline, the most common answer); always marked unverified."""
    qs = db.rows(c.execute("SELECT * FROM question WHERE test_id=? AND key_source='ai' AND correct_answer IS NULL", (tid,)))
    if not qs:
        return
    answers = {q["number"]: [r[0] for r in c.execute(
        "SELECT r.normalized_answer FROM response r JOIN paper p ON p.id=r.paper_id JOIN batch b ON b.id=p.batch_id"
        " WHERE b.test_id=? AND r.question_id=?", (tid, q["id"]))] for q in qs}
    keys = prov.derive_answers([{"number": q["number"], "type": q["type"], "text": q["text"]} for q in qs], answers)
    for q in qs:
        key = keys.get(q["number"])
        if not key:
            if prov.name in ("cloud", "openrouter", "nvidia"):  # a new key upload resets it
                c.execute("UPDATE question SET correct_answer='' WHERE id=?", (q["id"],))
            continue
        c.execute("UPDATE question SET correct_answer=? WHERE id=?", (key, q["id"]))
        for r in db.rows(c.execute("SELECT * FROM response WHERE question_id=?", (q["id"],))):
            if q["type"] == "mcq":
                ok = r["normalized_answer"] == key
                score = q["max_points"] if ok else 0
            else:
                score, ok, _, _ = grading.match_written(r["raw_read"] or "", key, q["max_points"], r["confidence"] or 0)
            c.execute("UPDATE response SET is_correct=?, score=?, final_score=CASE WHEN reviewed=1 THEN final_score ELSE ? END"
                      " WHERE id=?", (int(ok), score, score, r["id"]))


def ensure_reteach(c, weak, prov):
    """Activities are generated once per topic from topic names and miss rates only, then kept."""
    todo = [t for t in weak if not t["reteach"]]
    if todo:
        acts = prov.reteach([{"code": t["code"], "title": t["title"], "description": t["description"],
                              "miss_rate": t["miss_rate"]} for t in todo])
        for t in todo:
            t["reteach"] = acts.get(t["code"]) or []
            c.execute("UPDATE syllabus_topic SET reteach=? WHERE id=?", (json.dumps(t["reteach"]), t["id"]))
    return [{"code": t["code"], "title": t["title"], "activities": t["reteach"]} for t in weak]


def build_report(c, tid):
    t = get_or_404(c, "test", tid)
    prov = providers.get(c.execute("SELECT provider FROM settings").fetchone()[0])
    ensure_topics(c, tid, prov)
    ensure_keys(c, tid, prov)
    topics = {r["id"]: r for r in db.rows(c.execute("SELECT * FROM syllabus_topic WHERE test_id=?", (tid,)))}
    for tp in topics.values():
        tp["reteach"] = json.loads(tp["reteach"]) if tp["reteach"] else None
    qs = db.rows(c.execute("SELECT * FROM question WHERE test_id=? ORDER BY number", (tid,)))
    for q in qs:
        q["topic_code"] = topics[q["topic_id"]]["code"] if q["topic_id"] in topics else None
    graded = "FROM response r JOIN paper p ON p.id=r.paper_id JOIN batch b ON b.id=p.batch_id WHERE b.test_id=? AND p.status='graded'"
    resp = db.rows(c.execute("SELECT r.question_id, COALESCE(r.final_score, r.score) final_score, r.normalized_answer,"
                             f" r.is_correct {graded}", (tid,)))
    qrows, trows = analysis.aggregate(qs, resp)
    pending = c.execute(f"SELECT COUNT(*) {graded} AND r.needs_review=1 AND r.reviewed=0", (tid,)).fetchone()[0]
    papers = db.rows(c.execute("SELECT p.flags FROM paper p JOIN batch b ON b.id=p.batch_id WHERE b.test_id=? AND p.status='graded'", (tid,)))
    pending += sum(any(f.startswith("id_") and f != "id_reviewed" for f in p["flags"]) for p in papers)
    by_code = {tp["code"]: tp for tp in topics.values()}
    ai_keyed = {q["number"] for q in qs if q["key_source"] == "ai"}
    topic_out = [{"code": r["code"], "title": by_code[r["code"]]["title"] if r["code"] in by_code else "Not mapped to a topic",
                  "miss_rate": r["miss_rate"], "points_missed": r["points_missed"], "points_possible": r["points_possible"],
                  "questions": r["questions"], "unverified": bool(ai_keyed & set(r["questions"]))} for r in trows]
    weak = [dict(by_code[r["code"]], miss_rate=r["miss_rate"]) for r in trows if r["code"] in by_code and r["points_possible"]][:TOP_WEAK]
    return {
        "test": {"id": t["id"], "name": t["name"], "subject": t["subject"]},
        "papers": len(papers), "pending_review": pending, "provisional": pending > 0,
        "topics": topic_out,
        "questions": [{"number": q["number"], "type": q["type"], "topic_title": by_code[q["topic_code"]]["title"] if q["topic_code"] in by_code else None,
                       "topic_confidence": q["topic_confidence"], "miss_rate": q["miss_rate"], "responses": q["responses"],
                       "key_source": q["key_source"], "correct_answer": q["correct_answer"], "common_wrong": q["common_wrong"]}
                      for q in qrows],
        "reteach": ensure_reteach(c, weak, prov) if papers else [],
    }


@router.get("/tests/{tid}/report")
def report(tid: int):
    with db.connect() as c:
        return build_report(c, tid)


@router.get("/tests/{tid}/report.pdf")
def report_pdf(tid: int):
    from .report_pdf import render
    with db.connect() as c:
        data = build_report(c, tid)
    name = "".join(ch for ch in data["test"]["name"] if ch.isalnum() or ch in " -_").strip().replace(" ", "_") or "report"
    return Response(render(data), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}_report.pdf"'})
