"""Printed-test layout, handwriting, bubble marks and scanner noise (pure rendering, no ground truth)."""
import hashlib, io, math, random, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import TESTS  # noqa: E402

W, H = 1240, 1754  # A4 at 150 dpi
FONTS = "C:/Windows/Fonts/"
PRINT, PRINT_BOLD = FONTS + "arial.ttf", FONTS + "arialbd.ttf"
HANDS = ["segoepr.ttf", "LHANDW.TTF", "comic.ttf", "segoesc.ttf", "Inkfree.ttf"]
FID, FID_POS = 36, [(50, 50), (W - 86, 50), (50, H - 86), (W - 86, H - 86)]  # TL has a hole (orientation)
NAME_BOX, ID_BOX = (240, 110, 900, 178), (240, 194, 560, 262)
YEAR_BOX, SECTION_BOX = (670, 194, 770, 262), (900, 194, 1120, 262)
IDENTITY = (100, 100, 1125, 272)
TOP1, TOP, BOTTOM, LEFT, RIGHT = 310, 120, H - 120, 110, 1130
R = 13  # bubble radius


def R_(*k):
    return random.Random(":".join(map(str, k)))


def NR(*k):
    return np.random.default_rng(int.from_bytes(hashlib.sha256(":".join(map(str, k)).encode()).digest()[:8], "little"))


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(text, f, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def printed_text(q):
    if q["type"] == "mcq":
        return q["text"] + "  " + "  ".join(f"({'ABCD'[i]}) {o}" for i, o in enumerate(q["options"]))
    return q["text"]


# ---------- layout (canonical coordinates) ----------

def layout(t):
    qf = font(PRINT, 24)
    of = font(PRINT, 22)
    qs, n = t["questions"], t["pages"]
    sizes = [len(qs) // n + (i < len(qs) % n) for i in range(n)]
    pages, k = [], 0
    for p in range(n):
        y, items = (TOP1 if p == 0 else TOP), []
        for _ in range(sizes[p]):
            q, num = qs[k], k + 1
            k += 1
            lines = wrap(f"{num}. {q['text']}", qf, RIGHT - LEFT)
            text_y, y = y, y + 32 * len(lines) + 10
            if q["type"] == "mcq":
                horiz = all(of.getlength(o) <= 190 for o in q["options"])
                bubbles = []
                for i in range(4):
                    cx, cy = (150 + i * 250, y + 18) if horiz else (150, y + 18 + 42 * i)
                    bubbles.append((cx - R, cy - R, cx + R, cy + R))
                y += 42 if horiz else 42 * 4
                items.append(dict(kind="mcq", number=num, text_y=text_y, lines=lines, horiz=horiz,
                                  box=(LEFT, text_y, RIGHT, y), bubbles=bubbles))
            else:
                box = (130, y, 1100, y + 78)
                y += 78
                items.append(dict(kind="written", number=num, text_y=text_y, lines=lines, box=(LEFT, text_y, RIGHT, y),
                                  answer_box=box))
            y += 34
        assert y <= BOTTOM, f"{t['id']} page {p + 1} overflows ({y})"
        pages.append(items)
    return pages


# ---------- rendering ----------

def hand(img, text, box, f, ink, r, align_left=True):
    """Draw jittered handwriting inside box (darken-composite)."""
    x0, y0, x1, y1 = box
    layer = Image.new("L", (x1 - x0, y1 - y0), 255)
    d = ImageDraw.Draw(layer)
    size = f.size
    gb = f.getbbox("Hg8")
    x, base = 12 + r.randint(0, 25), (y1 - y0 - (gb[3] - gb[1])) // 2 - gb[1] + r.randint(-4, 4)
    for ch in text:
        d.text((x, base + r.randint(-2, 2)), ch, font=f, fill=max(0, min(255, ink + r.randint(-12, 12))))
        x += f.getlength(ch) + r.uniform(-1, 2)
        if x > layer.width - size:
            break
    layer = layer.rotate(r.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=255)
    region = img.crop(box)
    img.paste(ImageChops.darker(region, layer), box)


def mark_bubble(d, bb, color, r, partial=False):
    cx, cy = (bb[0] + bb[2]) / 2 + r.uniform(-2, 2), (bb[1] + bb[3]) / 2 + r.uniform(-2, 2)
    rr = R + r.uniform(-1, 2)
    if partial:
        d.ellipse((cx - rr, cy - rr * 0.5, cx + rr * 0.6, cy + rr * 0.5), fill=color)
        return
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=color)
    for _ in range(r.randint(1, 3)):  # scribble strokes poking out
        a = r.uniform(0, math.pi)
        dx, dy = math.cos(a) * (rr + 4), math.sin(a) * (rr + 4)
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=color, width=r.randint(2, 4))


