# SPEC.md: AI Test Paper Scanner (Prototype)

> Status: v0.1, from the project interview. Items marked **[ASSUMPTION]** were not stated by the owner and need confirmation. Items marked **[PROVISIONAL]** are placeholder targets.

## 0. How to read this spec (for the build loop)

- Sections 1-10 define WHAT to build. Section 11 (the Gauntlet) defines the ordered gates that prove it works. Section 12 defines loop rules.
- Prefer the simplest thing that passes the next gate. No speculative features. No new dependencies without a reason written in `DECISIONS.md`.
- Every gate has an objective, runnable check. Never weaken a test or a threshold to make a gate pass. If a gate seems wrong, stop and write the objection in `BLOCKERS.md`.

## 1. Goal

A teacher scans a stack of student test papers (one subject, one test) on a laptop with a regular printer-scanner. The system grades them, finds where most students went wrong, maps those errors to the syllabus, and gives the teacher a report of **which topics to reinforce**, with suggested reteach activities. A simple React UI makes the whole flow easy to navigate.

## 2. Users and scale

- Primary user: a teacher. Single machine (laptop + attached printer-scanner). Prototype; no multi-tenant requirement.
- Scale target: **500+ papers per batch**. Papers have a **varying number of pages** (set per test).
- Scanner: regular printer-scanner, **single-sided** scanning. Assume flatbed or basic feeder. Scanning throughput is the expected real-world bottleneck, so batches must be pausable and resumable.

## 3. Scope

### In scope
- Test setup with answer key and syllabus (file upload or pasted text).
- Two scan ingestion modes: watched folder, and direct scanner trigger from the app.
- Grading of **multiple-choice** and **handwritten** answers (mixed papers).
- Reading the student's handwritten name/ID locally.
- Question-to-syllabus-topic mapping inferred by AI.
- Review queue for low-confidence handwritten grades.
- Teacher report: ranked weak topics with % missed, per-question breakdown, suggested reteach activities, PDF export.
- Swappable AI backend: cloud API and local/offline model.

### Non-goals (v1)
- Duplex scanning, mobile apps, student-facing views, LMS integration, multi-teacher accounts or login, per-student report cards.
- Physically marking papers (separate project).
- Teacher manual topic tagging (AI infers topics; a teacher override can come later).

## 4. Locked decisions

| Area | Decision |
|---|---|
| Paper types | MCQ + handwritten answers on the same paper |
| Ingestion | Watched folder AND direct scanner trigger |
| AI | Cloud API (default: Claude) AND local/offline model, switchable in settings |
| Answer key | With or without key. No key means AI derives answers and marks them unverified |
| Key/syllabus input | File upload AND paste text |
| Handwritten grading | AI grades; low-confidence items go to teacher review queue |
| Student identity | Name/ID handwritten on paper; read locally |
| Cloud privacy | Names read locally; identity regions redacted before any cloud call |
| Topic mapping | AI infers topic per question from syllabus |
| Report | Ranked weak topics (% missed), per-question breakdown, reteach activities, PDF export |
| Backend | Python + FastAPI (recommended by assistant) **[ASSUMPTION: accepted]** |

## 5. Architecture

```
React UI (Vite + TS)  <--REST/JSON-->  FastAPI
                                        |-- Job worker (SQLite-backed queue, no Redis)
                                        |-- Pipeline stages (section 6)
                                        |-- AIProvider interface: CloudProvider | LocalProvider | MockProvider
                                        |-- ScannerAdapter interface: FolderWatcher | WiaScanner | MockScanner
                                        |-- SQLite + image files on disk
```

- **Stack [ASSUMPTION]:** Python 3.11+, FastAPI, SQLite, OpenCV, Pillow, PyMuPDF, ReportLab (PDF export); React + TypeScript + Vite, React Router, TanStack Query, Tailwind.
- **Scanner [ASSUMPTION]:** target OS is Windows, so WIA is the primary direct-scan path (TWAIN fallback). Everything behind `ScannerAdapter` so the OS can change.
- **Local AI [ASSUMPTION]:** local vision/OCR via Ollama and/or PaddleOCR. Exact model chosen in Gate 4 and recorded in `DECISIONS.md`.
- Keep the repo flat and readable: `backend/`, `frontend/`, `fixtures/`, `tests/`, `SPEC.md`, `DECISIONS.md`, `BLOCKERS.md`, `results.tsv`.

## 6. Pipeline

