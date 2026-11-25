"""Printable test: the answer key's questions laid out in the format the scanner reads (corner markers, "Page k of N",
student details block, option bubbles, answer boxes), as a vector PDF that prints sharply on any printer.
All geometry is in canonical page pixels (A4 at 150 dpi, the frame vision.register() maps scans onto)."""
import io

import pymupdf as fitz
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from . import vision
from .parse import split_options

W, H = vision.W, vision.H
PT = 72 / 150  # canonical px -> PDF points
FID = vision.FID_SIZE
FID_BOXES = [(int(x) - FID // 2, int(y) - FID // 2) for x, y in vision.FID_CENTERS]  # TL (hollow), TR, BR, BL
LEFT, RIGHT, TOP1, TOP, BOTTOM = 110, 1130, 310, 120, H - 120
R, ROW, GAP, LINE, Q_SIZE, OPT_SIZE = 13, 42, 34, 32, 24, 22
FIELDS = [("Name:", (110, 130), (240, 110, 900, 178)), ("ID:", (110, 212), (240, 194, 560, 262)),
          ("Year:", (590, 212), (670, 194, 770, 262)), ("Section:", (800, 212), (900, 194, 1120, 262))]
IDENTITY = (100, 100, 1125, 272)
IDENTITY_REGION = {"page": 1, "box": [round(v / s, 4) for v, s in zip(IDENTITY, (W, H, W, H))]}
LETTERS = "ABCDEF"


def width(s: str, size: int, bold=False) -> float:
    return stringWidth(s, "Helvetica-Bold" if bold else "Helvetica", size * PT) / PT


def wrap(text: str, size: int, maxw: float) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if width(t, size) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def measure(q: dict) -> dict:
    stem, opts = split_options(q["text"]) if q["type"] == "mcq" else (q["text"], None)
    lines = wrap(f"{q['number']}. {stem or 'Question ' + str(q['number'])}", Q_SIZE, RIGHT - LEFT)
    m = dict(kind=q["type"], number=q["number"], lines=lines)
    if q["type"] == "mcq":
        n = len(opts) if opts else 4  # no options in the key: bubbles A-D with letters only
        step = min(250, 1000 // n)
        labels = [f"{LETTERS[i]}.  {opts[i]}" if opts else f"{LETTERS[i]}." for i in range(n)]
        horiz = all(width(lab, OPT_SIZE) <= step - 40 for lab in labels)
        m.update(labels=labels, step=step, horiz=horiz, body=ROW if horiz else ROW * n)
    else:
        m.update(body=78)
    m["height"] = LINE * len(lines) + 10 + m["body"] + GAP
    return m


def place(m: dict, y: int) -> dict:
    it = dict(m, text_y=y)
    top = y + LINE * len(m["lines"]) + 10
    if m["kind"] == "mcq":
        centres = [(150 + i * m["step"], top + 18) if m["horiz"] else (150, top + 18 + ROW * i) for i in range(len(m["labels"]))]
        it["bubbles"] = [(cx - R, cy - R, cx + R, cy + R) for cx, cy in centres]
    else:
        it["answer_box"] = (130, top, 1100, top + 78)
    it["box"] = (LEFT, y, RIGHT, top + m["body"])
    return it


def layout(questions: list[dict], pages_hint: int | None = None) -> list[list[dict]]:
    """Questions flowed page by page; spread evenly only when pages_hint asks for more pages than that.
    Stable: the page count it returns, passed back as pages_hint, gives the same layout."""
    ms = [measure(q) for q in sorted(questions, key=lambda q: q["number"])]

    def fill(groups):
        pages = []
        for p, group in enumerate(groups):
            y, items = (TOP1 if p == 0 else TOP), []
            for m in group:
                if y + m["height"] - GAP > BOTTOM:
                    return None
                items.append(place(m, y))
                y += m["height"]
            pages.append(items)
        return pages

    groups, y = [[]], TOP1
    for m in ms:  # flow page by page
        if groups[-1] and y + m["height"] - GAP > BOTTOM:
            groups.append([])
            y = TOP
        groups[-1].append(m)
        y += m["height"]
    if pages_hint and len(groups) < pages_hint <= len(ms):  # the teacher asked for more pages: spread evenly
        sizes = [len(ms) // pages_hint + (i < len(ms) % pages_hint) for i in range(pages_hint)]
        spread, k = [], 0
        for size in sizes:
            spread.append(ms[k:k + size])
            k += size
        if (fitted := fill(spread)) is not None:
            return fitted
    pages = fill(groups)
    if pages is None:
        raise ValueError("a question is too long to fit on one page; shorten its text")
    return pages


def render_pdf(title: str, pages: list[list[dict]]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W * PT, H * PT))
    c.setTitle(title)
    for p, items in enumerate(pages, 1):
        draw_page(c, title, p, len(pages), items)
        c.showPage()
    c.save()
    return buf.getvalue()


def draw_page(c, title, page_no, n_pages, items):
    def text(x, ytop, s, size, bold=False, right=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size * PT)
        y = (H - (ytop + size * 0.78)) * PT  # PDF baseline from the text's top edge
        (c.drawRightString if right else c.drawString)(x * PT, y, s)

    def rect(box, fill=False):
        x0, y0, x1, y1 = box
        c.rect(x0 * PT, (H - y1) * PT, (x1 - x0) * PT, (y1 - y0) * PT, stroke=0 if fill else 1, fill=1 if fill else 0)

    c.setLineWidth(2 * PT)
    for i, (x, y) in enumerate(FID_BOXES):
        c.setFillGray(0)
        rect((x, y, x + FID, y + FID), fill=True)
        if i == 0:  # hollow top-left marker tells the scanner which way up the page is
            c.setFillGray(1)
            rect((x + 11, y + 11, x + FID - 11, y + FID - 11), fill=True)
    c.setFillGray(0)
    label = f"Page {page_no} of {n_pages}"
    room = RIGHT - LEFT - width(label, Q_SIZE) - 40
    while width(title, Q_SIZE, bold=True) > room and len(title) > 4:
        title = title[:-2] + "…"  # drops one character per pass, keeps the ellipsis
    text(LEFT, 52, title, Q_SIZE, bold=True)
    text(RIGHT, 52, label, Q_SIZE, right=True)
    text(LEFT, 84, "Shade one bubble per question. Write each answer inside its box.", 16)
    if page_no == 1:
        for lab, (lx, ly), box in FIELDS:
            text(lx, ly, lab, Q_SIZE)
            rect(box)
    for it in items:
        for j, line in enumerate(it["lines"]):
            text(LEFT, it["text_y"] + LINE * j, line, Q_SIZE)
        if it["kind"] == "mcq":
            for (x0, y0, x1, y1), lab in zip(it["bubbles"], it["labels"]):
                c.circle((x0 + R) * PT, (H - (y0 + R)) * PT, R * PT, stroke=1, fill=0)
                text(x1 + 10, y0 - 1, lab, OPT_SIZE)
        else:
            rect(it["answer_box"])


def page_png(pdf: bytes, index: int = 0) -> bytes:
    """One page rasterised at the scanner's 150 dpi (the sample page shown in the test wizard)."""
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        return doc[index].get_pixmap(dpi=150, colorspace=fitz.csGRAY).tobytes("png")
