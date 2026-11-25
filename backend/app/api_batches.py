"""Batches: create, upload pages, scanner / folder watch, pause, resume, finish, progress."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from . import db, ingest, pipeline, scanners
from .web import get_or_404

router = APIRouter()


def progress(c, b):
    """Counts the Scan screen shows, plus an ETA from recent per-job durations."""
    bid = b["id"]
    b["jobs"] = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM job WHERE batch_id=? GROUP BY status", (bid,))}
    b["watching"] = bid in ingest.WATCHERS
    waiting = c.execute("SELECT error FROM job WHERE batch_id=? AND status='queued' AND not_before > unixepoch() "
                        "ORDER BY not_before LIMIT 1", (bid,)).fetchone()
    if waiting and not b["last_error"]:
        b["last_error"] = f"{waiting['error']} Grading will retry automatically."
    papers = db.rows(c.execute("SELECT status, flags FROM paper WHERE batch_id=?", (bid,)))
    b["papers_graded"] = sum(p["status"] == "graded" for p in papers)
    b["papers_flagged"] = sum(bool(p["flags"]) and p["flags"] != ["id_reviewed"] for p in papers)
    id_pending = sum(any(f.startswith("id_") and f != "id_reviewed" for f in p["flags"]) for p in papers if p["status"] == "graded")
    answers = c.execute("SELECT COUNT(*) FROM response r JOIN paper p ON p.id=r.paper_id WHERE p.batch_id=?"
                        " AND r.needs_review=1 AND r.reviewed=0", (bid,)).fetchone()[0]
    b["review_pending"] = id_pending + answers
    avg = c.execute("SELECT AVG(d) FROM (SELECT finished_at - started_at d FROM job WHERE batch_id=? AND status='done'"
                    " AND finished_at IS NOT NULL ORDER BY id DESC LIMIT 50)", (bid,)).fetchone()[0]
    left = b["jobs"].get("queued", 0) + b["jobs"].get("running", 0)
    b["eta_seconds"] = round(avg * left) if avg is not None and left else (0 if not left else None)
    return b


class BatchIn(BaseModel):
    test_id: int


@router.post("/batches")
def create_batch(b: BatchIn):
    with db.connect() as c:
        get_or_404(c, "test", b.test_id)
        bid = c.execute("INSERT INTO batch(test_id) VALUES (?)", (b.test_id,)).lastrowid
        return progress(c, get_or_404(c, "batch", bid))


@router.get("/batches")
def list_batches(test_id: int | None = None):
    with db.connect() as c:
        q = "SELECT * FROM batch" + (" WHERE test_id=?" if test_id else "") + " ORDER BY id DESC"
        return [progress(c, b) for b in db.rows(c.execute(q, (test_id,) if test_id else ()))]


@router.get("/batches/{bid}")
def get_batch(bid: int):
    with db.connect() as c:
        return progress(c, get_or_404(c, "batch", bid))


@router.post("/batches/{bid}/pages")
async def upload_pages(bid: int, req: Request):
    form = await req.form()
    files = form.getlist("files") + form.getlist("file")
    if not files:
        raise HTTPException(422, "no files")
    added = dups = 0
    with db.connect() as c:
        get_or_404(c, "batch", bid)
        for f in files:
            try:
                a, d = ingest.ingest(c, bid, f.filename or "upload", await f.read())
            except ingest.NotAPage as e:
                raise HTTPException(422, str(e))
            added, dups = added + a, dups + d
    return {"added": added, "duplicates": dups}


class ScanIn(BaseModel):
    mode: str = Field(pattern="^(watch|scanner)$")
    device: str = Field(default="wia", pattern="^(wia|escl|sane|mock)$")
    target: str | None = Field(default=None, max_length=512)  # WIA device id, printer address or SANE device
    folder: str | None = None


@router.get("/scanners")
def find_scanners():
    """Scanners reachable now: Windows drivers (WIA), network printers (eSCL/AirScan), SANE."""
    return scanners.discover()


class PrinterIn(BaseModel):
    address: str = Field(min_length=1, max_length=512)


@router.post("/scanners/check")
def check_printer(p: PrinterIn):
    """Is there an eSCL (AirScan / Mopria) scanner at this address? Used for printers the search did not find."""
    try:
        s = scanners.EsclScanner(p.address)
        caps = s.capabilities()
    except scanners.ScannerError as e:
        raise HTTPException(422, f"No network scanner answered at that address ({e}).")
    return {"kind": "escl", "id": s.url, "name": caps["name"], "sources": sorted(caps["sources"])}


@router.post("/batches/{bid}/scan")
def scan(bid: int, s: ScanIn):
    with db.connect() as c:
        get_or_404(c, "batch", bid)
        folder = s.folder or c.execute("SELECT watch_folder FROM settings").fetchone()[0]
        if s.mode == "watch" or s.device == "mock":
            if not folder or not Path(folder).is_dir():
                raise HTTPException(422, f"folder not found: {folder}")
        if s.mode == "watch":
            c.execute("UPDATE batch SET watch_folder=? WHERE id=?", (folder, bid))
            ingest.start_watch(bid, folder)
            return {"watching": folder}
    try:
        device = scanners.make(s.device, folder if s.device == "mock" else s.target)
    except scanners.ScannerError as e:
        raise HTTPException(422, str(e))
    ingest.run_scanner(bid, device)
    return {"scanning": s.device}


@router.post("/batches/{bid}/pause")
def pause(bid: int):
    with db.connect() as c:
        get_or_404(c, "batch", bid)
        c.execute("UPDATE batch SET status='paused' WHERE id=?", (bid,))
    ingest.stop_watch(bid)
    return get_batch(bid)


@router.post("/batches/{bid}/resume")
def resume(bid: int):
    with db.connect() as c:
        b = get_or_404(c, "batch", bid)
        c.execute("UPDATE batch SET status='running' WHERE id=?", (bid,))
    if b["watch_folder"] and not b["finished"]:
        ingest.start_watch(bid, b["watch_folder"])
    return get_batch(bid)


@router.post("/batches/{bid}/finish")
def finish(bid: int):
    """Scanning is over: close the last open paper and let the batch complete."""
    with db.connect() as c:
        get_or_404(c, "batch", bid)
        c.execute("UPDATE batch SET finished=1, watch_folder=NULL WHERE id=?", (bid,))
        pipeline.enqueue_once(c, "group", bid)
    ingest.stop_watch(bid)
    return get_batch(bid)