Each stage is idempotent and re-runnable per paper. A failure in one paper never stops the batch.

1. **Ingest**: pages arrive from folder watcher, scanner, or manual upload. Store the original image untouched.
2. **Group pages into papers**: page 1 of a paper carries the name/ID. A new paper starts when page 1 is detected. If the test sets `pages_per_paper`, validate against it. Mismatch means flag the paper, never drop pages.
3. **Preprocess**: deskew, denoise, normalise contrast.
4. **Identify student (local only)**: read the name/ID region with a local model. Assign a pseudonymous `student_ref` (e.g. `S-0042`). Low confidence goes to the review queue.
5. **Redact**: mask the teacher-defined identity regions on each page. Only redacted images may ever leave the machine.
6. **Read and grade MCQ**: detect the selected option per question; compare to key.
7. **Read and grade handwritten**: transcribe, then grade against key or rubric (partial credit allowed via `max_points`). Emit a confidence per answer.
8. **Route**: confidence below threshold (default 0.80, configurable) means `needs_review = true`.
9. **Map topics** (once per test, not per paper): AI assigns each question a syllabus topic with a confidence.
10. **Aggregate and analyse**: compute per-question and per-topic miss rates.
11. **Suggest reteach activities**: AI drafts activities for the top weak topics. Input is topic names and aggregate stats only, never student data.
12. **Report**: render in UI and export to PDF.

**Keyless mode:** if no key is supplied for a question, the AI derives the answer from the printed question. Those questions carry `key_source = "ai"`, and the report visibly marks results derived from AI-keyed questions as unverified.

## 7. Data model (SQLite)

- `Test(id, subject, name, pages_per_paper NULL, redaction_regions JSON, created_at)`
- `SyllabusTopic(id, test_id, code, title, description)`
- `Question(id, test_id, number, type[mcq|written], max_points, correct_answer, key_source[key|ai], topic_id, topic_confidence)`
- `Batch(id, test_id, status[queued|running|paused|done|failed], total_pages, total_papers, created_at)`
- `Paper(id, batch_id, student_ref, student_name_local, page_paths JSON, status, flags JSON)`
- `Response(id, paper_id, question_id, raw_read, normalized_answer, is_correct, score, confidence, needs_review, reviewed, final_score)`
- `Job(id, batch_id, paper_id, stage, status, attempts, error)`
- `Settings(provider, confidence_threshold, cloud_model, local_model, watch_folder)`

`student_name_local` is never included in any outbound AI request or any export unless the teacher explicitly enables it.

## 8. API (REST, JSON)

- `POST /tests`, `GET /tests`, `GET /tests/{id}`
- `POST /tests/{id}/key` (file or text), `POST /tests/{id}/syllabus` (file or text)
- `PUT /tests/{id}/redaction` (regions drawn on a sample page)
- `POST /batches` (test_id), `POST /batches/{id}/pages` (upload), `POST /batches/{id}/scan` (direct trigger)
- `POST /batches/{id}/pause`, `POST /batches/{id}/resume`, `GET /batches/{id}` (progress, counts, ETA)
- `GET /batches/{id}/review` (filter by test, question, confidence, status; sort; paginate), `PATCH /responses/{id}`
- `GET /tests/{id}/report`, `GET /tests/{id}/report.pdf`
- `GET /settings`, `PUT /settings`

## 9. UI (simple, easy to navigate)

Left sidebar, six items max. Home to report in **3 clicks or fewer**.

1. **Tests**: list, create. Wizard: name/subject, add key (upload or paste, or "no key"), add syllabus (upload or paste), draw name/ID redaction box on a sample page.
2. **Scan**: pick test, then "Start scanning" or "Watch folder", then live progress (papers found, graded, flagged), pause/resume.
3. **Review**: queue of flagged items. Shows the redacted image crop, AI reading, AI score, confidence. Actions: accept, edit score, next. Keyboard shortcuts. Must stay fast with 500+ items.
4. **Report**: top weak topics first. Per-question table. Reteach suggestions. "Export PDF". Banner "Provisional" while review items remain unresolved.
5. **Settings**: AI provider (cloud/local), confidence threshold, watch folder, privacy toggles.

Design rules: one primary action per screen, plain language, empty states that say what to do next, no jargon.

## 10. Privacy rules (testable)

- Identity regions are read locally and masked before any cloud call.
- Cloud requests contain: redacted page or answer-crop images, question text, key text, syllabus text. Never names, IDs, or `student_name_local`.
- Local-only mode makes **zero** outbound network calls to AI services.
- Original unredacted scans stay on disk locally only.

