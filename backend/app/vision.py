"""Local image processing: registration, contrast normalisation, page labels, identity OCR.
Nothing here talks to the network; identity reading happens only here."""
import re
import threading

import cv2
import numpy as np

W, H = 1240, 1754  # canonical registered page (A4 @ 150 dpi)
FID_CENTERS = np.float32([[68, 68], [1172, 68], [1172, 1686], [68, 1686]])  # TL, TR, BR, BL
FID_SIZE = 36

_ocr, _ocr_lock = None, threading.Lock()


def ocr():
    global _ocr
    with _ocr_lock:
        if _ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            _ocr = RapidOCR(det_limit_type="max", det_limit_side_len=1280, intra_op_num_threads=4, inter_op_num_threads=1)
        return _ocr


def load_gray(path) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"cannot decode {path}")
    return img


def flatten(g: np.ndarray, k: int = 61) -> np.ndarray:
    """Divide out the paper background (shadows, tint) so ink is dark and paper ~255."""
    bg = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (k, k)))
    return np.clip(g.astype(np.float32) / np.maximum(bg, 1) * 255, 0, 255).astype(np.uint8)


def find_fiducials(g: np.ndarray):
    """Return 4 fiducial centres ordered TL,TR,BR,BL in *page* terms (hollow marker = page top-left), or None."""
    h, w = g.shape
    s = FID_SIZE * w / W
    ink = (flatten(g, k=max(31, int(s * 1.8) | 1)) < 128).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(ink, 8)
    cands = []
    for i in range(1, n):
        x, y, bw, bh, area = stats[i]
        if not (0.6 * s <= bw <= 1.6 * s and 0.6 * s <= bh <= 1.6 * s and abs(bw - bh) < 0.3 * max(bw, bh)):
            continue
        if area < 0.45 * bw * bh:  # hollow marker keeps ~70% of its box, solid ~100%, a ring/bubble far less
            continue
        cands.append((cent[i][0], cent[i][1], area / (bw * bh)))
    if len(cands) < 4:
        return None
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    pts = []
    for cx, cy in corners:
        best = min(cands, key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2)
        if ((best[0] - cx) ** 2 + (best[1] - cy) ** 2) ** 0.5 > 0.25 * w:
            return None
        pts.append(best)
    if len({(p[0], p[1]) for p in pts}) < 4:
        return None
    hollow = min(range(4), key=lambda i: pts[i][2])  # lowest fill ratio
    order = [(hollow + k) % 4 for k in range(4)]  # image corners are clockwise already
    return np.float32([[pts[i][0], pts[i][1]] for i in order]), hollow != 0


def register(g: np.ndarray):
    """Warp a scanned page onto the canonical frame. Returns (homography | None, rotated: bool)."""
    found = find_fiducials(cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    if found is None:
        return None, False
    src, rotated = found
    src = src * 2 + 0.5
    return cv2.getPerspectiveTransform(src, FID_CENTERS), rotated


def warp(g: np.ndarray, Hm) -> np.ndarray:
    return cv2.warpPerspective(g, np.asarray(Hm, np.float64), (W, H), flags=cv2.INTER_LINEAR, borderValue=255)


def clean_lines(g: np.ndarray, vlen=55, hlen=80) -> np.ndarray:
    """Erase printed box borders (long straight lines) so OCR doesn't read them as '1' or 'l'."""
    ink = (g < 160).astype(np.uint8) * 255
    lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, vlen)))
    lines |= cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (hlen, 1)))
    lines = cv2.dilate(lines, np.ones((3, 3), np.uint8))
    out = g.copy()
    out[lines > 0] = 255
    return out


def ocr_lines(g: np.ndarray):
    """Detect + recognise text lines. Returns [(text, score, (x0,y0,x1,y1))] top-to-bottom."""
    res, _ = ocr()(cv2.cvtColor(g, cv2.COLOR_GRAY2BGR), use_cls=False)
    out = []
    for box, text, score in res or []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        out.append((text, float(score), (min(xs), min(ys), max(xs), max(ys))))
    return sorted(out, key=lambda t: (t[2][1], t[2][0]))


