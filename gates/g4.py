"""G4: >=95% papers grouped correctly; >=90% student refs (IDs) read correctly; every unreadable item flagged; 0 pages dropped.
usage: python gates/g4.py [seed]   (default seed 7 = gate seed; use 11 for dev tuning, it is not logged)"""
import sys, time

import harness
from common import FIX, log

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
TESTS = ["sci7", "math8", "hist9"]


def evaluate(bid, truth):
    papers = harness.system_papers(bid)
    sets = {frozenset(files): p for p, files in papers}
    by_file = {f: p for p, files in papers for f in files}
    s = dict(gt_papers=0, grouped=0, id_total=0, id_ok=0, id_wrong_unflagged=0, unreadable=0, unreadable_flagged=0,
             anomalies=0, anomalies_flagged=0, dropped=0, year_total=0, year_ok=0, section_total=0, section_ok=0)
    for gp in truth["papers"]:
        files = [pg["file"] for pg in gp["pages"]]
        s["gt_papers"] += 1
        s["grouped"] += frozenset(files) in sets
        s["dropped"] += sum(f not in by_file for f in files)
        p1 = next((pg["file"] for pg in gp["pages"] if pg["page"] == 1 and not pg["duplicate"]), None)
        sp = by_file.get(p1 or files[0])
        if sp is None:
            continue
        id_flagged = any(f.startswith("id_") for f in sp["flags"])
        if p1:
            for f, col in (("year", "student_year_local"), ("section", "student_section_local")):
                s[f"{f}_total"] += 1
                s[f"{f}_ok"] += (sp[col] or "").lower() == gp[f].lower()
        if gp["id_written"] and p1:
            s["id_total"] += 1
            ok = sp["student_id_local"] == gp["student_id"]
            s["id_ok"] += ok
            s["id_wrong_unflagged"] += (not ok) and not id_flagged
        else:
            s["unreadable"] += 1
            s["unreadable_flagged"] += id_flagged
            if not id_flagged:
                print("  UNFLAGGED unreadable:", gp["index"], sp["flags"], sp["student_id_local"])
        if gp["missing_pages"] or any(pg["duplicate"] for pg in gp["pages"]):
            s["anomalies"] += 1
            s["anomalies_flagged"] += any(f.startswith(("missing", "duplicate")) for f in sp["flags"])
    s["dropped"] += sum(1 for p, files in papers if not files)
    return s


def main():
    tot = {}
    if True:
        client = harness.setup_app(harness.eval_dir(f"g4-seed{SEED}"))
        for tid in TESTS:
            tdir = FIX / f"seed{SEED}" / tid
            t = time.time()
            test_id = harness.create_test(client, tdir)
            bid, truth = harness.run_batch(client, test_id, tdir / "main")
            n, failed = harness.drain()
            s = evaluate(bid, truth)
            s["failed_jobs"] = failed
            print(f"{tid}: {s}  ({n} jobs, {time.time() - t:.0f}s)")
            for k, v in s.items():
                tot[k] = tot.get(k, 0) + v
    grouped = tot["grouped"] / tot["gt_papers"]
    ids = tot["id_ok"] / tot["id_total"]
    unflagged = tot["unreadable"] - tot["unreadable_flagged"]
    print("total:", tot)
    if SEED != 7:
        print(f"dev seed {SEED}: grouped={grouped:.4f} ids={ids:.4f} unflagged={unflagged} dropped={tot['dropped']} (not logged)")
        return
    ok = log("G4", "grouping_accuracy", grouped, grouped >= 0.95)
    ok &= log("G4", "student_id_accuracy", ids, ids >= 0.90)
    ok &= log("G4", "unreadable_unflagged", unflagged, unflagged == 0)
    ok &= log("G4", "pages_dropped", tot["dropped"], tot["dropped"] == 0)
    log("G4", "anomalies_flagged_frac", tot["anomalies_flagged"] / max(1, tot["anomalies"]), True)
    log("G4", "id_wrong_unflagged", tot["id_wrong_unflagged"], True)
    log("G4", "year_accuracy", tot["year_ok"] / tot["year_total"], True)
    log("G4", "section_accuracy", tot["section_ok"] / tot["section_total"], True)
    log("G4", "failed_jobs", tot["failed_jobs"], tot["failed_jobs"] == 0)
    sys.exit(0 if ok and tot["failed_jobs"] == 0 else 1)


if __name__ == "__main__":
    main()
