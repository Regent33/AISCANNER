"""Pipeline stages (SPEC 6). Each stage is idempotent and re-runnable; one bad paper never stops the batch."""
import json

import cv2
import numpy as np

from . import db, vision
from .jobs import enqueue, stage


def settings(conn):
    return db.row(conn.execute("SELECT * FROM settings").fetchone())


def enqueue_once(conn, name, batch_id, paper_id=None):
    q = "SELECT 1 FROM job WHERE stage=? AND batch_id=? AND status='queued'" + (" AND paper_id=?" if paper_id else "")
    if not conn.execute(q, (name, batch_id, paper_id) if paper_id else (name, batch_id)).fetchone():
        enqueue(conn, name, batch_id=batch_id, paper_id=paper_id)


def maybe_done(conn, bid):
    pending = conn.execute("SELECT COUNT(*) FROM job WHERE batch_id=? AND status IN ('queued','running')", (bid,)).fetchone()[0]
    if pending <= 1:  # only the job currently running
        conn.execute("UPDATE batch SET status='done' WHERE id=? AND finished=1 AND status='running'", (bid,))


# ---------- prep: register + read page label (per page) ----------

@stage("prep")
def prep(conn, job):
    p = db.row(conn.execute("SELECT * FROM page WHERE id=?", (job["page_id"],)).fetchone())
    g = vision.load_gray(p["path"])
    Hm, rotated = vision.register(g)
    if Hm is None:
        conn.execute("UPDATE page SET status='unregistered', homography=NULL, page_no=NULL WHERE id=?", (p["id"],))
    else:
        k, n = vision.read_page_label(vision.warp(g, Hm))
        conn.execute("UPDATE page SET status='prepped', homography=?, rotated=?, page_no=?, page_total=? WHERE id=?",
                     (json.dumps(Hm.tolist()), int(rotated), k, n, p["id"]))
    enqueue_once(conn, "group", p["batch_id"])


def page_image(p) -> np.ndarray | None:
    """Registered, contrast-normalised page (unredacted: local use only)."""
    if not p.get("homography"):
        return None
    return vision.flatten(vision.warp(vision.load_gray(p["path"]), json.loads(p["homography"])))


def same_scan(a, b, tol=3) -> bool:
    """Two scans of the same physical sheet (double feed / re-scan) vs. two students' copies of the same page."""
    ia, ib = page_image(a), page_image(b)
    if ia is None or ib is None:
        return False
    ka, kb = ia < 128, ib < 128
    k = np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)
    da, db_ = cv2.dilate(ka.astype(np.uint8), k) > 0, cv2.dilate(kb.astype(np.uint8), k) > 0
    miss = (ka & ~db_).sum() + (kb & ~da).sum()
    return miss / max(1, ka.sum() + kb.sum()) < 0.01


# ---------- group: pages -> papers (per batch) ----------

def build_groups(pages, n_expected):
    """Walk pages in scan order. Page 1 (or a page number going backwards) starts a paper; the same page number
    twice in a row is a duplicate scan only if the images match, otherwise the next paper lost its page 1."""
    groups, cur, last = [], None, None
    for p in pages:
        k = p["page_no"]
        if cur is not None and k is not None and k == last and same_scan(cur["pages"][-1], p):
            cur["flags"].add("duplicate_page")
        elif cur is None or k == 1 or (k is not None and last is not None and k <= last):
            cur = {"pages": [], "flags": set() if k == 1 else {"missing_page_1"}}
            groups.append(cur)
        if p["status"] == "unregistered":
            cur["flags"].add("unreadable_page")
        elif k is None:
            cur["flags"].add("page_label_unreadable")
        cur["pages"].append(p)
        last = k if k is not None else last
    for g in groups:
        nums = [p["page_no"] for p in g["pages"] if p["page_no"]]
        totals = [p["page_total"] for p in g["pages"] if p["page_total"]]
        n = n_expected or (max(totals) if totals else max(nums, default=1))
        g["n"] = n
        g["complete"] = set(range(1, n + 1)) <= set(nums)
        missing = sorted(set(range(1, n + 1)) - set(nums))
        if missing and "unreadable_page" not in g["flags"] and "page_label_unreadable" not in g["flags"]:
            g["flags"].add("missing_pages:" + ",".join(map(str, missing)))
        if n_expected and any(t != n_expected for t in totals):
            g["flags"].add("page_count_mismatch")
    return groups


@stage("group")
def group(conn, job):
    bid = job["batch_id"]
    b = db.row(conn.execute("SELECT * FROM batch WHERE id=?", (bid,)).fetchone())
    t = db.row(conn.execute("SELECT * FROM test WHERE id=?", (b["test_id"],)).fetchone())
    pages = []
    for p in db.rows(conn.execute("SELECT * FROM page WHERE batch_id=? ORDER BY seq", (bid,))):
        if p["status"] not in ("prepped", "unregistered"):
            break  # only the contiguous processed prefix; later pages wait for the next run
        pages.append(p)
    all_in = len(pages) == b["total_pages"]
    groups = build_groups(pages, t["pages_per_paper"])
    existing = {json.loads(r["page_ids"])[0]: db.row(r) for r in conn.execute("SELECT * FROM paper WHERE batch_id=?", (bid,))
                if json.loads(r["page_ids"])}
    keep = set()
    conn.execute("BEGIN IMMEDIATE")
    for i, g in enumerate(groups):
        ids = [p["id"] for p in g["pages"]]
        closed = i < len(groups) - 1 or (b["finished"] and all_in) or g["complete"]
        flags = sorted(g["flags"])
        old = existing.get(ids[0])
        if old is None:
            pid = conn.execute("INSERT INTO paper(batch_id, page_ids, page_paths, flags, status) VALUES (?,?,?,?,?)",
                               (bid, json.dumps(ids), json.dumps([p["path"] for p in g["pages"]]), json.dumps(flags),
                                "closed" if closed else "open")).lastrowid
            changed = True
        else:
            pid = old["id"]
            changed = old["page_ids"] != ids or (old["status"] == "open" and closed)
            status = ("closed" if closed else "open") if changed or old["status"] == "open" else old["status"]
            if not changed:  # keep identity flags from the last grade
                flags = sorted(set(flags) | {f for f in old["flags"] if f.startswith("id_")})
            conn.execute("UPDATE paper SET page_ids=?, page_paths=?, flags=?, status=? WHERE id=?",
                         (json.dumps(ids), json.dumps([p["path"] for p in g["pages"]]), json.dumps(flags), status, pid))
        keep.add(pid)
        if closed and changed:
            enqueue_once(conn, "grade", bid, pid)
    for old in existing.values():
        if old["id"] not in keep:
            conn.execute("DELETE FROM response WHERE paper_id=?", (old["id"],))
            conn.execute("DELETE FROM paper WHERE id=?", (old["id"],))
    conn.execute("UPDATE batch SET total_papers=? WHERE id=?", (len(groups), bid))
    conn.execute("COMMIT")
    maybe_done(conn, bid)
