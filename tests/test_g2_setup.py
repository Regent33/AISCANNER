"""G2: round-trip for every key/syllabus input mode, keyless flagging, redaction regions."""
import io

import pymupdf as fitz
import pytest

from content import TESTS
import generate as gen

TT = gen.test_truth(next(t for t in TESTS if t["id"] == "hist9"))
KEY, SYL = gen.key_txt(TT), gen.syllabus_txt(TT)


def make_test(client, **kw):
    r = client.post("/api/tests", json={"name": "Exam", "subject": "Humanities", "pages_per_paper": 4, **kw})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def pdf_bytes(text):
    doc = fitz.open()
    page = doc.new_page(width=842, height=1191)
    page.insert_textbox(fitz.Rect(20, 20, 822, 1171), text, fontsize=7)
    return doc.tobytes()


def expected_questions():
    out = []
    for q in TT.questions:
        ans = q.answer if q.type == "mcq" else "; ".join(" / ".join(p) for p in q.answer)
        out.append(dict(number=q.number, type=q.type, correct_answer=ans, max_points=q.max_points, text=q.text, key_source="key"))
    return out


def got_questions(client, tid):
    qs = client.get(f"/api/tests/{tid}").json()["questions"]
    return [{k: q[k] for k in ("number", "type", "correct_answer", "max_points", "text", "key_source")} for q in qs]


@pytest.mark.parametrize("mode", ["paste", "upload_txt", "upload_pdf"])
def test_key_round_trip(client, mode):
    tid = make_test(client)
    if mode == "paste":
        r = client.post(f"/api/tests/{tid}/key", json={"text": KEY})
    elif mode == "upload_txt":
        r = client.post(f"/api/tests/{tid}/key", files={"file": ("key.txt", KEY.encode(), "text/plain")})
    else:
        r = client.post(f"/api/tests/{tid}/key", files={"file": ("key.pdf", pdf_bytes(KEY), "application/pdf")})
    assert r.status_code == 200, r.text
    assert got_questions(client, tid) == expected_questions()


def test_short_key_format(client):
    tid = make_test(client)
    r = client.post(f"/api/tests/{tid}/key", json={"text": "1. B\n2) photosynthesis\nQ3 D\n4: oxygen; nitrogen\n"})
    assert r.status_code == 200, r.text
    qs = got_questions(client, tid)
    assert [(q["number"], q["type"], q["correct_answer"], q["max_points"]) for q in qs] == [
        (1, "mcq", "B", 1), (2, "written", "photosynthesis", 1), (3, "mcq", "D", 1), (4, "written", "oxygen; nitrogen", 2)]


def test_keyless_questions_flagged_ai(client):
    tid = make_test(client)
    lines = ["1 | mcq | | 1 | Which river?", "2 | written | | 2 | Name two gases.", "3 | mcq | C | 1 | Which ocean?"]
    assert client.post(f"/api/tests/{tid}/key", json={"text": "\n".join(lines)}).status_code == 200
    qs = got_questions(client, tid)
    assert [(q["key_source"], q["correct_answer"]) for q in qs] == [("ai", None), ("ai", None), ("key", "C")]
    assert client.get("/api/tests").json()[0]["keyless_questions"] == 2


def test_no_key_at_all_mode(client):
    tid = make_test(client)
    text = "\n".join(f"{q.number} | {q.type} | | {q.max_points} | {q.text}" for q in TT.questions)
    assert client.post(f"/api/tests/{tid}/key", json={"text": text}).status_code == 200
    assert {q["key_source"] for q in got_questions(client, tid)} == {"ai"}


@pytest.mark.parametrize("mode", ["paste", "upload_txt", "upload_pdf"])
def test_syllabus_round_trip(client, mode):
    tid = make_test(client)
    if mode == "paste":
        r = client.post(f"/api/tests/{tid}/syllabus", json={"text": SYL})
    elif mode == "upload_txt":
        r = client.post(f"/api/tests/{tid}/syllabus", files={"file": ("s.txt", SYL.encode(), "text/plain")})
    else:
        r = client.post(f"/api/tests/{tid}/syllabus", files={"file": ("s.pdf", pdf_bytes(SYL), "application/pdf")})
    assert r.status_code == 200, r.text
    topics = client.get(f"/api/tests/{tid}").json()["topics"]
    assert [(t["code"], t["title"], t["description"]) for t in topics] == [(t.code, t.title, t.description) for t in TT.topics]


def test_plain_syllabus_lines_get_codes(client):
    tid = make_test(client)
    client.post(f"/api/tests/{tid}/syllabus", json={"text": "Fractions\n\nLinear equations: solving for x\n"})
    topics = client.get(f"/api/tests/{tid}").json()["topics"]
    assert [(t["code"], t["title"], t["description"]) for t in topics] == [
        ("T1", "Fractions", ""), ("T2", "Linear equations", "solving for x")]


def test_reupload_replaces_and_keeps_question_ids(client):
    tid = make_test(client)
    client.post(f"/api/tests/{tid}/key", json={"text": KEY})
    ids = [q["id"] for q in client.get(f"/api/tests/{tid}").json()["questions"]]
    client.post(f"/api/tests/{tid}/key", json={"text": KEY.replace("| B |", "| C |", 1)})
    qs = client.get(f"/api/tests/{tid}").json()["questions"]
    assert [q["id"] for q in qs] == ids and qs[0]["correct_answer"] == "C"


def test_redaction_round_trip_and_validation(client):
    tid = make_test(client)
    regions = [{"page": 1, "box": [0.08, 0.057, 0.734, 0.155]}]
    assert client.put(f"/api/tests/{tid}/redaction", json={"regions": regions}).status_code == 200
    assert client.get(f"/api/tests/{tid}").json()["redaction_regions"] == regions
    bad = [{"page": 1, "box": [0.5, 0.5, 0.2, 0.9]}]  # x1 < x0
    assert client.put(f"/api/tests/{tid}/redaction", json={"regions": bad}).status_code == 422


def test_sample_page_upload(client):
    tid = make_test(client)
    png = io.BytesIO()
    from PIL import Image
    Image.new("L", (124, 175), 255).save(png, "PNG")
    assert client.post(f"/api/tests/{tid}/sample", files={"file": ("p.png", png.getvalue(), "image/png")}).status_code == 200
    r = client.get(f"/api/tests/{tid}/sample")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_bad_key_line_rejected(client):
    tid = make_test(client)
    r = client.post(f"/api/tests/{tid}/key", json={"text": "1 | essay | x | 1 | ?"})
    assert r.status_code == 422 and "line 1" in r.text


def test_slash_inside_answer_is_not_an_alternative(client):
    tid = make_test(client)
    client.post(f"/api/tests/{tid}/key", json={"text": "1 | written | 3/8 | 1 | chance?\n2 | written | 0.6 / .6 | 1 | dec?"})
    qs = got_questions(client, tid)
    assert [q["correct_answer"] for q in qs] == ["3/8", "0.6 / .6"]


def test_malformed_json_is_422(client):
    tid = make_test(client)
    r = client.post(f"/api/tests/{tid}/key", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422
