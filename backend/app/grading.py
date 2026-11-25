"""Answer-area detection on a registered page + MCQ reading + answer matching. Pure functions, local only."""
import re
from difflib import SequenceMatcher

import cv2
import numpy as np

from . import vision

CONTENT_TOP = 110  # below the printed header band (title + page label)
BUBBLE_R = (10, 17)


def answer_boxes(img, ink_thr=160):
    """Printed rectangles for written answers: long horizontal + vertical strokes forming a box."""
    ink = (img < ink_thr).astype(np.uint8) * 255
    hl = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (150, 1)))
    vl = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35)))
    grid = cv2.dilate(hl | vl, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for c in cnts:
        x, y, w, h = cv2.boundingRect(c)
        if w > 400 and 40 < h < 200:
            boxes.append((x, y, x + w, y + h))
    return sorted(boxes, key=lambda b: b[1])


def bubbles(img, exclude):
    """Option bubbles (rings or filled) as (cx, cy, r), outside excluded rectangles."""
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    cs = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1, minDist=18, param1=120, param2=14,
                          minRadius=BUBBLE_R[0], maxRadius=BUBBLE_R[1])
    out = []
    for cx, cy, _ in (cs[0] if cs is not None else []):
        if any(x0 - 5 <= cx <= x1 + 5 and y0 - 5 <= cy <= y1 + 5 for x0, y0, x1, y1 in exclude):
            continue
        hits, cx, cy, r = refine(img, cx, cy)
        if hits >= 0.85:
            out.append((cx, cy, r))
    return out


_ANG = np.linspace(0, 2 * np.pi, 32, endpoint=False)
_OFFS = np.array(sorted(((dx, dy) for dy in range(-3, 4) for dx in range(-3, 4)), key=lambda o: abs(o[0]) + abs(o[1])))


def refine(img, cx, cy, radii=(11, 12, 13, 14)):
    """Best-fitting printed ring near (cx, cy): (fraction of circumference inked, cx, cy, r).
    A printed bubble (empty or filled) has ink all the way round; text and scribbles don't.
    Ties (solid blobs) resolve to the offset nearest the original centre."""
    ink = img < 200  # gray shading over a ring still counts: the ring is there
    h, w = ink.shape
    best = (0.0, float(cx), float(cy), 13.0)
    for r in radii:
        hit = np.zeros((len(_OFFS), len(_ANG)), bool)
        for rr in (r - 1, r, r + 1):
            xs = np.clip(np.round(cx + _OFFS[:, :1] + np.cos(_ANG)[None] * rr).astype(int), 0, w - 1)
            ys = np.clip(np.round(cy + _OFFS[:, 1:] + np.sin(_ANG)[None] * rr).astype(int), 0, h - 1)
            hit |= ink[ys, xs]
        f = hit.mean(1)
        k = int(np.argmax(f))
        if f[k] > best[0]:
            best = (float(f[k]), float(cx + _OFFS[k, 0]), float(cy + _OFFS[k, 1]), float(r))
    return best


def evenly_spaced(xs, tol=12):
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    return all(g > 60 for g in gaps) and max(gaps) - min(gaps) <= tol


def group_options(circles, lo=2, hi=6):
    """Group circles into option sets of 2-6: horizontal rows (same y, even spacing) or vertical stacks
    (same x, 25-60 px apart)."""
    left = sorted(circles, key=lambda c: (c[1], c[0]))
    items, used = [], set()
    for i, c in enumerate(left):  # horizontal rows
        if i in used:
            continue
        row = sorted((j for j, d in enumerate(left) if j not in used and abs(d[1] - c[1]) < 8), key=lambda j: left[j][0])
        if lo <= len(row) <= hi and evenly_spaced([left[j][0] for j in row]):
            used.update(row)
            items.append([left[j] for j in row])
    rest = sorted((left[j] for j in range(len(left)) if j not in used), key=lambda c: c[1])
    taken = set()
    for i, c in enumerate(rest):  # vertical stacks: same x (+-10), evenly spaced downwards
        if i in taken:
            continue
        col = [i]
        for j in range(i + 1, len(rest)):
            if j not in taken and abs(rest[j][0] - c[0]) < 10 and 25 < rest[j][1] - rest[col[-1]][1] < 60:
                col.append(j)
                if len(col) == hi:
                    break
        if len(col) >= lo:
            taken.update(col)
            items.append([rest[j] for j in col])
    return sorted(items, key=lambda it: it[0][1])


def darkness(img, cx, cy, r):
    """Mean ink inside the bubble (ring stroke excluded): 0 = empty paper, 1 = solid black."""
    rr = max(3, int(r) - 4)
    y0, y1, x0, x1 = int(cy) - rr, int(cy) + rr + 1, int(cx) - rr, int(cx) + rr + 1
    patch = img[max(0, y0):y1, max(0, x0):x1].astype(np.float32)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    mask = ((yy - cy) ** 2 + (xx - cx) ** 2 <= rr * rr)[: patch.shape[0], : patch.shape[1]]
    return float(1 - patch[mask].mean() / 255) if mask.any() else 0.0


