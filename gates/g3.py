"""G3: dropped files appear within 5 s; duplicates ignored; upload + MockScanner paths; WIA checklist exists."""
import re, subprocess, sys
from common import PY, ROOT, log, pytest_gate

ok = pytest_gate("G3", "tests/test_g3_ingest.py")
out = subprocess.run([PY, "-m", "pytest", "tests/test_g3_ingest.py", "-k", "watcher", "-s"], cwd=ROOT,
                     capture_output=True, text=True).stdout
lat = max(float(x) for x in re.search(r"watch latency s: \[([^\]]+)\]", out).group(1).split(","))
ok &= log("G3", "max_watch_latency_s", lat, lat < 5)
checklist = (ROOT / "docs" / "SCANNER_CHECKLIST.md").exists()
ok &= log("G3", "scanner_manual_checklist", int(checklist), checklist)
sys.exit(0 if ok else 1)