def draw_template(t, page_no, items):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    for i, (x, y) in enumerate(FID_POS):
        d.rectangle((x, y, x + FID, y + FID), fill=0)
        if i == 0:
            d.rectangle((x + 11, y + 11, x + FID - 11, y + FID - 11), fill=255)
    d.text((LEFT, 52), t["name"], font=font(PRINT_BOLD, 24), fill=0)
    lab = f"Page {page_no} of {t['pages']}"
    pf = font(PRINT, 24)
    d.text((RIGHT - pf.getlength(lab), 52), lab, font=pf, fill=0)
    if page_no == 1:
        lf = font(PRINT, 24)
        d.text((LEFT, 130), "Name:", font=lf, fill=0)
        d.text((LEFT, 212), "ID:", font=lf, fill=0)
        d.text((590, 212), "Year:", font=lf, fill=0)
        d.text((800, 212), "Section:", font=lf, fill=0)
        for box in (NAME_BOX, ID_BOX, YEAR_BOX, SECTION_BOX):
            d.rectangle(box, outline=0, width=2)
    qf, of = font(PRINT, 24), font(PRINT, 22)
    q = {i + 1: x for i, x in enumerate(t["questions"])}
    for it in items:
        for j, line in enumerate(it["lines"]):
            d.text((LEFT, it["text_y"] + 32 * j), line, font=qf, fill=0)
        if it["kind"] == "mcq":
            for i, bb in enumerate(it["bubbles"]):
                d.ellipse(bb, outline=0, width=2)
                d.text((bb[2] + 10, bb[1] - 1), f"{'ABCD'[i]}.  {q[it['number']]['options'][i]}", font=of, fill=0)
        else:
            d.rectangle(it["answer_box"], outline=0, width=2)
    return img


def degrade(img, quality, r, nr):
    noisy = quality == "noisy"
    bg = r.randint(238, 252)
    ang = r.uniform(-2.5, 2.5) if noisy else r.uniform(-0.4, 0.4)
    sh = 14 if noisy else 4
    img = img.rotate(ang, resample=Image.BICUBIC, fillcolor=255, translate=(r.randint(-sh, sh), r.randint(-sh, sh)))
    if noisy:
        img = img.filter(ImageFilter.GaussianBlur(r.uniform(0.5, 1.1)))
    a = np.asarray(img, dtype=np.float32) * (bg / 255.0)
    if noisy:
        width, depth = r.randint(120, 320), r.uniform(0.55, 0.8)
        ramp = np.ones(max(W, H), np.float32)
        ramp[:width] = np.linspace(depth, 1.0, width)
        edge = r.choice("LRTB")
        if edge == "L": a *= ramp[:W][None, :]
        elif edge == "R": a *= ramp[:W][::-1][None, :]
        elif edge == "T": a *= ramp[:H][:, None]
        else: a *= ramp[:H][::-1][:, None]
        for _ in range(r.randint(5, 30)):  # dust specks
            x, y = r.randrange(W), r.randrange(H)
            a[y:y + 2, x:x + 2] *= 0.3
    a += nr.normal(0, r.uniform(4, 8) if noisy else 2, a.shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=r.randint(70, 85) if noisy else 92)
    return buf.getvalue()


def render_page(job):
    t = next(x for x in TESTS if x["id"] == job["test"])
    items = layout(t)[job["page"] - 1]
    paper = job["paper"]
    r = R_(*job["key"])
    img = draw_template(t, job["page"], items)
    d = ImageDraw.Draw(img)
    hf = font(FONTS + paper["font"], paper["hsize"])
    pr = R_(*job["key"][:-1], "ink")  # same marks on a duplicate scan
    if job["page"] == 1:
        hand(img, paper["student_name"], NAME_BOX, hf, paper["ink"], pr)
        if paper["id_written"]:
            hand(img, paper["student_id"], ID_BOX, hf, paper["ink"], pr)
        cr = R_(*job["key"][:-1], "class-ink")  # separate stream: other marks stay identical
        for value, box in ((paper["year"], YEAR_BOX), (paper["section"], SECTION_BOX)):
            if value:
                hand(img, value, box, hf, paper["ink"], cr)
    resp = {x["number"]: x for x in paper["responses"]}
    for it in items:
        x = resp[it["number"]]
        if it["kind"] == "mcq":
            style, letter = x["mark_style"], x["marked"]
            ink = paper["ink"]
            if style == "none":
                continue
            if style == "double":
                a, b = pr.sample(range(4), 2)
                mark_bubble(d, it["bubbles"][a], ink, pr); mark_bubble(d, it["bubbles"][b], ink, pr)
                continue
            i = "ABCD".index(letter)
            if style == "erased_extra":
                j = pr.choice([k for k in range(4) if k != i])
                mark_bubble(d, it["bubbles"][j], pr.randint(205, 220), pr, partial=True)
            mark_bubble(d, it["bubbles"][i], pr.randint(150, 175) if style == "faint" else ink, pr)
        elif x["text"]:
            hand(img, x["text"], it["answer_box"], hf, paper["ink"], pr)
    if job["rotated180"]:
        img = img.rotate(180)
    return job["out"], degrade(img, job["quality"], r, NR(*job["key"]))
