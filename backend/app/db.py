"""SQLite storage. One connection per thread/request; WAL so the worker and API don't block each other."""
import json, os, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = """
CREATE TABLE IF NOT EXISTS test(
  id INTEGER PRIMARY KEY, subject TEXT NOT NULL DEFAULT '', name TEXT NOT NULL, pages_per_paper INTEGER,
  redaction_regions TEXT NOT NULL DEFAULT '[]', sample_page TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS syllabus_topic(
  id INTEGER PRIMARY KEY, test_id INTEGER NOT NULL REFERENCES test(id), code TEXT NOT NULL, title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '', reteach TEXT);
CREATE TABLE IF NOT EXISTS question(
  id INTEGER PRIMARY KEY, test_id INTEGER NOT NULL REFERENCES test(id), number INTEGER NOT NULL,
  type TEXT NOT NULL CHECK(type IN ('mcq','written')), max_points INTEGER NOT NULL DEFAULT 1, correct_answer TEXT,
  key_source TEXT NOT NULL CHECK(key_source IN ('key','ai')), topic_id INTEGER REFERENCES syllabus_topic(id),
  topic_confidence REAL, text TEXT NOT NULL DEFAULT '', UNIQUE(test_id, number));
CREATE TABLE IF NOT EXISTS batch(
  id INTEGER PRIMARY KEY, test_id INTEGER NOT NULL REFERENCES test(id),
  status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','paused','done','failed')),
  total_pages INTEGER NOT NULL DEFAULT 0, total_papers INTEGER NOT NULL DEFAULT 0, finished INTEGER NOT NULL DEFAULT 0,
  watch_folder TEXT, last_error TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS page(
  id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES batch(id), seq INTEGER NOT NULL, path TEXT NOT NULL,
  sha256 TEXT NOT NULL, homography TEXT, page_no INTEGER, page_total INTEGER, rotated INTEGER, status TEXT NOT NULL DEFAULT 'new',
  UNIQUE(batch_id, sha256));
CREATE TABLE IF NOT EXISTS paper(
  id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES batch(id), student_ref TEXT, student_name_local TEXT,
  student_id_local TEXT, student_year_local TEXT, student_section_local TEXT, id_confidence REAL, page_paths TEXT NOT NULL DEFAULT '[]', page_ids TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'open', flags TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS response(
  id INTEGER PRIMARY KEY, paper_id INTEGER NOT NULL REFERENCES paper(id), question_id INTEGER NOT NULL REFERENCES question(id),
  raw_read TEXT, normalized_answer TEXT, is_correct INTEGER, score REAL, confidence REAL, needs_review INTEGER NOT NULL DEFAULT 0,
  reviewed INTEGER NOT NULL DEFAULT 0, final_score REAL, crop TEXT, UNIQUE(paper_id, question_id));
CREATE TABLE IF NOT EXISTS job(
  id INTEGER PRIMARY KEY, batch_id INTEGER, paper_id INTEGER, page_id INTEGER, stage TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','done','failed')),
  attempts INTEGER NOT NULL DEFAULT 0, error TEXT, started_at REAL, finished_at REAL);
CREATE INDEX IF NOT EXISTS job_status ON job(status, id);
CREATE INDEX IF NOT EXISTS response_review ON response(needs_review, reviewed);
CREATE TABLE IF NOT EXISTS settings(
  id INTEGER PRIMARY KEY CHECK(id = 1), provider TEXT NOT NULL DEFAULT 'local', confidence_threshold REAL NOT NULL DEFAULT 0.8,
  cloud_model TEXT NOT NULL DEFAULT 'claude-opus-5-5', local_model TEXT NOT NULL DEFAULT 'rapidocr-ppocr',
  watch_folder TEXT, show_names INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO settings(id) VALUES (1);
CREATE TABLE IF NOT EXISTS provider_model(
  provider TEXT NOT NULL, model TEXT NOT NULL, PRIMARY KEY(provider, model));
"""


def data_dir() -> Path:
    d = Path(os.environ.get("SCANNER_DATA", ROOT / "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def connect() -> sqlite3.Connection:
    c = sqlite3.connect(data_dir() / "scanner.db", timeout=30, isolation_level=None, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=30000")
    return c


# Columns added after the first release: (table, column, type). Added in place so existing data survives.
MIGRATIONS = [("batch", "watch_folder", "TEXT"), ("page", "homography", "TEXT"), ("response", "crop", "TEXT"),
              ("job", "started_at", "REAL"), ("job", "finished_at", "REAL"),
              ("paper", "student_year_local", "TEXT"), ("paper", "student_section_local", "TEXT"),
              ("batch", "last_error", "TEXT"), ("syllabus_topic", "reteach", "TEXT"),
              ("settings", "openrouter_model", "TEXT NOT NULL DEFAULT 'openrouter/auto'"),
              ("settings", "nvidia_model", "TEXT NOT NULL DEFAULT 'qwen/qwen3.5-122b-a10b'"),
              ("job", "not_before", "REAL NOT NULL DEFAULT 0")]


def init():
    with connect() as c:
        c.executescript(SCHEMA)
        for table, col, typ in MIGRATIONS:
            if col not in {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        c.execute("""INSERT OR IGNORE INTO provider_model(provider, model)
                     SELECT 'openrouter', openrouter_model FROM settings UNION ALL
                     SELECT 'nvidia', nvidia_model FROM settings""")


def row(r):
    if r is None:
        return None
    d = dict(r)
    for k in ("redaction_regions", "page_paths", "page_ids", "flags"):
        if k in d and isinstance(d[k], str):
            d[k] = json.loads(d[k])
    return d


def rows(rs):
    return [row(r) for r in rs]
