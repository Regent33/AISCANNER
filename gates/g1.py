"""G1: pytest green; UI loads (build + headless Edge); job survives a hard-killed worker (in pytest)."""
import subprocess, sys
from common import PY, ROOT, log

NPX = "npx.cmd" if sys.platform == "win32" else "npx"
NPM = "npm.cmd" if sys.platform == "win32" else "npm"


def ok(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd)
    return r.returncode == 0


build = ok([NPM, "run", "build"], ROOT / "frontend")
tests = ok([PY, "-m", "pytest", "tests/test_g1_skeleton.py"], ROOT)
ui = build and ok([NPX, "playwright", "test", "e2e/shell.spec.ts"], ROOT / "frontend")
log("G1", "pytest_green", int(tests), tests)
log("G1", "ui_loads", int(ui), ui)
sys.exit(0 if tests and ui else 1)
