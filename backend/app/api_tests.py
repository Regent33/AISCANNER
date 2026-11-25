"""Test setup: tests, answer key, syllabus, identity (redaction) regions, sample page."""
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from . import db
from .parse import ParseError, parse_key, parse_syllabus
from .web import get_or_404, text_or_file

router = APIRouter()

class TestIn(BaseModel):
    name: str = Field(min_length=1)
    subject: str = ""
    pages_per_paper: int | None = Field(default=None, ge=1)


@router.post("/tests")
def create_test(t: TestIn):
    with db.connect() as c:
        tid = c.execute("INSERT INTO test(name, subject, pages_per_paper) VALUES (?,?,?)",
                        (t.name, t.subject, t.pages_per_paper)).lastrowid
        return get_or_404(c, "test", tid)


@router.get("/tests")
def list_tests():
    with db.connect() as c:
        return db.rows(c.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM question q WHERE q.test_id=t.id) questions,"
            " (SELECT COUNT(*) FROM question q WHERE q.test_id=t.id AND q.key_source='ai') keyless_questions,"
            " (SELECT COUNT(*) FROM syllabus_topic s WHERE s.test_id=t.id) topics,"
            " (SELECT COUNT(*) FROM batch b WHERE b.test_id=t.id) batches FROM test t ORDER BY t.id DESC"))


@router.get("/tests/{tid}")
def get_test(tid: int):
    with db.connect() as c:
        t = get_or_404(c, "test", tid)
        t["questions"] = db.rows(c.execute("SELECT * FROM question WHERE test_id=? ORDER BY number", (tid,)))
        t["topics"] = db.rows(c.execute("SELECT * FROM syllabus_topic WHERE test_id=? ORDER BY id", (tid,)))
        return t


@router.post("/tests/{tid}/key")
async def set_key(tid: int, req: Request):
    text = await text_or_file(req)
    try:
        qs = parse_key(text)
    except ParseError as e:
        raise HTTPException(422, str(e))
    with db.connect() as c:
        get_or_404(c, "test", tid)
        c.execute("BEGIN")
        for q in qs:  # upsert keeps question ids stable for existing responses
            c.execute("INSERT INTO question(test_id, number, type, max_points, correct_answer, key_source, text)"
                      " VALUES (:t,:number,:type,:max_points,:correct_answer,:key_source,:text)"
                      " ON CONFLICT(test_id, number) DO UPDATE SET type=excluded.type, max_points=excluded.max_points,"
                      " correct_answer=excluded.correct_answer, key_source=excluded.key_source, text=excluded.text",
                      {**q, "t": tid})
        keep = [q["number"] for q in qs]
        c.execute(f"DELETE FROM question WHERE test_id=? AND number NOT IN ({','.join('?' * len(keep))})", (tid, *keep))
        c.execute("COMMIT")
    return {"questions": len(qs), "keyless": sum(q["key_source"] == "ai" for q in qs)}


@router.post("/tests/{tid}/syllabus")
async def set_syllabus(tid: int, req: Request):
    text = await text_or_file(req)
    try:
        topics = parse_syllabus(text)
    except ParseError as e:
        raise HTTPException(422, str(e))
    with db.connect() as c:
        get_or_404(c, "test", tid)
        c.execute("BEGIN")
        c.execute("UPDATE question SET topic_id=NULL, topic_confidence=NULL WHERE test_id=?", (tid,))
        c.execute("DELETE FROM syllabus_topic WHERE test_id=?", (tid,))
        c.executemany("INSERT INTO syllabus_topic(test_id, code, title, description) VALUES (?,?,?,?)",
                      [(tid, t["code"], t["title"], t["description"]) for t in topics])
        c.execute("COMMIT")
    return {"topics": len(topics)}


class Region(BaseModel):
    page: int = Field(ge=1)
    box: tuple[float, float, float, float]  # normalised x0, y0, x1, y1 on the registered page

    @model_validator(mode="after")
    def check(self):
        x0, y0, x1, y1 = self.box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError("box must be 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1")
        return self


class Redaction(BaseModel):
    regions: list[Region]


@router.put("/tests/{tid}/redaction")
def set_redaction(tid: int, r: Redaction):
    with db.connect() as c:
        get_or_404(c, "test", tid)
        c.execute("UPDATE test SET redaction_regions=? WHERE id=?", (json.dumps([x.model_dump() for x in r.regions]), tid))
    return {"regions": [x.model_dump() for x in r.regions]}


@router.post("/tests/{tid}/sample")
async def set_sample(tid: int, req: Request):
    form = await req.form()
    f = form.get("file")
    if f is None:
        raise HTTPException(422, "missing file")
    from PIL import Image
    import io
    try:
        img = Image.open(io.BytesIO(await f.read())).convert("L")
    except Exception:
        raise HTTPException(422, "not an image")
    path = db.data_dir() / "tests" / str(tid) / "sample.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    with db.connect() as c:
        get_or_404(c, "test", tid)
        c.execute("UPDATE test SET sample_page=? WHERE id=?", (str(path), tid))
    return {"ok": True, "width": img.width, "height": img.height}


@router.get("/tests/{tid}/sample")
def get_sample(tid: int):
    with db.connect() as c:
        t = get_or_404(c, "test", tid)
    if not t["sample_page"]:
        raise HTTPException(404, "no sample page")
    return FileResponse(t["sample_page"], media_type="image/png")



@router.get("/tests/{tid}/printable.pdf")
def printable_pdf(tid: int):
    """The test as a printable PDF in the format the scanner reads. Downloading it also aligns the test with what was
    printed: pages per paper, the student details area and the sample page (all derived, so repeating is harmless)."""
    from fastapi.responses import Response
    from . import printable
    with db.connect() as c:
        t = get_or_404(c, "test", tid)
        qs = db.rows(c.execute("SELECT number, type, text FROM question WHERE test_id=? ORDER BY number", (tid,)))
        if not qs:
            raise HTTPException(422, "Add the answer key first: the printed test is built from its questions.")
        try:
            pages = printable.layout(qs, t["pages_per_paper"])
        except ValueError as e:
            raise HTTPException(422, str(e))
        pdf = printable.render_pdf(t["name"], pages)
        sample = db.data_dir() / "tests" / str(tid) / "sample.png"
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_bytes(printable.page_png(pdf, 0))
        c.execute("UPDATE test SET pages_per_paper=?, redaction_regions=?, sample_page=? WHERE id=?",
                  (len(pages), json.dumps([printable.IDENTITY_REGION]), str(sample), tid))
    name = "".join(ch for ch in t["name"] if ch.isalnum() or ch in " -_").strip().replace(" ", "_") or "test"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})
