# Project Research Summary

**Project:** SyncTrack
**Domain:** Video-based ALPR (Automatic License Plate Recognition) + speed estimation + mock traffic-fine portal -- social-impact hackathon prototype (Guatemala, Zona 4)
**Researched:** 2026-07-16
**Confidence:** MEDIUM-HIGH

## Executive Summary

SyncTrack is a several-hours hackathon prototype that must run one continuous, live pipeline in front of judges: recorded street video -> vehicle detection/tracking -> plate OCR (Guatemala format) -> calibrated speed estimation -> fine record generation -> mock SMS/email notification -> a government-style public fines portal. Experts building this kind of system (real ALPR-to-citation pipelines, Vision Zero speed-camera programs, and multiple open-source YOLOv8+OCR+speed reference implementations) converge on the same shape: a pretrained YOLOv8 detector with built-in tracking (no custom training), an off-the-shelf OCR engine filtered by a plate-format regex, and a simple two-line/known-distance speed calibration -- all wired together as a single Python process with SQLite (or even in-memory) as the only integration point between the CV pipeline and a server-rendered FastAPI+Jinja2 portal. This is deliberately a "prototype shape," not a production architecture: no microservices, no message queues, no external providers, no live camera ingestion.

The recommended approach is to front-load all setup risk and all CV risk before writing any web code: install and warm-cache all model weights in the first 30 minutes, validate every candidate video clip opens/decodes correctly, and get a correct annotated detection+plate+speed overlay running from the CLI against the real Zona 4 footage before building the database, API, or portal. The single biggest technical risk is not any one library but integration and calibration: speed estimation is meaningless without a real-world reference distance measured in the actual footage, and OCR on real casually-shot street plates (angle, blur, glare) is the most scrutinized, most fragile part of the demo. The single biggest non-technical risk is that a polished government-style portal displaying real people's real plates, with automatically generated "multas," can read as an actual (unauthorized) enforcement action rather than a hackathon simulation -- this must be mitigated with a persistent disclaimer, fictional agency branding, and scoping displayed data to only the intentionally-demoed vehicle(s).

Key mitigations that should shape the roadmap: build and validate the CV pipeline (detection -> tracking -> OCR -> speed) end-to-end via CLI/overlay before any backend work; treat "pick the golden clip + golden vehicle with a legible plate that provably exceeds a realistic limit" as an explicit go/no-go gate before building fine generation and the portal on top; and decide early whether "live" demo means true on-stage inference or pre-processed-and-replayed results (the latter is a legitimate, recommended hedge given CPU-only inference speeds).

## Key Findings

### Recommended Stack

The stack is entirely `pip install`-based with zero native binaries or system installers, chosen specifically to minimize setup risk in a hours-only window even at some cost to peak accuracy. Everything runs as a single Python 3.11+ process/venv.

**Core technologies:**
- `ultralytics` (YOLO11/YOLOv8, e.g. `yolo11n.pt`) -- vehicle detection + built-in multi-object tracking via `.track(persist=True)` (ByteTrack/BoT-SORT) -- pretrained COCO weights already include car/motorcycle/bus/truck classes, zero training needed, and tracking comes free with the same call needed for speed math.
- `easyocr` -- OCR on cropped plate/vehicle regions -- single `pip install`, auto-downloads its own weights, handles Latin alphabet out of the box; chosen over PaddleOCR (higher accuracy but reported Windows/Python 3.12 install friction) and over Tesseract (requires a separate native binary on PATH).
- `opencv-python` -- video I/O (`cv2.VideoCapture`), frame preprocessing, drawing overlays, and the pixel<->real-world calibration math for speed.
- `fastapi[standard]` -- backend API + server-rendered portal -- the `[standard]` extra bundles `uvicorn`, `jinja2`, and `python-multipart` in one install, avoiding a separate frontend build/toolchain.
- SQLite (stdlib `sqlite3`, optionally via SQLAlchemy) or a simple in-memory Python list -- the only integration point between the CV pipeline and the web portal; in-memory is sufficient for a single continuous demo, SQLite only needed if the process must survive a mid-demo restart.

