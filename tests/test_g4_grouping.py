"""Grouping rules on synthetic page sequences (no images): never drop pages, flag every anomaly."""
from app import pipeline


def pages(*nums, dup_pairs=()):
    out = []
    for i, k in enumerate(nums):
        out.append(dict(id=i, page_no=k, page_total=None, status="prepped" if k != "X" else "unregistered"))
        if k == "X":
            out[-1]["page_no"] = None
    return out


def run(monkeypatch, nums, n=None, same=()):
    monkeypatch.setattr(pipeline, "same_scan", lambda a, b: (a["id"], b["id"]) in same)
    gs = pipeline.build_groups(pages(*nums), n)
    return [([p["id"] for p in g["pages"]], sorted(g["flags"])) for g in gs]


def test_normal(monkeypatch):
    assert run(monkeypatch, [1, 2, 1, 2], 2) == [([0, 1], []), ([2, 3], [])]


def test_missing_middle_page(monkeypatch):
    assert run(monkeypatch, [1, 3, 1, 2, 3], 3) == [([0, 1], ["missing_pages:2"]), ([2, 3, 4], [])]


def test_missing_page_one_detected_by_backwards_number(monkeypatch):
    assert run(monkeypatch, [1, 2, 3, 2, 3], 3) == [([0, 1, 2], []), ([3, 4], ["missing_page_1", "missing_pages:1"])]


def test_duplicate_vs_next_paper_missing_page_one(monkeypatch):
    # 2-page test: "2, 2" is a double scan only if the images match
    assert run(monkeypatch, [1, 2, 2, 1, 2], 2, same={(1, 2)}) == [([0, 1, 2], ["duplicate_page"]), ([3, 4], [])]
    assert run(monkeypatch, [1, 2, 2, 1, 2], 2) == [([0, 1], []), ([2], ["missing_page_1", "missing_pages:1"]), ([3, 4], [])]


def test_one_page_test_duplicate(monkeypatch):
    assert run(monkeypatch, [1, 1, 1], 1, same={(0, 1)}) == [([0, 1], ["duplicate_page"]), ([2], [])]


def test_unreadable_page_kept_and_flagged(monkeypatch):
    assert run(monkeypatch, [1, "X", 1], 2) == [([0, 1], ["unreadable_page"]), ([2], ["missing_pages:2"])]


def test_no_page_dropped(monkeypatch):
    seq = [1, 2, None, 3, 1, 1, 2, 3, 3, 2]
    got = run(monkeypatch, seq, 3)
    assert sorted(i for ids, _ in got for i in ids) == list(range(len(seq)))
