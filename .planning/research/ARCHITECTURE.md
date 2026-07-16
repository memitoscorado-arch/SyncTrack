# Architecture Research

**Domain:** Recorded-video ALPR + speed-estimation traffic-fine prototype (hackathon, Python/FastAPI/OpenCV/YOLOv8/OCR)
**Researched:** 2026-07-16
**Confidence:** MEDIUM-HIGH (core pipeline pattern cross-verified across Ultralytics official docs + multiple independent OSS implementations + academic paper; portal/backend structuring is standard FastAPI practice, HIGH confidence)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OFFLINE / ON-DEMAND JOB                      │
│                  (CLI script AND/OR FastAPI-triggered)               │
├───────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌────────────┐  ┌───────────┐  ┌────────────────┐  │
│  │  Video    │→ │  Vehicle + │→ │  Tracker  │→ │  Plate Crop +  │  │
│  │  Ingest   │  │  Plate     │  │ (ID       │  │  OCR Reader    │  │
│  │ (OpenCV   │  │  Detector  │  │ persist)  │  │  (EasyOCR/     │  │
│  │  VideoCap)│  │ (YOLOv8)   │  │           │  │  PaddleOCR)    │  │
│  └───────────┘  └────────────┘  └─────┬─────┘  └────────┬───────┘  │
│                                       │                  │          │
│                                       ▼                  ▼          │
│                          ┌─────────────────────────────────────┐    │
│                          │   Speed Estimator (per track_id)     │    │
│                          │   two-line crossing → km/h           │    │
│                          └───────────────┬───────────────────────┘  │
│                                          ▼                          │
│                          ┌─────────────────────────────────────┐    │
│                          │  Event Assembler → DetectionEvent    │    │
│                          └───────────────┬───────────────────────┘  │
├──────────────────────────────────────────┼───────────────────────────┤
│                        BACKEND (FastAPI, single process)             │
│                                          ▼                            │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────────┐    │
│  │ Fine Engine │→  │ Notification │   │  REST API (/detections, │    │
│  │ (limit cmp) │   │ Mock (log)   │   │  /fines) + Portal (HTML)│    │
│  └──────┬──────┘   └──────┬───────┘   └───────────┬────────────┘    │
├─────────┴─────────────────┴───────────────────────┴──────────────────┤
│                          PERSISTENCE (SQLite)                         │
│  ┌──────────────────┐  ┌───────────┐  ┌──────────────────┐          │
│  │ detection_events │  │  fines    │  │  notifications    │          │
│  └──────────────────┘  └───────────┘  └──────────────────┘          │
└───────────────────────────────────────────────────────────────────────┘
```

The processing pipeline (top block) and the web backend (bottom block) are **decoupled only by the database**, not by a message queue or microservice boundary — for an hours-only build, everything runs as one Python process/monolith. The pipeline can be invoked from a CLI script during development and later wired to a FastAPI endpoint (`BackgroundTasks` or a subprocess call) for the "watch it happen live" demo moment.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Video Ingest | Read recorded clip frame-by-frame, expose fps/frame index/timestamp | `cv2.VideoCapture(path)`, `cap.get(cv2.CAP_PROP_FPS)` |
| Vehicle/Plate Detector | Locate vehicle bbox, locate plate bbox within/near it | Pretrained YOLOv8 (COCO classes: car/truck/bus/motorbike) + a pretrained license-plate YOLOv8 model (open weights exist on Roboflow Universe/HF) run on the vehicle crop |
| Tracker | Assign a stable `track_id` to each vehicle across frames so OCR reads and speed crossings can be aggregated per vehicle | Ultralytics built-in `model.track(..., persist=True)` with ByteTrack/BoT-SORT, or SORT (used in most reference ALPR+speed repos) |
| OCR Reader | Read plate text from cropped plate region, normalize/correct characters | EasyOCR or PaddleOCR on grayscale+thresholded+upscaled crop; character-confusion correction map (0↔O, 5↔S, 1↔I, 8↔B) tuned to Guatemala plate format |
| Speed Estimator | Convert pixel displacement + elapsed time into km/h per `track_id` | Two-line crossing with a known real-world distance (see below) |
| Event Assembler | Once a `track_id` has both a stabilized plate string and a computed speed, emit one `DetectionEvent` | Plain Python function/class, not a separate service |
| Fine Engine | Compare `speed_kmh` vs configured `speed_limit_kmh`; create `Fine` row if exceeded | Simple comparison + fine-amount formula, in-process |
| Notification Mock | "Send" SMS/email by writing a `Notification` row (and printing/logging it) instead of calling a real provider | Jinja-rendered message string, `status="mock_sent"` |
| Persistence | Store all of the above so the portal can read it | SQLite via SQLAlchemy (file-based, zero setup) |
| REST API | Serve JSON for detections/fines, expose a "process this clip" trigger endpoint | FastAPI routers |
| Portal (frontend) | Show plates + fines list, "autoridad de tránsito" look | FastAPI + Jinja2 server-rendered HTML (no SPA build step) |

## Recommended Project Structure

```
synctrack/
├── app/
│   ├── main.py                 # FastAPI app creation, mounts routers + templates
│   ├── db.py                   # SQLAlchemy engine/session, SQLite file
│   ├── models.py                # DetectionEvent, Fine, Notification ORM models
│   ├── schemas.py               # Pydantic response models for the API
│   ├── routers/
│   │   ├── fines.py             # GET /fines, GET /fines/{id}
│   │   ├── detections.py        # GET /detections
│   │   └── process.py           # POST /process (kick off pipeline on a video)
│   ├── templates/
│   │   ├── base.html            # shared layout ("autoridad de tránsito" chrome)
│   │   ├── portal.html          # table of plates/fines
│   │   └── fine_detail.html     # single fine w/ evidence image (stretch)
│   └── static/
│       └── evidence/            # saved annotated frame snapshots per event
├── pipeline/
│   ├── ingest.py                 # VideoCapture wrapper, fps/frame iterator
│   ├── detect.py                 # YOLOv8 vehicle + plate detection
│   ├── track.py                  # tracker wrapper (ByteTrack/SORT), track_id state
│   ├── ocr.py                    # plate crop preprocessing + OCR + correction map
│   ├── speed.py                  # two-line calibration + crossing-time → km/h
│   ├── events.py                 # per-track_id aggregation → DetectionEvent
│   └── run.py                    # CLI entrypoint: `python -m pipeline.run video.mp4`
├── notifications/
│   └── mock.py                   # builds message text, writes Notification row
├── config.py                     # speed_limit_kmh, calibration line coords, distance_m
├── data/
│   └── synctrack.db              # SQLite file (gitignored, regenerated each run)
└── videos/                       # the pre-recorded Zona 4 clips
```

### Structure Rationale

- **`pipeline/` is a plain importable Python package, not a web layer.** It must run standalone from the CLI (`python -m pipeline.run`) so it can be developed and demoed *before* any FastAPI code exists — this is the single most important structural decision for hours-only demoability.
- **`app/` only depends on the database, never imports OpenCV/YOLO directly at request time.** The web process should stay fast/lightweight; heavy CV inference happens in the pipeline job, not inside a request handler (except the one `/process` trigger endpoint, which should run the pipeline in a background task or subprocess).
- **One SQLite file is the integration point** between the CV pipeline and the web portal — the simplest possible contract for a few hours of work. No queue, no API between the two halves.
- **`config.py` centralizes the one thing you will tune repeatedly during rehearsal:** the speed limit and the calibration line coordinates/distance. Keep these as plain constants (or a tiny YAML), not hardcoded inside `speed.py`, because you will re-measure/re-tune this against the real footage more than once before the live demo.

## Architectural Patterns

### Pattern 1: Track-then-aggregate (stabilize OCR and speed per vehicle, not per frame)

**What:** Never trust a single frame's OCR read or a single-frame speed number. Assign each vehicle a `track_id` via the tracker, accumulate OCR reads and position samples across all frames that track is visible, and only emit one final `DetectionEvent` per `track_id` once it leaves the frame (or after a plate-read confidence threshold + both calibration lines have been crossed).
**When to use:** Always, for both OCR (real plates from real handheld street footage will be unreadable in most frames but readable in a few) and speed (a single frame-to-frame delta is noisy; a full crossing over a known distance is far more stable).
**Trade-offs:** Slightly more state to manage (a small in-memory dict keyed by `track_id`), but it is what makes the whole system reliable enough for a live demo instead of flickering, contradictory readings.

**Example:**
```python
# pipeline/events.py
track_state = {}  # track_id -> {"plate_votes": Counter(), "line_a_t": None, "line_b_t": None}

