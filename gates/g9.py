"""G9: the 600-paper stress batch completes without crash; a run hard-killed mid-way and resumed gives identical
results to an uninterrupted run; peak memory, throughput (papers/min) and estimated cloud cost per 500 papers recorded.
Both runs go in parallel processes (cuts wall time; throughput is measured under that shared load, so it is conservative)."""
import json, math, sqlite3, subprocess, sys, time

import harness
from common import FIX, PY, ROOT, log

SEED = 7
KILL_AT = 0.4  # fraction of papers graded when the second run is killed
PRICE_IN, PRICE_OUT = 4.00, 20.00  # USD per million tokens, claude-opus-5-5 (claude-api skill, cached 2026-11-03)
OUT_TOKENS_PER_CROP = 200  # assumption: short JSON reply plus adaptive thinking at default (medium) effort
PROMPT_TOKENS = 110  # instruction text of CloudProvider.transcribe, about 4 characters per token


def run(data, resume=False):
    args = [PY, str(ROOT / "gates" / "g9_run.py"), "--data", str(data), "--seed", str(SEED)] + (["--resume"] if resume else [])
    return subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, text=True)


def result(proc):
    out = proc.communicate()[0].strip().splitlines()
    return json.loads(out[-1])


def dump(data):
    """Canonical, id-free view of everything the pipeline produced."""
    c = sqlite3.connect(data / "scanner.db")
    seq = dict(c.execute("SELECT id, seq FROM page"))
    papers, firsts = [], {}
    for pid, ids, ref, sid, year, sec, flags, status in c.execute(
            "SELECT id, page_ids, student_ref, student_id_local, student_year_local, student_section_local, flags, status FROM paper"):
        seqs = [seq[i] for i in json.loads(ids)]
        firsts[pid] = seqs[0]
        papers.append([seqs, ref, sid, year, sec, sorted(json.loads(flags)), status])
    resp = [[firsts[p], q, a, raw, s, fs, round(conf or 0, 4), nr] for p, q, a, raw, s, fs, conf, nr in c.execute(
        "SELECT r.paper_id, q.number, r.normalized_answer, r.raw_read, r.score, r.final_score, r.confidence, r.needs_review"
        " FROM response r JOIN question q ON q.id=r.question_id")]
    return sorted(papers), sorted(resp, key=lambda r: (r[0], r[1]))


def cost_per_500(data, papers):
    """Cloud mode sends one redacted crop per written answer (MCQ and identity stay local). Image tokens ~ w*h/750."""
    c = sqlite3.connect(data / "scanner.db")
    tokens_in = n = 0
    for crop, text in c.execute("SELECT r.crop, q.text FROM response r JOIN question q ON q.id=r.question_id WHERE q.type='written'"):
        x0, y0, x1, y1 = json.loads(crop)["box"]
        w, h = (x1 - x0) - 10, (y1 - y0 - 40) - 10  # transcribe gets the box interior, not the question line
        tokens_in += math.ceil(w * h / 750) + PROMPT_TOKENS + len(text) // 4
        n += 1
    per_paper = (tokens_in * PRICE_IN + n * OUT_TOKENS_PER_CROP * PRICE_OUT) / 1e6 / papers
    return round(per_paper * 500, 2), n


def main():
    truth = json.loads((FIX / f"seed{SEED}" / "math8" / "stress" / "truth.json").read_text())
    expected = len(truth["papers"])
    ref_dir, kill_dir = harness.eval_dir("g9-ref"), harness.eval_dir("g9-kill")
    t = time.time()
    ref, victim = run(ref_dir), run(kill_dir)
    graded_at_kill = 0
    while victim.poll() is None:
        try:
            graded_at_kill = sqlite3.connect(kill_dir / "scanner.db").execute(
                "SELECT COUNT(*) FROM paper WHERE status='graded'").fetchone()[0]
        except sqlite3.Error:
            pass
        if graded_at_kill >= KILL_AT * expected:
            victim.kill()  # hard kill: no cleanup, jobs left 'running'
            victim.wait()
            break
        time.sleep(1)
    print(f"killed second run at {graded_at_kill} graded papers; resuming")
    resumed = run(kill_dir, resume=True)
    r_ref, r_res = result(ref), result(resumed)
    print(f"reference: {r_ref}\nresumed:   {r_res}\nwall {time.time() - t:.0f}s")
    same = dump(ref_dir) == dump(kill_dir)
    throughput = r_ref["papers"] / (r_ref["process_s"] / 60)
    cost, crops = cost_per_500(ref_dir, r_ref["papers"])
    print(f"written crops that cloud mode would send: {crops}")
    if SEED != 7:
        return
    done = r_ref["papers"] == r_ref["papers_total"] and r_ref["failed_jobs"] == 0
    ok = log("G9", "stress_all_papers_graded", f"{r_ref['papers']}/{r_ref['papers_total']} (truth {expected})", done)
    ok &= log("G9", "killed_at_graded_papers", graded_at_kill, 0 < graded_at_kill < expected)
    ok &= log("G9", "kill_resume_identical", int(same), same)
    ok &= log("G9", "peak_memory_mb", r_ref["peak_mb"], r_ref["peak_mb"] < 4096)
    log("G9", "throughput_papers_per_min", round(throughput, 1), True)
    log("G9", "est_cloud_cost_usd_per_500_papers", cost, True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main()
