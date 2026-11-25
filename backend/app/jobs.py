"""SQLite-backed job queue + single worker thread. Jobs left 'running' by a crash are requeued on start."""
import os, threading, time, traceback

from . import db
from .provider_keys import MissingProviderKeys, PoolLimited

STAGES = {}
NOW = "((julianday('now') - 2440587.5) * 86400.0)"  # unix seconds, sub-second
MAX_ATTEMPTS = 3


def stage(name):
    def deco(fn):
        STAGES[name] = fn
        return fn
    return deco


@stage("selftest")
def _selftest(conn, job):  # used by the restart test
    time.sleep(float(os.environ.get("SCANNER_SELFTEST_SLEEP", "2")))


def enqueue(conn, stage_name, batch_id=None, paper_id=None, page_id=None):
    return conn.execute("INSERT INTO job(stage, batch_id, paper_id, page_id) VALUES (?,?,?,?)",
                        (stage_name, batch_id, paper_id, page_id)).lastrowid


def claim(conn):
    return conn.execute(
        f"UPDATE job SET status='running', attempts=attempts+1, started_at={NOW} WHERE id = ("
        " SELECT j.id FROM job j LEFT JOIN batch b ON b.id = j.batch_id"
        f" WHERE j.status='queued' AND j.not_before <= {NOW} AND (b.status IS NULL OR b.status != 'paused') ORDER BY j.id LIMIT 1)"
        " RETURNING *").fetchone()


def run_one(conn):
    job = claim(conn)
    if job is None:
        return False
    try:
        STAGES[job["stage"]](conn, job)
        conn.execute(f"UPDATE job SET status='done', error=NULL, finished_at={NOW} WHERE id=?", (job["id"],))
    except (PoolLimited, MissingProviderKeys) as e:
        conn.execute("UPDATE job SET status='queued', attempts=attempts-1, not_before=?, error=? WHERE id=?",
                     (e.until, str(e), job["id"]))
    except Exception:
        err = traceback.format_exc(limit=5)
        status = "failed" if job["attempts"] >= MAX_ATTEMPTS else "queued"
        conn.execute("UPDATE job SET status=?, error=? WHERE id=?", (status, err, job["id"]))
    return True


class Worker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="worker")
        self.stopping = threading.Event()

    def run(self):
        conn = db.connect()
        conn.execute("UPDATE job SET status='queued' WHERE status='running'")  # recover from crash
        while not self.stopping.is_set():
            if not run_one(conn):
                self.stopping.wait(0.1)
        conn.close()
