"""G5: MCQ per-answer accuracy >= 95% on fixtures; clean and noisy scans reported separately.
usage: python gates/g5.py [seed]  (seed != 7 is a dev run and is not logged)"""
import sys

import harness
from common import log

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7


def main():
    runs = harness.full_run(SEED)
    stats = {"clean": [0, 0], "noisy": [0, 0]}
    errors = []
    for tid, (bid, truth, tj) in runs.items():
        by_file, resp = harness.responses(bid)
        page_of = harness.gt_page_of(tj)
        for gp in truth["papers"]:
            pages = {pg["page"]: pg for pg in gp["pages"] if not pg["duplicate"]}
            for r in gp["responses"]:
                if r["marked"] is None:
                    continue  # written
                pg = pages.get(page_of[r["number"]])
                if pg is None:
                    continue  # page missing from the batch: nothing to read
                sp = by_file.get(pg["file"])
                got = resp.get((sp["id"], r["number"])) if sp else None
                read = got["normalized_answer"] if got else None
                ok = read == r["marked"]
                stats[pg["quality"]][0] += ok
                stats[pg["quality"]][1] += 1
                if not ok:
                    errors.append((tid, gp["index"], r["number"], r["marked"], r["mark_style"], read, pg["quality"]))
    for e in errors[:20]:
        print("  wrong:", e)
    total = [sum(v[i] for v in stats.values()) for i in (0, 1)]
    acc = total[0] / total[1]
    clean, noisy = (stats[k][0] / stats[k][1] for k in ("clean", "noisy"))
    print(f"MCQ answers={total[1]} acc={acc:.4f} clean={clean:.4f} (n={stats['clean'][1]}) noisy={noisy:.4f} (n={stats['noisy'][1]})")
    if SEED != 7:
        return
    ok = log("G5", "mcq_accuracy", acc, acc >= 0.95)
    log("G5", "mcq_accuracy_clean", clean, True)
    log("G5", "mcq_accuracy_noisy", noisy, True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
