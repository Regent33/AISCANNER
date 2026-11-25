# Progress

All gates except G9 re-run together at commit `b57fb2f` (2026-11-26) with the results below; G9 last ran at `bfecf1c^` (its code path is unchanged since). A fresh clone of HEAD installs, builds and passes pytest. Open issues and gate interpretations: `BLOCKERS.md`.

| Gate | Status | Latest metric |
|---|---|---|
| G0 Fixtures | PASS | byte_identical=1, schema_errors=0 (1399 pages; re-passed after Year/Section added) |
| G1 Skeleton | PASS | pytest_green=1, ui_loads=1, job survives hard kill |
| G2 Test setup | PASS | 14 round-trip tests green (paste, txt, pdf, keyless, redaction) |
| G3 Ingestion | PASS | upload, folder watch (1.06 s), WIA + eSCL/AirScan + SANE + mock; dups ignored; hardware = docs/SCANNER_CHECKLIST.md |
| G4 Grouping + ID | PASS | grouping 1.00, IDs 1.00, unreadable unflagged 0, dropped 0; year 0.967, section 0.967 (info) |
| G5 MCQ | PASS | accuracy 0.996 (clean 0.992, noisy 1.000); re-passed on new fixtures |
| G6 Handwritten | PASS | agreement 0.980, high-conf agreement 0.998 (89% of answers), 0 low-conf missing from queue |
| G7 Privacy | PASS | 691 cloud payloads (transcribe, map_topics, reteach): 0 identity pixels, 0 name/ID strings; local mode 0 outbound calls |
| G8 Topics + report | PASS | topic mapping 0.979; miss rates exact (diff 0); top-3 match 3/3; PDF 4 sections, 0 identity leaks |
| G9 Scale | PASS | 600/600 papers, kill at 240 + resume identical, peak 468 MB, 38.8 papers/min (shared CPU), est. cloud $16.63 per 500 papers |
| G10 UI e2e | PASS | golden path (create, print, scan, review, report, PDF) in Edge; home to report 1 click; 500-item review latency median 1.6 ms, max 3.2 ms |
| Printable round trip | PASS | app's printed PDF filled by 30 simulated students + scan noise: grouping 1.00, IDs 1.00, MCQ 1.00, written 0.974 |
| G11 Human | STOP: needs hardware and a teacher | see docs/G11_CHECKLIST.md and docs/SCANNER_CHECKLIST.md |
