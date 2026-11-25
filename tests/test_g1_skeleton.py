import sqlite3, time


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_unknown_api_is_404_not_spa(client):
    assert client.get("/api/nope").status_code == 404


def test_ui_index_served(client):
    r = client.get("/tests")  # client-side route falls back to index.html
    assert r.status_code == 200 and '<div id="root">' in r.text


def wait(pred, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(0.1)
    raise AssertionError("timed out")


def test_job_survives_worker_restart(server, data):
    s = server(SCANNER_SELFTEST_SLEEP="3").start()
    db = sqlite3.connect(data / "scanner.db", isolation_level=None)
    jid = db.execute("INSERT INTO job(stage) VALUES ('selftest')").lastrowid
    status = lambda: db.execute("SELECT status, attempts FROM job WHERE id=?", (jid,)).fetchone()
    wait(lambda: status()[0] == "running")
    s.kill()  # hard kill mid-job
    assert status() == ("running", 1)
    s2 = server(SCANNER_SELFTEST_SLEEP="0.1").start()
    wait(lambda: status()[0] == "done")
    assert status() == ("done", 2)
    s2.kill()
