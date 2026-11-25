"""G6: written agreement >= 85% overall; >= 95% for answers at/above the confidence threshold;
every below-threshold answer is in the review queue (checked through the API).
usage: python gates/g6.py [seed]  (seed != 7 is a dev run and is not logged)"""
import sys

import harness
from common import log

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
THR = 0.80  # SPEC default; the app reads its own copy from settings


def main():
    runs = harness.full_run(SEED)
    from fastapi.testclient import TestClient
    from app import db, main as app_main
    client = TestClient(app_main.app)
    n = agree = hi_n = hi_agree = 0
    missing_from_queue, low_total, errors = 0, 0, []
    for tid, (bid, truth, tj) in runs.items():
        by_file, resp = harness.responses(bid)
        page_of = harness.gt_page_of(tj)
        queue = client.get(f"/api/batches/{bid}/review", params={"page_size": 100000, "status": "pending"}).json()
        queued = {it["response_id"] for it in queue["items"] if it["kind"] == "response"}
        conn = db.connect()
        for r in conn.execute("SELECT r.id FROM response r JOIN paper p ON p.id=r.paper_id WHERE p.batch_id=?"
                              " AND r.confidence < ? AND r.reviewed=0", (bid, THR)):
            low_total += 1
            missing_from_queue += r[0] not in queued
        for gp in truth["papers"]:
            pages = {pg["page"]: pg for pg in gp["pages"] if not pg["duplicate"]}
            for r in gp["responses"]:
                if r["text"] is None:
                    continue  # mcq
                pg = pages.get(page_of[r["number"]])
                if pg is None:
                    continue
                sp = by_file.get(pg["file"])
                got = resp.get((sp["id"], r["number"])) if sp else None
                ok = got is not None and got["score"] == r["score"]
                n += 1
                agree += ok
                if got is not None and got["confidence"] >= THR:
                    hi_n += 1
                    hi_agree += ok
                    if not ok:
                        errors.append((tid, gp["index"], r["number"], r["text"], r["score"], got["raw_read"], got["score"], round(got["confidence"], 3)))
    for e in errors[:25]:
        print("  confident & wrong:", e)
    overall, hi = agree / n, hi_agree / max(1, hi_n)
    print(f"written={n} agreement={overall:.4f} high_conf={hi_n} ({hi_n / n:.2%}) high_conf_agreement={hi:.4f}"
          f" low_conf={low_total} missing_from_queue={missing_from_queue}")
    if SEED != 7:
        return
    ok = log("G6", "written_agreement", overall, overall >= 0.85)
    ok &= log("G6", "high_conf_agreement", hi, hi >= 0.95)
    log("G6", "high_conf_fraction", hi_n / n, True)
    ok &= log("G6", "low_conf_missing_from_queue", missing_from_queue, missing_from_queue == 0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
