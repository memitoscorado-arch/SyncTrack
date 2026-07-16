"""End-to-end pipeline: video -> detect/track -> plate OCR -> speed ->
fine -> mock notification -> in-memory portal store.

Run this, then `python main.py --serve-only` (or just run main.py directly)
to view results in the portal.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from synctrack import portal
from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource
from synctrack.notifications import generate_notifications, send_fine_notifications
from synctrack.plates import read_plate
from synctrack.speed import SpeedCalibration, SpeedEstimator

MIN_OCR_CROP_HEIGHT = 200
MAX_OCR_ATTEMPTS_PER_TRACK = 3  # OCR is the slowest step; don't retry every frame
EVIDENCE_PADDING_PX = 25  # extra margin around the vehicle bbox for a clearer evidence photo


def run(video_path, line1_y=None, line2_y=None, distance_m=12.0, limit_kmh=30.0, output=None):
    source = VideoSource(video_path)
    line1_y = line1_y if line1_y is not None else int(source.height * 0.35)
    line2_y = line2_y if line2_y is not None else int(source.height * 0.75)

    cal = SpeedCalibration(line1_y=line1_y, line2_y=line2_y, distance_m=distance_m, fps=source.fps)
    speed_estimator = SpeedEstimator(cal)
    tracker = VehicleTracker()

    writer = None
    if output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output, fourcc, source.fps, (source.width, source.height))

    best_plate_per_track = {}
    ocr_attempts_per_track = {}
    fined_tracks = set()
    frame_idx = 0

    for frame in source.frames():
        cv2.line(frame, (0, line1_y), (source.width, line1_y), (255, 0, 0), 1)
        cv2.line(frame, (0, line2_y), (source.width, line2_y), (255, 0, 0), 1)

        detections = tracker.track_frame(frame)
        for det in detections:
            _, cy = det.centroid
            speed = speed_estimator.update(det.track_id, cy, frame_idx)

            crop_height = det.y2 - det.y1
            existing_plate = best_plate_per_track.get(det.track_id)
            attempts = ocr_attempts_per_track.get(det.track_id, 0)
            if (
                crop_height >= MIN_OCR_CROP_HEIGHT
                and attempts < MAX_OCR_ATTEMPTS_PER_TRACK
                and (existing_plate is None or not existing_plate.matches_format)
            ):
                ocr_attempts_per_track[det.track_id] = attempts + 1
                crop = frame[det.y1 : det.y2, det.x1 : det.x2]
                reading = read_plate(crop)
                if reading and (existing_plate is None or reading.confidence > existing_plate.confidence):
                    best_plate_per_track[det.track_id] = reading
                    existing_plate = reading

            plate_text = existing_plate.normalized_text if existing_plate else "?"
            label = f"ID {det.track_id} {plate_text}"
            color = (0, 255, 0)

            if speed is not None:
                label += f" {speed:.0f}km/h"
                if speed > limit_kmh:
                    color = (0, 0, 255)
                    if det.track_id not in fined_tracks:
                        fined_tracks.add(det.track_id)
                        evidence_filename = (
                            f"{Path(video_path).stem}_track{det.track_id}_frame{frame_idx}.jpg"
                        )
                        evidence_full_path = portal.EVIDENCE_DIR / evidence_filename
                        ex1 = max(det.x1 - EVIDENCE_PADDING_PX, 0)
                        ey1 = max(det.y1 - EVIDENCE_PADDING_PX, 0)
                        ex2 = min(det.x2 + EVIDENCE_PADDING_PX, source.width)
                        ey2 = min(det.y2 + EVIDENCE_PADDING_PX, source.height)
                        cv2.imwrite(str(evidence_full_path), frame[ey1:ey2, ex1:ex2])
                        fine = portal.registry.register(
                            plate=plate_text,
                            speed_kmh=speed,
                            limit_kmh=limit_kmh,
                            evidence_path=evidence_filename,
                            track_id=det.track_id,
                        )
                        notifications = generate_notifications(fine)
                        portal.notifications_log.extend(notifications)
                        send_fine_notifications(fine, notifications, evidence_full_path)
                        print(
                            f"FINE registered: track {det.track_id}, plate {plate_text}, "
                            f"{speed:.1f} km/h > {limit_kmh} km/h limit"
                        )

            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            cv2.putText(
                frame,
                label,
                (det.x1, max(det.y1 - 8, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        if writer:
            writer.write(frame)
        frame_idx += 1

    if writer:
        writer.release()

    print(f"Done. {frame_idx} frames processed, {len(fined_tracks)} fine(s) generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the full SyncTrack pipeline on a video.")
    parser.add_argument("video")
    parser.add_argument("--line1-y", type=int, default=None)
    parser.add_argument("--line2-y", type=int, default=None)
    parser.add_argument("--distance-m", type=float, default=12.0)
    parser.add_argument("--limit-kmh", type=float, default=30.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    run(args.video, args.line1_y, args.line2_y, args.distance_m, args.limit_kmh, args.output)
