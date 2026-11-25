"""Shared gate helpers: results.tsv logging and fixture paths."""
import datetime, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures" / "out"
PY = sys.executable


def commit():
    h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!results.tsv", ":!PROGRESS.md"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return (h or "none") + ("-dirty" if dirty else "")


def log(gate, metric, value, passed):
    f = ROOT / "results.tsv"
    if not f.exists():
        f.write_text("timestamp\tgate\tmetric\tvalue\tpass\tcommit\n")
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    v = f"{value:.4f}" if isinstance(value, float) else str(value)
    with f.open("a") as fh:
        fh.write(f"{ts}\t{gate}\t{metric}\t{v}\t{'PASS' if passed else 'FAIL'}\t{commit()}\n")
    print(f"[{gate}] {metric} = {v} -> {'PASS' if passed else 'FAIL'}")
    return passed


def pytest_gate(gate, *files, extra=()):
    """Run pytest files; log passed count and failures. Returns True if all green."""
    import re, subprocess
    r = subprocess.run([PY, "-m", "pytest", *files, *extra], cwd=ROOT, capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-500:]
    print(tail)
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", tail)) else 0
    failed = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", tail))
    if r.returncode:
        print(r.stdout[-3000:])
    log(gate, "tests_passed", passed, r.returncode == 0)
    log(gate, "tests_failed", failed, failed == 0 and r.returncode == 0)
    return r.returncode == 0
