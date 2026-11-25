"""G8: topic mapping >= 90%; per-topic miss rates exact (app aggregation on ground-truth inputs vs plain arithmetic);
top-3 weak topics match ground truth after the review queue is resolved (simulated teacher, through the API);
PDF has all four sections and no student names/IDs. Ground truth only counts questions on pages that were scanned.
usage: python gates/g8.py [seed]   (seed != 7 is not logged)"""
import sys

import pymupdf as fitz

import harness
from common import log

SEED = 7


def gt_inputs(truth, tj):
    """Per (paper index, question): score, counting only questions whose page was scanned."""
    page_of, qmax = harness.gt_page_of(tj), {q["number"]: q["max_points"] for q in tj["questions"]}
    out = []
    for gp in truth["papers"]:
        present = {pg["page"] for pg in gp["pages"]}
        out += [(gp, r) for r in gp["responses"] if page_of[r["number"]] in present]
    return out, qmax


def gt_topic_rates(inputs, qmax, topic_of):
    lost, poss = {}, {}
    for _, r in inputs:
        t = topic_of[r["number"]]
        lost[t] = lost.get(t, 0) + qmax[r["number"]] - r["score"]
        poss[t] = poss.get(t, 0) + qmax[r["number"]]
    return {t: lost[t] / poss[t] for t in poss}


def main():
    from fastapi.testclient import TestClient
    from app import analysis, db, main as app_main
    from app.report_pdf import SECTIONS
    runs = harness.full_run(SEED)
    client = TestClient(app_main.app)
    m = {"mapped_ok": 0, "questions": 0, "exact_diff": 0.0, "e2e_diff": 0.0, "top3_ok": 0, "tests": 0, "pdf_ok": 0, "pdf_leaks": 0}
    for i, (tid, (bid, truth, tj)) in enumerate(runs.items(), start=1):
        test_id = i
        conn = db.connect()
        client.get(f"/api/tests/{test_id}/report")  # runs topic mapping
        app_topic = {r[0]: r[1] for r in conn.execute(
            "SELECT q.number, s.code FROM question q LEFT JOIN syllabus_topic s ON s.id=q.topic_id WHERE q.test_id=?", (test_id,))}
        gt_topic = {q["number"]: q["topic"] for q in tj["questions"]}
        m["questions"] += len(gt_topic)
        m["mapped_ok"] += sum(app_topic[n] == t for n, t in gt_topic.items())
        # simulated teacher clears the review queue with the true answers
        by_file, resp = harness.responses(bid)
        sys_to_gt = {by_file[pg["file"]]["id"]: gp for gp in truth["papers"] for pg in gp["pages"] if pg["file"] in by_file}
        queue = client.get(f"/api/batches/{bid}/review", params={"page_size": 100000}).json()["items"]
        for it in queue:
            gp = sys_to_gt[it["paper_id"]]
            if it["kind"] == "response":
                true = next(r["score"] for r in gp["responses"] if r["number"] == it["question"])
                client.patch(f"/api/responses/{it['response_id']}", json={"final_score": true})
            else:
                client.patch(f"/api/papers/{it['paper_id']}", json={"student_id": gp["student_id"] or "000000",
                                                                       "year": gp["year"], "section": gp["section"]})
        report = client.get(f"/api/tests/{test_id}/report").json()
        inputs, qmax = gt_inputs(truth, tj)
        gt_rates = gt_topic_rates(inputs, qmax, gt_topic)
        # exactness of the aggregation itself: ground-truth scores + ground-truth topics through analysis.aggregate
        qs = [{"id": n, "number": n, "max_points": qmax[n], "topic_code": gt_topic[n]} for n in gt_topic]
        rs = [{"question_id": r["number"], "final_score": r["score"], "normalized_answer": None, "is_correct": r["is_correct"]}
              for _, r in inputs]
        _, trows = analysis.aggregate(qs, rs)
        m["exact_diff"] = max(m["exact_diff"], max(abs(t["miss_rate"] - gt_rates[t["code"]]) for t in trows))
        app_rates = {t["code"]: t["miss_rate"] for t in report["topics"]}
        m["e2e_diff"] = max(m["e2e_diff"], max(abs(app_rates.get(c, 1.0) - v) for c, v in gt_rates.items()))
        gt_top3 = [c for c, _ in sorted(gt_rates.items(), key=lambda kv: (-kv[1], kv[0]))][:3]
        app_top3 = [t["code"] for t in report["topics"]][:3]
        m["tests"] += 1
        m["top3_ok"] += app_top3 == gt_top3
        print(f"{tid}: provisional={report['provisional']} top3 app={app_top3} gt={gt_top3} "
              f"rates={ {c: round(v, 3) for c, v in gt_rates.items()} }")
        pdf = client.get(f"/api/tests/{test_id}/report.pdf").content
        text = "".join(p.get_text() for p in fitz.open(stream=pdf, filetype="pdf"))
        m["pdf_ok"] += all(s in text for s in SECTIONS)
        m["pdf_leaks"] += sum(gp["student_name"] in text or gp["student_id"] in text for gp in truth["papers"])
    acc = m["mapped_ok"] / m["questions"]
    print(m)
    if SEED != 7:
        return
    ok = log("G8", "topic_mapping_accuracy", acc, acc >= 0.90)
    ok &= log("G8", "topic_miss_rate_max_abs_diff", m["exact_diff"], m["exact_diff"] < 1e-12)
    ok &= log("G8", "top3_weak_topics_match", f"{m['top3_ok']}/{m['tests']}", m["top3_ok"] == m["tests"])
    ok &= log("G8", "pdf_four_sections", f"{m['pdf_ok']}/{m['tests']}", m["pdf_ok"] == m["tests"])
    ok &= log("G8", "pdf_identity_leaks", m["pdf_leaks"], m["pdf_leaks"] == 0)
    log("G8", "end_to_end_topic_rate_max_abs_diff", m["e2e_diff"], True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main()