def update_track(track_id, plate_text=None, confidence=0.0, crossed_line=None, t=None):
    st = track_state.setdefault(track_id, {"plate_votes": Counter(), "line_a_t": None, "line_b_t": None})
    if plate_text and confidence > 0.5:
        st["plate_votes"][plate_text] += 1
    if crossed_line == "A" and st["line_a_t"] is None:
        st["line_a_t"] = t
    if crossed_line == "B" and st["line_b_t"] is None:
        st["line_b_t"] = t
    if st["line_a_t"] and st["line_b_t"] and st["plate_votes"]:
        plate = st["plate_votes"].most_common(1)[0][0]
        speed_kmh = distance_m / (st["line_b_t"] - st["line_a_t"]) * 3.6
        emit_detection_event(track_id, plate, speed_kmh)
```

### Pattern 2: Two-line / two-timestamp speed calibration (no calibration hardware)

**What:** Mark two lines across the road in the frame (e.g., two visible fixed reference points already in the footage — a lamp post and a driveway edge, or painted lane-marking gaps) whose real-world separation you know or can measure. Record the video timestamp (`frame_index / fps`) when a tracked vehicle's centroid/bottom-point crosses line A, then line B. `speed = distance_m / (t_B - t_A)`, converted to km/h (`* 3.6`).
**When to use:** This is the recommended primary method for this project — it needs no camera calibration, no homography matrix, and no special hardware. It only needs one number: the real-world distance between two points visible in the frame.
**Trade-offs:** Accuracy depends entirely on how well you can measure that real-world distance. Options, cheapest first:
  1. Measure it physically on the street with a tape measure / paced steps (best accuracy, needs someone to go stand on the street once).
  2. Use Google Maps' "measure distance" tool between two landmarks visible in the frame (fast, no equipment, ~1-2m error — plenty good enough for a demo threshold check).
  3. Assume a standard road-paint dash length (varies by country/road, riskier — don't use this for Guatemala without checking, since it's not a verified constant here).
**Fallback if there's no time to identify two clean crossing points:** use a known average vehicle width (~1.8 m for a typical car) as a one-frame pixel-to-meter scale, then estimate speed from a *single* frame-to-frame pixel displacement over 1/fps seconds. This is strictly less accurate (perspective distortion, single-frame noise) and should only be used if the two-line approach can't be set up in time. It is a heuristic, not a calibration — flag it as such in the demo.

**Example:**
```python
# pipeline/speed.py
LINE_A_Y = 420          # pixel row in frame where line A is drawn
LINE_B_Y = 540          # pixel row in frame where line B is drawn
DISTANCE_M = 12.0        # measured real-world distance between the two lines

