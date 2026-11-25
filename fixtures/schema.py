"""Ground-truth schema. Only fixtures/ and gates/ read ground truth; the app never does."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator

Box = tuple[int, int, int, int]  # x0, y0, x1, y1 in canonical page pixels (150 dpi A4, 1240x1754)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Topic(Strict):
    code: str
    title: str
    description: str


class Question(Strict):
    number: int
    type: Literal["mcq", "written"]
    text: str  # printed text, options included for mcq
    options: list[str] | None = None
    answer: str | list[list[str]]  # mcq letter | written parts x accepted spellings
    max_points: int
    topic: str


class LayoutItem(Strict):
    kind: Literal["mcq", "written"]
    number: int
    box: Box  # whole answer area
    bubbles: list[Box] | None = None  # mcq only, A..D


class PageLayout(Strict):
    page: int
    items: list[LayoutItem]


class TestTruth(Strict):
    id: str
    name: str
    subject: str
    pages_per_paper: int
    identity_regions: list[Box]  # page-1 name/ID block (what the teacher draws)
    topics: list[Topic]
    questions: list[Question]
    layout: list[PageLayout]


class Response(Strict):
    number: int
    marked: str | None = None  # mcq: "A".."D", "" blank, "MULTI"
    mark_style: Literal["dark", "faint", "erased_extra", "none", "double"] | None = None
    text: str | None = None  # written: what the student wrote ("" = blank)
    is_correct: bool
    score: int


class Page(Strict):
    file: str
    page: int  # 1-based page within paper
    quality: Literal["clean", "noisy"]
    rotated180: bool
    duplicate: bool


class Paper(Strict):
    index: int
    student_ref: str
    student_name: str
    student_id: str
    id_written: bool  # False => blank ID box, must be flagged
    year: str  # "" = left blank
    section: str  # "" = left blank
    font: str
    pages: list[Page]
    missing_pages: list[int]
    responses: list[Response]


class BatchTruth(Strict):
    test_id: str
    seed: int
    scan_order: list[str]  # files in the order the scanner produced them
    papers: list[Paper]

    @field_validator("scan_order")
    @classmethod
    def unique(cls, v):
        assert len(v) == len(set(v)), "duplicate file names"
        return v
