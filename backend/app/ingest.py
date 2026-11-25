"""Page ingestion: manual upload, folder watcher, direct scanner trigger (adapters in scanners.py).
Originals are stored byte-for-byte; a page whose bytes were already seen in the batch is ignored."""
import hashlib, io, sys, threading
from pathlib import Path

import pymupdf as fitz
from PIL import Image

from . import db, jobs
from .scanners import IMAGE_EXT, natural_key


class NotAPage(ValueError):
    pass


def split_pages(name: str, data: bytes) -> list[tuple[str, bytes]]:
    """A PDF becomes one PNG per page (150 dpi); images pass through untouched."""
    if name.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        out = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for i, p in enumerate(doc):
                out.append((f"{Path(name).stem}_p{i + 1}.png", p.get_pixmap(dpi=150, colorspace=fitz.csGRAY).tobytes("png")))
        return out
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise NotAPage(f"{name}: not an image or PDF") from None
    return [(name, data)]


def ingest(conn, batch_id: int, name: str, data: bytes) -> tuple[int, int]:
    """Store pages + queue their prep jobs. Returns (added, duplicates)."""
    added = dups = 0
    for pname, pdata in split_pages(name, data):
        sha = hashlib.sha256(pdata).hexdigest()
        conn.execute("BEGIN IMMEDIATE")
        try:
            if conn.execute("SELECT 1 FROM page WHERE batch_id=? AND sha256=?", (batch_id, sha)).fetchone():
                dups += 1
                conn.execute("COMMIT")
                continue
            seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM page WHERE batch_id=?", (batch_id,)).fetchone()[0]
            path = db.data_dir() / "batches" / str(batch_id) / "orig" / f"{seq:06d}{Path(pname).suffix.lower() or '.png'}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pdata)
            pid = conn.execute("INSERT INTO page(batch_id, seq, path, sha256) VALUES (?,?,?,?)",
                               (batch_id, seq, str(path), sha)).lastrowid
            conn.execute("UPDATE batch SET total_pages=total_pages+1,"
                         " status=CASE WHEN status IN ('queued','done') THEN 'running' ELSE status END WHERE id=?", (batch_id,))
            jobs.enqueue(conn, "prep", batch_id=batch_id, page_id=pid)
            conn.execute("COMMIT")
            added += 1
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return added, dups


class FolderWatcher(threading.Thread):
    """Polls a folder; ingests new files (natural name order) once their size is stable across two polls."""

    def __init__(self, batch_id: int, folder: Path, poll=0.5):
        super().__init__(daemon=True, name=f"watch-{batch_id}")
        self.batch_id, self.folder, self.poll = batch_id, Path(folder), poll
        self.stopping = threading.Event()
        self.seen: dict[str, tuple] = {}
        self.pending: dict[str, tuple] = {}

    def run(self):
        conn = db.connect()
        while not self.stopping.is_set():
            try:
                self.tick(conn)
            except Exception as e:  # never kill the watcher on one bad file
                print(f"watcher {self.batch_id}: {e}", file=sys.stderr)
            self.stopping.wait(self.poll)
        conn.close()

    def tick(self, conn):
        for f in sorted((p for p in self.folder.iterdir() if p.is_file()), key=natural_key):
            if f.suffix.lower() not in IMAGE_EXT | {".pdf"}:
                continue
            st = f.stat()
            sig = (st.st_size, st.st_mtime_ns)
            if self.seen.get(f.name) == sig:
                continue
            if st.st_size == 0 or self.pending.get(f.name) != sig:  # unchanged across two polls = fully written
                self.pending[f.name] = sig
                continue
            try:
                ingest(conn, self.batch_id, f.name, f.read_bytes())
            except NotAPage:
                pass
            self.seen[f.name] = sig


WATCHERS: dict[int, FolderWatcher] = {}


def start_watch(batch_id: int, folder: str):
    stop_watch(batch_id)
    w = FolderWatcher(batch_id, Path(folder))
    WATCHERS[batch_id] = w
    w.start()


def stop_watch(batch_id: int):
    if w := WATCHERS.pop(batch_id, None):
        w.stopping.set()


def run_scanner(batch_id: int, device):
    """Background thread for a direct scan trigger."""
    def go():
        conn = db.connect()
        conn.execute("UPDATE batch SET last_error=NULL WHERE id=?", (batch_id,))
        try:
            for name, data in device.scan():
                ingest(conn, batch_id, name, data)
        except Exception as e:
            msg = ("No scanner found. Check it is switched on and connected." if "NO_SCANNER" in str(e)
                   else f"Scanning stopped: {e}")
            conn.execute("UPDATE batch SET last_error=? WHERE id=?", (msg, batch_id))
            print(f"scan {batch_id}: {e}", file=sys.stderr)
        finally:
            conn.close()
    t = threading.Thread(target=go, daemon=True, name=f"scan-{batch_id}")
    t.start()
    return t


def resume_watchers():
    with db.connect() as c:
        for b in c.execute("SELECT id, watch_folder FROM batch WHERE watch_folder IS NOT NULL AND status != 'paused' AND finished=0"):
            if Path(b["watch_folder"]).is_dir():
                start_watch(b["id"], b["watch_folder"])


def stop_all():
    for bid in list(WATCHERS):
        stop_watch(bid)

