"""Scanner support beyond WIA: eSCL (AirScan/Mopria) over real HTTP against a mock printer, SANE parsing, discovery."""
import time

import pytest

from app import scanners
from app.escl import EsclScanner, ScannerError, normalize_url
from escl_mock import MockPrinter


@pytest.fixture
def printer():
    p = MockPrinter(pages=3)
    yield p
    p.close()


def test_normalize_url():
    assert normalize_url("192.168.1.20") == "http://192.168.1.20/eSCL"
    assert normalize_url("https://printer.local:8443/eSCL/") == "https://printer.local:8443/eSCL"
    with pytest.raises(ScannerError):
        normalize_url("ftp://printer")


def test_escl_feeder_scan_reads_every_page(printer):
    s = EsclScanner(printer.url.removeprefix("http://"))
    assert s.capabilities()["name"] == "Mock Printer 3000"
    pages = list(s.scan(busy_wait=0.01))  # the printer answers "busy" once, then feeds
    assert [n for n, _ in pages] == ["escl_00001.jpg", "escl_00002.jpg", "escl_00003.jpg"]
    job = printer.jobs[0]
    assert "<pwg:InputSource>Feeder</pwg:InputSource>" in job and "Grayscale8" in job and ">150<" in job
    assert "<pwg:Width>2480</pwg:Width>" in job  # clamped to A4


def test_escl_glass_scan_is_one_page():
    p = MockPrinter(pages=0)  # feeder empty => glass
    p.feeder = [b"\xff\xd8glass\xff\xd9"]
    try:
        pages = list(EsclScanner(p.url).scan(source="Platen", busy_wait=0.01))
        assert len(pages) == 1 and "Platen" in p.jobs[0]
    finally:
        p.close()


def test_escl_scan_through_api(client, printer):
    tid = client.post("/api/tests", json={"name": "T"}).json()["id"]
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    r = client.post(f"/api/batches/{bid}/scan", json={"mode": "scanner", "device": "escl", "target": printer.url})
    assert r.status_code == 200, r.text
    end = time.time() + 10
    while client.get(f"/api/batches/{bid}").json()["total_pages"] < 3 and time.time() < end:
        time.sleep(0.05)
    assert client.get(f"/api/batches/{bid}").json()["total_pages"] == 3


def test_check_printer_by_address(client, printer):
    r = client.post("/api/scanners/check", json={"address": printer.url})
    assert r.status_code == 200 and r.json()["name"] == "Mock Printer 3000" and r.json()["kind"] == "escl"
    assert client.post("/api/scanners/check", json={"address": "127.0.0.1:1"}).status_code == 422


def test_scan_error_is_reported_to_the_teacher(client):
    tid = client.post("/api/tests", json={"name": "T"}).json()["id"]
    bid = client.post("/api/batches", json={"test_id": tid}).json()["id"]
    client.post(f"/api/batches/{bid}/scan", json={"mode": "scanner", "device": "escl", "target": "127.0.0.1:1"})
    end = time.time() + 10
    while not client.get(f"/api/batches/{bid}").json()["last_error"] and time.time() < end:
        time.sleep(0.05)
    assert "printer" in client.get(f"/api/batches/{bid}").json()["last_error"].lower()


def test_sane_list_parsing():
    out = "device `pixma:04A91234_1' is a CANON Canon PIXMA MG3600 multi-function peripheral\nnoise\n"
    assert scanners.parse_sane_list(out) == [{"kind": "sane", "id": "pixma:04A91234_1",
                                              "name": "CANON Canon PIXMA MG3600 multi-function peripheral"}]


def test_discover_never_raises(monkeypatch):
    monkeypatch.setattr(scanners.escl, "discover", lambda: (_ for _ in ()).throw(OSError("no multicast")))
    monkeypatch.setattr(scanners.WiaScanner, "list_devices", staticmethod(lambda: [{"kind": "wia", "id": "x", "name": "HP"}]))
    monkeypatch.setattr(scanners.SaneScanner, "list_devices", staticmethod(lambda: []))
    assert scanners.discover() == [{"kind": "wia", "id": "x", "name": "HP"}]
