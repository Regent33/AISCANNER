"""Offline analysis: question -> syllabus topic (lexical), miss-rate aggregation, reteach templates, keyless keys.
Everything here sees question/syllabus text and aggregate scores only, never student data."""
import math
import re
from collections import Counter

STOP = set("""a an and any are as at be been by can could did do does each for from had has have how if in into is it
its many may more most much name no not of on one or other our out over same so some such than that the their them then
there these they this those to two up use used uses using very was way we were what when where which while who whom
why will with would write you your called called give state find""".split())


def stem(w: str) -> str:
    for suf in ("ations", "ation", "ments", "ment", "ings", "ing", "ies", "ers", "es", "ed", "er", "ly", "al", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            w = w[: -len(suf)] + ("y" if suf == "ies" else "")
            break
    return w[:-1] if w.endswith("e") and len(w) > 4 else w  # solve / solving -> solv


# Math notation carries no words; say what it is in the words syllabi use.
NOTATION = [(re.compile(r"\d+\s*/\s*\d+"), " fraction "), (re.compile(r"%"), " percentage "),
            (re.compile(r"\d[a-z]\b|\b[a-z]\s*=|=\s*\d+[a-z]\b"), " equation unknown ")]


def tokens(text: str) -> list[str]:
    t = text.lower()
    for rx, words in NOTATION:
        t = rx.sub(lambda m, w=words: m.group(0) + w, t)
    return [stem(w) for w in re.findall(r"[a-z]+", t) if w not in STOP and len(w) > 2]


def overlap(qt: set, doc, idf) -> float:
    """Exact token matches, plus half credit when one word is the start of another (rain / rainfall)."""
    score = 0.0
    for w in qt:
        if w in doc:
            score += idf[w]
        elif len(w) >= 4:
            near = [d for d in doc if len(d) >= 4 and (d.startswith(w) or w.startswith(d))]
            score += 0.5 * max((idf[d] for d in near), default=0.0)
    return score


def lexical_topic_map(questions, topics):
    """TF-IDF overlap between each question (text + options) and each topic (title + description).
    Returns {number: (topic code | None, confidence 0..1)}."""
    docs = {t["code"]: Counter(tokens(f"{t['title']} {t['title']} {t['description']}")) for t in topics}
    df = Counter(w for d in docs.values() for w in d)
    idf = {w: math.log((len(docs) + 1) / (n + 1)) + 1 for w, n in df.items()}
    out = {}
    for q in questions:
        qt = set(tokens(q["text"]))
        scores = sorted(((overlap(qt, d, idf), code) for code, d in docs.items()), reverse=True)
        if not scores or scores[0][0] == 0:
            out[q["number"]] = (None, 0.0)
            continue
        best, second = scores[0][0], scores[1][0] if len(scores) > 1 else 0.0
        out[q["number"]] = (scores[0][1], round(best / (best + second), 3))
    return out


def aggregate(questions, responses):
    """questions: [{id, number, max_points, topic_code}], responses: [{question_id, final_score, normalized_answer, is_correct}]
    (only responses with a score). Returns (per-question rows, per-topic rows ranked by miss rate, highest first)."""
    by_q = {q["id"]: [] for q in questions}
    for r in responses:
        if r["question_id"] in by_q and r["final_score"] is not None:
            by_q[r["question_id"]].append(r)
    qrows = []
    for q in sorted(questions, key=lambda q: q["number"]):
        rs = by_q[q["id"]]
        possible = q["max_points"] * len(rs)
        lost = sum(q["max_points"] - r["final_score"] for r in rs)
        wrong = Counter(r["normalized_answer"] for r in rs if not r["is_correct"] and r["normalized_answer"]
                        and r["normalized_answer"] != "MULTI")
        qrows.append({**q, "responses": len(rs), "points_possible": possible, "points_lost": lost,
                      "miss_rate": lost / possible if possible else None,
                      "common_wrong": wrong.most_common(1)[0][0] if wrong else None})
    topics = {}
    for r in qrows:
        t = topics.setdefault(r["topic_code"], {"code": r["topic_code"], "points_possible": 0, "points_missed": 0, "questions": []})
        t["points_possible"] += r["points_possible"]
        t["points_missed"] += r["points_lost"]
        t["questions"].append(r["number"])
    trows = [{**t, "miss_rate": t["points_missed"] / t["points_possible"] if t["points_possible"] else 0.0}
             for t in topics.values()]
    trows.sort(key=lambda t: (-t["miss_rate"], str(t["code"])))
    return qrows, trows


def template_reteach(weak_topics):
    """Offline activities built from the topic's own syllabus wording."""
    out = {}
    for t in weak_topics:
        title = t["title"].lower()
        detail = [p.strip() for p in re.split(r",| and ", t["description"]) if p.strip()][:2]
        focus = " and ".join(detail) or title
        focus = focus[:1].lower() + focus[1:]  # mid-sentence
        out[t["code"]] = [
            f"Start with a 10-minute recap quiz on {title} built from the questions most students missed.",
            f"Model two worked examples on {focus}, then have pairs solve a third and explain their reasoning.",
            f"End with a 3-question exit ticket on {title} to see who still needs small-group help.",
        ]
    return out


def modal_answer(answers):
    """Keyless fallback without a model: the most common non-blank answer, marked unverified by the caller."""
    c = Counter(a for a in answers if a and a != "MULTI")
    return c.most_common(1)[0][0] if c else None
