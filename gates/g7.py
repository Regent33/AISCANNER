"""G7: privacy over all fixtures.
- Cloud mode (network replaced by a capture transport): outbound payloads hold 0 identity-region pixels and 0 name/ID
  strings (checked in the JSON text and by OCR of every outbound image).
- Local mode (every socket connect blocked and counted): 0 outbound connection attempts.
usage: python gates/g7.py [seed]   (seed != 7 is not logged)"""
import base64, json, re, socket, sys

import cv2
import numpy as np

import harness
from common import FIX, log

SEED = 7
TESTS = ["sci7", "math8", "hist9"]


class Capture:
    """Stands in for api.anthropic.com: records every request body and answers with schema-valid canned JSON."""

    def __init__(self):
        self.bodies = []

    def handler(self, request):
        import httpx2
        body = json.loads(request.content)
        self.bodies.append(body)
        content = body["messages"][0]["content"]
        text = content[-1]["text"]
        if content[0]["type"] == "image":
            out = {"text": "", "confidence": 0.5}
        elif text.startswith("Syllabus topics"):  # map every question to the first topic so reteach runs too
            code = re.search(r"^(\S+) \|", text.split("\n", 1)[1], re.M).group(1)
            out = {"mappings": [{"number": int(n), "topic_code": code, "confidence": 0.9}
                                for n in re.findall(r"^(\d+)\. ", text, re.M)]}
        elif text.startswith("Answer key needed"):
            out = {"keys": []}
        else:
            codes = re.findall(r"^(\S+) \|", text, re.M)
            out = {"topics": [{"code": c, "activities": ["Recap quiz."]} for c in codes]}
        return httpx2.Response(200, json={
            "id": "msg_capture", "type": "message", "role": "assistant", "model": body["model"],
            "content": [{"type": "text", "text": json.dumps(out)}], "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1}})


def run_all(provider):
    client = harness.setup_app(harness.eval_dir(f"g7-{provider}-seed{SEED}"), provider)
    truths, regions = [], {}
    for tid in TESTS:
        tdir = FIX / f"seed{SEED}" / tid
        test_id = harness.create_test(client, tdir)
        _, truth = harness.run_batch(client, test_id, tdir / "main")
        harness.drain(verbose=False)
        client.get(f"/api/tests/{test_id}/report")  # exercises topic mapping + reteach once G8 exists
        truths.append(truth)
        regions[tid] = json.loads((tdir / "redaction.json").read_text())["regions"]
    return truths, regions


def identities(truths):
    names, ids = set(), set()
    for t in truths:
        for p in t["papers"]:
            names.add(p["student_name"].lower())
            names.update(w.lower() for w in p["student_name"].split() if len(w) >= 4)
            ids.add(p["student_id"])
    return names, ids


def identity_pixels(img, where, regions_px):
    """Non-black pixels of an outbound crop that fall inside an identity region of its source page."""
    x0, y0, x1, y1 = where["box"]
    n = hits = 0
    for rx0, ry0, rx1, ry1 in regions_px:
        ix0, iy0, ix1, iy1 = max(x0, rx0), max(y0, ry0), min(x1, rx1), min(y1, ry1)
        if ix0 < ix1 and iy0 < iy1:
            hits += 1
            n += int((img[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0] != 0).sum())
    return n, hits


def strip_images(body):
    b = json.loads(json.dumps(body))
    for part in b["messages"][0]["content"]:
        if part.get("type") == "image":
            part["source"]["data"] = "<image>"
    return json.dumps(b).lower()


def cloud_checks():
    import anthropic, httpx2
    from app import cloud, providers, vision
    cap = Capture()
    fake = anthropic.Anthropic(api_key="capture-only", http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(cap.handler)))
    prov = cloud.CloudProvider(client=fake)
    providers._providers["cloud"] = prov
    truths, regions = run_all("cloud")
    names, ids = identities(truths)
    audit = list(prov.audit)
    assert len(audit) == len(cap.bodies), (len(audit), len(cap.bodies))
    all_regions = [vision.region_px(r["box"]) for rs in regions.values() for r in rs if r["page"] == 1]
    pix = overlaps = text_hits = ocr_hits = images = 0
    for body, a in zip(cap.bodies, audit):
        text = strip_images(body)
        text_hits += sum(bool(re.search(rf"\b{re.escape(n)}\b", text)) for n in names) + sum(i in text for i in ids)
        for part in body["messages"][0]["content"]:
            if part.get("type") != "image":
                continue
            images += 1
            img = cv2.imdecode(np.frombuffer(base64.b64decode(part["source"]["data"]), np.uint8), cv2.IMREAD_GRAYSCALE)
            x0, y0, x1, y1 = a["where"]["box"]
            assert list(img.shape) == [y1 - y0, x1 - x0], "audit box does not match the image sent"
            n, hits = identity_pixels(img, a["where"], all_regions if a["where"]["page_no"] == 1 else [])
            pix, overlaps = pix + n, overlaps + hits
            read = re.sub(r"\s", "", vision.ocr_crop(img)[0].lower())
            ocr_hits += any(n.replace(" ", "") in read for n in names if " " in n) or any(i in read for i in ids)
    kinds = sorted({a["kind"] for a in audit})
    print(f"cloud: requests={len(cap.bodies)} images={images} kinds={kinds} region_overlaps={overlaps} "
          f"identity_pixels={pix} name_hits_text={text_hits} name_hits_ocr={ocr_hits}")
    return len(cap.bodies), pix, text_hits + ocr_hits


LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def local_checks():
    """Block and count every non-loopback connection (loopback is the event loop's own socketpair, not outbound)."""
    attempts = []
    real_connect, real_connect_ex, real_create = socket.socket.connect, socket.socket.connect_ex, socket.create_connection

    def host(addr):
        return addr[0] if isinstance(addr, tuple) else str(addr)

    def connect(self, addr):
        if host(addr) not in LOOPBACK:
            attempts.append(host(addr))
            raise OSError("outbound network blocked by G7")
        return real_connect(self, addr)

    def connect_ex(self, addr):
        if host(addr) not in LOOPBACK:
            attempts.append(host(addr))
            return 111
        return real_connect_ex(self, addr)

    def create(addr, *a, **k):
        if host(addr) not in LOOPBACK:
            attempts.append(host(addr))
            raise OSError("outbound network blocked by G7")
        return real_create(addr, *a, **k)

    socket.socket.connect, socket.socket.connect_ex, socket.create_connection = connect, connect_ex, create
    try:
        run_all("local")
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = real_connect, real_connect_ex, real_create
    print(f"local: outbound connection attempts={len(attempts)} {attempts[:3]}")
    return len(attempts)


def main():
    requests, pix, names = cloud_checks()
    local_calls = local_checks()
    if SEED != 7:
        return
    ok = log("G7", "cloud_requests_captured", requests, requests > 0)
    ok &= log("G7", "identity_region_pixels_sent", pix, pix == 0)
    ok &= log("G7", "name_or_id_strings_sent", names, names == 0)
    ok &= log("G7", "local_mode_outbound_calls", local_calls, local_calls == 0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main()
