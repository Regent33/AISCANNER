"""G10: Playwright golden path (create test, scan a batch, review, report, PDF) in a real browser (Edge, headless);
home to report in <= 3 clicks; review queue of 500 items stays responsive (< 200 ms per action, timed in the page).
The tests run in order against one server and one fresh data folder."""
import json, subprocess, sys

from common import ROOT, log

NPX = "npx.cmd" if sys.platform == "win32" else "npx"
NPM = "npm.cmd" if sys.platform == "win32" else "npm"
TESTS = {"golden path": "golden_path", "3 clicks": "home_to_report_le_3_clicks", "500 items": "review_500_responsive",
         "UI shell": "ui_shell"}


def statuses(report):
    out = {}

    def walk(suite):
        for spec in suite.get("specs", []):
            out[spec["title"]] = all(t["status"] == "expected" for t in spec["tests"])
        for s in suite.get("suites", []):
            walk(s)
    for s in report["suites"]:
        walk(s)
    return out


def main():
    fe = ROOT / "frontend"
    if subprocess.run([NPM, "run", "build"], cwd=fe).returncode:
        sys.exit(0 if log("G10", "ui_build", 0, False) else 1)
    lat_file = ROOT / "data" / "e2e-review-latency.json"
    lat_file.unlink(missing_ok=True)
    r = subprocess.run([NPX, "playwright", "test", "--reporter=json"], cwd=fe, capture_output=True, text=True)
    got = statuses(json.loads(r.stdout))
    if r.returncode:
        print(r.stderr[-3000:])
    results = []
    for key, metric in TESTS.items():
        passed = any(key in title and ok for title, ok in got.items())
        results.append(log("G10", metric, int(passed), passed))
    if lat_file.exists():
        lat = json.loads(lat_file.read_text())
        results.append(log("G10", "review_action_latency_max_ms", round(lat["max"], 1), lat["max"] < 200))
        log("G10", "review_action_latency_median_ms", round(lat["median"], 1), True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
