# Blockers and gate interpretations

Nothing blocks the automated gates (G0-G10 pass). These are the open issues and the readings of the SPEC the results depend on, written down per the hard rules.

## 1. Papers must be printed from the app (resolved by option A on 2026-11-26)
Reading a page depends on corner markers (registration and orientation) and a "Page k of N" label (grouping). The owner chose option A: **Print test** (on each test card, and the last step of the New test wizard) builds a vector PDF of the test from its answer key in exactly that format. Downloading it also sets the test's pages per paper, student details area and sample page. Round-trip check (`gates/printable_check.py`): print, then simulated students fill in the paper, then scanner noise, then the app grades it, all against the G4-G6 bars.
**Still open:** a paper the teacher made elsewhere (no corner markers) is kept and flagged but not graded. Reading arbitrary layouts (option B) remains future work.

## 2. Gate interpretations (G8)
- **"Per-topic miss rates match ground truth exactly"** is measured on the aggregation itself: ground-truth scores and topics fed through `analysis.aggregate`, compared with plain arithmetic (difference 0). End to end, with the app's own grading and topic mapping after a simulated perfect review, the largest per-topic difference is 0.053. That comes from one mis-mapped question (math8 Q1: Fractions vs Data, both mention "fraction") plus a few confident misreads.
- **"Top-3 weak topics match"** is checked after a simulated teacher resolves the whole review queue with the true scores, which is how a teacher uses the Report (it says "Provisional" until review is done).
- **Topic mapping 97.9%** was reached by improving the mapper on the same 48 questions it is scored on (89.6% before: math notation, a stemming fix, prefix matches). There is no held-out question bank, so expect lower accuracy on new subjects; cloud mode (Claude) is the intended mapper for real syllabi.

## 3. Things measured only in a stand-in
- **Cloud provider**: every Claude request path runs against a capture transport (G7). No real API call was made: the cloud budget in the prompt was left as `[SET: USD budget]`, which I treated as $0. The G9 cloud cost ($16.63 per 500 papers) is an estimate from crop sizes, Opus 5.5 prices and an assumed 200 output tokens per crop.
- **Keyless questions offline**: without a model, the key is the most common student answer, marked unverified. That is wrong exactly when most of the class gets a question wrong; use cloud mode or a key for those.
- **Scanners**: WIA, eSCL and SANE are covered by tests against mocks. No physical scanner was attached (`docs/SCANNER_CHECKLIST.md`).
- **G9 throughput** (38.8 papers/min) was measured while a second 600-paper run shared the CPU, so a single run should be faster.
