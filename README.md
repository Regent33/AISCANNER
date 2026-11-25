# AISCANNER · Paper Scanner

AISCANNER turns a stack of completed tests into a class report showing which syllabus topics students missed. A teacher creates the printable test, scans the completed papers, checks uncertain grades, and exports a PDF. You can try the entire workflow with one practice sheet and the offline provider.

## Start the app on Windows

**For an installed checkout, double-click `Start-AISCANNER.cmd` in the project folder.** Keep its window open and visit [Settings](http://127.0.0.1:8000/settings) once it says “Application startup complete.” This starts the API and serves the built interface together. If you already have the development interface open at `localhost:5173`, refresh it after the API starts. Its **Bad Gateway** and **Server not reachable** messages can appear when only the frontend is running.

**If this checkout already has `.venv` and `frontend\dist`**, open PowerShell in the project folder and run the command below. Keep the terminal open while using the app. After updating the frontend, repeat the build step below.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [Paper Scanner](http://127.0.0.1:8000). The sidebar should show **Server connected**. Press **Ctrl+C** in the terminal to shut down. Use the same command to start it again.

**For a fresh checkout**, install Python 3.11 and Node.js 22.12+ with npm. In PowerShell, run these commands from the project folder, then run the start command above.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy opencv-python-headless pillow rapidocr-onnxruntime pydantic fastapi uvicorn python-multipart pymupdf reportlab anthropic zeroconf httpx pytest psutil
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
```

## Choose the AI provider

Open **Settings**, choose a provider, and click **Save**. Choose before starting a batch so its papers use the same settings. Multiple-choice bubbles and identity fields are read locally in every mode.

| Provider | Set it up | What it does |
| --- | --- | --- |
| On this computer | Select it and save. This is the initial setting. | Uses offline OCR for handwriting and local rules for topic mapping and reteach suggestions. |
| Cloud AI (Claude) | Set `ANTHROPIC_API_KEY` in the server environment before starting the app, then select Cloud AI. | Uses the project's direct Anthropic integration. |
| OpenRouter | Select OpenRouter. Browse its catalog, enter the exact chat model ID or keep `openrouter/auto`, add keys, and save. | Sends requests to OpenRouter using the selected ID. The auto option lets OpenRouter choose the model. |
| NVIDIA NIM | Select NVIDIA NIM. Copy a hosted chat model ID from the NVIDIA catalog, add keys, and save. | Sends requests to NVIDIA's hosted API. The model field starts with `qwen/qwen3.5-122b-a10b`. |

The model fields accept custom IDs from their respective catalogs. For a test with handwriting, choose a chat model that accepts an image and returns text. For text-only report tasks, a text chat model can work. The app asks for JSON and validates the response. Saving a model ID stores the choice locally. The provider checks availability and access on the first request. [OpenRouter models](https://openrouter.ai/models) · [NVIDIA models](https://build.nvidia.com/models)

**Save models and keys.** In OpenRouter or NVIDIA NIM, enter a model ID and click **Save settings** under the key field. Each saved ID appears in **Saved models** for that provider. To switch, pick an ID and save again. The list and active selection persist across restarts.

In **Add API keys**, paste one or more keys separated by commas and click **Save settings**. The field clears, the configured count updates, and duplicate keys count once. You can add more later. Keys entered here stay in server memory until shutdown.

**Load keys on startup.** On Windows, open **Edit environment variables for your account** and add the variable for your provider. Put the comma-separated keys in its value, then open a new PowerShell window and start the app. Environment keys and keys entered in Settings work together. To remove a key, remove it from the environment if present and restart the server.

| Provider | One key | Multiple keys |
| --- | --- | --- |
| OpenRouter | `OPENROUTER_API_KEY` | `OPENROUTER_API_KEYS` |
| NVIDIA NIM | `NVIDIA_API_KEY` | `NVIDIA_API_KEYS` |

**When a key is rate limited**, the app retries the same request with the next available key for that provider and model. It honors an HTTP 429 response's `Retry-After` header, using 60 seconds when the header is missing or unreadable. If all keys are cooling down, scan jobs wait and retry automatically. For a report, reopen it after the displayed wait. Multiple keys can share an account or organization quota, so every key can reach the limit together. Authentication errors and unsupported models require a configuration change.

**Set the review threshold.** At the default 80%, answers with confidence below 80% go to Review. Raise the threshold to check more answers yourself. **Scanner folder** sets the default path for folder scanning. **Show student names on this computer** controls local display.

## Run a practice test from start to finish

### 1. Create the answer sheet

Open **Tests → New test**. Enter a test name, such as *Biology practice*, and a subject. Pages per paper can be left blank when using the generated PDF. Click **Continue**.

In **Answer key**, paste the two lines below. You can also upload a UTF-8 text file or a PDF with selectable text. The columns are question number, type, correct answer, maximum points, and the question to print.

```text
1 | mcq | B | 1 | Which organ pumps blood? (A) Lung (B) Heart (C) Kidney
2 | written | neuron / nerve cell | 1 | Name the basic signaling cell of the nervous system.
```

For multiple choice, label two to five options in order starting with `(A)`. For written answers, ` / ` separates accepted alternatives and a semicolon separates required parts. You can leave the answer column blank if you supply the question. The report marks the generated key as unverified. Offline mode uses the most common student response for a missing key.

### 2. Upload the syllabus

Click **Continue** from Answer key to reach **Syllabus**, the third step. Paste one topic per line, or use **Or upload the syllabus (.txt or .pdf)**. For the sample quiz, paste these lines and click **Continue**.

```text
CIRC | Circulation | Heart, blood and movement through the body
NERV | Nervous system | Neurons, nerve cells and signaling
```

For an existing test, choose **Tests → Edit**, continue past Answer key, and replace the syllabus. Leaving an edit step empty keeps the saved content.

### 3. Print and complete the test

At **Print**, click **Download printable test**. This sets the page count and the student-details area. Open the downloaded PDF and print on A4, one side per sheet, with all four corner marks and the page label visible. Later, use **Print test** on the test card to download another copy.

For a practice run, fill in a fictional name and ID in the marked fields, shade one bubble, and write the short answer inside its box. Keep each student's pages together, page 1 first. Click **Save and start scanning**.

### 4. Scan the completed papers

Select the matching test on **Scan**, then choose an input.

| Input | How to use it |
| --- | --- |
| Start scanning | Select the installed scanner, load its feeder or place a page on the glass, then press **Start scanning**. Windows uses WIA, compatible network devices use eSCL/AirScan, and Linux supports SANE. A network scanner can also be added by IP. |
| Watch folder | Use a dedicated folder for this batch. Enter its full path, click **Watch folder**, and save the scans there in page order. Existing files in the folder can also be picked up. |
| Upload files | Choose an ordered multipage PDF or page images. An ordered PDF is convenient for a first run. Byte-identical pages are skipped within the same batch. |

Wait for **Pages** to match your stack, then click **Last page is in**. Watch **Papers found**, **Papers graded** and **Need a look**. Use **Pause** and **Resume** if interrupted. A batch's original scans and queued jobs are stored locally.

### 5. Review uncertain answers and export the report

Open **Review** for the test and batch. For student details, check the ID against the scan, correct it if needed, and save. For each flagged answer, compare the crop with the suggested grade. Accept it or enter the score you want counted.

| Keyboard shortcut | Action |
| --- | --- |
| Enter | Accept the current answer grade |
| 0–9 | Assign that score to the current answer |
| J / Down or K / Up | Move to the next or previous item |

Open **Report** and select the test. The report combines graded papers across that test's batches. It ranks topics by the share of possible points missed, lists per-question results and suggests reteach activities. A **Provisional** label means reviews are still outstanding. Finish the reviews and click **Export PDF** for a copy.

## Data, backups and troubleshooting

The default data folder is `data\` inside the project. It holds `scanner.db`, original pages and other scan files. To back it up, stop the server and copy the entire folder. Restore it at the same path because the database stores file paths. To start with a different location, set `SCANNER_DATA` to an absolute path before launching.

The app has no login and the start command binds it to this computer. Cloud modes send redacted answer crops, question and syllabus text, and topic-level figures. Original scans and locally read identity fields stay on the machine. Put identifying details only in the designated student-details area, which is the area the app blacks out.

| What you see | What to check |
| --- | --- |
| The page will not open | Keep the terminal running. Check [server health](http://127.0.0.1:8000/api/health). If health works but the UI fails or looks outdated, rebuild the frontend and reload. |
| The syllabus or key imports as empty | Use a text PDF or paste the text directly. A photograph embedded in a PDF has no selectable text for the importer. |
| Scanner missing | Try **Find scanners**, check the Windows driver or network address, or use the vendor's software with **Watch folder**. |
| A cloud request fails | Confirm the selected provider, exact model ID, image support and account access. Check the provider dashboard for credentials, credits and quota. With session-only keys, add them again after restarting. |
| Missing papers or an unexpected report | Check the selected test, scan order, visible corner marks and page labels. Compare papers graded with the number submitted, then resolve the review queue before relying on the report. |

## Maintainer checks and handoff

From the project root, run the backend suite. For the full browser workflow, generate the seed-7 fixtures, build the frontend, and run the Playwright suite with Microsoft Edge installed.

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe fixtures\generate.py --seed 7
Push-Location frontend
npm.cmd run lint
npm.cmd run build
npx.cmd --no-install playwright test
Pop-Location
```

The latest imported Claude Code session was `e0a3726b-dfd8-4f1c-83a2-868bd07b2df7`. Its local transcript is in `.claude/imported-sessions/`, which Git ignores. On the original computer, run `claude --resume e0a3726b-dfd8-4f1c-83a2-868bd07b2df7` from the project folder to reopen it in Claude Code.

That session completed printable tests, two-to-five-option questions, and a simulated print-to-scan check at commits `b73b3a3` and `d59e402`. Real scanner and classroom acceptance remain open. [Progress](PROGRESS.md) · [Scanner checklist](docs/SCANNER_CHECKLIST.md) · [Teacher acceptance checklist](docs/G11_CHECKLIST.md) · [Changelog](docs/changelogs/CHANGELOGS.md)