Guatemalan plates (post-2021 Mercosur-style) follow **1 letter + 3 digits + 3 letters** (e.g. `P123ABC`); build the OCR-validation regex loosely (allowing `0`/`O`, `1`/`I` confusions) rather than strictly, since a too-strict filter will silently drop real detections under demo lighting/motion-blur conditions.

### Expected Features

**Must have (table stakes -- PROJECT.md's Core Value, all P1):**
- Frame-by-frame video ingestion of the pre-recorded Zona 4 clip
- Vehicle detection + tracking across frames (hard dependency for speed estimation)
- Plate localization + OCR in Guatemala format (highest-risk, most-scrutinized output)
- Calibrated speed estimation from video (the core technical claim -- not GPS/radar)
- Configurable speed-limit comparison (a single hardcoded value is fine for MVP)
- Automatic fine record generation (plate, speed, limit, timestamp, **evidence frame** -- a fine without evidence is not credible)
- Mock (not real) SMS/email notification generation, clearly labeled simulated
- Public-style web portal listing plates/fines, styled like a transit-authority lookup page, with a persistent "SIMULATED" disclaimer
- One continuous end-to-end pipeline run, live, for judges

**Should have (differentiators, cut first under time pressure, best ROI in this order):**
- Violations stats/dashboard (count, avg speed vs. limit) -- cheapest once fine records exist, answers "so what, at scale?"
- Annotated video playback (bounding boxes, plate crop, speed overlay burned in) -- highest "wow factor per minute"
- Zone-based/school-zone speed-limit config (conceptual, not real geofencing)
- Plate/date search filter in the portal; OCR confidence badge per reading

**Defer (v2+, do not build even if time remains):**
- Real SMS/email delivery, real government system integration (SAT/PROVIAL/RENAP), owner identity lookup, facial/biometric recognition, live camera/RTSP ingestion, real payment processing, automated legal escalation -- all explicitly out of scope and, for several of these, ethically disqualifying regardless of time available.

### Architecture Approach

A single-process monolith: an offline/on-demand CV pipeline (`pipeline/` -- ingest -> detect -> track -> OCR -> speed -> event assembly) that is a plain importable/CLI-runnable Python package, decoupled from a FastAPI web layer (`app/`) only by a shared SQLite database (or in-memory store) -- no queues, no microservices, no separate frontend build. The pipeline must be demoable and testable entirely from the CLI before any web code exists, since it is the highest-risk, highest-uncertainty part of the project.

**Major components:**
1. **Video Ingest** (`cv2.VideoCapture`) -- reads the recorded clip frame-by-frame, exposes fps/frame index for downstream timing math.
2. **Vehicle Detector + Tracker** (YOLOv8 `.track(persist=True)`) -- locates vehicles and assigns a stable `track_id` used to aggregate OCR reads and speed crossings per vehicle (Pattern: track-then-aggregate, never trust a single frame).
3. **Plate OCR** (EasyOCR on preprocessed crops + regex/character-confusion correction) -- resolves a validated plate string per track.
4. **Speed Estimator** (two-line crossing with a manually measured real-world reference distance, `distance_m / (t_B - t_A) * 3.6`) -- the recommended calibration method over a single frame-to-frame or `meter_per_pixel` approach, given a fixed-angle street-level (non-overhead) camera.
5. **Fine Engine + Notification Mock + Persistence + Portal** -- mechanical CRUD/event-sourcing-lite layer (`DetectionEvent` -> `Fine` -> `Notification`, append-only) built last, once the pipeline reliably produces correct `(plate, speed)` pairs; FastAPI + Jinja2 server-rendered HTML portal, no SPA.

### Critical Pitfalls

1. **Setup/dependency install eats the whole time budget** -- resolve in the first 30 minutes: install everything, run one trivial inference call per library to force weight downloads/caching, pin versions, default to CPU-only torch unless GPU+CUDA is already confirmed working.
2. **CPU-bound pipeline too slow for a live demo** -- downscale frames to ~640px, use the nano model, run OCR only every few frames per track (not every frame), and explicitly decide whether "live" means true on-stage inference or a pre-processed-and-replayed result (the latter is a legitimate, recommended hedge).
3. **Video ingestion quietly fails (codec/VFR/rotation)** -- validate every candidate clip's `isOpened()`/fps/orientation in OpenCV before any pipeline work; re-encode with ffmpeg to constant-frame-rate H.264 up front if anything looks wrong.
4. **Speed estimate is meaningless without real calibration** -- pick one fixed, measurable real-world reference distance along the vehicle's direction of travel (tape measure or Google Maps distance tool) per clip/angle; sanity-check every computed speed against physical plausibility (~30-40 km/h typical for a Guatemala city street) before trusting it.
5. **The chosen footage may not actually contain a validated speeding + legible-plate event** -- as soon as any speed number can be produced, manually catalog every clip's candidate vehicles and choose a realistic limit and a "golden clip + golden vehicle" (with fallback) before building fine/notification/portal layers on top; this is an explicit go/no-go gate.
6. **Framing risk -- looks like a real enforcement system** -- persistent "PROTOTIPO/SIMULACION" disclaimer on every surface (portal, fine records, mock notifications), fictional (non-government) agency branding, and scoping displayed plates to only the intentionally-demoed vehicle(s) to avoid exposing bystanders' real, non-consenting data.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Setup & Environment Validation
**Rationale:** Pitfalls 1 and 3 (dependency installs and video-decode issues) are pure time sinks if discovered mid-build; research is unanimous that these must be resolved first, in isolation, before any pipeline logic is written.
**Delivers:** A working venv with all libraries installed and weight downloads cached; every candidate Zona 4 clip confirmed to open/decode/orient correctly in OpenCV (re-encoded via ffmpeg if not).
**Addresses:** Foundational requirement for all subsequent features (nothing in FEATURES.md works without this).
**Avoids:** Pitfall 1 (setup eats time budget), Pitfall 3 (video ingestion silently fails).

### Phase 2: Vehicle Detection & Tracking (CLI/overlay only)
**Rationale:** Architecture research is explicit that the CV pipeline must be built and verified via CLI overlay before any web/database code -- it's the highest technical risk and the actual subject-matter proof judges care about.
**Delivers:** `pipeline/run.py` reading the real clip, drawing correct, stable (tracked) bounding boxes on real vehicles.
**Uses:** `ultralytics` YOLO11n/YOLOv8n with `.track(persist=True)` (STACK.md).
**Implements:** Video Ingest + Vehicle Detector/Tracker components (ARCHITECTURE.md).

### Phase 3: Plate Localization & OCR
**Rationale:** Depends on vehicle detection (crop region to search); is flagged as the single most scrutinized and highest-risk table-stakes feature (FEATURES.md) and requires dedicated preprocessing/validation work (PITFALLS.md Pitfall 4).
**Delivers:** Validated, regex-filtered plate text overlay per tracked vehicle on the real footage.
**Addresses:** "Plate localization + OCR (Guatemala format)" table-stakes feature.
**Avoids:** Pitfall 4 (OCR fails on real street footage) -- via crop preprocessing (upscale/binarize), Guatemala-format regex validation, and multi-frame best-reading selection (track-then-aggregate pattern).

### Phase 4: Speed Estimation & Calibration (dedicated phase, not bundled)
**Rationale:** PITFALLS.md explicitly calls for this as its own phase, not folded into general detection work, because calibration is a manual, per-clip, error-prone task that is the core technical claim of the project.
**Delivers:** A calibrated, sanity-checked speed number (km/h) per tracked vehicle, using a two-line/known-distance crossing method.
**Uses:** `opencv-python` perspective/pixel math (STACK.md); two-line crossing pattern (ARCHITECTURE.md Pattern 2).
**Avoids:** Pitfall 5 (inaccurate speed without real calibration).
**Includes go/no-go gate:** Confirm at least one clip has a legible-plate vehicle whose calibrated speed plausibly and believably exceeds a realistically-chosen limit (Pitfall 6) -- do this before Phase 5.

### Phase 5: Fine Engine, Mock Notifications & Persistence
**Rationale:** Mechanical CRUD once (plate, speed) pairs are reliably produced -- comparatively low technical risk, can be built quickly once Phases 2-4 work (ARCHITECTURE.md build-order rationale).
**Delivers:** `DetectionEvent` -> `Fine` -> `Notification` records (SQLite or in-memory), including evidence-frame capture and deterministic mock "SMS/email sent" content.
**Addresses:** "Automatic fine record generation" and "Mock SMS/email notification" table-stakes features.
**Avoids:** Duplicate-fine technical debt (dedup per track/event, not per frame).

### Phase 6: Portal & Disclaimers
**Rationale:** The visible artifact judges interact with directly; must be built with ethical/framing safeguards from the start, not retrofitted.
**Delivers:** FastAPI + Jinja2 server-rendered fines-listing portal (styled like a transit-authority lookup page), with a persistent "SIMULATED / prototype, no legal validity" disclaimer and fictional agency branding baked in from the first commit.
**Addresses:** "Public-style web portal" table-stakes feature; optionally stats dashboard / annotated video playback / search as P2 stretch additions if time remains.
**Avoids:** Pitfall 7 (framing risk -- looks like real enforcement) and associated security/UX pitfalls (exposing real bystander plates, no visible evidence/rationale for a fine).

### Phase 7: Demo Rehearsal & End-to-End Validation
**Rationale:** PITFALLS.md's "Looks Done But Isn't" checklist and Pitfall 6/2 both require a full, uninterrupted, start-to-finish run on the exact demo machine and exact clip before presenting -- this is the actual acceptance test from PROJECT.md, not a formality.
**Delivers:** A confirmed, timed, working live (or pre-processed-and-replayed) run of the complete pipeline on the golden clip, with a documented fallback clip/vehicle.
**Addresses:** "One-shot end-to-end pipeline run" table-stakes feature -- PROJECT.md's Core Value acceptance test.
**Avoids:** Pitfall 2 (CPU pipeline too slow live), Pitfall 6 (no validated speeding event), and re-verifies Pitfall 7 (disclaimers actually present, not just planned).

### Phase Ordering Rationale

- CV-pipeline-first, backend-last is the dominant theme across STACK.md, ARCHITECTURE.md, and PITFALLS.md: detection -> tracking -> OCR -> speed calibration are each individually higher-risk and higher-uncertainty than the backend/portal, which is comparatively mechanical CRUD once real `(plate, speed)` data exists.
- Speed estimation is deliberately isolated as its own phase (not merged into detection) because it is the single feature most likely to be quietly wrong (a plausible-looking but miscalibrated number) if rushed, and because it gates a hard go/no-go decision (does any clip actually show a legible-plate speeding vehicle?) that must happen before fine/notification/portal work is built on top of possibly-nonexistent data.
- Ethical/framing safeguards (disclaimers, fictional branding, scoped data exposure) are placed as a first-class part of the Portal phase rather than a "polish" pass at the end, per PITFALLS.md's explicit warning that this is a bigger reputational risk than any technical risk in the project.
- A dedicated Rehearsal phase closes the loop, matching PROJECT.md's Core Value requirement that the full pipeline run live, once, start-to-finish, in front of judges -- every research file independently flags "never tested full-length/full-resolution end-to-end before demo day" as a critical failure mode.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Plate OCR):** Guatemala plate-format specifics are sourced from consumer/blog articles (MEDIUM confidence, not an official government spec); confirm regex tolerance and character-confusion handling against actual OCR output on real footage early.
- **Phase 4 (Speed Calibration):** The two-line/known-distance method is a well-documented tutorial pattern but not a formal spec, and accuracy depends entirely on manual, per-clip measurement quality -- may need on-the-spot research/testing time to validate against the actual Zona 4 camera angle.

Phases with standard, well-documented patterns (research-phase likely unnecessary):
- **Phase 1 (Setup):** Standard pip-only Python CV stack install; version compatibility fully verified against PyPI.
- **Phase 2 (Detection/Tracking):** Ultralytics `.track(persist=True)` is an official, documented feature, not custom integration.
- **Phase 5 (Fine Engine/Notifications):** Simple CRUD + event-sourcing-lite pattern over SQLite/in-memory store, no external integrations.
- **Phase 6 (Portal):** Standard FastAPI + Jinja2 server-rendered pattern, no SPA/build tooling.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Core library versions/requirements verified directly on PyPI and official docs (HIGH); Guatemalan plate-format specifics and speed-calibration approach are MEDIUM/LOW, sourced from consumer blogs and community tutorials rather than official specs. |
| Features | MEDIUM | Grounded in verified real-world program documentation (NYC DOT official releases, congressional research, EFF, official Guatemalan government pages) plus established generic ALPR industry patterns; some Guatemala-specific fine/legal-context details are LOW-MEDIUM (local news sources). |
| Architecture | MEDIUM-HIGH | Core pipeline pattern (YOLOv8 + tracker + OCR + speed) cross-verified across Ultralytics official docs, an academic arXiv paper, and multiple independent OSS reference implementations; portal/backend structuring is standard FastAPI practice (HIGH). |
| Pitfalls | MEDIUM-HIGH | Patterns verified against multiple independent CV/ALPR research sources and known operational issues (OpenCV/Ultralytics/PaddleOCR/EasyOCR forums, peer-reviewed surveys); exact numeric error rates vary by source and are not guarantees for this specific footage. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Guatemala plate-format precision:** No official government spec was found; the regex (1 letter + 3 digits + 3 letters) is MEDIUM confidence from blog/consumer sources -- validate against actual plates visible in the team's own footage early, and keep the regex loose rather than strict.
- **Speed-calibration accuracy on the actual Zona 4 footage:** No ground-truth (radar/GPS) is available to validate against; the two-line method's accuracy depends entirely on how precisely the real-world reference distance is measured for the specific camera angle used -- treat the go/no-go gate at the end of Phase 4 as mandatory, not optional.
- **Whether the available clips actually contain a clean, legible-plate speeding event:** This is explicitly unverified until real footage is processed -- Phase 4's go/no-go gate must resolve this before Phase 5/6 work proceeds; if no clip qualifies, the recovery strategy is to set the limit based on the fastest clearly-legible vehicle actually observed, not to invent a scenario.
- **Whether a plate-specific detector is needed vs. whole-vehicle-crop + regex-filtered OCR:** STACK.md's chosen simplification (skip a dedicated plate detector) trades accuracy for setup speed; if it proves too noisy in a quick test, a pretrained plate-detector fallback exists (Hugging Face `keremberke/yolov5m-license-plate`) but its generalization to Guatemalan plates is unverified.
- **CPU vs. GPU inference speed on the actual demo laptop:** Not yet measured; Phase 7 (Rehearsal) must confirm whether true live processing is feasible or whether the "pre-processed and replayed" fallback framing should be adopted from the start.

## Sources

### Primary (HIGH confidence)
- https://pypi.org/project/ultralytics/, https://pypi.org/project/easyocr/, https://pypi.org/project/opencv-python/, https://pypi.org/project/fastapi/ -- versions and requirements verified directly on PyPI
- https://docs.ultralytics.com/quickstart and Ultralytics Speed Estimation guide (github.com/ultralytics/ultralytics/blob/main/docs/en/guides/speed-estimation.md) -- official docs
- Congress.gov CRS Report R48160 -- "Law Enforcement and Technology: Use of Automated License Plate Readers"
- Vision-based Vehicle Speed Estimation for ITS: A Survey (IET, 2021) and arXiv 2101.06159 -- published surveys

### Secondary (MEDIUM confidence)
- NYC DOT official press releases and Vision Zero pages -- speed-camera program scale, school-zone hours, public-reporting pattern
- EFF -- "License Plate Reader Mission Creep Is Already Here" -- informs anti-features/ethical framing
- DGT Guatemala and SAT Guatemala official portal pages -- local legal/fine context and portal UX pattern (not to be copied/impersonated)
- PaddleOCR GitHub install issues, OCR benchmark blog comparisons -- install friction and accuracy tradeoffs
- Pysource and PyImageSearch speed-estimation tutorials; jamal022 and Muhammad-Zeerak-Khan GitHub reference implementations -- pipeline shape and calibration approach
- arXiv 2606.04684 (Real-Time ALPR Using YOLOv8, SORT, Temporal Data Interpolation) -- validates track-then-aggregate pattern
- OpenCV community forum threads -- video ingestion/codec operational issues

### Tertiary (LOW confidence)
- matriculasdelmundo.com, corporacionbi.com, sensorautomotriz.com -- Guatemalan plate format specifics (cross-checked against Wikipedia, still not an official spec)
- Prensa Libre / La Hora / local news -- Guatemala fine-amount context only

---
*Research completed: 2026-07-16*
*Ready for roadmap: yes*
