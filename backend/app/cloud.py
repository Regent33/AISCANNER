"""Cloud AI provider: Claude via the official Anthropic SDK.

Privacy contract (SPEC 10): callers hand this class only redacted answer crops, question/key/syllabus text, and
topic-level aggregates. It never receives names, IDs or student_name_local. Every request passes through _send(),
which first appends a metadata-only audit entry (kind, model, source page/box, image size) so what left the machine
can be checked afterwards.
"""
import base64
from collections import deque

import anthropic
import cv2
import numpy as np
from pydantic import BaseModel, Field

from . import db

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # on a policy decline the API retries on a fallback model


class Reading(BaseModel):
    text: str = Field(description="exactly what the student wrote; empty string if the box is blank")
    confidence: float = Field(ge=0, le=1, description="how sure you are the transcription matches the handwriting")


class TopicPick(BaseModel):
    number: int
    topic_code: str
    confidence: float = Field(ge=0, le=1)


class TopicMap(BaseModel):
    mappings: list[TopicPick]


class TopicActivities(BaseModel):
    code: str
    activities: list[str]


class ReteachPlan(BaseModel):
    topics: list[TopicActivities]


class DerivedKey(BaseModel):
    number: int
    answer: str = Field(description="mcq: the option letter A-E; written: the short correct answer")


class KeyList(BaseModel):
    keys: list[DerivedKey]


class CloudRefusal(RuntimeError):
    pass


def png_b64(img: np.ndarray) -> str:
    return base64.standard_b64encode(cv2.imencode(".png", img)[1].tobytes()).decode()


class CloudTasks:
    """Both cloud transports receive the same redacted inputs and validate the same results."""
    def __init__(self):
        self.audit = deque(maxlen=200_000)

    def _send(self, kind: str, content: list, schema: type[BaseModel], max_tokens: int, where=None, image=None):
        model = self.model()
        self.audit.append({"kind": kind, "model": model, "where": where,
                           "image_shape": None if image is None else list(image.shape)})
        return self._request(model, kind, content, schema, max_tokens)

    def transcribe(self, crop: np.ndarray, question: dict, where=None):
        prompt = ("This image is one student's handwritten answer box from a scanned test (any name area is blacked "
                  "out). Transcribe exactly what the student wrote, keeping their spelling. If several parts are "
                  f"written, separate them with commas. The question was: {question['text']}")
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": png_b64(crop)}},
                   {"type": "text", "text": prompt}]
        r = self._send("transcribe", content, Reading, 4096, where, crop)
        return r.text, float(r.confidence)

    def map_topics(self, questions, topics):
        """questions: [{number, text}], topics: [{code, title, description}] (no student data)."""
        lines = "\n".join(f"{t['code']} | {t['title']} | {t['description']}" for t in topics)
        qs = "\n".join(f"{q['number']}. {q['text']}" for q in questions)
        prompt = (f"Syllabus topics (code | title | description):\n{lines}\n\nTest questions:\n{qs}\n\n"
                  "Assign each question the single syllabus topic it tests, using the topic code. "
                  "confidence = how sure you are (0 to 1).")
        r = self._send("map_topics", [{"type": "text", "text": prompt}], TopicMap, 16000)
        codes = {t["code"] for t in topics}
        return {m.number: (m.topic_code if m.topic_code in codes else None, float(m.confidence)) for m in r.mappings}

    def derive_answers(self, questions, answers_by_number):
        """Work out keys from the printed questions alone (student answers are not sent)."""
        qs = "\n".join(f"{q['number']} ({q['type']}). {q['text']}" for q in questions)
        prompt = ("Answer key needed. For each test question below give the correct answer: the option letter for "
                  f"multiple choice (mcq), a short answer for written questions.\n\n{qs}")
        r = self._send("derive_answers", [{"type": "text", "text": prompt}], KeyList, 16000)
        return {k.number: k.answer.strip() for k in r.keys}

    def reteach(self, weak_topics):
        """weak_topics: [{code, title, description, miss_rate}] (aggregates only, never student data)."""
        lines = "\n".join(f"{t['code']} | {t['title']} | {t['description']} | {round(t['miss_rate'] * 100)}% of points missed"
                          for t in weak_topics)
        prompt = ("A teacher's class did poorly on these syllabus topics (code | title | description | miss rate):\n"
                  f"{lines}\n\nFor each topic suggest three short, concrete reteach activities a teacher can run "
                  "in one lesson. Plain language, no jargon, each under 25 words.")
        r = self._send("reteach", [{"type": "text", "text": prompt}], ReteachPlan, 16000)
        return {t.code: t.activities[:5] for t in r.topics}


class CloudProvider(CloudTasks):
    name = "cloud"

    def __init__(self, client: anthropic.Anthropic | None = None):
        super().__init__()
        self.client = client or anthropic.Anthropic()

    def model(self) -> str:
        with db.connect() as c:
            return c.execute("SELECT cloud_model FROM settings").fetchone()[0] or DEFAULT_MODEL

    def _request(self, model, kind, content, schema, max_tokens):
        resp = self.client.beta.messages.parse(
            model=model, max_tokens=max_tokens, betas=[FALLBACK_BETA], fallbacks="default",
            messages=[{"role": "user", "content": content}], output_format=schema)
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            raise CloudRefusal(f"{kind}: model declined ({resp.stop_reason})")
        return resp.parsed_output
