# G11: human gates

G0 to G10 pass on synthetic fixtures (see `PROGRESS.md`, `results.tsv`). G11 needs real hardware and a real teacher, so the build loop stops here.

## 1. Small real batch with the actual printer-scanner
Follow `docs/SCANNER_CHECKLIST.md` with 5 to 10 real papers of one test, and record the scanner model and the results there.

## 2. Does a teacher find the report useful? (short feedback form)
After the teacher has used the Report for a real test, ask them to answer:

| # | Question | Answer |
|---|---|---|
| 1 | Did the top 3 "Topics to reinforce" match what you would have guessed? (yes / partly / no, and which differed) | |
| 2 | Would you change your next lesson because of this report? (yes / maybe / no) | |
| 3 | Were the reteach suggestions usable as written? (rate 1 to 5; which one would you actually run?) | |
| 4 | How long did checking the Review queue take, and how many items were in it? | |
| 5 | Was any score wrong after review? (which question and paper) | |
| 6 | From the home screen, was the report easy to find? (yes / no) | |
| 7 | One thing to add, and one thing to remove: | |

## 3. Re-run G4 to G6 on real scans
1. Scan one real class set (both clean and messy papers) into a folder, page 1 first, in scan order.
2. Make the ground truth: copy `fixtures/out/seed7/math8/main/truth.json` as a template and fill in, per paper, `student_id`, `year`, `section`, each page's file name, and for every question what the student marked or wrote and the points it earned. `fixtures/schema.py` validates the file.
3. Put the test's `test.json`, `key.txt`, `syllabus.txt` and `redaction.json` beside it (same layout as `fixtures/out/seed7/<test>/`), and point the gates at that folder with the `FIX` path in `gates/common.py`.
4. Run `gates/g4.py`, `gates/g5.py` and `gates/g6.py`, and record the numbers in `results.tsv` next to the fixture numbers.
5. If handwriting agreement is well below the fixture number, compare local and cloud mode on the same scans (Settings > Cloud AI) before tuning anything. The 0.80 confidence threshold and the 85% / 95% targets are placeholders until this real data exists (SPEC 13.3).
