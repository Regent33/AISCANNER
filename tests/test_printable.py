"""Printable test: layout is stable, the PDF reads back through the scanner pipeline, and downloading it aligns the
test (pages per paper, student details area, sample page). Also the 2-5 option and A-E key support it needs."""
import io

import cv2
import numpy as np
import pymupdf as fitz
import pytest

from app import grading, printable, vision
from app.parse import ParseError, parse_key, split_options

KEY = "\n".join([
    "1 | mcq | B | 1 | Which part of a plant takes in water?  (A) Leaves  (B) Roots  (C) Flowers  (D) Seeds",
    "2 | written | chlorophyll | 1 | Name the green pigment that plants use to capture sunlight.",
    "3 | mcq | A | 1 | True or false: the Sun is a star.  (A) True  (B) False",
    "4 | mcq | E | 1 | Which is a mammal?  (A) Shark  (B) Frog  (C) Eagle  (D) Snake  (E) Whale",
    "5 | mcq | C | 1 | A question printed with no options in the key",
] + [f"{n} | written | x | 1 | Filler question number {n} about plants and water and light." for n in range(6, 26)])


def test_split_options_and_five_option_keys():
    assert split_options("Q?  (A) a  (B) b") == ("Q?", ["a", "b"])
    assert split_options("3x + 5 = 17") == ("3x + 5 = 17", None)
    assert [q["type"] for q in parse_key("1. E\n2. e")] == ["mcq", "mcq"]
    with pytest.raises(ParseError):
        parse_key("1 | mcq | F | 1 | ?")


def test_layout_is_stable_and_flows_onto_pages():
    qs = parse_key(KEY)
    pages = printable.layout(qs, None)
    assert len(pages) >= 2 and sum(map(len, pages)) == 25
    assert [[i["number"] for i in p] for p in printable.layout(qs, len(pages))] == [[i["number"] for i in p] for p in pages]
    assert len(printable.layout(qs, len(pages) + 1)) == len(pages) + 1  # more pages asked: spread evenly
    for page in pages:
        assert all(it["box"][3] <= printable.BOTTOM for it in page)


def test_blank_printable_reads_back_through_the_pipeline():
    qs = parse_key(KEY)
    pages = printable.layout(qs, None)
    pdf = printable.render_pdf("A test with a rather long title that has to be shortened to fit the header", pages)
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        assert doc.page_count == len(pages)
        for i, p in enumerate(doc):
            g = cv2.imdecode(np.frombuffer(p.get_pixmap(dpi=150, colorspace=fitz.csGRAY).tobytes("png"), np.uint8), 0)
            hm, rotated = vision.register(g)
            assert hm is not None and not rotated
            reg = vision.flatten(vision.warp(g, hm))
            assert vision.read_page_label(reg) == (i + 1, len(pages))
            ex = [vision.region_px(printable.IDENTITY_REGION["box"])] if i == 0 else []
            items = grading.detect_items(reg, ex)
            grading.number_items(reg, items, max([grading.CONTENT_TOP] + [e[3] for e in ex]))
            got = [(it["kind"], it["number"], len(it.get("opts", []))) for it in items]
            want = [(it["kind"], it["number"], len(it.get("bubbles", []))) for it in pages[i]]
            assert got == want


def test_download_aligns_the_test(client):
    tid = client.post("/api/tests", json={"name": "Plants", "pages_per_paper": 1}).json()["id"]
    assert client.get(f"/api/tests/{tid}/printable.pdf").status_code == 422  # no key yet
    client.post(f"/api/tests/{tid}/key", json={"text": KEY})
    r = client.get(f"/api/tests/{tid}/printable.pdf")
    assert r.status_code == 200 and r.content[:5] == b"%PDF-" and "Plants.pdf" in r.headers["content-disposition"]
    t = client.get(f"/api/tests/{tid}").json()
    assert t["pages_per_paper"] == fitz.open(stream=r.content, filetype="pdf").page_count >= 2
    assert t["redaction_regions"] == [printable.IDENTITY_REGION]
    assert client.get(f"/api/tests/{tid}/sample").status_code == 200
    again = client.get(f"/api/tests/{tid}/printable.pdf")
    assert fitz.open(stream=again.content, filetype="pdf").page_count == t["pages_per_paper"]  # stable


def test_sample_page_is_the_printed_page_one():
    from PIL import Image
    pdf = printable.render_pdf("T", printable.layout(parse_key(KEY), None))
    assert Image.open(io.BytesIO(printable.page_png(pdf, 0))).size == (vision.W, vision.H)
