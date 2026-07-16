# Pitfalls Research

**Domain:** Real-time-style ALPR + video-based speed estimation + mock traffic-fine pipeline (hackathon prototype)
**Researched:** 2026-07-16
**Confidence:** MEDIUM-HIGH (patterns verified against multiple independent CV/ALPR research sources and known OpenCV/Ultralytics/PaddleOCR/EasyOCR operational issues; exact numeric error rates vary by source and should not be treated as guarantees for this specific footage)

## Critical Pitfalls

### Pitfall 1: Model/dependency setup silently eats the entire time budget

**What goes wrong:**
The team spends 1-2 of their few available hours fighting `pip install`, CUDA/torch version mismatches, PaddleOCR's dependency tree (paddlepaddle + paddleocr + paddlex extras), or Ultralytics/EasyOCR downloading multi-hundred-MB weights from the internet at the worst possible moment (including during the actual demo, if Wi-Fi is involved).

**Why it happens:**
Computer-vision stacks (OpenCV, Ultralytics YOLO, PaddleOCR, EasyOCR, torch) have heavy, fragile, platform-specific installs (Windows especially: CUDA wheel size, DLL conflicts, `paddlepaddle` Windows wheel quirks). Under time pressure, teams assume "pip install and go" and discover otherwise mid-hackathon. First-run model weight downloads (YOLOv8 `.pt`, EasyOCR/PaddleOCR recognition+detection models) are easy to forget because they "just worked" once on a previous machine with a warm cache.

**How to avoid:**
- In the first 30 minutes: `pip install` the full stack and run one trivial inference call for each library (YOLO on any image, OCR on any cropped text image) to force all weight downloads to complete and get cached, *before* writing any pipeline code.
- Pin exact versions in a requirements file the moment installs succeed — do not "upgrade later."
- Prefer CPU-only `torch`/`ultralytics` unless GPU + correct CUDA toolkit is already confirmed working (see Pitfall 2). GPU wheel installs are the single biggest time sink on Windows.
- Choose OCR based on setup speed, not accuracy: EasyOCR is simpler to install on Windows than PaddleOCR (fewer native-dependency issues); PaddleOCR is faster/more accurate at inference but has a heavier install. For a few-hours budget, default to EasyOCR unless PaddleOCR is already proven to install cleanly on the target machine.
- After demo-machine setup is confirmed, disable further "upgrade"/"try a different model" temptation — lock the stack.

**Warning signs:**
- Any `pip install` step taking longer than ~3 minutes or requiring a Visual C++ Build Tools install.
- First inference call trying to reach the internet (visible download progress bar) more than once per library.
- CUDA-related errors (`CUDA driver version is insufficient`, `torch.cuda.is_available() == False` when GPU was expected).

**Phase to address:**
Phase 0 / Setup — must be resolved and verified working before any detection/OCR/speed logic is written.

---

### Pitfall 2: CPU-bound pipeline is too slow for a live, in-front-of-judges demo

**What goes wrong:**
YOLOv8 + OCR per frame on a laptop CPU (no GPU, or GPU misconfigured — see Pitfall 1) can run at 1-5 FPS or worse, especially on higher-resolution phone footage. Running this "live" against a multi-minute video in front of judges turns into an awkward multi-minute wait, or the demo appears frozen/broken.

**Why it happens:**
Teams design and test the pipeline on short 5-10 second clips at low resolution during development, then feed the full-resolution, longer real footage on demo day and hit a wall. Detection models are fast; OCR (especially PaddleOCR/EasyOCR neural recognizers) is comparatively slow and is often run on every single frame instead of only when needed.

