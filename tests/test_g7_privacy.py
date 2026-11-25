"""Privacy building blocks: redaction blacks out identity regions; the cloud provider sends only what it is given
and audits it; the G7 pixel check catches a leak (negative control)."""

import numpy as np

from app import cloud, grade, vision
from g7 import Capture, identity_pixels

REGION = [{"page": 1, "box": [0.0806, 0.057, 0.7339, 0.1551]}]


def test_redacted_page_blacks_out_identity(monkeypatch):
    page = np.full((vision.H, vision.W), 200, np.uint8)
    monkeypatch.setattr(grade, "page_image", lambda p: page.copy())
    out = grade.redacted_page({"page_no": 1}, REGION)
    x0, y0, x1, y1 = vision.region_px(REGION[0]["box"])
    assert (out[y0:y1, x0:x1] == 0).all() and out[y1 + 10, x0] == 200
    assert (grade.redacted_page({"page_no": 2}, REGION) == 200).all()  # region is page-1 only


def test_pixel_check_catches_unredacted_crop():
    x0, y0, x1, y1 = vision.region_px(REGION[0]["box"])
    crop = np.full((y1 - y0, 200), 255, np.uint8)  # leaked, unredacted identity pixels
    n, hits = identity_pixels(crop, {"box": [x0, y0, x0 + 200, y1]}, [(x0, y0, x1, y1)])
    assert hits == 1 and n == crop.size
    assert identity_pixels(np.zeros_like(crop), {"box": [x0, y0, x0 + 200, y1]}, [(x0, y0, x1, y1)])[0] == 0


def test_cloud_provider_payload_and_audit(data):
    import anthropic, httpx2
    from app import db
    db.init()
    cap = Capture()
    prov = cloud.CloudProvider(client=anthropic.Anthropic(
        api_key="capture-only", http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(cap.handler))))
    crop = np.full((60, 300), 255, np.uint8)
    text, conf = prov.transcribe(crop, {"number": 3, "text": "Name the green pigment."}, {"page_no": 1, "box": [5, 300, 305, 360]})
    assert (text, conf) == ("", 0.5)
    body = cap.bodies[0]
    assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default"
    assert [p["type"] for p in body["messages"][0]["content"]] == ["image", "text"]
    assert prov.audit[0]["where"]["box"] == [5, 300, 305, 360] and prov.audit[0]["image_shape"] == [60, 300]
    assert "Name the green pigment." in body["messages"][0]["content"][1]["text"]
