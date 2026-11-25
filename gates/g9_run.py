"""G9 worker process: ingest the 600-paper stress batch (skipped with --resume), then process it with the app's real
Worker thread (the same crash recovery as the server). Prints one JSON line: papers, seconds, peak memory."""
import argparse, json, time
from pathlib import Path

import psutil

import harness
from common import FIX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    client = harness.setup_app(Path(a.data))
    t_ingest = time.time()
    if not a.resume:
        tdir = FIX / f"seed{a.seed}" / "math8"
        test_id = harness.create_test(client, tdir)
        harness.run_batch(client, test_id, tdir / "stress")
    from app import db, jobs
    conn = db.connect()
    t0 = time.time()
    w = jobs.Worker()
    w.start()  # requeues anything a killed run left 'running'
    idle = 0
    while idle < 3:  # three empty polls in a row: the queue is drained
        busy = conn.execute("SELECT COUNT(*) FROM job WHERE status IN ('queued','running')").fetchone()[0]
        idle = idle + 1 if busy == 0 else 0
        time.sleep(0.5)
    w.stopping.set()
    w.join(timeout=30)
    mem = psutil.Process().memory_info()
    print(json.dumps({
        "papers": conn.execute("SELECT COUNT(*) FROM paper WHERE status='graded'").fetchone()[0],
        "papers_total": conn.execute("SELECT COUNT(*) FROM paper").fetchone()[0],
        "pages": conn.execute("SELECT COUNT(*) FROM page").fetchone()[0],
        "failed_jobs": conn.execute("SELECT COUNT(*) FROM job WHERE status='failed'").fetchone()[0],
        "ingest_s": round(t0 - t_ingest, 1), "process_s": round(time.time() - t0, 1),
        "peak_mb": round(getattr(mem, "peak_wset", mem.rss) / 2**20, 1),
    }), flush=True)


if __name__ == "__main__":
    main()