def read_mcq(img, opts, blank=0.18):
    """Returns (answer 'A'..'D' | '' | 'MULTI', darkness list, confidence 0..1)."""
    d = [darkness(img, *o) for o in opts]
    order = sorted(range(len(d)), key=lambda i: -d[i])
    top, second = d[order[0]], d[order[1]]
    if top < blank:
        return "", d, float(min(1.0, (blank - top) / blank + 0.5))
    if second >= blank and second >= 0.6 * top:
        return "MULTI", d, 0.5
    conf = (top - second) / top  # 1 = one clear mark, 0 = tie
    conf = min(1.0, 0.5 + conf / 2 + min(top - blank, 0.3))
    return "ABCDEFGH"[order[0]], d, float(conf)


def mostly_inside(b, e, frac=0.5):
    """At least half of box b lies inside region e (the blacked-out identity block is not an answer box)."""
    ix = max(0, min(b[2], e[2]) - max(b[0], e[0]))
    iy = max(0, min(b[3], e[3]) - max(b[1], e[1]))
    return ix * iy >= frac * (b[2] - b[0]) * (b[3] - b[1])


def detect_items(img, exclude=()):
    """All answer areas on a registered page, top to bottom: {'kind','top','bottom', 'opts'|'box'}."""
    boxes = [b for b in answer_boxes(img) if not any(mostly_inside(b, e) for e in exclude)]
    items = [dict(kind="written", box=b, top=b[1], bottom=b[3]) for b in boxes]
    for opts in group_options(bubbles(img, list(exclude) + boxes)):
        items.append(dict(kind="mcq", opts=opts, top=int(min(o[1] - o[2] for o in opts)), bottom=int(max(o[1] + o[2] for o in opts))))
    return sorted(items, key=lambda it: it["top"])


NUM_RE = re.compile(r"^\D{0,2}?(\d{1,3})")


def number_items(img, items, top):
    """Read the printed question number on the first text line above each item; repair gaps by sequence."""
    prev = top
    for it in items:
        it["number"] = None
        col = img[prev:it["top"] - 2, 100:128] < 128  # question numbers start at the left margin
        rows = col.sum(1) > 0
        y0 = 0
        while y0 < len(rows):  # first run of >= 10 inked rows = the number's text line
            if rows[y0]:
                y1 = y0
                while y1 + 1 < len(rows) and rows[y1 + 1]:
                    y1 += 1
                if y1 - y0 >= 9:
                    text, _ = vision.ocr_crop(img[prev + y0 - 4: prev + y1 + 5, 95:215])
                    m = NUM_RE.match(text.translate(vision.DIGIT_FIX) if text else "")
                    if m:
                        it["number"] = int(m.group(1))
                    break
                y0 = y1
            y0 += 1
        prev = it["bottom"] + 2
    nums = [it["number"] for it in items]
    for i in range(1, len(items)):  # repair OCR misses/misreads using neighbours (a gap = undetected item)
        p, cur = items[i - 1]["number"], nums[i]
        nxt = nums[i + 1] if i + 1 < len(nums) else None
        if p is not None and (cur is None or cur <= p or (cur != p + 1 and nxt == p + 2)):
            items[i]["number"] = p + 1
    for i in range(len(items) - 2, -1, -1):
        if items[i]["number"] is None and items[i + 1]["number"] is not None:
            items[i]["number"] = items[i + 1]["number"] - 1
    return items


# ---------- written answer matching ----------

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9./]", "", s.lower())


def key_parts(correct_answer: str) -> list[list[str]]:
    return [[a.strip() for a in re.split(r"\s+/\s+", part) if a.strip()] for part in correct_answer.split(";") if part.strip()]


def similarity(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def match_written(read: str, correct_answer: str, max_points: int, ocr_conf: float, accept=0.8):
    """Grade a transcription against key parts (order-free). Returns (score, is_correct, confidence, normalized)."""
    parts = key_parts(correct_answer)
    pieces = [p for p in re.split(r"[,;]|\band\b|&", read) if norm(p)] if len(parts) > 1 else [read]
    pieces = pieces or [""]
    used, score, margins = set(), 0, []
    for alts in parts:
        best, best_j = 0.0, None
        for j, piece in enumerate(pieces):
            if j in used:
                continue
            s = max(similarity(piece, a) for a in alts)
            if s > best:
                best, best_j = s, j
        if best >= accept:
            score += 1
            used.add(best_j)
        margins.append(abs(best - accept))
    margin = min(margins) if margins else 0
    conf = ocr_conf * min(1.0, 0.6 + margin * 2)
    if len(parts) > 1 and len(pieces) == 1 and score < len(parts):  # separator lost in OCR: "19451939"
        whole = norm(read)
        sub = sum(any(norm(a) and norm(a) in whole for a in alts) for alts in parts)
        if sub > score:
            score, conf = sub, ocr_conf * 0.9
    points = round(score * max_points / len(parts)) if parts else 0
    if not norm(read):
        conf = ocr_conf
    return points, points == max_points, float(conf), " | ".join(norm(p) for p in pieces)