def check_crossing(track_id, centroid_y, frame_idx, fps):
    t = frame_idx / fps
    if centroid_y >= LINE_A_Y and track_id not in crossed_a:
        crossed_a[track_id] = t
    if centroid_y >= LINE_B_Y and track_id not in crossed_b:
        crossed_b[track_id] = t
        if track_id in crossed_a:
            dt = crossed_b[track_id] - crossed_a[track_id]
            return DISTANCE_M / dt * 3.6  # km/h
    return None
```

Note: Ultralytics also ships a built-in `SpeedEstimator` "Solution" using a `meter_per_pixel` continuous-displacement approach instead of two lines (see Sources). It is simpler to wire up (one constant instead of two line positions) but its accuracy degrades more with camera angle/perspective, because `meter_per_pixel` is only truly constant directly under/near an overhead camera. For a fixed-angle street-level recording (the likely case here), the two-line method is the more defensible choice; only use `meter_per_pixel` if the demo clip happens to be a near-overhead or very long-lens (flat-perspective) shot.

### Pattern 3: Event-sourcing-lite for the fine pipeline

**What:** Model the domain as an append-only chain: one `DetectionEvent` (a fact: this plate was seen at this speed at this time) can produce at most one `Fine` (a decision: this event exceeded the limit) which can produce one or more `Notification` rows (an action: this fine was "communicated"). Never mutate a `DetectionEvent` after creation; only mutate `Fine.status` (e.g., `generated` → `notified`) if you need a status field at all.
**When to use:** This keeps the data model trivial to reason about under time pressure and maps directly onto the demo narrative ("here's the detection, here's the fine it generated, here's the mock notification it sent") — good for judges to follow on screen.
**Trade-offs:** No real trade-off at this scale; the "cost" (extra tables/joins) is negligible for a SQLite prototype and the clarity is worth it.

## Data Flow

### Pipeline → Database Flow

```
video.mp4 (frame N)
    ↓ cv2.VideoCapture.read()
