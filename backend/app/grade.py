"""Grade stage (per paper): identify the student locally, redact, read and grade every answer."""
import json

import numpy as np

from . import db, grading, providers, vision
from .parse import split_options
from .jobs import stage
from .pipeline import maybe_done, page_image, settings


# ---------- redaction: the only way page pixels reach grading or a provider ----------

def regions_on(regions, page_no):
    return [vision.region_px(r["box"]) for r in regions if r["page"] == page_no]


def redacted_page(p, regions) -> np.ndarray | None:
    """Registered page with every identity region on that page filled black. Use this for everything except
    the local identity read."""
    img = page_image(p)
    if img is None:
        return None
    for x0, y0, x1, y1 in regions_on(regions, p["page_no"] or 1):
        img[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = 0
    return img


# ---------- grade: identify (local), redact, read, grade (per paper) ----------

def assign_ref(conn, test_id, paper_id, student_id):
    """Pseudonymous ref, stable per (test, student id). Unreadable IDs get a fresh ref."""
    if student_id:
        r = conn.execute("SELECT p.student_ref FROM paper p JOIN batch b ON b.id=p.batch_id WHERE b.test_id=?"
                         " AND p.student_id_local=? AND p.id != ? AND p.student_ref IS NOT NULL LIMIT 1",
                         (test_id, student_id, paper_id)).fetchone()
        if r:
            return r[0]
    cur = conn.execute("SELECT student_ref FROM paper WHERE id=?", (paper_id,)).fetchone()[0]
    if cur:
        return cur
    n = conn.execute("SELECT COALESCE(MAX(CAST(SUBSTR(p.student_ref, 3) AS INTEGER)), 0) FROM paper p JOIN batch b"
                     " ON b.id=p.batch_id WHERE b.test_id=?", (test_id,)).fetchone()[0]
    return f"S-{n + 1:04d}"


@stage("grade")
def grade(conn, job):
    paper = db.row(conn.execute("SELECT * FROM paper WHERE id=?", (job["paper_id"],)).fetchone())
    if paper is None:
        return  # regrouped away
    b = db.row(conn.execute("SELECT * FROM batch WHERE id=?", (paper["batch_id"],)).fetchone())
    t = db.row(conn.execute("SELECT * FROM test WHERE id=?", (b["test_id"],)).fetchone())
    thr = settings(conn)["confidence_threshold"]
    pages = [db.row(conn.execute("SELECT * FROM page WHERE id=?", (i,)).fetchone()) for i in paper["page_ids"]]
    flags = set(f for f in paper["flags"] if not f.startswith("id_"))

    first = next((p for p in pages if p["page_no"] == 1), None)
    ident = dict(name="", student_id="", year="", section="", id_conf=0.0)
    if "id_reviewed" in paper["flags"]:  # teacher already confirmed the identity: keep it
        flags.add("id_reviewed")
        ident = dict(name=paper["student_name_local"] or "", student_id=paper["student_id_local"] or "", id_conf=1.0,
                     year=paper["student_year_local"] or "", section=paper["student_section_local"] or "")
    elif not t["redaction_regions"]:
        flags.add("id_no_region")
    elif first is None or (img := page_image(first)) is None:
        flags.add("id_unreadable")
    else:
        ident = vision.read_identity(img, t["redaction_regions"])
        if not ident["student_id"]:
            flags.add("id_unreadable")
        elif ident["id_conf"] < thr:
            flags.add("id_low_confidence")
    sid = ident["student_id"] or None
    if sid and conn.execute("SELECT 1 FROM paper WHERE batch_id=? AND student_id_local=? AND id != ?",
                            (b["id"], sid, paper["id"])).fetchone():
        flags.add("id_duplicate")
    ref = assign_ref(conn, t["id"], paper["id"], sid if "id_low_confidence" not in flags else None)
    quota_retry = "not_before" in job.keys() and job["not_before"] > 0
    flags |= grade_answers(conn, t, paper, pages, thr, quota_retry)
    conn.execute("UPDATE paper SET student_id_local=?, student_name_local=?, student_year_local=?, student_section_local=?,"
                 " id_confidence=?, student_ref=?, flags=?, status='graded' WHERE id=?",
                 (sid, ident["name"] or None, ident["year"] or None, ident["section"] or None, ident["id_conf"], ref,
                  json.dumps(sorted(flags)), paper["id"]))
    maybe_done(conn, b["id"])


def grade_answers(conn, t, paper, pages, thr, quota_retry=False):
    """Detect answer areas on each redacted page, read them, grade against the key. Returns paper flags."""
    qs = {q["number"]: q for q in db.rows(conn.execute("SELECT * FROM question WHERE test_id=?", (t["id"],)))}
    prov = providers.get(settings(conn)["provider"])
    regions = t["redaction_regions"]
    flags, seen = set(), set()
    reviewed = {r[0] for r in conn.execute("SELECT question_id FROM response WHERE paper_id=? AND reviewed=1", (paper["id"],))}
    completed = {(r["question_id"], json.loads(r["crop"])["page_id"]) for r in conn.execute(
        "SELECT question_id, crop FROM response WHERE paper_id=? AND crop IS NOT NULL", (paper["id"],))
    } if quota_retry else set()
    for p in sorted(pages, key=lambda p: (p["page_no"] or 99, p["seq"])):
        if p["page_no"] is None or p["page_no"] in seen:  # unreadable page / duplicate scan: already flagged
            continue
        seen.add(p["page_no"])
        img = redacted_page(p, regions)
        ex = regions_on(regions, p["page_no"])
        items = grading.detect_items(img, ex)
        grading.number_items(img, items, max([grading.CONTENT_TOP] + [e[3] for e in ex]))
        for it in items:
            q = qs.get(it["number"])
            if q is None or q["type"] != it["kind"]:
                flags.add("layout_mismatch")
                continue
            if q["id"] in reviewed:
                continue
            key = q["correct_answer"]
            if it["kind"] == "mcq":
                ans, dark, conf = grading.read_mcq(img, it["opts"])
                expected = len(split_options(q["text"])[1] or "ABCD")  # printed tests without options show A-D
                if len(it["opts"]) != expected:  # a bubble went undetected: letters could shift, so ask a person
                    flags.add("layout_mismatch")
                    conf = 0.0
                ok = None if key is None else ans == key
                score = None if ok is None else (q["max_points"] if ok else 0)
                raw = json.dumps([round(x, 3) for x in dark])
                x0 = int(min(o[0] - o[2] for o in it["opts"])) - 30
                box = [max(0, x0), it["top"] - 50, 1150, it["bottom"] + 10]
                review = conf < thr or ans == "MULTI"
            else:
                if (q["id"], p["id"]) in completed:
                    continue
                x0, y0, x1, y1 = it["box"]
                crop = img[y0 + 5:y1 - 5, x0 + 5:x1 - 5]
                where = {"page_no": p["page_no"], "box": [x0 + 5, y0 + 5, x1 - 5, y1 - 5]}
                text, ocr_conf = prov.transcribe(crop, {"number": q["number"], "text": q["text"]}, where)
                if key is None:
                    score, ok, conf, ans = None, None, ocr_conf, grading.norm(text)
                else:
                    score, ok, conf, ans = grading.match_written(text, key, q["max_points"], ocr_conf)
                raw = text
                box = [x0, y0 - 40, x1, y1]
                review = conf < thr
            conn.execute(
                "INSERT INTO response(paper_id, question_id, raw_read, normalized_answer, is_correct, score, confidence,"
                " needs_review, reviewed, final_score, crop) VALUES (?,?,?,?,?,?,?,?,0,?,?)"
                " ON CONFLICT(paper_id, question_id) DO UPDATE SET raw_read=excluded.raw_read,"
                " normalized_answer=excluded.normalized_answer, is_correct=excluded.is_correct, score=excluded.score,"
                " confidence=excluded.confidence, needs_review=excluded.needs_review, final_score=excluded.final_score,"
                " crop=excluded.crop",
                (paper["id"], q["id"], raw, ans, None if ok is None else int(ok), score, conf, int(review), score,
                 json.dumps({"page_id": p["id"], "box": box})))
    return flags