**How to avoid:**
- Downscale every frame before detection (e.g., resize to 640px on the long edge) — YOLOv8 input is 640×640 regardless, so feeding 4K frames wastes time for zero accuracy gain.
- Use the smallest model variant (`yolov8n`) — verified in ALPR research to sustain 30+ FPS with adequate accuracy for plate/vehicle localization at hackathon scale.
- Do not run OCR every frame: run detection every frame (cheap), but only run OCR once per tracked vehicle (e.g., every 5-10th frame or when the plate crop is largest/sharpest), then keep the best-confidence reading.
- Decide *before* building the demo whether "live" means (a) true frame-by-frame live inference on stage, or (b) pre-processing the video once and replaying the already-computed results with a synced video player. Option (b) is legitimate and far lower-risk for a hackathon — see Recovery Strategies.
- Time-box a real dry run of the full video end-to-end at least once, at least an hour before presenting, on the actual demo machine.

**Warning signs:**
- Processing a 30-60 second clip takes noticeably longer than the clip's own duration during dev testing (i.e., pipeline is not real-time-capable even offline).
- Any "let's just test on the small clip" habit — full-length/full-resolution footage never actually run through the whole pipeline until just before demo.

**Phase to address:**
Phase covering Detection/OCR pipeline build, validated again in a dedicated Demo Rehearsal phase.

---

### Pitfall 3: Video ingestion fails or behaves unexpectedly (codec, container, variable frame rate, orientation)

**What goes wrong:**
`cv2.VideoCapture` silently fails to open a file, returns frames in the wrong orientation (portrait phone video rotated via metadata that OpenCV ignores), reports a frame count/FPS that doesn't match reality, or the phone-recorded video uses Variable Frame Rate (VFR) — common with iPhone/Android H.264/HEVC recordings — which breaks any assumption of "frame N = time N/fps".

**Why it happens:**
OpenCV's video backend depends on the FFmpeg build it ships with; certain codecs (HEVC/H.265, some MOV variants) or missing `ffmpeg.dll` cause silent open failures or garbled decoding rather than clear errors. Phone cameras commonly use VFR, and rotation is stored as metadata that many decoders (including OpenCV) don't apply automatically, so video appears sideways.

**How to avoid:**
- In the first 30 minutes, load every candidate video clip with OpenCV and print `cap.isOpened()`, `frame_count`, `fps`, and the shape of the first decoded frame. Do this before any other pipeline work.
- If a clip fails to open or looks rotated/garbled, immediately re-encode it with a known-good tool (`ffmpeg -i input.mov -vf "transpose=1" -r 30 -c:v libx264 output.mp4`) to a fixed frame rate, standard H.264 MP4, correct orientation baked into pixels. Do this for *all* clips up front, not reactively.
- Never trust `cap.get(cv2.CAP_PROP_FPS)` alone for VFR source video — if timing accuracy for speed estimation matters (it does, see Pitfall 5), re-encode to constant frame rate (CFR) first so frame-index-to-time math is valid.
- Keep original files untouched; work from the re-encoded copies.

**Warning signs:**
- `cap.isOpened()` returns `False`, or frames decode as green/garbled blocks.
- Video plays sideways/upside-down in the pipeline despite looking correct in a normal media player.
- `fps` reported by OpenCV doesn't match the phone's known recording setting, or frame timestamps drift.

**Phase to address:**
Phase 0 / Setup — video ingestion must be validated for every clip before building detection on top of it.

---

### Pitfall 4: Plate detection/OCR fails on real street footage (angle, lighting, resolution, blur, occlusion)

**What goes wrong:**
Plates in real, casually-recorded street footage are frequently: too small in the frame (low effective resolution once cropped), at an oblique angle (not head-on), motion-blurred (moving vehicle + rolling shutter), partially occluded (other vehicles, pedestrians, poles), or unevenly lit (Zona 4 street lighting/shadows, daytime glare). Generic detectors trained mostly on frontal, well-lit plates degrade sharply, and OCR without post-processing produces garbage or plausible-looking wrong characters.

