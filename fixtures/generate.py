"""Deterministic fixture generator: printed tests + handwritten answers + scan noise + ground truth.

python fixtures/generate.py --seed 7 --out fixtures/out/seed7 [--papers 30] [--stress 600] [--tests sci7,math8]
Same seed + same machine fonts => byte-identical output (checked by gates/g0.py)."""
import argparse, hashlib, io, json, math, sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import FIRST, LAST, TESTS  # noqa: E402
from render import FONTS, HANDS, IDENTITY, H, W, R_, draw_template, layout, printed_text, render_page  # noqa: E402
from schema import BatchTruth, TestTruth  # noqa: E402


# ---------- ground truth ----------

def make_paper(t, seed, batch, idx, ref, used_ids):
    r = R_(seed, t["id"], batch, "paper", idx)
    name = f"{r.choice(FIRST)} {r.choice(LAST)}"
    while True:
        sid = f"{r.randint(100000, 999999)}"
        if sid not in used_ids:
            used_ids.add(sid); break
    theta = r.gauss(0, 1)
    diff = {c: d for c, _, _, d in t["topics"]}
    responses = []
    for num, q in enumerate(t["questions"], 1):
        d = diff[q["topic"]] + R_(seed, t["id"], "qdiff", num).gauss(0, 0.3)
        p = 1 / (1 + math.exp(-(theta - d)))
        if q["type"] == "mcq":
            u = r.random()
            if u < 0.02:
                responses.append(dict(number=num, marked="", mark_style="none", is_correct=False, score=0)); continue
            letter = q["answer"] if r.random() < p else r.choice([c for c in "ABCD" if c != q["answer"]])
            u = r.random()
            style = "double" if u < 0.02 else "faint" if u < 0.06 else "erased_extra" if u < 0.10 else "dark"
            marked = "MULTI" if style == "double" else letter
            ok = marked == q["answer"]
            responses.append(dict(number=num, marked=marked, mark_style=style, is_correct=ok, score=int(ok)))
        else:
            if r.random() < 0.03:
                responses.append(dict(number=num, text="", is_correct=False, score=0)); continue
            parts, score = [], 0
            for acc, dis in zip(q["answer"], q["distractors"]):
                if r.random() < p:
                    parts.append(r.choice(acc)); score += 1
                else:
                    parts.append(r.choice(dis))
            if len(parts) > 1 and r.random() < 0.5:
                parts.reverse()
            parts = [s.capitalize() if r.random() < 0.3 and s[:1].isalpha() else s for s in parts]
            responses.append(dict(number=num, text=", ".join(parts), is_correct=score == len(parts), score=score))
    n = t["pages"]
    missing = [r.randint(1, n)] if n > 1 and r.random() < 0.03 else []
    dup = r.choice([p for p in range(1, n + 1) if p not in missing]) if r.random() < 0.02 else None
    rot = r.randint(1, n) if r.random() < 0.03 else None
    id_written = r.random() >= 0.03 and 1 not in missing
    pages = []
    for pg in range(1, n + 1):
        if pg in missing:
            continue
        for d in ([False, True] if pg == dup else [False]):
            pages.append(dict(page=pg, quality="noisy" if r.random() < 0.5 else "clean",
                              rotated180=(pg == rot and not d), duplicate=d))
    c = R_(seed, t["id"], batch, "class", idx)  # separate stream: earlier ground truth is unchanged
    year = "" if c.random() < 0.02 else t["year"]
    section = "" if c.random() < 0.02 else c.choice(t["sections"])
    return dict(index=idx, student_ref=ref, student_name=name, student_id=sid, id_written=id_written, year=year, section=section,
                font=HANDS[r.randrange(len(HANDS))], ink=r.randint(20, 70), hsize=r.randint(36, 44),
                pages=pages, missing_pages=missing, responses=responses)


# ---------- outputs ----------

