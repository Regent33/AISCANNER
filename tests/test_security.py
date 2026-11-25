"""Security regressions from docs/security/run-1: DNS rebinding, cross-site requests, PowerShell argument injection."""
import sys

import pytest

from app import scanners


def test_foreign_host_header_rejected(client):
    """DNS rebinding: a page on attacker.example resolved to 127.0.0.1 sends Host: attacker.example."""
    assert client.get("/api/settings", headers={"host": "attacker.example:8000"}).status_code == 400
    assert client.get("/api/settings", headers={"host": "127.0.0.1:8000"}).status_code == 200
    assert client.get("/api/settings", headers={"host": "localhost:8000"}).status_code == 200


def test_cross_site_state_change_rejected(client):
    tid = client.post("/api/tests", json={"name": "T"}).json()["id"]
    client.post(f"/api/tests/{tid}/key", json={"text": "1. B"})
    for headers in ({"origin": "https://attacker.example"}, {"sec-fetch-site": "cross-site"}):
        r = client.post(f"/api/tests/{tid}/key", json={"text": "1. A"}, headers=headers)
        assert r.status_code == 403, headers
    assert client.get(f"/api/tests/{tid}").json()["questions"][0]["correct_answer"] == "B"
    ok = client.post(f"/api/tests/{tid}/key", json={"text": "1. C"},
                                     headers={"origin": "http://127.0.0.1:8000", "host": "127.0.0.1:8000"})
    assert ok.status_code == 200  # the app's own pages still work


def test_text_plain_json_not_accepted(client):
    """A CORS 'simple' request (text/plain, no preflight) must not be parsed as JSON."""
    tid = client.post("/api/tests", json={"name": "T"}).json()["id"]
    r = client.post(f"/api/tests/{tid}/key", content=b'{"text": "1. A"}', headers={"content-type": "text/plain"})
    assert r.status_code == 415


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell")
def test_powershell_receives_device_id_as_data():
    """Curly quotes (U+2019) are string delimiters in PowerShell; the device id must never be spliced into script text."""
    payload = "x’; Write-Output INJECTED; ’'"
    r = scanners._ps("Write-Output ('dev=' + $env:SCAN_DEVICE)", env={"SCAN_DEVICE": payload}, timeout=60)
    out = r.stdout.strip()
    # one line of data echoed back (console may re-encode the curly quote); an injection would print INJECTED alone
    assert "\n" not in out and out.startswith("dev=x") and "Write-Output INJECTED" in out


def test_sane_device_cannot_be_an_option():
    with pytest.raises(scanners.ScannerError):
        scanners.make("sane", "--batch=/tmp/x")
