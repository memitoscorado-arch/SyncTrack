# Roadmap: SyncTrack

## Overview

SyncTrack goes from a real, pre-recorded Zona 4 street video to a single live demo showing a speeding vehicle caught, cited, and published. The path is CV-pipeline-first, backend-last: first prove vehicles can be reliably detected and tracked on the real footage, then prove plates can be read and validated, then prove a calibrated speed can be computed and sanity-checked against a chosen limit (with an explicit go/no-go gate on real footage), then wire up the mechanical fine/notification/portal layer on top of proven data, and finally rehearse the whole thing end-to-end on the exact demo machine and exact clip.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Video Ingestion, Vehicle Detection & Tracking** - Read the real Zona 4 clip frame-by-frame and reliably detect/track vehicles with stable IDs
- [ ] **Phase 2: Plate Localization & OCR** - Locate and read plate text per tracked vehicle, validated against Guatemala format
- [ ] **Phase 3: Speed Calibration & Violation Detection** - Compute a calibrated, sanity-checked speed per vehicle and flag violations against a configurable limit
- [ ] **Phase 4: Fine Engine, Mock Notifications & Public Portal** - Auto-generate fine records with evidence, mock SMS/email content, and a disclaimed public-style portal
- [ ] **Phase 5: End-to-End Demo Integration & Rehearsal** - Run the complete pipeline live, continuously, on the golden clip with a validated fallback

## Phase Details

### Phase 1: Video Ingestion, Vehicle Detection & Tracking
**Goal**: Given the real Zona 4 video, the system reads it frame-by-frame and reliably detects and tracks vehicles with stable identifiers across consecutive frames.
**Depends on**: Nothing (first phase)
**Requirements**: INGEST-01, DETECT-01, DETECT-02
**Success Criteria** (what must be TRUE):
  1. The pipeline opens and decodes a real clip (e.g. IMG_8852.MOV) frame-by-frame without errors, correctly reporting fps/orientation.
  2. Vehicles visible in the footage are detected with bounding boxes drawn on the correct real vehicles, using a pretrained model (no custom training).
  3. A single physical vehicle keeps the same tracking ID as it moves across multiple consecutive frames, without ID switches during its pass through frame.
**Plans**: TBD

### Phase 2: Plate Localization & OCR
**Goal**: For a tracked vehicle, the system isolates the plate region and reads validated Guatemala-format plate text.
**Depends on**: Phase 1
**Requirements**: PLATE-01, PLATE-02
**Success Criteria** (what must be TRUE):
  1. Given a tracked vehicle's bounding box, the system isolates a plate region within that crop.
  2. The system produces OCR text for the plate that matches the real plate visible in close-range footage (e.g. "P527FQJ").
  3. Plate reads are validated against the Guatemala format (1 letter + 3 digits + 3 letters), with malformed reads rejected or corrected rather than silently accepted.
**Plans**: TBD

### Phase 3: Speed Calibration & Violation Detection
**Goal**: The system computes a believable, calibrated speed for a tracked vehicle and correctly flags it against a configurable speed limit.
**Depends on**: Phase 2
**Requirements**: SPEED-01, SPEED-02
**Success Criteria** (what must be TRUE):
  1. Using a manually measured real-world reference distance (e.g. dashed lane markings visible in the footage) and elapsed time between two crossing points, the system computes a vehicle's speed in km/h.
  2. Computed speeds are physically plausible for a Guatemala City street (sanity-checked against realistic ranges, not implausible outliers).
  3. The system compares computed speed against a configurable limit value and correctly flags violations (and does not flag non-violations).
  4. Go/no-go gate: at least one real clip/vehicle is confirmed to produce both a legible plate and a speed that plausibly exceeds the chosen limit, before Phase 4 work begins.
**Plans**: TBD

### Phase 4: Fine Engine, Mock Notifications & Public Portal
**Goal**: When a tracked vehicle violates the limit, a fine record with evidence is generated automatically, a simulated notification is produced, and both are visible in a disclaimed public-style portal.
**Depends on**: Phase 3
**Requirements**: FINE-01, NOTIF-01, PORTAL-01, PORTAL-02
**Success Criteria** (what must be TRUE):
  1. When a tracked vehicle's speed exceeds the limit, a fine record is automatically created with plate, speed, limit, timestamp, and an evidence frame.
  2. For each fine, mock SMS and email notification content is generated (never sent) and explicitly labeled "SIMULADO".
  3. A web portal lists registered plates and their fines, showing plate, date/time, measured speed, limit, amount, and an evidence thumbnail.
  4. The portal displays a persistent, visible disclaimer ("SIMULADO — prototipo de hackathon, no es una entidad gubernamental") on every page.
**Plans**: TBD

### Phase 5: End-to-End Demo Integration & Rehearsal
**Goal**: The complete pipeline runs as a single continuous, live pass from video ingestion through the portal, in front of judges.
**Depends on**: Phase 4
**Requirements**: DEMO-01
**Success Criteria** (what must be TRUE):
  1. Running the full pipeline once, continuously, on the golden clip produces ingestion -> detection -> OCR -> speed -> fine -> notification -> portal entry without manual intervention between stages.
  2. The full run's timing has been validated on the actual demo machine and fits a live-presentation time budget.
  3. A documented fallback clip/vehicle is confirmed working, in case the primary golden clip fails during the live run.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|-----------------|--------|-----------|
| 1. Video Ingestion, Vehicle Detection & Tracking | 0/TBD | Not started | - |
| 2. Plate Localization & OCR | 0/TBD | Not started | - |
| 3. Speed Calibration & Violation Detection | 0/TBD | Not started | - |
| 4. Fine Engine, Mock Notifications & Public Portal | 0/TBD | Not started | - |
| 5. End-to-End Demo Integration & Rehearsal | 0/TBD | Not started | - |
