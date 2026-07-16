# Feature Research

**Domain:** Automated speed-enforcement / ALPR (Automatic License Plate Recognition) fine systems — hackathon prototype
**Researched:** 2026-07-16
**Confidence:** MEDIUM (grounded in verified real-world program documentation + established ALPR industry patterns; some Guatemala-specific specifics are approximate)

## Context Recap

Real-world reference systems researched: NYC DOT's Automated Speed Enforcement / Vision Zero camera program, generic municipal ALPR-to-citation pipelines (Motorola/Safe Fleet/OpenALPR-style solution briefs), and Guatemala's own traffic-fine ecosystem (SAT multas portal, DGT/Reglamento de Tránsito, PROVIAL). This grounds what a "credible-looking" system needs to visibly do, and what a real system does that this prototype must NOT imitate.

## Feature Landscape

### Table Stakes (Must Be Visibly Working in the Demo)

These are the steps explicitly named in PROJECT.md's Core Value. If any one is missing or faked, the demo doesn't read as "a system," it reads as a slideshow.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Video ingestion (frame-by-frame read of a pre-recorded clip) | Baseline input for the whole pipeline; real ALPR systems always start from a camera feed/frame stream | LOW | OpenCV `VideoCapture` over the pre-recorded Zona 4 clip. Trivial but must exist before anything else works. |
| Vehicle detection + tracking across frames | Every real ALPR/enforcement system detects the vehicle before it reads the plate; without tracking, speed cannot be computed (need same vehicle across ≥2 frames) | MEDIUM | YOLOv8 (pretrained COCO "car/truck/bus" classes) is enough — no custom training needed. Tracking can be as simple as a centroid/IoU tracker; doesn't need ByteTrack-level sophistication for one demo clip. **This is a hard dependency for speed estimation — build it early.** |
| Plate localization + OCR (Guatemala format) | This is the "it read the actual plate" moment judges will look for — the single most scrutinized output on screen | HIGH | Highest-risk table-stakes item. Real ALPR systems get plate crops from a dedicated plate-detector, not just a full-frame OCR pass. Guatemala plates are small, often glare/angle-affected in real street footage. Budget the most rehearsal time here; pick the clip/frame with the clearest frontal plate view for the "hero" run. Have a fallback: if OCR confidence is low, still surface *a* plate reading rather than silently failing — real systems have manual-review queues for exactly this reason (see Differentiators). |
| Speed estimation from video (not from GPS/radar) | This is the core technical claim of the project — "we computed real speed from a real video" | HIGH | Real camera-based speed-enforcement systems (radar-camera hybrids, ANPR average-speed corridors like SPECS/"safety camera" systems in the UK) all rely on either (a) a physical calibration (known distance between two reference points/lines, e.g. road-paint markings measured on-site) and elapsed frame time, or (b) stereo/lidar depth. For a video-only hackathon build, (a) is the only feasible approach: mark two reference lines a known real-world distance apart on the Zona 4 footage, track when the vehicle's bounding-box centroid crosses each line, and divide distance by elapsed time (using video FPS). This requires accurate manual calibration against the actual filmed street — treat as its own build task, not a byproduct of detection. |
| Configurable speed limit comparison | Every real system (NYC ASE, Guatemala's own speed rules) compares a measured value against a posted/legal limit before deciding "violation" | LOW | A single hardcoded limit value for the filmed street segment is enough for MVP. Making it "configurable" (a variable/config field, not a hardcoded literal) costs almost nothing extra and pays off for the zone-based story (see Differentiators). |
| Automatic fine record generation (plate, speed, limit, timestamp, evidence) | This is literally the deliverable — a citation record is what every real ALPR-to-ticket pipeline produces (Motorola/Safe Fleet solution briefs describe exactly this: detection → DB match → automated citation workflow) | LOW | Mostly a DB insert once OCR + speed + limit are known. Must capture an evidence frame/crop image alongside the record — real systems always attach photographic evidence to a citation; a fine with no evidence image will look unconvincing to judges who know how real systems work. |
| Mock SMS/email notification (generated, not sent) | Every enforcement program (NYC, SAT Guatemala) closes the loop by notifying the registered owner; without this step the "system" looks incomplete even though sending is explicitly out of scope | LOW | Render a realistic-looking SMS/email template (plate, location, speed, fine amount, "citation number") and store/display it — e.g., in an admin log or a "notifications sent" tab in the portal. No provider integration. Clearly label as **SIMULATED**. |
| Public-style web portal listing plates/fines | The "SAT multas" style lookup portal is the artifact judges will interact with directly; it's the visible proof the backend pipeline worked | LOW–MEDIUM | Simple table/list view (plate, violation date/time, location, measured speed, limit, fine amount, evidence thumbnail) styled to resemble a government fines-lookup page (portal.sat.gob.gt-style layout: search box, plate lookup, table of results). Do **not** copy real government logos/branding — see Anti-Features. |
| One-shot end-to-end pipeline run (video → detection → OCR → speed → fine → notification → portal) | PROJECT.md explicitly requires this to run live for judges in a single pass — this is the actual acceptance test | MEDIUM–HIGH (integration risk, not new logic) | This is glue work: every module above must chain without manual intervention and finish inside the demo's time budget. The dominant risk isn't any single feature being hard, it's the pipeline stalling somewhere (slow inference, tracker losing the vehicle, OCR retry loop). Rehearse the exact clip end-to-end multiple times before the demo, not just its parts. |
| "This is a simulation" disclaimer/watermark | Ethically necessary the moment the UI resembles a real government portal and processes a real street's real plates | LOW | A visible banner ("Prototipo de hackathon — sistema simulado, no es una entidad gubernamental") on both the portal and any mock notification content. Cheap insurance against judges (or anyone else) mistaking this for a real enforcement claim. |

### Differentiators (Impressive, Cut First Under Time Pressure)

These are what make judges believe the "social impact" story beyond "the OCR worked once." None of these are needed to satisfy Core Value; all are legitimate reasons NYC-style programs and Guatemala's own reporting emphasize similar things.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Violations dashboard / stats (count over time, speed distribution, avg speed vs. limit) | Real programs (NYC's own "94% reduction" reporting) win public support by showing *aggregate* numbers, not single incidents — a small stats view reframes "we caught one car" as "here's a monitoring capability" | LOW (once fine records exist in a DB, this is just a query + chart) | **Best ROI differentiator** — cheapest to build once table stakes exist, and directly answers the judges' "so what, at scale?" question. Prioritize this first if time remains. |
| Zone-based speed limit config (e.g., simulated "school zone" / "pedestrian zone" limit override) | Mirrors real Vision Zero logic (NYC's 750 school speed zones with time-restricted lower limits) and is the clearest way to make the pitch about *pedestrian safety*, not just "gotcha" tickets | LOW–MEDIUM if the config is just a settable field per street segment; MEDIUM+ if you want it tied to actual GPS/zone boundaries | Only build the *config concept* (a named zone + its own limit, shown in the portal/UI), not real geofencing. You likely only have footage of one street segment — treat it as "if this were a school zone, the limit would be X" framing rather than pretending you detected an actual school. Be honest in the pitch about what's simulated vs. real. |
| Annotated video playback (bounding boxes, plate crop, speed overlay burned into or drawn over the frame) | This is the single highest "wow factor per minute of judge attention" item — seeing boxes track the car and a speed number appear live is far more convincing than reading a database table | MEDIUM | Cheap using OpenCV drawing primitives once detection/tracking/speed are already computed — mostly presentation layer on data you already have. Strong candidate for second priority after the stats dashboard. |
| Plate/date/zone search or filter in the portal | Mimics the actual "look up a plate" interaction pattern of real fines portals (SAT Guatemala's own multas portal is literally a plate-lookup search) | LOW | Nice authenticity touch, low cost if portal already has a table — add a search input filtering client-side. |
| Repeat-offender flag / highlight | Real programs report on repeat offenders as a policy story ("X% of violations come from repeat drivers") — reinforces enforcement narrative without extra pipeline work | LOW | Only meaningful if the demo processes multiple clips/passes of the same plate; skip if only one hero vehicle is demoed. |
| Before/after narrative (no build required — pure pitch framing) | Real Vision Zero reporting's most persuasive artifact is a before/after or trend claim ("94% reduction where cameras installed") | ZERO (narrative only) | This costs nothing to build — it's a slide/talking point: "before this tool, no one at [street] knew vehicles were speeding; now every pass through this corridor is measured." Don't spend engineering time simulating "before" data; just say it in the pitch. |
| OCR confidence score shown per plate reading | Real ALPR-to-citation systems typically flag low-confidence reads for human review rather than auto-issuing a citation — shows judges you understand the failure mode, not just the happy path | LOW | A simple confidence number/threshold badge next to each plate reading in the portal. Cheap credibility signal that also functions as an honest hedge if OCR is imperfect during the live run. |

### Anti-Features (Do Not Attempt — Ethically/Legally/Scope Problematic)

These map directly to items PROJECT.md already marks Out of Scope, plus additional risks surfaced by researching real ALPR programs (notably the EFF's documented concerns about ALPR "mission creep" into surveillance and civil-liberties exposure).

| Feature | Why It Seems Appealing | Why Problematic | Alternative |
|---------|------------------------|------------------|-------------|
| Real SMS/email sending (Twilio, SendGrid, etc.) | "Looks more real," judges see an actual text arrive | Requires real credentials/costs under time pressure; more importantly, sending a real notification implies a real legal fine to a real (possibly innocent, misread) plate owner — a live ethical liability, not just a technical one | Render the notification content and display/log it as "sent (simulated)" — value is in showing *what would be sent*, not delivering it |
| Real integration with a government entity (SAT, PROVIAL, RENAP, municipal traffic authority) | Would make the demo feel "production-ready" | Implies this prototype has legal enforcement authority it does not have; could be read as impersonating a government system, which is a serious ethical/legal line, especially since the portal is styled to resemble a real fines-lookup site | Portal must carry a clear "simulated / not an official government system" disclaimer at all times; never reuse real government logos, seals, or exact branding |
| Owner identity lookup (matching plate → real name/address of vehicle owner) | Feels like it "closes the loop" like a real citation would | This is exactly the kind of ALPR "mission creep" flagged in EFF's reporting on plate readers being used beyond their stated purpose — pulling real personal data (name, address) tied to a real plate captured on a real public street is a genuine privacy exposure, not a simulated one, since the plate itself is real | Store and display only the plate string + violation data; never attempt registry/owner lookups, even mocked with fake data that could be confused for real records |
| Facial recognition / driver or occupant identification | "More impressive detection" | Biometric identification of individuals is a categorically different (and far more sensitive) capability than plate/vehicle detection; wildly out of scope for a speed-enforcement pitch and raises real biometric-privacy concerns | Detect and blur/ignore faces if visible in frame; the system's subject is the *vehicle*, not the *person* |
| Live camera / RTSP / IP camera ingestion | "Real-time" sounds more advanced | No hardware, no time — already explicitly out of scope in PROJECT.md; also reintroduces uptime/networking risk into a few-hours build | Pre-recorded clip only, as already decided |
| Real fine payment processing | "End-to-end like the real SAT portal" | Implies real financial/legal transactions attached to a hackathon prototype — well outside any reasonable scope and a compliance nightmare (payment handling, PCI, etc.) | Portal shows a fine amount as a static computed number; no payment flow at all |
| Automated escalation (license suspension, points system, watchlist alerts) | Mirrors "real" enforcement consequences (Guatemala's SLV fines include line suspension) | These are real legal/administrative penalties; simulating them risks the demo reading as though it claims real regulatory authority | Cap the simulated consequence at "a fine record + a mock notification" — no downstream punitive actions modeled |
| Publishing/exposing all captured real plates indiscriminately (not just the demoed violation) | "More data = more impressive" | The footage is a real street with real passing vehicles' real plates; broadly capturing and displaying every plate that appears (not just the one demo violation) turns this into ad hoc surveillance of bystanders who did nothing wrong and did not consent to being in a public demo/dataset | Limit the demo dataset to the specific vehicle(s) intentionally used for the speeding demonstration; avoid indexing/publishing incidental plates from the footage, and don't retain the raw video/plate data beyond the hackathon |

**Ethical/legal flag (explicit, per quality gate):** This prototype visually mimics a government enforcement and fines-lookup system, and processes real license plates captured from a real public street without those drivers' consent. That combination is the single biggest reputational/ethical risk of the whole project — bigger than any technical risk. Mitigate with: (1) a persistent "SIMULATED / not an official system" disclaimer everywhere the fines portal or notification content is shown, (2) scoping data capture/display to only the intentionally-demoed vehicle(s) rather than every plate visible in the footage, (3) never claiming or implying integration with a real government entity, and (4) not retaining or redistributing the source video/plate data after the hackathon.

## Feature Dependencies

```
Video ingestion
    └──requires──> (nothing — entry point)

Vehicle detection
    └──requires──> Video ingestion

Vehicle tracking (same vehicle across frames)
    └──requires──> Vehicle detection

Plate localization + OCR
    └──requires──> Vehicle detection (crop region to search for a plate)

Speed estimation
    └──requires──> Vehicle tracking
    └──requires──> Manual calibration (known real-world reference distance in the filmed scene)

Speed limit comparison
    └──requires──> Speed estimation
    └──requires──> Configurable limit value (hardcoded is fine for MVP)

Fine record generation
    └──requires──> Plate OCR result
    └──requires──> Speed limit comparison (violation = true)
    └──requires──> Evidence frame capture

Mock notification generation
    └──requires──> Fine record generation

Portal (list view)
    └──requires──> Fine record generation (reads from the same store)

Stats/dashboard ──enhances──> Portal (adds aggregate view on top of same data)

Zone-based limit config ──enhances──> Speed limit comparison (replaces hardcoded single value)

Annotated video playback ──enhances──> (Vehicle detection + tracking + Speed estimation) — presentation layer over existing outputs, no new detection logic

OCR confidence badge ──enhances──> Plate OCR (surfaces existing model output, no new capability)

Repeat-offender flag ──requires──> Fine record generation (multiple records) ──conflicts with──> single-hero-vehicle demo scope (needs multiple plates/passes to be meaningful)
```

### Dependency Notes

- **Speed estimation requires vehicle tracking, not just detection:** a per-frame detector alone gives you "there's a car in this frame" — you need the *same* vehicle linked across at least two frames (ideally crossing two calibrated reference lines) to compute displacement over time. Build tracking before attempting speed math; it is the load-bearing dependency the whole demo rests on.
- **Speed estimation requires manual calibration against the real scene:** because there's no radar/lidar/GPS ground truth, someone must measure a real-world reference distance in the actual Zona 4 footage (e.g., distance between two visible road features) before any speed number can be trusted. This is a one-time setup task, not code — do it early, ideally before writing the speed-math code, so the code can be tested against a known value.
- **Fine generation requires an evidence frame, not just numeric fields:** a citation record without a captured image is not credible against the reference systems researched (all real ALPR-to-citation pipelines attach photographic evidence). Capture and store the crop/frame at the moment of the highest-confidence plate read.
- **Zone-based config enhances but does not replace hardcoded-limit MVP:** ship with one hardcoded limit for the filmed segment first; only generalize to a per-zone config structure if the stats dashboard and video overlay differentiators are already done.
- **Repeat-offender flagging conflicts with a single-hero-vehicle demo:** if the live run is built around reliably catching exactly one speeding vehicle, don't build repeat-offender logic — there's nothing for it to show. Only pursue this if multiple clips/passes of recognizable vehicles are actually being processed.

## MVP Definition

### Launch With (v1 — must work live for judges)

- [ ] Ingest the pre-recorded Zona 4 video and process it frame-by-frame — entry point for everything else
- [ ] Detect and track at least the one target vehicle across frames — required before speed can be computed
- [ ] Localize and OCR its plate in Guatemala format — the visible "it read a real plate" proof point
- [ ] Estimate its speed using a manually calibrated real-world reference distance — the core technical claim of the project
- [ ] Compare estimated speed to a single hardcoded street-segment limit — minimum viable "violation" decision
- [ ] Generate a fine record (plate, speed, limit, timestamp, evidence frame) — the deliverable artifact
- [ ] Generate (not send) a mock SMS/email notification tied to that fine — closes the narrative loop cheaply
- [ ] Show the fine in a portal styled like a transit-authority fines lookup, with a "SIMULATED" disclaimer — the artifact judges actually look at
- [ ] Run all of the above as one continuous pass, live, in front of judges — the actual acceptance test from PROJECT.md

### Add After Validation (v1.x — only if the above is solid and time remains)

- [ ] Stats/dashboard view (violation count, avg speed vs. limit) — cheapest, highest-ROI addition once fine records exist
- [ ] Annotated video playback with bounding boxes / speed overlay — best per-minute "wow factor" for judges
- [ ] Zone-based/school-zone speed limit config (even if simulated/conceptual) — strengthens the social-impact pitch
- [ ] Plate/date search in the portal — cheap authenticity touch
- [ ] OCR confidence badge per reading — cheap credibility hedge

### Future Consideration (v2+ — explicitly not for this hackathon)

- [ ] Real SMS/email delivery — deferred indefinitely; introduces real legal/ethical liability, not just engineering cost
- [ ] Real government system integration (SAT/PROVIAL/RENAP) — deferred indefinitely; this prototype has no legal enforcement authority and should never claim to
- [ ] Owner identity lookup / biometric or facial recognition — should not be pursued even in later versions without a fundamentally different ethical/legal review
- [ ] Live camera ingestion, multi-region plate formats, real payment processing — deferred per PROJECT.md's existing Out of Scope list

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| Video ingestion | HIGH | LOW | P1 |
| Vehicle detection + tracking | HIGH | MEDIUM | P1 |
| Plate localization + OCR | HIGH | HIGH | P1 |
| Speed estimation (calibrated) | HIGH | HIGH | P1 |
| Speed limit comparison | HIGH | LOW | P1 |
| Fine record + evidence capture | HIGH | LOW | P1 |
| Mock notification generation | MEDIUM | LOW | P1 |
| Fines portal (list view + disclaimer) | HIGH | LOW–MEDIUM | P1 |
| End-to-end live pipeline run | HIGH | MEDIUM–HIGH (integration) | P1 |
| Stats/dashboard | HIGH (judge persuasion) | LOW | P2 |
| Annotated video playback overlay | HIGH (judge persuasion) | MEDIUM | P2 |
| Zone-based speed limit config | MEDIUM (narrative value) | LOW–MEDIUM | P2 |
| Portal search/filter | LOW–MEDIUM | LOW | P2 |
| OCR confidence badge | LOW–MEDIUM | LOW | P2 |
| Repeat-offender flag | LOW (only if multi-plate demo) | LOW | P3 |
| Real SMS/email sending | NEGATIVE (risk > value) | MEDIUM | Do not build |
| Real government integration | NEGATIVE (risk > value) | HIGH | Do not build |
| Owner/biometric identification | NEGATIVE (risk > value) | HIGH | Do not build |

**Priority key:**
- P1: Must have — this is the Core Value from PROJECT.md; the demo fails without it
- P2: Should have — build only after every P1 item runs reliably end-to-end
- P3: Nice to have — only pursue if P1+P2 are done with time to spare

## Competitor / Reference System Feature Analysis

| Feature | NYC DOT Automated Speed Enforcement (Vision Zero) | Generic municipal ALPR-to-citation pipeline (Motorola/Safe Fleet-style) | SAT Guatemala multas portal | Our Approach |
|---------|----------------------------------------------------|--------------------------------------------------------------------------|------------------------------|--------------|
| Detection trigger | Fixed cameras at data-selected high-risk locations, radar/loop-based speed measurement | Fixed/mobile ALPR cameras matching plates against violation/registry databases in real time | N/A (post-hoc lookup, not detection) | Single pre-recorded clip, vision-only speed estimation via calibrated reference distance |
| Zone-based rules | School-zone hours (6am–10pm weekdays), now 24/7 city-wide | Configurable per deployment (parking, tolling, watchlists) | Fixed national/municipal fine schedule | Optional simulated zone/limit config as a differentiator, not a real geofence |
| Evidence capture | Time-stamped photo/video evidence attached to each violation | Time/location/lane metadata + image attached to citation | Citation record referencing an infraction code, no live evidence shown to public | Evidence frame/crop attached to every fine record — table stakes |
| Owner notification | Mailed violation notice to registered owner | Automated workflow triggers citation issuance to registered owner | SMS/portal notice of pending fines (payment-oriented) | Mock-only SMS/email content, generated and displayed, never sent |
| Public reporting | Public dashboards/annual reports showing aggregate violation trends (used to justify/expand the program) | Not typically public-facing (law-enforcement/operator tool) | Public-facing plate lookup (search by plate to see fines owed) | Portal styled like SAT's plate-lookup UX, plus an aggregate stats view for the social-impact narrative |
| Legal/authority basis | State/city legislation grants camera-ticket authority | Operates under contracted government or private-property authority | Operates under Guatemala's SAT/traffic legal framework | Explicitly **no legal authority claimed** — persistent "simulated" disclaimer everywhere the resemblance to a real system could cause confusion |

## Sources

- NYC DOT — "Speed Cameras Achieved a 94 Percent Reduction in Speeding," https://www.nyc.gov/html/dot/html/pr2025/nyc-dot-speed-cameras.shtml (MEDIUM confidence — official government press release; verifies program scale, school-zone hours, and public-trend-reporting pattern)
- Vision Zero Network — "Designing Speed Safety Camera Programs That Are Fair & Effective," https://visionzeronetwork.org/designing-speed-safety-camera-programs-that-are-fair-effective/ (MEDIUM confidence — advocacy org, cross-checked against NYC DOT's own reporting)
- NYC DOT — Vision Zero Safe Driving, https://www.nyc.gov/html/dot/html/motorist/vision-zero-safe-driving.shtml (MEDIUM confidence)
- e-con Systems — "How ALPR Cameras Empower Violation Ticketing Systems," https://www.e-consystems.com/blog/camera/applications/how-alpr-cameras-empower-violation-ticketing-systems-to-help-law-enforcement-agencies/ (LOW–MEDIUM confidence, vendor content — used only for generic pipeline-shape claims, cross-checked against Motorola/Safe Fleet solution briefs)
- EFF — "Traffic Violation! License Plate Reader Mission Creep Is Already Here," https://www.eff.org/deeplinks/2026/03/traffic-violation-license-plate-reader-mission-creep-already-here (MEDIUM confidence — directly informs the Anti-Features/ethical-flag section on ALPR data mission creep)
- Congress.gov CRS Report — "Law Enforcement and Technology: Use of Automated License Plate Readers," https://www.congress.gov/crs-product/R48160 (MEDIUM–HIGH confidence — official congressional research product)
- City of Palo Alto — ALPR public information page, https://www.paloalto.gov/Departments/Police/Public-Information-Portal/Automated-License-Plate-Recognition-ALPR (MEDIUM confidence — municipal disclosure of ALPR data-handling policy)
- DGT Guatemala — Sistema Limitador de Velocidad / Acuerdo Ministerial 69-2026, https://dgt.gob.gt/comunicado-oficial-acuerdo-ministerial-no-69-2026-establece-implementacion-del-sistema-limitador-de-velocidad-con-sanciones/ (MEDIUM confidence — official Guatemalan government communication; used for local fine-amount/legal-context grounding only, not for portal-feature copying)
- SAT Guatemala — Portal de Multas de Tránsito, https://portal.sat.gob.gt/portal/multas/ (MEDIUM confidence — official portal referenced only for its plate-lookup UX pattern, not to be copied/impersonated)
- Prensa Libre / La Hora / Living in Guatemala — SLV and traffic fine reporting (LOW–MEDIUM confidence, local news; used only as supplementary context on typical Guatemala fine amounts, not as authoritative legal source)

---
*Feature research for: Automated speed-enforcement / ALPR fine-generation hackathon prototype (SyncTrack)*
*Researched: 2026-07-16*