def ocr_crop(g: np.ndarray):
    """Recognise one tight text line (no detection). Returns (text, score); ('', 0) if blank."""
    if (g < 200).sum() < 40:
        return "", 0.95  # clearly empty: confidently blank
    ink = g < 150
    if ink.sum() < 30:
        return "", 0.3  # only faint marks: let a person decide
    ys, xs = np.nonzero(ink)
    pad = 8
    y0, y1 = max(0, ys.min() - pad), min(g.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(g.shape[1], xs.max() + pad)
    res, _ = ocr()(cv2.cvtColor(g[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR), use_det=False, use_cls=False, use_rec=True)
    if not res:
        return "", 0.0
    return res[0][0], float(res[0][1])


PAGE_RE = re.compile(r"page\s*(\d+)\s*(?:of|/)\s*(\d+)", re.I)


def read_page_label(reg: np.ndarray):
    """Find 'Page k of N' in the top band. Returns (k, N) or (None, None)."""
    band = reg[25:115, 90:1150]
    for text, _, _ in ocr_lines(band):
        m = PAGE_RE.search(text.replace(" ", " "))
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


DIGIT_FIX = str.maketrans("OoQDIlL|iSsZzBbGgqT", "0000111115522886697")
FIELD_RE = re.compile(r"^\s*(student\s*id|id\s*no|name|id|year(?:\s*level)?|grade|section|sec)\b\s*[:.]?\s*(.*)$", re.I)


def field_of(label: str) -> str:
    l = label.lower()
    return "name" if l.startswith("name") else "year" if l.startswith(("year", "grade")) else         "section" if l.startswith("sec") else "id"


def clean_value(field: str, text: str) -> str:
    t = text.strip(" :.|")
    if field in ("id", "year"):
        digits = re.sub(r"\D", "", t.translate(DIGIT_FIX))
        return digits[:2] if field == "year" else digits
    return t


def region_px(box):
    x0, y0, x1, y1 = box
    return int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)


def read_identity(reg: np.ndarray, regions):
    """OCR the teacher-defined identity region(s) of page 1. Each handwritten line goes to the printed label
    (Name / ID / Year / Section) to its left on the same row; without labels, digits => ID and words => name.
    Returns dict(name, student_id, year, section, id_conf, name_conf)."""
    best = {f: ("", 0.0) for f in ("name", "id", "year", "section")}
    for r in regions:
        if r["page"] != 1:
            continue
        x0, y0, x1, y1 = region_px(r["box"])
        labels, values = [], []
        for text, score, box in ocr_lines(clean_lines(flatten(reg[y0:y1, x0:x1]))):
            m = FIELD_RE.match(text)
            if m:
                labels.append((field_of(m.group(1)), box))
                if m.group(2).strip(" :."):
                    values.append((m.group(2), score, box, field_of(m.group(1))))
            else:
                values.append((text, score, box, None))
        for text, score, box, field in values:
            if field is None:
                row = [(f, b) for f, b in labels if b[2] <= box[0] + 8 and b[1] < box[3] and box[1] < b[3]]
                if row:
                    field = max(row, key=lambda fb: fb[1][2])[0]  # nearest label to the left
                else:
                    digits = sum(ch.isdigit() for ch in text)
                    field = "id" if digits >= 4 and digits >= sum(ch.isalpha() for ch in text) else "name"
            value = clean_value(field, text)
            if value and score > best[field][1]:
                best[field] = (value, score)
        crop = clean_lines(flatten(reg[y0:y1, x0:x1]))
        for field, b in labels:  # detector skipped a short value (a lone digit): read the strip right of the label
            if best[field][0]:
                continue
            right = [o[0] for _, o in labels if o[0] > b[2] and o[1] < b[3] and b[1] < o[3]]
            ya, yb = int(max(0, b[1] - 25)), int(min(crop.shape[0], b[3] + 25))
            text, score = ocr_crop(crop[ya:yb, int(b[2]) + 4:int(min(right, default=crop.shape[1])) - 4])
            value = clean_value(field, text)
            if value:
                best[field] = (value, score)
    if len(best["id"][0]) < 4:  # an ID needs at least 4 digits to be usable
        best["id"] = ("", 0.0)
    return dict(name=best["name"][0], student_id=best["id"][0], year=best["year"][0], section=best["section"][0],
                id_conf=best["id"][1], name_conf=best["name"][1])