**Why it happens:**
Development/testing typically happens on the best-looking frame of the best clip. The demo, however, needs the pipeline to work on whichever frames actually contain the chosen "speeding" vehicle — which may not be the clearest ones. A generic COCO-pretrained YOLOv8 does **not** detect license plates out of the box (COCO has no "license plate" class) — it only detects the vehicle class; a separate plate-detection step or a plate-specific model/weights is required.
OCR engines by default do not validate output against a real plate grammar, so `O`/`0`, `I`/`1`, `B`/`8` confusions and stray characters pass through as "results" indistinguishable from a correct read.

**How to avoid:**
- Confirm early (first 30-60 min) whether the chosen YOLOv8 weights actually detect plates directly (a plate-specific fine-tuned model/weights, e.g. from an existing open ALPR project) or only detect the vehicle bounding box, requiring a secondary plate-localization step (e.g., a second small detector, or classical CV plate-region heuristics inside the vehicle crop). Do not discover this gap mid-build.
- Preprocess plate crops before OCR: upscale (2-4x) the tight plate crop, apply grayscale + adaptive threshold/Otsu binarization, and mild sharpening. Research on plate OCR preprocessing confirms bilateral filtering + Otsu thresholding measurably improves character accuracy over raw crops.
- Validate every OCR output against Guatemala's plate grammar before accepting it: current format is 1 letter (vehicle class: P=particular, C=comercial, A=alquiler/taxi, M=motocicleta, U=urbano, etc.) + 3 digits + 3 letters, e.g. `P123ABC`. Reject/flag OCR strings that don't match this pattern with a regex (`^[A-Z]\d{3}[A-Z]{3}$`), and apply targeted character-confusion fixes (`0↔O`, `1↔I`, `8↔B`) before the regex check rather than after discarding.
- Run OCR across multiple frames of the same tracked vehicle and take the most-frequent/highest-confidence valid reading rather than trusting a single frame.
- Pick (in advance) which recorded pass/clip has the clearest, most head-on view of the plate for the vehicle used in the "guaranteed" demo moment — don't leave this to chance during a live, unpracticed run.

**Warning signs:**
- OCR returns strings that don't match any plausible Guatemalan plate format (wrong length, lowercase, symbols).
- Plate crop, when viewed manually, is visibly under 15-20px tall — too small for reliable OCR regardless of preprocessing.
- Detector draws vehicle boxes fine but never draws a distinct plate box — sign that plate-level detection isn't actually wired up.

**Phase to address:**
Phase covering Detection/OCR pipeline build.

---

### Pitfall 5: Speed estimate is wildly inaccurate (or meaningless) without real calibration

**What goes wrong:**
Speed is computed as "pixels moved per frame" without converting to real-world units, or with a guessed/made-up pixels-per-meter constant, producing numbers that are either absurd (e.g., "180 km/h" on a city street) or suspiciously convenient (exactly matching whatever threshold was hardcoded). Camera angle/perspective is also ignored: a monocular camera not perpendicular to the vehicle's path measures a foreshortened or elongated apparent distance, and without a homography/bird's-eye correction, speed error can be very large depending on where in the frame the vehicle is. Research on monocular vision speed estimation shows this is a known, nontrivial problem even with careful calibration (reported errors range from near-perfect with precise calibration to 20%+ MAPE with looser setups) — a hackathon-speed guess is likely to be substantially worse than published research baselines.

**Why it happens:**
Proper calibration (measuring real-world reference distances in the scene, computing a homography or at least a per-lane pixels-per-meter scale, accounting for camera tilt) takes real effort and is the part most likely to get skipped under time pressure in favor of "just multiply by a number that looks right."

