import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource
from synctrack.plates import read_plate

# Below this crop height, plates are usually too small to read reliably —
# skip OCR entirely to save time on distant vehicles. Confirmed empirically:
# vehicles need to be quite close (large bbox) before plate text is legible
# at all in this footage (elevated, distant camera angle).
MIN_CROP_HEIGHT = 200


def main():
    parser = argparse.ArgumentParser(description="Detect vehicles and read their plates.")
    parser.add_argument("video")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    source = VideoSource(args.video)
    tracker = VehicleTracker()

    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, source.fps, (source.width, source.height))

    best_plate_per_track = {}
    frame_idx = 0

    for frame in source.frames():
        detections = tracker.track_frame(frame)
        for det in detections:
            crop = frame[det.y1 : det.y2, det.x1 : det.x2]
            crop_height = det.y2 - det.y1
            existing = best_plate_per_track.get(det.track_id)

            should_try = crop_height >= MIN_CROP_HEIGHT and (
                existing is None or not existing.matches_format
            )
            if should_try:
                reading = read_plate(crop)
                if reading and (existing is None or reading.confidence > existing.confidence):
                    best_plate_per_track[det.track_id] = reading
                    existing = reading

            label = f"ID {det.track_id} {det.class_name}"
            if existing:
                tag = "OK" if existing.matches_format else "?"
                label += f" [{existing.normalized_text} {tag} {existing.confidence:.2f}]"

            color = (0, 255, 0) if (existing and existing.matches_format) else (0, 200, 255)
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

    print(f"Processed {frame_idx} frames from {args.video}")
    print(f"Plates read for {len(best_plate_per_track)} tracked vehicles:")
    for tid in sorted(best_plate_per_track):
        r = best_plate_per_track[tid]
        status = "MATCHES FORMAT" if r.matches_format else "no format match"
        print(f"  ID {tid}: '{r.normalized_text}' (raw='{r.raw_text}', conf={r.confidence:.2f}, {status})")


if __name__ == "__main__":
    main()