frame (numpy array) + frame_idx
    ↓ YOLOv8 detect (vehicle, plate)
bboxes[] + track_id (via .track(persist=True))
    ↓ crop plate region → preprocess → OCR
plate_text_candidate + confidence  ──┐
    ↓                                 │ (accumulated per track_id,
centroid position + frame_idx/fps    │  Pattern 1: track-then-aggregate)
    ↓ line-crossing check             │
speed_kmh (once both lines crossed) ─┘
    ↓ (once plate + speed both resolved for this track_id)
DetectionEvent{plate, speed_kmh, timestamp, evidence_frame} → INSERT (SQLite)
    ↓
Fine Engine: speed_kmh > speed_limit_kmh ?
    ↓ yes
Fine{detection_event_id, over_by_kmh, fine_amount} → INSERT
    ↓
Notification Mock: render SMS/email text → Notification{fine_id, channel, status="mock_sent"} → INSERT (+ console log)
```

### Database → Portal Flow

```
Browser GET /portal
    ↓
FastAPI route → SQLAlchemy query (Fine JOIN DetectionEvent, ORDER BY created_at DESC)
    ↓
Jinja2 template render (portal.html) → HTML table (plate, speed, limit, timestamp, evidence thumbnail, status)
    ↓
Response → Browser
```

Optional live-feel refresh during the demo: either a `<meta http-equiv="refresh" content="5">` tag (zero JS, trivially reliable) or a tiny `fetch()` poll every few seconds against `GET /api/fines`. Given the time budget, prefer the meta-refresh — it cannot break.

### Key Data Flows

1. **Detection → Fine → Notification is one-directional and append-only.** Nothing flows back from the portal into the pipeline. The portal is a pure read view over the database.
2. **The pipeline never talks to the web layer directly.** It writes to the same SQLite file the web layer reads from. This means the pipeline can be run entirely from the CLI while the web portal is being built, and vice versa — the two halves of the system can be developed and demoed independently, then wired together only via a `/process` trigger endpoint at the end.
3. **Evidence images flow as files, not blobs in SQLite.** Save the annotated frame (with bounding box + speed overlay) as a JPEG under `app/static/evidence/{event_id}.jpg` and store only the path in the DB — keeps the DB tiny and lets the portal `<img>` tag serve it directly as a static file.

## Data Model

```python
# app/models.py (SQLAlchemy, illustrative)

