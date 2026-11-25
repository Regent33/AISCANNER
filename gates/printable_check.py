"""Printable round trip: the app's printable PDF -> rasterised -> filled in by simulated students (handwriting fonts,
filled / faint / double / erased bubbles, blanks) -> scanner noise -> scanned, grouped and graded by the app.
Bars are G4-G6's: grouping >= 95%, IDs >= 90%, MCQ >= 95%, written agreement >= 85%.
usage: python gates/printable_check.py [students per test]"""
import io, json, sys
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw

import harness
from common import FIX, log
import generate
import render
from content import TESTS

SEED, STUDENTS = 21, int(sys.argv[1]) if len(sys.argv) > 1 else 10


def fill(page_img, page_no, items, paper, qs, r):
    from app import printable
    img = page_img.copy()
    d = ImageDraw.Draw(img)
    hf = render.font(render.FONTS + paper["font"], paper["hsize"])
    if page_no == 1:
        boxes = {lab: box for lab, _, box in printable.FIELDS}
        values = [(paper["student_name"], "Name:"), (paper["student_id"] if paper["id_written"] else "", "ID:"),
                  (paper["year"], "Year:"), (paper["section"], "Section:")]
        for value, lab in values:
            if value:
                render.hand(img, value, boxes[lab], hf, paper["ink"], r)
    resp = {x["number"]: x for x in paper["responses"]}
    for it in items:
        x = resp[it["number"]]
        if it["kind"] == "mcq":
            style, bub = x["mark_style"], it["bubbles"]
            if style == "double":
                for k in r.sample(range(len(bub)), 2):
                    render.mark_bubble(d, bub[k], paper["ink"], r)
            elif style != "none":
                i = "ABCDEF".index(x["marked"])
                if style == "erased_extra":
                    render.mark_bubble(d, bub[r.choice([k for k in range(len(bub)) if k != i])], r.randint(205, 220), r, partial=True)
                render.mark_bubble(d, bub[i], r.randint(150, 175) if style == "faint" else paper["ink"], r)
        elif x["text"]:
            render.hand(img, x["text"], it["answer_box"], hf, paper["ink"], r)
    return img


def run_test(client, t):
    from app import db, printable
    from app.parse import parse_key
    tdir = FIX / "seed7" / t["id"]
    tid = client.post("/api/tests", json={"name": t["name"], "subject": t["subject"]}).json()["id"]
    client.post(f"/api/tests/{tid}/key", json={"text": (tdir / "key.txt").read_text()})
    client.post(f"/api/tests/{tid}/syllabus", json={"text": (tdir / "syllabus.txt").read_text()})
    pdf = client.get(f"/api/tests/{tid}/printable.pdf").content  # also sets pages and the student details area
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        blanks = [Image.open(io.BytesIO(p.get_pixmap(dpi=150, colorspace=fitz.csGRAY).tobytes("png"))).convert("L") for p in doc]
    layout = printable.layout(parse_key((tdir / "key.txt").read_text()), len(blanks))
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    from app import ingest
    conn, used, papers, seq = db.connect(), set(), [], 0
    for i in range(STUDENTS):
        p = generate.make_paper(t, SEED, "printable", i, f"S-{i + 1:04d}", used)
        p["files"] = []
        for n, (blank, items) in enumerate(zip(blanks, layout), 1):
            r = render.R_(SEED, t["id"], "printable", i, n)
            img = fill(blank, n, items, p, t["questions"], r)
            seq += 1
            data = render.degrade(img, "noisy" if r.random() < 0.5 else "clean", r, render.NR(SEED, t["id"], i, n))
            ingest.ingest(conn, bid, f"{seq:06d}.jpg", data)
            p["files"].append(f"{seq:06d}.jpg")
        papers.append(p)
    client.post(f"/api/batches/{bid}/finish")
    harness.drain(verbose=False)
    by_file, resp = harness.responses(bid)
    s = dict(papers=len(papers), grouped=0, ids=0, id_total=0, mcq=0, mcq_ok=0, written=0, written_ok=0)
    groups = [fs for _, fs in harness.system_papers(bid)]
    for p in papers:
        sp = by_file.get(p["files"][0])
        s["grouped"] += p["files"] in groups
        if p["id_written"]:
            s["id_total"] += 1
            s["ids"] += bool(sp) and sp["student_id_local"] == p["student_id"]
        for x in p["responses"]:
            got = resp.get((sp["id"], x["number"])) if sp else None
            if x.get("marked") is not None:
                s["mcq"] += 1
                s["mcq_ok"] += bool(got) and got["normalized_answer"] == x["marked"]
            else:
                s["written"] += 1
                s["written_ok"] += bool(got) and got["score"] == x["score"]
    return s


def main():
    client = harness.setup_app(harness.eval_dir("printable-check"))
    tot = {}
    for t in TESTS:
        s = run_test(client, t)
        print(t["id"], s)
        for k, v in s.items():
            tot[k] = tot.get(k, 0) + v
    g, i, m, w = (tot["grouped"] / tot["papers"], tot["ids"] / tot["id_total"], tot["mcq_ok"] / tot["mcq"],
                  tot["written_ok"] / tot["written"])
    ok = log("PT", "printable_grouping", g, g >= 0.95)
    ok &= log("PT", "printable_student_id", i, i >= 0.90)
    ok &= log("PT", "printable_mcq_accuracy", m, m >= 0.95)
    ok &= log("PT", "printable_written_agreement", w, w >= 0.85)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
