# Stack Research

**Domain:** Hackathon prototype — video-based ALPR + speed estimation + mock traffic-fine portal (Python)
**Researched:** 2026-07-16
**Confidence:** MEDIUM-HIGH (core libraries verified against PyPI/official docs at time of research; plate-format and speed-calibration specifics are MEDIUM/LOW and flagged individually)

**Framing:** every recommendation below is chosen to minimize *setup risk* in a several-hour window on a single Windows laptop, even when a more accurate alternative exists. Time lost to a broken install (e.g. a native dependency, a CUDA mismatch, an npm toolchain) is more costly than a few points of model accuracy for a live demo.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | Required by the stack; matches FastAPI (`>=3.10`) and Ultralytics (`>=3.8`) requirements. Confidence: HIGH (verified on PyPI). |
| `ultralytics` (YOLO11 / YOLOv8) | 8.4.96 (pip: `ultralytics`) | Vehicle detection + built-in multi-object tracking | Ships pretrained COCO weights (`yolo11n.pt` / `yolov8n.pt`) that already include `car`, `motorcycle`, `bus`, `truck` classes — zero training needed. `model.track(source, persist=True)` gives you ByteTrack/BoT-SORT tracking for free, which is exactly what speed estimation needs (consistent object IDs across frames) without adding a separate tracking library. Confidence: HIGH (PyPI verified). |
| `easyocr` | 1.7.2 | OCR on cropped plate/vehicle regions | Single `pip install easyocr` with minimal manual setup (auto-downloads its own detection+recognition weights on first run). Handles Latin alphabet (digits + uppercase letters) needed for Guatemalan plates out of the box — no language-pack wrangling. Confidence: HIGH for install simplicity (verified official docs); MEDIUM for accuracy vs. PaddleOCR (see Alternatives). |
| `opencv-python` | 5.0.0.93 (pip: `opencv-python`) | Video I/O (`cv2.VideoCapture`), frame preprocessing, drawing overlays, perspective math for speed calibration | Standard, zero-friction way to read the pre-recorded MP4 clips frame-by-frame and do the pixel↔real-world math (`cv2.getPerspectiveTransform` if you go beyond a 2-point calibration). Confidence: HIGH (verified on PyPI). |
| `fastapi[standard]` | 0.139.2 | Backend API + server-rendered portal | The `[standard]` extra pulls in `uvicorn` (dev server), `jinja2` (templates), and `python-multipart` in one install — no separate frontend build needed. Confidence: HIGH (verified on PyPI, install-extras confirmed). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | latest (pulled in transitively by opencv/ultralytics/easyocr) | Array math for centroid tracking, calibration math | Always — you'll need it directly for the speed-estimation formulas even though it's also a transitive dependency. |
| `Pillow` | latest (transitive dep of easyocr/ultralytics) | Image handling | Only if you need to save/annotate crops as evidence images for a fine record; otherwise cv2 alone is enough. |
| `jinja2` (bundled via `fastapi[standard]`) | bundled | Server-rendered HTML portal templates | Use for the "traffic authority" plates/fines listing page — avoids building a separate SPA. |
| `sqlite3` (Python stdlib, no pip install) | stdlib | Optional persistence for detections/fines | Only if the demo needs to survive a FastAPI restart mid-demo. Otherwise skip entirely — see storage recommendation below. |
| `python-dotenv` | latest | Config (speed limit, calibration constants, video path) | Optional, only if you want the speed limit / calibration distance configurable without editing code. Skippable if truly out of time. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uvicorn --reload` (bundled with `fastapi[standard]`) | Local dev server for the portal | Comes free with the `[standard]` extra — no separate install. |
| `venv` (stdlib) | Isolated environment | Create one venv immediately; avoids polluting global Python and avoids version clashes between opencv variants (see Version Compatibility). |

## Installation

```bash
python -m venv venv
# Windows (PowerShell/Git Bash):
venv\Scripts\activate

