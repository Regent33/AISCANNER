"""Review queue: low-confidence answers and unreadable student IDs; on-demand crops."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import db, grade, pipeline
from .vision import region_px
from .web import get_or_404, png

router = APIRouter()

SORTS = {"confidence": "r.confidence ASC, r.id", "question": "q.number, r.confidence", "paper": "p.id, q.number"}


@router.get("/batches/{bid}/review")
def review_queue(bid: int, question: int | None = None, max_confidence: float | None = None,
                 status: str = "pending", sort: str = "confidence", page: int = 1, page_size: int = 50):
    """Flagged items: student identities that could not be read confidently, then low-confidence answers."""
    if status not in ("pending", "reviewed", "all") or sort not in SORTS:
        raise HTTPException(422, "bad status or sort")
    with db.connect() as c:
        get_or_404(c, "batch", bid)
        show_names = c.execute("SELECT show_names FROM settings").fetchone()[0]
        where, args = ["p.batch_id=?", "r.needs_review=1"], [bid]
        if status != "all":
            where.append("r.reviewed=?"); args.append(int(status == "reviewed"))
        if question is not None:
            where.append("q.number=?"); args.append(question)
        if max_confidence is not None:
            where.append("r.confidence<=?"); args.append(max_confidence)
        resp = c.execute(
            "SELECT r.id response_id, p.id paper_id, p.student_ref, q.number question, q.type, q.max_points,"
            " q.correct_answer, q.key_source, r.raw_read, r.normalized_answer, r.score, r.confidence, r.reviewed,"
            f" r.final_score FROM response r JOIN paper p ON p.id=r.paper_id JOIN question q ON q.id=r.question_id"
            f" WHERE {' AND '.join(where)} ORDER BY {SORTS[sort]}", args).fetchall()
        items = []
        if question is None and max_confidence is None:
            for p in db.rows(c.execute("SELECT * FROM paper WHERE batch_id=? AND status='graded' ORDER BY id", (bid,))):
                pending = any(f.startswith("id_") and f != "id_reviewed" for f in p["flags"])
                if (status == "pending" and pending) or (status == "reviewed" and "id_reviewed" in p["flags"]) or \
                        (status == "all" and (pending or "id_reviewed" in p["flags"])):
                    items.append({"kind": "identity", "paper_id": p["id"], "student_ref": p["student_ref"],
                                  "read_id": p["student_id_local"], "confidence": p["id_confidence"],
                                  "year": p["student_year_local"], "section": p["student_section_local"],
                                  "flags": p["flags"], "name": p["student_name_local"] if show_names else None})
        items += [{"kind": "response", **dict(r)} for r in resp]
    total = len(items)
    start = (max(page, 1) - 1) * page_size
    return {"total": total, "page": page, "page_size": page_size, "items": items[start:start + page_size]}


class ResponsePatch(BaseModel):
    final_score: float | None = Field(default=None, ge=0)


@router.patch("/responses/{rid}")
def review_response(rid: int, body: ResponsePatch):
    """Accept the AI score (no final_score) or set the teacher's score. Marks the item reviewed."""
    with db.connect() as c:
        r = get_or_404(c, "response", rid)
        q = get_or_404(c, "question", r["question_id"])
        score = r["score"] if body.final_score is None else body.final_score
        if score is not None and score > q["max_points"]:
            raise HTTPException(422, f"score above max_points ({q['max_points']})")
        c.execute("UPDATE response SET reviewed=1, final_score=? WHERE id=?", (score, rid))
        return get_or_404(c, "response", rid)


class IdentityPatch(BaseModel):
    student_id: str = Field(min_length=1, max_length=32)
    year: str | None = Field(default=None, max_length=16)
    section: str | None = Field(default=None, max_length=64)


@router.patch("/papers/{pid}")
def review_identity(pid: int, body: IdentityPatch):
    """Teacher confirms or corrects the student ID (and year / section) of a paper. Fields left out keep their value."""
    with db.connect() as c:
        p = get_or_404(c, "paper", pid)
        b = get_or_404(c, "batch", p["batch_id"])
        flags = sorted({f for f in p["flags"] if not f.startswith("id_")} | {"id_reviewed"})
        year = p["student_year_local"] if body.year is None else body.year.strip() or None
        section = p["student_section_local"] if body.section is None else body.section.strip() or None
        c.execute("UPDATE paper SET student_id_local=?, student_year_local=?, student_section_local=?, student_ref=NULL"
                  " WHERE id=?", (body.student_id.strip(), year, section, pid))
        ref = grade.assign_ref(c, b["test_id"], pid, body.student_id)
        c.execute("UPDATE paper SET student_ref=?, flags=?, id_confidence=1.0 WHERE id=?", (ref, json.dumps(flags), pid))
        return get_or_404(c, "paper", pid)


@router.get("/responses/{rid}/crop")
def response_crop(rid: int):
    """Redacted crop of the answer area (what the review screen shows)."""
    with db.connect() as c:
        r = get_or_404(c, "response", rid)
        info = json.loads(r["crop"])
        p = get_or_404(c, "page", info["page_id"])
        t = c.execute("SELECT t.redaction_regions FROM test t JOIN batch b ON b.test_id=t.id WHERE b.id=?",
                      (p["batch_id"],)).fetchone()[0]
    img = grade.redacted_page(p, json.loads(t))
    x0, y0, x1, y1 = info["box"]
    return png(img[max(0, y0):y1, max(0, x0):x1])


@router.get("/papers/{pid}/identity")
def identity_crop(pid: int):
    """Unredacted identity region of page 1, for the teacher's eyes only (local; never sent to a provider)."""
    with db.connect() as c:
        p = get_or_404(c, "paper", pid)
        t = c.execute("SELECT t.redaction_regions FROM test t JOIN batch b ON b.test_id=t.id WHERE b.id=?",
                      (p["batch_id"],)).fetchone()[0]
        pages = [get_or_404(c, "page", i) for i in p["page_ids"]]
    first = next((pg for pg in pages if pg["page_no"] == 1), None)
    regions = [r for r in json.loads(t) if r["page"] == 1]
    img = pipeline.page_image(first) if first else None
    if img is None or not regions:
        raise HTTPException(404, "no readable page 1")
    x0, y0, x1, y1 = region_px(regions[0]["box"])
    return png(img[y0:y1, x0:x1])


