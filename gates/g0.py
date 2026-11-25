"""G0: same seed gives byte-identical output (two separate processes); ground truth validates against schema."""
import json, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fixtures"))
from common import FIX, PY, ROOT, log  # noqa: E402
from schema import BatchTruth, TestTruth  # noqa: E402

SEED = 7


def gen(out):
    subprocess.run([PY, str(ROOT / "fixtures" / "generate.py"), "--seed", str(SEED), "--out", str(out)], check=True)
    return (Path(out) / "manifest.sha256").read_text()


def main():
    t = time.time()
    a = gen(FIX / f"seed{SEED}")
    with tempfile.TemporaryDirectory() as tmp:
        b = gen(Path(tmp) / "again")
    identical = a == b
    print(f"generated twice in {time.time() - t:.0f}s; files={len(a.splitlines())}")

    out, errors, page_counts, n_stress = FIX / f"seed{SEED}", [], set(), 0
    for tdir in sorted(p for p in out.iterdir() if p.is_dir()):
        tt = TestTruth.model_validate_json((tdir / "test.json").read_text())
        page_counts.add(tt.pages_per_paper)
        for bdir in sorted(p for p in tdir.iterdir() if p.is_dir()):
            bt = BatchTruth.model_validate_json((bdir / "truth.json").read_text())
            files = sorted(p.name for p in (bdir / "pages").iterdir())
            if files != sorted(bt.scan_order):
                errors.append(f"{bdir}: files on disk != scan_order")
            for p in bt.papers:
                if len(p.responses) != len(tt.questions):
                    errors.append(f"{bdir} paper {p.index}: response count")
                present = {pg.page for pg in p.pages}
                if present | set(p.missing_pages) != set(range(1, tt.pages_per_paper + 1)):
                    errors.append(f"{bdir} paper {p.index}: pages + missing != all pages")
            if bdir.name == "main" and len(bt.papers) < 30:
                errors.append(f"{bdir}: < 30 papers")
            if bdir.name == "stress":
                n_stress = len(bt.papers)
            json.loads((bdir / "truth.json").read_text())
    if len(page_counts) < 3 or min(page_counts) != 1 or max(page_counts) < 4:
        errors.append(f"page counts {sorted(page_counts)} do not span 1..4+")
    if n_stress < 600:
        errors.append(f"stress set has {n_stress} papers")
    for e in errors[:20]:
        print("ERROR", e)
    log("G0", "byte_identical", int(identical), identical)
    ok = log("G0", "schema_errors", len(errors), not errors)
    sys.exit(0 if identical and ok else 1)


if __name__ == "__main__":
    main()