# Kick this off FIRST — it pulls torch as a transitive dependency (~200MB+) and is the slowest step.
pip install "fastapi[standard]" ultralytics easyocr opencv-python numpy pillow
```

No native binaries, no system-level installers (unlike Tesseract or PaddlePaddle's GPU wheels), no npm/node toolchain. Everything above is `pip install`-only.

**First run note:** both `ultralytics` (COCO weights, ~6MB for `yolo11n.pt`/`yolov8n.pt`) and `easyocr` (detection+recognition weights, ~50-100MB) auto-download their pretrained weights the first time you instantiate them. Do a throwaway "hello world" inference call early (before you're mid-demo-build) so these downloads happen while you're still writing code, not while judges are waiting.

## Recommended Pipeline (how these pieces fit together)

1. **Ingest video:** `cv2.VideoCapture(path)` — read frame by frame, but only *run inference* on every 3rd–5th frame (not every frame) to keep a CPU-only laptop responsive. Confidence: HIGH, standard practice.
2. **Detect + track vehicles:** `YOLO('yolo11n.pt').track(frame, persist=True, classes=[2,3,5,7])` (COCO class ids for car/motorcycle/bus/truck). This gives you a bounding box **and** a stable track ID per vehicle across frames in one call. Confidence: HIGH — `.track()` with built-in ByteTrack is a documented Ultralytics feature, not a custom addition.
3. **Locate + read the plate:** Crop the vehicle bounding box, run `easyocr.Reader(['en']).readtext(crop)`, and **filter results with a regex** for the Guatemalan plate format instead of adding a dedicated plate-detector model (see rationale below). Confidence: MEDIUM — this simplification trades a little accuracy for a lot of setup-time savings; see "Plate detection" row in Alternatives Considered for the fallback if it's too noisy.
4. **Estimate speed:** Using the track ID's centroid positions across N frames + a manual pixel↔meters calibration (see Stack Patterns below), compute `distance / elapsed_time` and convert to km/h. Confidence: MEDIUM — this is the well-documented "VASCAR-style" two-point calibration approach used in multiple OpenCV tutorials, but requires a manual, per-video calibration step done by the team (pace out or estimate a known distance in the filmed street) since there's no ground-truth calibration object mentioned in the project context. Flag for phase-specific research/testing time.
5. **Generate a mock fine:** When estimated speed > configured limit, write a record `{plate, speed, limit, timestamp, evidence_crop}` to an in-memory Python list (see Storage below) and print/log a fake "SMS sent to..." / "Email sent to..." line — no real provider calls.
6. **Serve the portal:** FastAPI + Jinja2 template rendering the current in-memory list as an HTML table; a simple `<meta http-equiv="refresh">` or a few lines of `fetch()` polling gives a "live updating" feel without WebSockets.

### Guatemalan plate format (for the OCR regex filter)

Current-generation Guatemalan plates (post-2021, Mercosur-style) follow **1 letter + 3 digits + 3 letters** (e.g. `P123ABC`, displayed as `P-123-ABC`), where the leading letter denotes vehicle class (`P` = particular/private, `A` = rental/taxi, `M` = motorcycle, `C` = commercial, `O` = official, etc.), and the trailing 3 letters conventionally exclude vowels and Ñ. Confidence: MEDIUM — sourced from consumer/blog articles (matriculasdelmundo.com, corporacionbi.com, sensorautomotriz.com), not an official government spec. **Recommendation:** build the regex a bit loose (`^[A-Z]\d{3}[A-Z]{3}$` with an allowance for OCR confusions like `0`/`O`, `1`/`I`) rather than strict, since misreads under demo conditions (motion blur, lighting) are likely and a too-strict filter will silently drop real detections.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Skip a dedicated plate-detector model; run EasyOCR directly on the YOLO vehicle crop, filtered by regex | A pretrained plate-detector (e.g. `keremberke/yolov5m-license-plate` on Hugging Face, loaded via the `yolov5` pip package) for a tighter plate crop before OCR | Use this if the whole-vehicle-crop approach returns too much noise (reflections, other text on the vehicle) during a quick test **and** you still have 30-60 minutes of buffer. It's still a pretrained, no-training-required option, just one more moving part (extra pip package + HF Hub download) to get working under time pressure. Confidence: MEDIUM — model exists and is documented, but was trained on non-Guatemalan plates so generalization is unverified. |
| `easyocr` for OCR | `PaddleOCR` (generally higher accuracy per multiple benchmarks — e.g. ~88-91% vs Tesseract's 52-84% on hard cases) | Only if your team already has a clean, working Python env (ideally Python ≤3.11, since PaddlePaddle has reported `setuptools`-related install failures on Python 3.12+ on Windows) and 20-30 extra minutes to validate the install. Multiple sources report Windows/dependency friction (missing `setuptools`, conflicts when another inference engine like `transformers` is already installed) that is a real risk under a hard multi-hour deadline. Confidence: MEDIUM (multiple independent sources agree on both the accuracy edge and the install friction). |
| `yolo11n.pt` / `yolov8n.pt` (nano) | `yolov8s.pt` / `yolo11s.pt` (small) | Use the larger "s" variant only if the nano model is visibly missing vehicles in your actual footage during a quick sanity check and your laptop CPU (or GPU, if present) can still keep pace — small is roughly 2x the compute of nano. |
| In-memory Python list for detections/fines | Stdlib `sqlite3` (no extra pip install — it's built into Python) | Use SQLite only if the demo plan involves restarting the FastAPI process mid-demo and needing previously recorded fines to survive that restart. For a single continuous demo run, in-memory is strictly simpler and equally sufficient. |
| Simple 2-point pixel-distance calibration along the direction of travel | Full 4-point perspective-transform (`cv2.getPerspectiveTransform`) using a real-world rectangle in the scene | Use the perspective-transform version if the camera angle is steep enough that the naive 2-point method gives obviously wrong speeds (e.g. off by 2x+) during a sanity test on the actual Zona 4 footage, and you have ~15-20 extra minutes. This is the more "correct" approach per the OpenCV/PyImageSearch/Pysource tutorials but adds a calibration step (defining 4 correspondence points) that costs setup time. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Custom-trained YOLO model (vehicle or plate) | Training requires labeled data, GPU time, and hyperparameter iteration — none of which fits in a multi-hour hackathon window. | Pretrained COCO weights (`yolo11n.pt`/`yolov8n.pt`) for vehicles; regex-filtered OCR (or a pretrained plate detector) for plates. |
| `pytesseract` / Tesseract OCR | Requires installing a **separate native binary** (not just pip) and getting it on `PATH` — an extra manual step that's historically finicky on Windows. Benchmarks also show it trailing EasyOCR/PaddleOCR in accuracy on plate-like text. | `easyocr` (pure pip install, auto-downloads its own weights). |
| `PaddleOCR` as the primary/only choice under time pressure | Reported Windows install friction (missing `setuptools` on Python 3.12+, dependency conflicts with other inference engines, heavier `paddlepaddle` wheel). A broken install mid-hackathon is much worse than easyocr's slightly lower accuracy. | `easyocr`; keep PaddleOCR as a fallback only if there's spare time to validate the install separately. |
| A separate multi-object tracker library (e.g. `deep-sort-realtime`, standalone `sort`) | `ultralytics`'s `.track()` already bundles ByteTrack/BoT-SORT — adding a second tracking library is redundant integration work with no benefit here. | `model.track(..., persist=True)` from the `ultralytics` package you're already installing. |
| Real SMS/email providers (Twilio, SendGrid, AWS SNS, etc.) | Explicitly out of scope per PROJECT.md — requires account setup, API keys/credentials, and possible costs, none of which is worth the setup time for a mock notification. | `print()`/log statements or a simple in-memory "notifications" list rendered in the portal, clearly labeled as simulated. |
| SQLAlchemy/SQLModel + a real database server (Postgres/MySQL) + Docker | Adds an ORM layer, a running DB process, and (if containerized) Docker setup — all pure overhead for a single-process, single-demo-run prototype. | In-memory Python list/dict (or stdlib `sqlite3` if restart-resilience matters — no extra pip install needed either way). |
| A separate React/Vue/Next.js frontend | Requires `npm install`, a bundler/build step, and CORS configuration between two separate dev servers — all setup-time sinks that add no demo value over server-rendered HTML. | FastAPI + `Jinja2Templates` (bundled via `fastapi[standard]`) rendering a plain HTML table, optionally styled with a CDN-hosted Bootstrap `<link>` tag (no build step). |
| RTSP/live-camera ingestion libraries (e.g. `av`, GStreamer bindings) | Out of scope per PROJECT.md — the video source is pre-recorded clips, not a live feed. | `cv2.VideoCapture(file_path)` reading the local MP4 files directly. |
| Commercial ANPR SDKs / APIs (OpenALPR commercial tier, Plate Recognizer API) or radar/LIDAR speed sensors | Paid, require API keys/accounts, or require physical hardware you don't have — none feasible in a no-budget, no-hardware, few-hours prototype. | The free pretrained-model + calibration-math pipeline described above. |

## Stack Patterns by Variant

**If the laptop has an NVIDIA GPU with CUDA already configured:**
- Install the CUDA build of `torch` first (per pytorch.org instructions for your CUDA version), *then* install `ultralytics`/`easyocr` — both will auto-detect and use the GPU, meaningfully speeding up per-frame inference.
- Because: both libraries depend on `torch` and will silently fall back to CPU if no CUDA-enabled torch is found; verify with `torch.cuda.is_available()` before assuming GPU speed in your demo runs.

**If the laptop is CPU-only (the more likely case for a hackathon laptop):**
- Use the nano model variants (`yolo11n.pt`/`yolov8n.pt`), resize frames to a smaller width (e.g. 640px) before inference, process every 3rd-5th frame rather than every frame, and only run EasyOCR on small cropped regions (never the full frame).
- Because: CPU inference on full-resolution frames for every single frame will make the "live" demo visibly laggy; these are the standard levers to keep a CPU pipeline usable for a live audience.

**If time runs out before implementing a proper OCR-noise filter:**
- Just display the raw OCR string alongside a "confidence" flag rather than trying to perfect the regex.
- Because: for a judged demo, a plausible-looking plate string with visible detection logic is more valuable than spending remaining minutes chasing OCR edge cases.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `ultralytics` 8.4.x | `torch` >=1.8 (pulled in automatically) | Let pip resolve a single torch install in the venv; don't manually install a second/different torch build (e.g. mixing a CPU wheel with a CUDA wheel) — this is a common source of import errors. |
| `easyocr` 1.7.2 | `torch` (pulled in automatically) | Shares the same `torch` dependency as `ultralytics`; installing both in the same `pip install` command (as shown above) lets pip resolve one consistent torch version instead of two. |
| `opencv-python` vs `opencv-python-headless` | Do not install both | `ultralytics` may pull in `opencv-python-headless` as a transitive dependency in some environments. If you see a `cv2` import conflict or GUI-function errors after installing `opencv-python` yourself, uninstall one of the two variants and keep only one in the venv. |
| `fastapi` 0.139.x | Python >=3.10 | If your available Python is older (3.8/3.9), either upgrade Python or pin an older FastAPI release — don't discover this mismatch mid-build. |

## Sources

- https://pypi.org/project/ultralytics/ — version (8.4.96) and Python requirement verified directly on PyPI (HIGH confidence)
- https://pypi.org/project/easyocr/ — version (1.7.2), torch dependency, Windows install note verified directly on PyPI (HIGH confidence)
- https://pypi.org/project/opencv-python/ — version (5.0.0.93) verified directly on PyPI (HIGH confidence)
- https://pypi.org/project/fastapi/ — version (0.139.2), Python requirement, and `[standard]` extra contents verified directly on PyPI (HIGH confidence)
- https://docs.ultralytics.com/quickstart — install guidance (MEDIUM-HIGH, official docs)
- PaddleOCR GitHub install docs (github.com/PaddlePaddle/PaddleOCR) and related GitHub issues (#15272, paddle/paddle#73449) — Windows/Python 3.12 install friction (MEDIUM, multiple corroborating GitHub issues)
- OCR accuracy/speed comparison articles (codesota.com, tildalice.io, koncile.ai) comparing PaddleOCR/EasyOCR/Tesseract — accuracy figures (MEDIUM, WebSearch-sourced blog benchmarks, not independently re-run)
- Pysource "Estimate the speed of any object with Python and OpenCV" (2025) and PyImageSearch "OpenCV Vehicle Detection, Tracking, and Speed Estimation" — two-point/VASCAR calibration approach (MEDIUM, established tutorial pattern, not a formal spec)
- Guatemalan license plate format: matriculasdelmundo.com/en/guatemala.html, blog.corporacionbi.com, sensorautomotriz.com — plate structure (1 letter + 3 digits + 3 letters) (MEDIUM, consumer/blog sources, not an official government document)
- Hugging Face `keremberke/yolov5m-license-plate` and Roboflow Universe license-plate detection projects — pretrained plate-detector fallback option (MEDIUM, exists and documented, generalization to Guatemalan plates unverified)

---
*Stack research for: hackathon ALPR + speed-estimation + mock-fine-portal prototype*
*Researched: 2026-07-16*
