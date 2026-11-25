"""Evaluation harness: push a fixture batch through the real API + pipeline in-process.
Ground truth is read only by the gate scripts, never passed to the app."""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "fixtures")]


def eval_dir(name):
    """Fresh, gitignored data dir for one gate run (kept afterwards for inspection)."""
    import shutil
    d = ROOT / "data" / "eval" / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def setup_app(data_dir: Path, provider="local"):
    os.environ["SCANNER_DATA"] = str(data_dir)
    from fastapi.testclient import TestClient
    from app import db, main
    db.init()
    client = TestClient(main.app)  # no lifespan => no background worker; we drive jobs ourselves
    client.put("/api/settings", json={"provider": provider})
    return client


def create_test(client, tdir: Path):
    t = json.loads((tdir / "test.json").read_text())
    tid = client.post("/api/tests", json={"name": t["name"], "subject": t["subject"],
                                          "pages_per_paper": t["pages_per_paper"]}).json()["id"]
    for ep, f in (("key", "key.txt"), ("syllabus", "syllabus.txt")):
        r = client.post(f"/api/tests/{tid}/{ep}", json={"text": (tdir / f).read_text()})
        assert r.status_code == 200, r.text
    r = client.put(f"/api/tests/{tid}/redaction", json=json.loads((tdir / "redaction.json").read_text()))
    assert r.status_code == 200, r.text
    return tid


def drain(verbose=True):
    from app import db, jobs
    conn = db.connect()
    n, t = 0, time.time()
    while jobs.run_one(conn):
        n += 1
        if verbose and n % 200 == 0:
            print(f"  {n} jobs, {time.time() - t:.0f}s", flush=True)
    failed = conn.execute("SELECT stage, error FROM job WHERE status='failed'").fetchall()
    for f in failed[:5]:
        print("FAILED JOB", f[0], f[1][-800:])
    return n, len(failed)


def run_batch(client, tid, bdir: Path, finish=True):
    from app import db, ingest
    truth = json.loads((bdir / "truth.json").read_text())
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    conn = db.connect()
    for f in truth["scan_order"]:
        ingest.ingest(conn, bid, f, (bdir / "pages" / f).read_bytes())
    if finish:
        client.post(f"/api/batches/{bid}/finish")
    return bid, truth


def system_papers(bid):
    """[(paper row, [scan-order file names])] using seq -> scan_order index."""
    from app import db
    conn = db.connect()
    seq_of = {r["id"]: r["seq"] for r in conn.execute("SELECT id, seq FROM page WHERE batch_id=?", (bid,))}
    out = []
    for p in db.rows(conn.execute("SELECT * FROM paper WHERE batch_id=? ORDER BY id", (bid,))):
        out.append((p, [f"{seq_of[i]:06d}.jpg" for i in p["page_ids"]]))
    return out


def full_run(seed: int, tests=("sci7", "math8", "hist9"), provider="local"):
    """Run every main batch of a seed through the pipeline once per commit; reuse the DB if the code is unchanged.
    Returns {test_id: (bid, truth, test_json)}."""
    from common import FIX, commit
    name = f"full-seed{seed}-{provider}"
    d = ROOT / "data" / "eval" / name
    stamp = d / "commit.txt"
    c = commit()
    reuse = stamp.exists() and stamp.read_text() == c and not c.endswith("-dirty")
    if not reuse:
        d = eval_dir(name)
    client = setup_app(d, provider)
    out = {}
    for i, tid in enumerate(tests):
        tdir = FIX / f"seed{seed}" / tid
        test_json = json.loads((tdir / "test.json").read_text())
        if reuse:
            bid = i + 1
            truth = json.loads((tdir / "main" / "truth.json").read_text())
        else:
            t = time.time()
            test_id = create_test(client, tdir)
            bid, truth = run_batch(client, test_id, tdir / "main")
            n, failed = drain()
            print(f"  {tid}: {n} jobs, {failed} failed, {time.time() - t:.0f}s", flush=True)
        out[tid] = (bid, truth, test_json)
    if not reuse:
        stamp.write_text(c)
    return out


def responses(bid):
    """{(scan-order file of the paper's first page, question number): response row}, plus paper rows by file."""
    from app import db
    conn = db.connect()
    papers = system_papers(bid)
    by_file = {f: p for p, files in papers for f in files}
    resp = {}
    for p, files in papers:
        for r in db.rows(conn.execute("SELECT r.*, q.number FROM response r JOIN question q ON q.id=r.question_id"
                                      " WHERE r.paper_id=?", (p["id"],))):
            resp[(p["id"], r["number"])] = r
    return by_file, resp


def gt_page_of(test_json):
    return {it["number"]: pg["page"] for pg in test_json["layout"] for it in pg["items"]}