def test_truth(t):
    pages = layout(t)
    qs = []
    for num, q in enumerate(t["questions"], 1):
        qs.append(dict(number=num, type=q["type"], text=printed_text(q), options=q.get("options"),
                       answer=q["answer"], max_points=1 if q["type"] == "mcq" else len(q["answer"]), topic=q["topic"]))
    lay = [dict(page=p + 1, items=[dict(kind=i["kind"], number=i["number"], box=i["box"], bubbles=i.get("bubbles"))
                                   for i in items]) for p, items in enumerate(pages)]
    return TestTruth(id=t["id"], name=t["name"], subject=t["subject"], pages_per_paper=t["pages"],
                     identity_regions=[IDENTITY], topics=[dict(code=c, title=ti, description=de) for c, ti, de, _ in t["topics"]],
                     questions=qs, layout=lay)


def key_txt(tt: TestTruth):
    out = ["# number | type | answer | points | question text"]
    for q in tt.questions:
        ans = q.answer if q.type == "mcq" else "; ".join(" / ".join(p) for p in q.answer)
        out.append(f"{q.number} | {q.type} | {ans} | {q.max_points} | {q.text}")
    return "\n".join(out) + "\n"


def syllabus_txt(tt: TestTruth):
    return "\n".join(f"{x.code} | {x.title} | {x.description}" for x in tt.topics) + "\n"


def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


def batch(t, seed, name, n_papers, out: Path, ref_start=1):
    used, papers, jobs, order = set(), [], [], []
    seq = 0
    for i in range(n_papers):
        p = make_paper(t, seed, name, i, f"S-{ref_start + i:04d}", used)
        for pg in p["pages"]:
            seq += 1
            pg["file"] = f"{seq:06d}.jpg"
            order.append(pg["file"])
            jobs.append(dict(test=t["id"], page=pg["page"], paper=p, quality=pg["quality"], rotated180=pg["rotated180"],
                             key=(seed, t["id"], name, i, pg["page"], int(pg["duplicate"])),
                             out=str(out / name / "pages" / pg["file"])))
        papers.append(p)
    truth = BatchTruth(test_id=t["id"], seed=seed, scan_order=order, papers=[
        {k: v for k, v in p.items() if k not in ("ink", "hsize")} for p in papers])
    write(out / name / "truth.json", json.dumps(truth.model_dump(), indent=1, sort_keys=True))
    return jobs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=None)
    ap.add_argument("--papers", type=int, default=30)
    ap.add_argument("--stress", type=int, default=600)
    ap.add_argument("--tests", default="sci7,math8,hist9")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    out = Path(a.out or Path(__file__).parent / "out" / f"seed{a.seed}")
    jobs = []
    for t in TESTS:
        if t["id"] not in a.tests.split(","):
            continue
        tt = test_truth(t)
        d = out / t["id"]
        write(d / "test.json", json.dumps(tt.model_dump(), indent=1, sort_keys=True))
        write(d / "key.txt", key_txt(tt))
        write(d / "syllabus.txt", syllabus_txt(tt))
        write(d / "redaction.json", json.dumps({"regions": [dict(page=1, box=[round(b / s, 4) for b, s in zip(IDENTITY, (W, H, W, H))])]}, sort_keys=True))
        buf = io.BytesIO()
        draw_template(t, 1, layout(t)[0]).save(buf, "PNG")
        write(d / "sample_page1.png", buf.getvalue())
        jobs += batch(t, a.seed, "main", a.papers, d)
        if t["id"] == "math8" and a.stress:
            jobs += batch(t, a.seed, "stress", a.stress, d)
    with Pool(a.workers) as pool:
        for path, data in pool.imap_unordered(render_page, jobs, chunksize=8):
            write(Path(path), data)
    fonts = {f: hashlib.sha256(Path(FONTS + f).read_bytes()).hexdigest()[:16] for f in HANDS + ["arial.ttf", "arialbd.ttf"]}
    write(out / "fonts.json", json.dumps(fonts, indent=1, sort_keys=True))
    lines = sorted(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}"
                   for p in out.rglob("*") if p.is_file() and p.name != "manifest.sha256")
    write(out / "manifest.sha256", "\n".join(lines) + "\n")
    print(f"wrote {len(jobs)} pages to {out}")


if __name__ == "__main__":
    main()
