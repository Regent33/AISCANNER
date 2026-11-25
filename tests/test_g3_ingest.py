"""G3: manual upload, folder watcher (<5 s), MockScanner trigger, duplicates ignored, originals untouched."""
import io, shutil, sys, time

import pymupdf as fitz
import pytest
from PIL import Image


def img_bytes(seed):
    im = Image.new("L", (200, 280), 255)
    im.putpixel((seed % 200, seed % 280), 0)
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); return b.getvalue()


def setup_batch(c):
    tid = c.post("/api/tests", json={"name": "T", "pages_per_paper": 1}).json()["id"]
    return c.post("/api/batches", json={"test_id": tid}).json()["id"]


def wait(pred, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        if v := pred():
            return v
        time.sleep(0.05)
    raise AssertionError("timed out")


def test_manual_upload_keeps_originals_untouched(client, data):
    bid = setup_batch(client)
    files = [img_bytes(i) for i in range(3)]
    r = client.post(f"/api/batches/{bid}/pages", files=[("files", (f"p{i}.jpg", f, "image/jpeg")) for i, f in enumerate(files)])
    assert r.status_code == 200 and r.json() == {"added": 3, "duplicates": 0}
    b = client.get(f"/api/batches/{bid}").json()
    assert b["total_pages"] == 3
    stored = sorted((data / "batches" / str(bid) / "orig").iterdir())
    assert [p.read_bytes() for p in stored] == files


def test_duplicate_upload_ignored(client):
    bid = setup_batch(client)
    f = img_bytes(1)
    client.post(f"/api/batches/{bid}/pages", files=[("files", ("a.jpg", f, "image/jpeg"))])
    r = client.post(f"/api/batches/{bid}/pages", files=[("files", ("b.jpg", f, "image/jpeg"))])
    assert r.json() == {"added": 0, "duplicates": 1}
    assert client.get(f"/api/batches/{bid}").json()["total_pages"] == 1


def test_multipage_pdf_upload(client):
    bid = setup_batch(client)
    doc = fitz.open()
    for i in range(3):
        doc.new_page().insert_text((72, 72 + i * 20), f"page {i}")
    r = client.post(f"/api/batches/{bid}/pages", files=[("files", ("scan.pdf", doc.tobytes(), "application/pdf"))])
    assert r.json() == {"added": 3, "duplicates": 0}


def test_rejects_non_image(client):
    bid = setup_batch(client)
    r = client.post(f"/api/batches/{bid}/pages", files=[("files", ("x.txt", b"hello", "text/plain"))])
    assert r.status_code == 422


def test_folder_watcher_appears_within_5s_and_ignores_duplicates(client, tmp_path):
    watch = tmp_path / "inbox"; watch.mkdir()
    bid = setup_batch(client)
    assert client.post(f"/api/batches/{bid}/scan", json={"mode": "watch", "folder": str(watch)}).status_code == 200
    lat = []
    for i in range(3):
        t = time.time()
        (watch / f"scan_{i:03d}.jpg").write_bytes(img_bytes(10 + i))
        wait(lambda: client.get(f"/api/batches/{bid}").json()["total_pages"] == i + 1, timeout=5)
        lat.append(time.time() - t)
    (watch / "scan_dup.jpg").write_bytes(img_bytes(10))  # same bytes as scan_000 => ignored
    time.sleep(2)
    assert client.get(f"/api/batches/{bid}").json()["total_pages"] == 3
    assert max(lat) < 5, lat
    print("watch latency s:", [round(x, 2) for x in lat])


def test_mock_scanner_direct_trigger(client, tmp_path):
    src = tmp_path / "feeder"; src.mkdir()
    for i in range(4):
        (src / f"{i}.jpg").write_bytes(img_bytes(30 + i))
    bid = setup_batch(client)
    r = client.post(f"/api/batches/{bid}/scan", json={"mode": "scanner", "device": "mock", "folder": str(src)})
    assert r.status_code == 200
    wait(lambda: client.get(f"/api/batches/{bid}").json()["total_pages"] == 4)


def test_watch_folder_must_exist(client, tmp_path):
    bid = setup_batch(client)
    r = client.post(f"/api/batches/{bid}/scan", json={"mode": "watch", "folder": str(tmp_path / "nope")})
    assert r.status_code == 422


@pytest.mark.skipif(sys.platform != "win32", reason="WIA is Windows-only")
def test_wia_device_listing_runs():
    from app.scanners import WiaScanner
    devices = WiaScanner.list_devices()  # read-only enumeration; never triggers a scan
    assert isinstance(devices, list)
