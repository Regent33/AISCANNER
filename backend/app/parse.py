"""Answer-key and syllabus text parsers (the same text arrives by paste or by file upload)."""
import re

import pymupdf as fitz


class ParseError(ValueError):
    pass


def file_text(name: str, data: bytes) -> str:
    if name.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(p.get_text() for p in doc)
    return data.decode("utf-8-sig", errors="replace")


ALT = re.compile(r"\s+/\s+")  # "pyramids / pyramid" = alternatives; "3/8" is one answer
SHORT = re.compile(r"^\s*(?:q|question)?\s*(\d+)\s*[.):\-]?\s+(.*)$", re.I)


def parse_key(text: str) -> list[dict]:
    """Full: `number | type | answer | points | text`. Short: `1. B` (type inferred: single A-D letter = mcq).
    Blank answer => keyless (key_source 'ai'). Written parts split by ';' (1 point each by default),
    accepted alternatives by ' / ' (spaces required, so '3/8' stays one answer)."""
    out = []
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            f = [p.strip() for p in line.split("|")]
            f += [""] * (5 - len(f))
            num, typ, ans, pts, qtext = f[0], f[1].lower(), f[2], f[3], "|".join(f[4:]).strip(" |")
        else:
            m = SHORT.match(line)
            if not m:
                raise ParseError(f"line {i}: expected '1. B' or 'number | type | answer | points | text'")
            num, ans, pts, qtext = m.group(1), m.group(2).strip(), "", ""
            typ = "mcq" if re.fullmatch(r"[A-Ea-e]", ans) else "written"
        num = num.lower().lstrip("q").rstrip(".")
        if not num.isdigit():
            raise ParseError(f"line {i}: question number '{num}' is not a number")
        if typ not in ("mcq", "written"):
            raise ParseError(f"line {i}: type must be mcq or written, got '{typ}'")
        if typ == "mcq":
            ans = ans.upper()
            if ans and (len(ans) != 1 or ans not in "ABCDE"):
                raise ParseError(f"line {i}: mcq answer must be one letter, A to E")
        parts = [p for p in ans.split(";") if p.strip()]
        ans = "; ".join(" / ".join(a.strip() for a in ALT.split(p)) for p in parts) if typ == "written" else ans
        try:
            points = int(pts) if pts else (max(1, len(parts)) if typ == "written" else 1)
        except ValueError:
            raise ParseError(f"line {i}: points must be a whole number") from None
        out.append(dict(number=int(num), type=typ, correct_answer=ans or None, max_points=points,
                        text=qtext, key_source="key" if ans else "ai"))
    if not out:
        raise ParseError("no questions found")
    nums = [q["number"] for q in out]
    if len(set(nums)) != len(nums):
        raise ParseError("duplicate question numbers")
    return out


OPT_RE = re.compile(r"\(([A-F])\)\s*")


def split_options(text: str):
    """'Which ...?  (A) Leaves (B) Roots' -> ('Which ...?', ['Leaves', 'Roots']); no options -> (text, None)."""
    parts = OPT_RE.split(text)
    letters, opts = parts[1::2], [p.strip() for p in parts[2::2]]
    if len(letters) < 2 or letters != list("ABCDEF"[: len(letters)]):
        return text.strip(), None
    return parts[0].strip(), opts


def parse_syllabus(text: str) -> list[dict]:
    """`CODE | Title | description` per line, or plain `Title[: description]` lines (auto-coded T1, T2...)."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            f = [p.strip() for p in line.split("|")] + ["", ""]
            out.append(dict(code=f[0], title=f[1] or f[0], description="|".join(f[2:]).strip(" |")))
        else:
            title, _, desc = line.partition(":")
            out.append(dict(code=f"T{len(out) + 1}", title=title.strip(), description=desc.strip()))
    if not out:
        raise ParseError("no topics found")
    return out
