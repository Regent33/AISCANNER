"""AI providers. Every image a provider receives has already been redacted by pipeline.redacted_page();
providers never see student_name_local / student_id_local (they are not passed in)."""
import base64

import cv2
import numpy as np

from . import vision


class LocalProvider:
    """Offline: PP-OCR (RapidOCR) transcription + deterministic text heuristics. Makes no network calls."""
    name = "local"

    def transcribe(self, crop: np.ndarray, question: dict, where=None):
        return vision.ocr_crop(vision.clean_lines(crop))

    def map_topics(self, questions, topics):
        from .analysis import lexical_topic_map
        return lexical_topic_map(questions, topics)

    def reteach(self, weak_topics):
        from .analysis import template_reteach
        return template_reteach(weak_topics)

    def derive_answers(self, questions, answers_by_number):
        """No model offline: the most common student answer stands in for the key (marked unverified)."""
        from .analysis import modal_answer
        return {q["number"]: modal_answer(answers_by_number.get(q["number"], [])) for q in questions}


class MockProvider:
    """Deterministic stand-in for plumbing tests; records every payload it is sent."""
    name = "mock"

    def __init__(self):
        self.payloads = []

    def transcribe(self, crop, question, where=None):
        self.payloads.append({"kind": "transcribe", "image": png_b64(crop), "question": question, "where": where})
        return "", 0.0

    def map_topics(self, questions, topics):
        self.payloads.append({"kind": "map_topics", "questions": questions, "topics": topics})
        return {q["number"]: (topics[0]["code"] if topics else None, 0.0) for q in questions}

    def reteach(self, weak_topics):
        self.payloads.append({"kind": "reteach", "topics": weak_topics})
        return {t["code"]: [] for t in weak_topics}

    def derive_answers(self, questions, answers_by_number):
        self.payloads.append({"kind": "derive_answers", "questions": questions})
        return {}


def png_b64(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


_providers = {}


def get(name: str):
    if name not in _providers:
        if name == "local":
            _providers[name] = LocalProvider()
        elif name == "mock":
            _providers[name] = MockProvider()
        elif name == "cloud":
            from .cloud import CloudProvider
            _providers[name] = CloudProvider()
        elif name in ("openrouter", "nvidia"):
            from .chat_provider import ChatProvider
            _providers[name] = ChatProvider(name)
        else:
            raise ValueError(f"unknown provider {name}")
    return _providers[name]

