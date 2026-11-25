"""E2E helper: fill a fresh data dir with a test whose review queue holds N items (default 500), each with a real
answer crop. Prints the batch id. usage: python gates/seed_review.py <data dir> [n]"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def main():
    os.environ["SCANNER_DATA"] = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    from app import db
    from app.parse import parse_key
    db.init()
    c = db.connect()
    tdir = ROOT / "fixtures" / "out" / "seed7" / "hist9"
    tid = c.execute("INSERT INTO test(name, subject, pages_per_paper) VALUES ('Review load test', 'Humanities', 4)").lastrowid
    for q in parse_key((tdir / "key.txt").read_text()):
        c.execute("INSERT INTO question(test_id, number, type, max_points, correct_answer, key_source, text) VALUES (?,?,?,?,?,?,?)",
                  (tid, q["number"], q["type"], q["max_points"], q["correct_answer"], q["key_source"], q["text"]))
    written = [r for r in c.execute("SELECT id, number FROM question WHERE test_id=? AND type='written'", (tid,))]
    layout = {it["number"]: it["box"] for pg in json.loads((tdir / "test.json").read_text())["layout"] for it in pg["items"]}
    bid = c.execute("INSERT INTO batch(test_id, status, finished) VALUES (?, 'done', 1)", (tid,)).lastrowid
    identity = json.dumps([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    page = c.execute("INSERT INTO page(batch_id, seq, path, sha256, homography, page_no, status) VALUES (?,1,?,?,?,2,'prepped')",
                     (bid, str(tdir / "main" / "pages" / "000002.jpg"), "seed", identity)).lastrowid
    papers = (n + len(written) - 1) // len(written)
    made = 0
    for p in range(papers):
        pid = c.execute("INSERT INTO paper(batch_id, student_ref, page_ids, status, flags) VALUES (?,?,?, 'graded', '[]')",
                        (bid, f"S-{p + 1:04d}", json.dumps([page]))).lastrowid
        for qid, num in written:
            if made == n:
                break
            x0, y0, x1, y1 = layout[num]
            c.execute("INSERT INTO response(paper_id, question_id, raw_read, normalized_answer, is_correct, score, final_score,"
                      " confidence, needs_review, crop) VALUES (?,?,?,?,0,0,0,?,1,?)",
                      (pid, qid, "unclear", "unclear", round(0.3 + (made % 50) / 100, 2), json.dumps({"page_id": page, "box": [x0, y0, x1, y1]})))
            made += 1
    print(json.dumps({"test_id": tid, "batch_id": bid, "items": made}))


if __name__ == "__main__":
    main()
