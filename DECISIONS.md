# Decisions

One line per non-obvious choice, with the reason.

- Python 3.11.9 in an in-repo `.venv` (uv): keeps every install inside the repo; 3.14 install on this machine is broken.
- Fixtures render at 150 dpi A4 (1240x1754), grayscale JPEG: realistic scan size; PNG of noisy pages would be ~2 GB for the stress set.
- Fixture handwriting uses Windows system fonts (Segoe Print, Lucida Handwriting, Comic Sans, Segoe Script, Ink Free); hashes recorded in `fixtures/out/seed*/fonts.json`, so byte-identity holds per machine. Juice ITC / Viner Hand rejected: OCR spike read them at 3-45%.
- Printed tests carry 4 corner fiducials (top-left hollow = orientation) and a "Page k of N" label: standard OMR practice, gives registration, 180° detection and page numbering.
- Local OCR = RapidOCR (PP-OCR ONNX, `rapidocr-onnxruntime`): models ship in the wheel (no runtime download), CPU-fast (~20 ms/crop). Spike on noisy handwriting fonts: IDs 90-100% after digit filtering, words 97-100% fuzzy.
- Open question defaults (SPEC 13): MCQ = shaded bubbles; pages per test fixed; Windows/WIA; flatbed; names shown only locally (review queue shows student_ref); cloud model per claude-api skill.
- Answer key text format: `number | type | answer | points | question text`, parts split by `;`, alternatives by ` / ` (spaces required so `3/8` stays one answer); blank answer = keyless (`key_source=ai`). Question text comes from the key because topic mapping needs it.
- Syllabus text format: `CODE | Title | description` per line; plain lines become auto-coded topics.
- Cloud budget in the prompt is unset (`[SET: USD budget]`) so it is treated as $0: no cloud calls; G9 cost is an estimate from captured payload sizes.
- Frontend follows the owner's layered architecture (`app/`, `shared/{kernel,ui,infrastructure,utils}`, `features/<f>/{domain,data,presentation,di}`). Not created because nothing uses them: `shared/infrastructure/analytics` (no tracking: privacy), `agents/` (the UI ships no AI; AI runs in the backend).
- `@phosphor-icons/react`: one consistent icon family for the sidebar and actions (the taste skill bans hand-drawn SVG icons).
- System UI font stack instead of a web font: the app runs offline on the teacher's laptop and must not fetch fonts.
- Max 250 lines per source file (owner rule). `backend/app/main.py` split into routers; `fixtures/generate.py` split into `render.py` + `generate.py` (output verified byte-identical to the committed seed-7 manifest).
- API lives under `/api` so React Router paths (`/tests`, `/report`) and API paths never collide.
- Blank answer boxes read as blank at 0.95 confidence; only faint, unreadable marks go to review (UI review finding: blanks flooded the queue).
- `anthropic` (official Python SDK): CloudProvider calls Claude through it (claude-api skill: SDK over raw HTTP); a custom `httpx2` transport lets G7 capture payloads with no network. Default model `claude-opus-5-5`, with server-side refusal fallbacks (`fallbacks: "default"`).
- Scanner coverage = WIA (any Windows driver) + eSCL/AirScan/Mopria (driverless network printers, any OS) + SANE (Linux) + watched folder (everything else, e.g. TWAIN-only devices or the printer's scan-to-folder) + upload. One protocol cannot reach every device, so the folder is the universal fallback. TWAIN is not driven directly: on Windows the vendors ship WIA drivers too, and pytwain's 32/64-bit driver mismatch is a known trap.
- `zeroconf`: mDNS discovery of eSCL printers (`_uscan._tcp`, `_uscans._tcp`) so network printer-scanners appear without typing an IP address.
- eSCL over https skips certificate verification: printers ship self-signed certificates. The client only ever talks to the LAN address the teacher picked, only scan settings are sent, and discovery prefers plain http when both are offered.
- `psutil` (gate tooling only): G9 reads peak memory of the run process; the app itself does not import it.
- Printable test = vector PDF (ReportLab, already a dependency) drawn from the answer key in the scanner's canonical frame; corner-marker positions come from `vision.FID_CENTERS`, so print and scan share one contract. Questions flow page by page (stable across downloads); options parsed from `(A) ... (B) ...` in the key text, 2-5 per question.
- MCQ rows of 2-6 bubbles (evenly spaced) instead of exactly 4; when the detected count differs from the key's option count the answer goes to Review (a missed bubble could shift letters).