## 11. The Gauntlet (ordered gates)

Run in order. Do not start gate N+1 until gate N passes. Log every run to `results.tsv` (`timestamp, gate, metric, value, pass, commit`).

**G0: Fixtures (no real samples exist yet).** Build a deterministic generator (seeded) that produces: mock tests with MCQ + handwritten-style answers (handwriting fonts, jitter), single-sided pages with scan noise (skew, blur, shadows), answer keys, syllabi, and ground-truth JSON (correct answers, topics, student refs). Produce at least 3 tests with different page counts (1 to 4+ pages), 30 papers each, plus a 600-paper stress set.
*Pass:* same seed gives byte-identical output; ground truth validates against schema.

**G1: Skeleton.** FastAPI + SQLite + job queue + health endpoint + React shell.
*Pass:* `pytest` green; UI loads; job survives worker restart.

**G2: Test setup.** Key/syllabus upload and paste; keyless mode; redaction regions.
*Pass:* round-trip tests for each input mode; keyless questions flagged `key_source = "ai"`.

**G3: Ingestion.** Folder watcher, manual upload, `MockScanner` direct-trigger path.
*Pass:* dropped files appear in a batch within 5 s; duplicate files ignored; WIA adapter implemented and covered by a manual checklist (hardware cannot be automated).

**G4: Grouping and student ID.**
*Pass:* **>= 95%** of fixture papers grouped correctly [PROVISIONAL]; **>= 90%** student refs read correctly; every unreadable item flagged, **0 pages dropped**.

**G5: MCQ grading.**
*Pass:* **>= 95%** per-answer accuracy on fixtures (owner target). Report clean and noisy scans separately.

**G6: Handwritten grading and review routing.**
*Pass [PROVISIONAL]:* **>= 85%** agreement with ground truth overall; answers at or above the confidence threshold have **>= 95%** agreement; every below-threshold answer lands in the review queue.

**G7: Privacy.**
*Pass:* automated capture of outbound provider payloads over all fixtures shows **0** identity-region pixels and **0** name strings; local-only mode makes **0** outbound AI calls.

**G8: Topic mapping, analysis, report.**
*Pass:* topic mapping **>= 90%** vs ground truth [PROVISIONAL]; per-topic miss rates match ground truth exactly; top-3 weak topics match ground truth ranking; PDF contains all four report sections.

**G9: Scale.**
*Pass:* the 600-paper stress batch completes without crash; kill mid-run then resume produces identical results; peak memory bounded (record the number); throughput (papers/min) and estimated cloud cost per 500 papers recorded in `results.tsv`.

**G10: UI end-to-end.**
*Pass:* Playwright golden path (create test, import batch, review, report, PDF); home to report in <= 3 clicks; review queue with 500 items stays responsive (interaction < 200 ms).

**G11: Human gates (loop must stop and ask).**
- Small real batch demo with the actual printer-scanner.
- A real teacher finds the report useful (short structured feedback form).
- Real scans replace fixtures; re-run G4-G6 on the real data and record the numbers.

## 12. Loop rules

- One logical change per iteration; run the current gate's check; record the result; keep the change only if the gate's metric improves or passes, otherwise revert.
- Never edit fixtures' ground truth or thresholds to pass a gate.
- Keep `DECISIONS.md` short: one line per non-obvious choice (library, model, threshold) with the reason.
- If a gate cannot be verified without hardware or a human, write the manual checklist and stop at G11.

## 13. Assumptions and open questions

1. **MCQ format:** circled letters, shaded bubbles, or written letters? Spec reads the selected option visually and needs no fixed bubble-sheet template. A fixed template would improve accuracy.
2. **Varying pages:** per test, or within one test? Spec uses page-1 name/ID detection as the primary boundary signal, with `pages_per_paper` as validation.
3. **Handwritten thresholds** (85% / 95% / confidence 0.80) are placeholders until real data exists.
4. **Target OS** assumed Windows (WIA). Confirm.
5. **Scanner feeder:** flatbed or basic feeder assumed. If an auto feeder exists, add a throughput target to G9.
6. **Names in the report:** default is pseudonymous `student_ref` only. Decide whether the teacher wants names shown in the review queue (local display is fine; cloud never).
7. **Cloud model and budget:** which cloud model, and is there a per-batch cost ceiling?