**How to avoid:**
- Pick **one fixed physical reference** in the actual footage that's measurable in real life or via a map: e.g., the known width of a traffic lane (~3-3.5m standard), the length of a visible painted crosswalk stripe/pattern, or the distance between two fixed landmarks (poles, curb markings) visible in the frame. Use Google Maps / Google Earth distance measurement between two identifiable fixed points visible in the shot as a fast substitute for a physical tape-measure trip.
- Compute pixels-per-meter using **two points along the vehicle's direction of travel**, not perpendicular to it, since that's the axis being measured for speed.
- If the camera is not perpendicular/overhead (it won't be — it's a casually recorded street video), do at minimum a simple 2-point or 4-point perspective correction (a basic homography using `cv2.getPerspectiveTransform` with 4 known reference points) rather than a flat single scale factor across the whole frame. A single scale factor is acceptable only if the vehicle's tracked path stays within a small, calibrated region of the frame near where the reference distance was measured.
- Use the actual, verified constant frame rate (post re-encode, see Pitfall 3) as the time base: `speed = distance_in_meters / (frame_count_between_points / fps)`.
- Sanity-check every computed speed against physical plausibility for a residential Zona 4 street (typical limits ~30-40 km/h) before trusting it — if the pipeline reports 150+ km/h for a passenger car on that street, that's a calibration bug, not a real reading.
- Calibrate **per clip** — each recorded pass/angle needs its own reference measurement; a scale factor derived from one camera position/angle does not transfer to a differently angled clip.

**Warning signs:**
- Computed speeds vary wildly (e.g., 20 km/h to 200 km/h) across vehicles that visually look like they're moving at similar, normal speeds.
- No explicit reference-distance/scale-factor value exists anywhere in the code — speed is derived directly from raw pixel displacement.
- The "speeding" demo vehicle's reported speed happens to land suspiciously exactly at or just above the configured limit with no margin, across multiple unrelated runs.

