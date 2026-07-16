"""Live-camera streaming pipeline (MJPEG over HTTP).

Source can be a webcam device index (e.g. "0") or a network stream URL
(http/rtsp) -- e.g. an iPhone exposed as an IP camera on the local WiFi via
a webcam-bridging app (Windows doesn't recognize an iPhone as a webcam
natively, so a bridging app on the phone side is required).
"""

from pathlib import Path

import cv2

from synctrack import portal
from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource
from synctrack.notifications import generate_notifications, send_fine_notifications
from synctrack.plates import read_plate
from synctrack.speed import SpeedCalibration, SpeedEstimator

MIN_OCR_CROP_HEIGHT = 200
MAX_OCR_ATTEMPTS_PER_TRACK = 1
EVIDENCE_PADDING_PX = 25


def generate_mjpeg(source, distance_m=12.0, limit_kmh=30.0, line1_y=None, line2_y=None):
    video_source = VideoSource(source)
    l1 = line1_y if line1_y is not None else int(video_source.height * 0.35)
    l2 = line2_y if line2_y is not None else int(video_source.height * 0.75)

    cal = SpeedCalibration(line1_y=l1, line2_y=l2, distance_m=distance_m, fps=video_source.fps)
    estimator = SpeedEstimator(cal)
    tracker = VehicleTracker()

    best_plate_per_track = {}
    ocr_attempts = {}
    fined_tracks = set()
    frame_idx = 0

    for frame in video_source.frames():
        cv2.line(frame, (0, l1), (video_source.width, l1), (255, 0, 0), 1)
        cv2.line(frame, (0, l2), (video_source.width, l2), (255, 0, 0), 1)

        detections = tracker.track_frame(frame)
        for det in detections:
            _, cy = det.centroid
            speed = estimator.update(det.track_id, cy, frame_idx)

            crop_height = det.y2 - det.y1
            existing_plate = best_plate_per_track.get(det.track_id)
            attempts = ocr_attempts.get(det.track_id, 0)
            if (
                crop_height >= MIN_OCR_CROP_HEIGHT
                and attempts < MAX_OCR_ATTEMPTS_PER_TRACK
                and (existing_plate is None or not existing_plate.matches_format)
            ):
                ocr_attempts[det.track_id] = attempts + 1
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
                        evidence_filename = f"live_track{det.track_id}_frame{frame_idx}.jpg"
                        evidence_full_path = portal.EVIDENCE_DIR / evidence_filename
                        ex1 = max(det.x1 - EVIDENCE_PADDING_PX, 0)
                        ey1 = max(det.y1 - EVIDENCE_PADDING_PX, 0)
                        ex2 = min(det.x2 + EVIDENCE_PADDING_PX, video_source.width)
                        ey2 = min(det.y2 + EVIDENCE_PADDING_PX, video_source.height)
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

        ok, jpeg = cv2.imencode(".jpg", frame)
        if ok:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        frame_idx += 1