class DetectionEvent(Base):
    id: int
    video_source: str          # filename of the clip processed
    track_id: int              # tracker's internal id, useful for debugging
    plate_text: str            # OCR-resolved plate string
    plate_confidence: float
    speed_kmh: float
    timestamp_video_s: float   # seconds into the clip
    evidence_path: str         # e.g. "static/evidence/12.jpg"
    created_at: datetime

class Fine(Base):
    id: int
    detection_event_id: int    # FK -> DetectionEvent
    plate_text: str            # denormalized for fast portal queries
    speed_kmh: float
    speed_limit_kmh: float
    over_by_kmh: float
    fine_amount_gtq: float      # mock computed, e.g. base + per-km/h-over
    status: str                 # "generated" | "notified"
    created_at: datetime

class Notification(Base):
    id: int
    fine_id: int                # FK -> Fine
    channel: str                 # "sms" | "email"
    recipient: str                # mock/deterministic pseudo-owner contact
    message_body: str
    status: str                   # "mock_sent"
    created_at: datetime
```

**Mock recipient trick:** real plates read off the street won't have a real owner-lookup database. Generate a deterministic pseudo-owner from a hash of the plate string (e.g., pick from a small fixed list of Guatemalan names/phone-number patterns seeded by `hash(plate_text) % N`) so every fine always has a plausible-looking "Notificado a: Juan Pérez, +502 5xxx-xxxx" line in the demo, without needing any real personal data.

## Scaling Considerations

This system has no real "scale" axis in the traditional sense (it is a single-laptop, single-demo-session prototype). The more relevant axis is **processing time vs. video length/resolution** and **number of vehicles simultaneously in frame**.

| Concern | 1 short clip, few vehicles (demo case) | Longer clips / more clips | Many vehicles at once |
|---------|------------------------------------------|-----------------------------|---------------------------|
| Frame processing | Fine to run every frame at full inference | Downsample: run detection every 2nd–3rd frame, interpolate tracker positions between | Batch detection call handles multiple boxes per frame natively (YOLO already does this) |
| OCR cost | Run OCR every frame while plate box exists | Only run OCR once every N frames per track, or only inside a "read zone" near the calibration lines | Cap max concurrent OCR calls per frame (queue/skip lowest-confidence boxes) |
| Storage | SQLite fine indefinitely at this volume | Still fine — dozens to low-thousands of rows | Still fine |

### Scaling Priorities

1. **First bottleneck (and the only one that matters for a few hours of demo prep): OCR latency.** EasyOCR/PaddleOCR inference per crop is the slowest step in the pipeline by a wide margin. Mitigation: only call OCR every few frames per track and/or downscale the search — never call OCR on every frame for every box.
2. **Second bottleneck: real-time playback expectations.** If the demo narrative implies "watch it process live," full YOLO+tracker+OCR on CPU may run slower than real-time video playback. Decide explicitly whether the live demo shows (a) pre-processed output played back, or (b) genuinely live processing at reduced fps with a visible progress indicator — don't assume real-time throughput without testing on the actual demo laptop first.

## Anti-Patterns

### Anti-Pattern 1: Building the web portal/API before the CV pipeline produces a single correct detection

**What people do:** Start with FastAPI routes, database models, and a polished frontend because "that's the demoable UI," then bolt on the CV pipeline last.
**Why it's wrong:** The CV pipeline (detection + OCR + speed calibration against *real* footage) is the actual technical risk and the part most likely to eat all the remaining time if something doesn't work on the real Zona 4 clips (lighting, angle, plate legibility). A beautiful empty portal with no real data is not demoable; an annotated video with correct boxes/speeds and no portal is at least a partial, honest demo.
**Do this instead:** Get the CLI pipeline to print/overlay a correct detection + plate + speed on the real footage first. Build the portal last, once you know what data shape you actually have.

### Anti-Pattern 2: Per-frame instantaneous speed instead of crossing-based speed

**What people do:** Compute speed from consecutive-frame pixel displacement every single frame and display a constantly-jittering number.
**Why it's wrong:** Detection/tracking bounding-box centroids jitter frame to frame; a per-frame speed is noisy and will show implausible values (0 km/h one frame, 300 km/h the next) in front of judges.
**Instead:** Use the two-line crossing method (Pattern 2) or at minimum average displacement over a several-frame sliding window before reporting a number.

### Anti-Pattern 3: Splitting the system into separate services/processes for detection, OCR, and API under time pressure

**What people do:** Reach for a "proper" architecture — a detection microservice, a message queue, a separate OCR worker — because that's what a "real" production ALPR system might look like.
**Why it's wrong:** Every process boundary and queue is integration risk and setup time you don't have. For a few hours of build time on one laptop, this only adds failure surface.
**Instead:** One Python process. Pipeline code and web code live in the same repo/venv and share the same SQLite file. Only introduce `BackgroundTasks` (still in-process) if you need the `/process` endpoint to not block the HTTP response.

### Anti-Pattern 4: Building a full SPA frontend (React/Vite) for the portal

**What people do:** Default to a modern JS framework for "the frontend" out of habit.
**Why it's wrong:** Build tooling, CORS configuration, and a second dev server are pure overhead with zero payoff for a table-listing portal that needs to exist for one demo session.
**Instead:** FastAPI + Jinja2 server-rendered templates. One route returns HTML directly from a DB query. If interactivity is wanted, a few lines of vanilla `fetch()`/`<script>` is enough — no framework, no build step.

## Integration Points

### External Services

None. By explicit project constraint, SMS/email are mocked (no Twilio/SendGrid), there is no live camera feed, and there is no real government system integration. This removes an entire category of hackathon risk (API keys, rate limits, network dependency during the live demo) — treat "zero external services" as a feature to protect, not a gap to fill.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `pipeline/` ↔ `app/` (SQLite) | Shared database file, no direct function calls | Lets the pipeline be developed/run standalone via CLI while portal code is built in parallel or afterward; the only coupling is the schema in `app/models.py`, which `pipeline/events.py` should import and reuse (don't duplicate the schema) |
| `pipeline/detect.py` ↔ `pipeline/track.py` | Direct in-process function calls / Ultralytics `.track()` call | Keep synchronous; no need for async here, CV inference is CPU/GPU-bound not I/O-bound |
| `app/routers/process.py` ↔ `pipeline/run.py` | FastAPI `BackgroundTasks` calls the pipeline's main entrypoint function | Enables the "trigger processing from the portal" stretch feature without blocking the HTTP request; if this proves fragile close to demo time, fall back to running the pipeline via CLI before the demo and only using the portal as a read view |
| `notifications/mock.py` ↔ `Fine` creation | Called synchronously right after a `Fine` row is inserted, in the same transaction/flow | Keeps the demo narrative simple: detection → fine → notification happens as one visible sequence, not an async side effect that might not have "arrived" yet when judges look at the portal |

## Suggested Build Order (optimized for "always have something demoable")

Each step below produces a visible, verifiable artifact on its own — if time runs out at any point, the last completed step is still a legitimate (partial) demo.

1. **Skeleton:** repo + venv, FastAPI app boots and serves a static "hello" page; SQLite file created with empty tables. *Demoable: "the system runs."*
2. **Vehicle detection overlay (CLI only):** `pipeline/run.py` reads a real Zona 4 clip frame-by-frame with `cv2.VideoCapture`, runs pretrained YOLOv8 (COCO vehicle classes), draws bounding boxes, writes an annotated output video/frame set to disk. *Demoable: "it sees the cars in our real footage."*
3. **Tracking + plate localization overlay:** add `.track(persist=True)` for stable IDs across frames; add plate-detector model to crop a plate region per vehicle box; draw both boxes. *Demoable: boxes stay attached to the same car across frames, plate region highlighted.*
4. **OCR overlay:** run OCR on plate crops, apply the character-correction map, overlay the best-read text near each car in the output video. *Demoable: video shows plate text.*
5. **Speed overlay:** add the two calibration lines (tuned against the real clip's visible landmarks/measured distance), compute crossing-based km/h per track, overlay the number. *Demoable: video shows a plausible speed per car — this is the core "wow" moment, get here as early as possible.*
6. **Persistence:** wire the event assembler to write `DetectionEvent` rows to SQLite when the pipeline runs; add the Fine Engine to compare against `speed_limit_kmh` and insert `Fine` rows. *Demoable: run the CLI, then inspect the SQLite DB (or print a summary table) showing generated fines.*
7. **Notification mock:** on each `Fine` insert, generate a mock SMS/email message (with the deterministic pseudo-owner trick) and log/print it plus store a `Notification` row. *Demoable: console shows "SMS enviado a +502... : Multa por exceso de velocidad..."*
8. **REST API + portal page:** `GET /fines`, `GET /detections` JSON endpoints; Jinja2 `portal.html` rendering the fines table with evidence thumbnails. *Demoable: open a browser, see the "autoridad de tránsito" table — this is the piece judges will look at longest.*
9. **Stretch — trigger from the web:** `POST /process` endpoint (BackgroundTasks) so the portal itself can kick off processing on a selected clip live in front of judges, rather than requiring a pre-run CLI step.
10. **Stretch — polish:** styling/branding pass on the portal, evidence-image detail page, meta-refresh for a "live" feel, tuning thresholds/calibration against the exact clip chosen for the live run-through.

**Critical ordering rationale:** steps 2-5 (the CV pipeline, run purely from the CLI against real footage, with visual overlays as the verification method) come before any backend/database/web work. This is deliberate — the CV pipeline is the highest-risk, highest-uncertainty part (real street footage, real plates, one calibration shot) and also the actual subject-matter "proof" the judges care about. The backend (steps 6-8) is comparatively mechanical CRUD once the pipeline produces correct `(plate, speed)` pairs, and can be built quickly at the end even under time pressure. If the CV pipeline is running behind schedule, it's better to still have steps 6-8 be simplified (e.g., manually insert one hardcoded `Fine` row to prove the portal renders) than to have spent the early hours on a portal with no real data feeding it.

## Sources

- Ultralytics — Speed Estimation guide (official docs): https://github.com/ultralytics/ultralytics/blob/main/docs/en/guides/speed-estimation.md — HIGH confidence, describes the `meter_per_pixel` continuous-displacement approach and its accuracy caveats (perspective distortion, need for tuning against ground truth)
- Ultralytics blog — "YOLOv8 for Speed Estimation in Computer Vision Projects": https://www.ultralytics.com/blog/ultralytics-yolov8-for-speed-estimation-in-computer-vision-projects — MEDIUM confidence, describes line-crossing based speed measurement
- jamal022/automatic-number-plate-recognition-Speed-Estimation (GitHub) — YOLOv8 + SORT + EasyOCR reference implementation, MEDIUM confidence (community project, not officially maintained, but matches the recommended pipeline shape)
- Real-Time Automatic License Plate Recognition Using YOLOv8, SORT Tracking, and Temporal Data Interpolation (arXiv, 2026): https://arxiv.org/html/2606.04684 — MEDIUM confidence, validates YOLOv8+SORT+OCR pipeline shape and the value of temporal aggregation/interpolation across frames (supports Pattern 1: track-then-aggregate)
- Muhammad-Zeerak-Khan/Automatic-License-Plate-Recognition-using-YOLOv8 (GitHub) — MEDIUM confidence, additional reference for YOLOv8-based plate detection + EasyOCR wiring

---
*Architecture research for: recorded-video ALPR + speed-estimation + mock-fine hackathon prototype*
*Researched: 2026-07-16*