**Phase to address:**
Dedicated Speed Estimation & Calibration phase — should not be bundled into general "detection" work, and must be tested against manually eyeballed/known reference speeds (e.g., timing a vehicle's known travel across a measured span using a stopwatch as a rough independent check) before demo day.

---

### Pitfall 6: The selected footage may not actually contain a validated speeding event

**What goes wrong:**
The team builds the entire pipeline assuming "some vehicle in some clip is speeding," but never explicitly verifies, ahead of time, that (a) at least one vehicle in the chosen demo clip genuinely exceeds the configured limit once calibration is applied, and (b) that vehicle's plate is actually legible enough for OCR to succeed. Discovering this gap during the live demo run is the single most damaging failure mode for this project's stated Core Value.

**Why it happens:**
"At least one vehicle exceeds the limit" is treated as a given from real-world traffic behavior, but with only a few pre-recorded clips and imperfect calibration/detection, there's a real chance no clip cleanly produces a confirmed, presentable speeding+legible-plate combination — or the limit is set unrealistically (e.g., copying a highway limit) so nothing in slow city-street footage ever exceeds it.

**How to avoid:**
- As soon as the pipeline can produce *any* speed number (even roughly calibrated), run it against every available clip and manually catalog: which vehicle, which clip, what speed, plate legibility. Do this well before building the fine/notification/portal layers.
- Set the configurable speed limit to a realistic value for the actual street (residential Zona 4 street ≈ 30-40 km/h is typical for Guatemala urban streets), then confirm at least one observed, plausible vehicle speed clears it with a believable margin (not by an absurd amount, and not by 0.1 km/h either).
- If no clip naturally produces a clean speeding+legible-plate case, deliberately choose the limit value based on the *fastest clearly-legible-plate vehicle actually observed* across the footage, rather than picking a limit first and hoping.
- Have a designated "golden clip + golden vehicle" chosen and hardcoded as the demo path, with a fallback second candidate identified in case the first misbehaves during rehearsal.

**Warning signs:**
- No one has manually scrubbed through all clips looking for a vehicle that's both visibly moving quickly and has a readable plate.
- The speed limit value was chosen before any real speed measurement existed from the footage.
- Rehearsal has never been run start-to-finish on the exact clip that will be used live.

**Phase to address:**
Should be explicitly checked at the end of the Speed Estimation phase and reconfirmed in Demo Rehearsal — this is a go/no-go gate before building fine generation/portal on top.

---

### Pitfall 7: Framing risk — the prototype looks/feels like a real enforcement system

**What goes wrong:**
A polished "portal de autoridad de tránsito" UI, real street footage of real Guatemalan vehicles/plates, and automatically generated "multas" with SMS/email notifications can easily read as an actual government enforcement action rather than a hackathon simulation — both to judges and to anyone who later sees a screenshot/recording. This creates two distinct problems: (1) reputational/ethical risk of implying legal authority the project doesn't have, and (2) privacy exposure of real, identifiable people's real plates (and possibly faces, if visible) captured in public without their consent, now displayed and "fined" in a public demo/recording.

**Why it happens:**
Under hackathon pressure, the instinct is to make the demo as realistic and impressive as possible — real footage, real-looking plates, official-sounding portal branding — without pausing to add the disclaimers and redactions that distinguish "prototype demonstrating a concept" from "unauthorized deployment mimicking a government system." This is explicitly a social-impact hackathon submission, which increases scrutiny and the chance the recording circulates.

**How to avoid:**
- Put a persistent, unmissable "PROTOTIPO / SIMULACIÓN — Proyecto de hackathon, sin validez legal" (or English equivalent) label on every surface: portal header/footer, every generated "multa" record, every mock SMS/email template. Do not omit this to save five minutes — it's a single reusable component/banner.
- Do not use real government agency names, seals, or logos (e.g., do not brand it as SAT, PNC, or any actual Guatemalan transit authority) — invent a clearly fictional agency name for the portal to avoid impersonation concerns.
- Limit the plates/vehicles actually surfaced in the demo and any published recording to the minimum needed to tell the story (ideally just the one "golden" speeding vehicle plus maybe one non-speeding control example) rather than listing every plate detected across all footage — reduces the number of real identifiable third parties exposed.
- If feasible in the time available, blur or mask plates/faces of vehicles/pedestrians in the footage that are **not** part of the demonstrated scenario (simple OpenCV Gaussian blur over their detected boxes) before it's shown live or recorded — even a basic blanket blur on all non-selected detections is better than none.
- Keep mock SMS/email templates visually distinct from real carrier/government notification formats (avoid copying real SAT/telecom letterhead styling) so they can't be mistaken for or repurposed as a real notice if screenshotted.
- Do not persist or publish the raw source video / full plate database anywhere public beyond what's needed for the live demo; keep it local to the presentation environment.

**Warning signs:**
- Anyone on the team refers to the system in front of judges as "detecta infractores" without immediately following with "esto es una simulación de prototipo."
- The portal or notification templates were designed by copying visual style from a real government or carrier site/message.
- No blur/redaction pass has been applied to bystander vehicles that appear in the same footage but aren't part of the demonstrated scenario.

**Phase to address:**
Should be baked into the Portal + Notifications phase from the start (disclaimer components, fictional branding) and double-checked in Demo Rehearsal before presenting to judges.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Hardcoded pixels-per-meter constant instead of homography | Saves calibration time | Speed numbers may be systematically wrong outside the calibrated region of frame | Acceptable for hackathon MVP only if vehicle path stays within the calibrated frame region and sanity-checked against plausible speeds |
| No object tracker; re-run detection+OCR independently per frame | Simpler code, faster to build | Same vehicle can generate multiple "fines" across frames (duplicate multa spam) | Never acceptable even for MVP — a minimal IOU-based tracker (a few lines) or a simple "same plate string within N seconds = same event" dedup rule is cheap and prevents an embarrassing demo bug |
| Skipping plate-format regex validation on OCR output | Faster to wire OCR straight to DB | Portal fills with garbage plate strings, undermining demo credibility | Never acceptable — regex validation is a 10-minute add with high payoff |
| Precomputing all detections/speeds offline and replaying as "live" | Removes live-performance risk entirely | Not a "true" live pipeline if judges ask to test other footage on the spot | Acceptable and recommended given a few-hours budget (see Recovery Strategies) — be honest with judges about this design choice, it's a legitimate engineering tradeoff, not cheating |
| Single global speed limit constant, no per-street config | Simpler | Fine, this is genuinely fine — matches project's real scope (one street) | Always acceptable for this project |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|------------------|--------------------|
| YOLOv8 (Ultralytics) | Assuming a stock/COCO-pretrained model detects "license plate" as a class | Confirm the model/weights actually include a plate class or a dedicated plate detector step before building around it |
| EasyOCR / PaddleOCR | Calling OCR on the full frame or full vehicle box instead of a tight, upscaled plate crop | Crop tightly to the plate region, upscale + binarize before OCR call |
| FastAPI serving video/images to frontend | Serving video files without byte-range support, breaking browser seek/scrub in the `<video>` element | Use `StaticFiles`/a range-aware endpoint, or just serve short evidence clips/still frames instead of full scrubbable video for the portal |
| Mock SMS/email "sending" | Leaving real provider SDK imports (Twilio/SendGrid) or placeholder API keys in code/config that could accidentally fire or leak in a public repo | Implement mocks as pure local functions/log entries or templated in-app "notification feed" — no real provider SDK in the dependency tree at all |
| Windows + GPU torch | Installing default `pip install torch` hoping for CUDA support, burning time on driver/toolkit mismatches | Explicitly install CPU-only wheel unless GPU+CUDA already verified working; don't attempt GPU setup mid-hackathon if not already known-good |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|-----------|-------------|------------------|
| Running OCR on every frame instead of per tracked vehicle | Pipeline crawls; demo playback stalls | Run OCR only every N frames per track, keep best reading | Breaks immediately on any clip longer than a few seconds on CPU |
| Feeding full-resolution (e.g. 1080p/4K) phone frames straight into YOLO | Slow inference, no accuracy gain over resized input | Resize frames to ~640px long edge before detection | Breaks as soon as real (non-tiny test) footage is used |
| Re-decoding/re-processing the entire video from scratch on every demo run/restart | Long dead air before anything appears on screen during rehearsal or live run | Precompute once, cache results (JSON/DB) for instant replay | Breaks the moment the live run needs a restart in front of judges |
| No frame skipping/sampling for detection | Wastes compute on visually near-identical consecutive frames | Detect every frame is fine for a short clip, but consider processing at reduced effective FPS (e.g., every 2nd-3rd frame) if still too slow | Only matters if Pitfall 2's mitigations aren't enough |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing real plate numbers + evidence frames in a portal accessible without any access control, then exposing it beyond the local demo environment (e.g., public tunnel/ngrok left open) | Real people's identifiable plates/vehicles exposed publicly without consent, reputational and possible privacy-law exposure | Keep the portal local/localhost for the demo; if a public URL is needed for judges, restrict to the exact time window and take it down immediately after |
| Embedding a real government agency name/logo "to make it look convincing" | Impersonation of a real authority (see Pitfall 7) | Use a clearly fictional agency name/branding |
| Leaving placeholder real API keys (Twilio/SendGrid) or `.env` files with real credentials in the repo "just in case" | Credential leak if repo made public later | Do not add real provider SDKs/keys at all — mocks should need none |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|--------------|-------------------|
| Portal shows a raw, unstyled table of every single detection across all footage (including non-speeding, blurry, or garbage entries) | Judges see noise/garbage instead of the clean success story, undermining confidence in the system | Filter portal display to validated (regex-passed) plates and clearly flag which entries triggered a "multa"; keep the demo narrative focused |
| No clear visual indication of *why* a fine was generated (evidence frame, computed speed, limit) | Judges can't verify the claim at a glance, demo feels like a black box | Show the plate crop, computed speed vs. limit, and timestamp together on the fine record — this is also good "showing your work" for a judged hackathon |
| No disclaimer visible during the actual live walkthrough | Risk of the demo being perceived as real enforcement (Pitfall 7) | Persistent banner/label as described in Pitfall 7 |

## "Looks Done But Isn't" Checklist

- [ ] **OCR integration:** Works on a hand-picked test image in isolation — verify it's actually being called inside the live video pipeline on real detected crops, not just in a standalone test script.
- [ ] **Speed calibration:** A number is displayed — verify it's derived from an actual measured reference distance and a verified constant FPS, not a placeholder scale factor of `1.0` or similar left over from early development.
- [ ] **Video ingestion:** Pipeline runs on the short test clip — verify it's also been run at least once, end-to-end, on the actual full-length/full-resolution clip that will be used live.
- [ ] **Duplicate-fine prevention:** A fine appears in the portal — verify the same real-world vehicle passing across multiple frames doesn't produce multiple separate fine records for the same event.
- [ ] **Mock notifications:** SMS/email "sent" confirmation appears — verify it's actually a local mock/log entry and not an accidental live call to a real provider SDK left in from a copy-pasted tutorial.
- [ ] **Disclaimer/branding:** Portal and notifications look polished — verify the "prototype/simulation, no legal validity" label and fictional agency name are actually present, not just planned.
- [ ] **End-to-end demo path:** Individual components (detection, OCR, speed, fine, notification, portal) each work in isolation — verify the full chain has been run start-to-finish, uninterrupted, on the exact machine and exact clip that will be used in front of judges, at least once before presenting.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Live per-frame processing too slow for demo (Pitfall 2) | LOW | Switch framing to "pre-processed once, replayed live" — run the pipeline ahead of time, store detections/speeds/fines in a JSON/DB, and have the portal + a synced video player replay it as if live. This is a legitimate and common pattern, not a failure, if disclosed honestly. |
| Speed numbers implausible/inconsistent close to demo time (Pitfall 5) | MEDIUM | Re-derive the pixels-per-meter constant using a simpler, more conservative reference (e.g., just the lane width) restricted to the specific frame region where the golden vehicle travels, rather than trying to fix a general-purpose homography under time pressure. |
| No clip cleanly shows a legible-plate speeding vehicle (Pitfall 6) | MEDIUM | Lower the configured limit to the highest *genuinely observed and plausible* speed in the available footage rather than abandoning the automatic-detection narrative; be transparent that the limit reflects the specific street's real posted/typical limit. |
| Video won't decode / rotated wrong close to demo time (Pitfall 3) | LOW | Re-encode with `ffmpeg` to standard H.264 MP4, CFR, correct orientation baked in — a few-minute fix if ffmpeg is already installed (confirm this in Setup phase, not during recovery). |
| Portal/demo accidentally implies real enforcement authority late in the game (Pitfall 7) | LOW | Add the disclaimer banner/component and rename the agency branding — this is a fast, mechanical fix if not left until the last minute. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| Dependency/model setup eats time budget | Phase 0: Setup | All libraries import and run one trivial inference call with no further downloads needed |
| CPU pipeline too slow for live demo | Detection/OCR build + Demo Rehearsal | Full-length, full-resolution clip processed end-to-end within an acceptable, pre-agreed time on the actual demo machine |
| Video ingestion/codec/VFR issues | Phase 0: Setup | Every candidate clip opens, decodes, and reports correct orientation/FPS in OpenCV before pipeline work begins |
| Plate detection/OCR fails on real footage | Detection/OCR build | OCR output for the golden demo vehicle passes the Guatemala plate regex consistently across multiple frames |
| Speed estimation inaccurate without calibration | Speed Estimation & Calibration | Computed speed for at least one known clip is sanity-checked against a manual/independent rough estimate and against physical plausibility |
| No clip has a validated speeding + legible-plate event | End of Speed Estimation phase (go/no-go gate) | A specific "golden clip + golden vehicle" is identified, documented, and confirmed to exceed the configured limit with a legible plate |
| Demo implies real legal authority / exposes real people without consent | Portal + Notifications build | Disclaimer banner present on every surface; fictional agency branding; non-essential bystander plates blurred or excluded from what's shown |
| Duplicate fines from re-detecting the same vehicle | Detection/OCR build | Portal shows exactly one fine record per real speeding event in the golden clip |

## Sources

- [License Plate Detection with YOLOv8 (Emergent Mind)](https://www.emergentmind.com/topics/license-plate-detection-using-yolov8) — MEDIUM confidence, aggregated research summary
- [Optimized YOLOv8 for Automatic License Plate Recognition on Resource Constrained Devices (ETASR)](https://etasr.com/index.php/ETASR/article/view/9983) — MEDIUM confidence, peer-reviewed
- [License Plate Detection and Recognition with YOLO and PaddleOCR (Medium)](https://medium.com/@ggulsumkayhann/license-plate-detection-and-recognition-with-yolo-and-paddleocr-9c39baecce87) — LOW-MEDIUM confidence, practitioner writeup
- [License Plate Detection using YOLOv8 and Performance Evaluation of EasyOCR, PaddleOCR and Tesseract (ResearchGate)](https://www.researchgate.net/publication/385535133_License_Plate_Detection_using_YOLO_v8_and_Performance_Evaluation_of_EasyOCR_PaddleOCR_and_Tesseract) — MEDIUM confidence
- [Comparison of Image Preprocessing Techniques for Vehicle License Plate Recognition Using OCR (arXiv 2410.13622)](https://arxiv.org/pdf/2410.13622) — MEDIUM confidence, peer-reviewed preprint
- [Vision-based Vehicle Speed Estimation for ITS: A Survey (Fernández Llorca et al., IET, 2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12079) — HIGH confidence, published survey
- [Vision-based Vehicle Speed Estimation: A Survey (arXiv 2101.06159)](https://arxiv.org/pdf/2101.06159) — HIGH confidence
- [Accurate Vehicles Detection and Speed Estimation Using Homography Based Background Subtraction (ResearchGate)](https://www.researchgate.net/publication/378528773_Accurate_Vehicles_Detection_and_Speed_Estimation_Using_Homography_Based_Background_Subtraction_and_Deep_Learning_Approaches) — MEDIUM confidence
- [Vehicle Speed Estimation Using Consecutive Frame Approaches and Deep Image Homography (ResearchGate)](https://www.researchgate.net/publication/386195390_Vehicle_Speed_Estimation_Using_Consecutive_Frame_Approaches_and_Deep_Image_Homography_for_Image_Rectification_on_Monocular_Videos) — MEDIUM confidence
- [OpenCV forum: Couldn't read video stream from file](https://forum.opencv.org/t/opencv-couldnt-read-video-stream-from-file/1495) — MEDIUM confidence, community-verified operational issue
- [OpenCV forum: VideoCapture doesn't open](https://forum.opencv.org/t/videocapture-doesnt-open/6697) — MEDIUM confidence
- [Vehicle registration plates of Guatemala (Wikipedia)](https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_Guatemala) — MEDIUM confidence, cross-checked against multiple Guatemala plate-format sources found in search
- [Guatemala license plate format overview (matriculasdelmundo.com)](https://matriculasdelmundo.com/en/guatemala.html) — MEDIUM confidence
- General ALPR/CV hackathon operational knowledge (dependency installs, calibration difficulty, demo-day live-processing risk) — LOW-MEDIUM confidence where not independently verified above; based on well-established, widely-reported patterns in computer-vision engineering practice rather than a single citable source

---
*Pitfalls research for: Real-time-style ALPR + speed estimation + mock fine generation (hackathon MVP)*
*Researched: 2026-07-16*
