"""PDF export of the teacher report: Summary, Topics to reinforce, Reteach suggestions, Question by question.
Built only from the report dict, which holds no student names or IDs."""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SECTIONS = ("Summary", "Topics to reinforce", "Reteach suggestions", "Question by question")


def pct(x):
    return "n/a" if x is None else f"{round(x * 100)}%"


def table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f5")])]))
    return t


def render(r: dict) -> bytes:
    st = getSampleStyleSheet()
    body, h1, h2 = st["BodyText"], st["Title"], st["Heading2"]
    p = lambda s, style=body: Paragraph(escape(str(s)), style)  # noqa: E731
    out = [p(f"Report: {r['test']['name']}", h1), p(SECTIONS[0], h2),
           p(f"{r['papers']} papers graded" + (f" in {r['test']['subject']}." if r["test"]["subject"] else "."))]
    if r["provisional"]:
        out.append(p(f"Provisional: {r['pending_review']} items still need a teacher's check in Review."))
    if any(t["unverified"] for t in r["topics"]):
        out.append(p("Topics marked * include questions whose answers were worked out by the AI and are unverified."))
    out += [Spacer(1, 4 * mm), p(SECTIONS[1], h2),
            table([["#", "Topic", "Missed", "Points lost", "Questions"]] +
                  [[i + 1, p(t["title"] + (" *" if t["unverified"] else "")), pct(t["miss_rate"]),
                    f"{t['points_missed']:g} of {t['points_possible']:g}", p(", ".join(map(str, t["questions"])))]
                   for i, t in enumerate(r["topics"])], [10 * mm, 62 * mm, 20 * mm, 28 * mm, 45 * mm]),
            Spacer(1, 4 * mm), p(SECTIONS[2], h2)]
    for rt in r["reteach"]:
        out += [p(rt["title"], st["Heading4"]),
                ListFlowable([ListItem(p(a)) for a in rt["activities"]], bulletType="bullet", leftIndent=12)]
    if not r["reteach"]:
        out.append(p("No suggestions yet: scan and grade some papers first."))
    out += [Spacer(1, 4 * mm), p(SECTIONS[3], h2),
            table([["Q", "Topic", "Missed", "Key", "Most common wrong answer"]] +
                  [[q["number"], p(q["topic_title"] or "Not mapped"), pct(q["miss_rate"]),
                    p((q["correct_answer"] or "n/a") + (" (AI, unverified)" if q["key_source"] == "ai" else "")),
                    p(q["common_wrong"] or "n/a")] for q in r["questions"]], [10 * mm, 50 * mm, 18 * mm, 42 * mm, 45 * mm])]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, title=f"Report: {r['test']['name']}", leftMargin=18 * mm, rightMargin=18 * mm,
                      topMargin=16 * mm, bottomMargin=16 * mm).build(out)
    return buf.getvalue()
