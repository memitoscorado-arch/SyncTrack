"""Estimate vehicle speed using a two-line pixel/time crossing method.

CALIBRATION NOTE: --distance-m is the real-world distance between the two
horizontal reference lines (--line1-y / --line2-y), measured against the
actual filmed street (e.g. via a Google Maps distance check between two
visible landmarks, or by counting a known number of lane-dash cycles).
The default below is an urban-lane-marking approximation, NOT a verified
on-site measurement -- absolute speed values are only as accurate as this
number. Verify it against the real street before trusting exact km/h in
the live demo; the crossing-detection logic itself is independent of it
and can be sanity-checked by confirming speeds stay in a physically
plausible range for a city street.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource
from synctrack.speed import SpeedCalibration, SpeedEstimator


def main():
    parser = argparse.ArgumentParser(description="Estimate vehicle speed via two-line crossing.")
    parser.add_argument("video")
    parser.add_argument("--line1-y", type=int, default=None, help="Default: 35%% of frame height")
    parser.add_argument("--line2-y", type=int, default=None, help="Default: 75%% of frame height")
    parser.add_argument(
        "--distance-m",
        type=float,
        default=12.0,
        help="Real-world distance between the two lines (default: 12m approximation)",
    )
    parser.add_argument("--limit-kmh", type=float, default=40.0, help="Speed limit for this street segment")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    source = VideoSource(args.video)
    line1_y = args.line1_y if args.line1_y is not None else int(source.height * 0.35)
    line2_y = args.line2_y if args.line2_y is not None else int(source.height * 0.75)

    cal = SpeedCalibration(line1_y=line1_y, line2_y=line2_y, distance_m=args.distance_m, fps=source.fps)
    estimator = SpeedEstimator(cal)
    tracker = VehicleTracker()

    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, source.fps, (source.width, source.height))

    speeds = {}
    frame_idx = 0

    for frame in source.frames():
        cv2.line(frame, (0, line1_y), (source.width, line1_y), (255, 0, 0), 2)
        cv2.line(frame, (0, line2_y), (source.width, line2_y), (255, 0, 0), 2)

        detections = tracker.track_frame(frame)
        for det in detections:
            cx, cy = det.centroid
            speed = estimator.update(det.track_id, cy, frame_idx)
            if speed is not None and det.track_id not in speeds:
                speeds[det.track_id] = speed

            known_speed = speeds.get(det.track_id)
            violation = known_speed is not None and known_speed > args.limit_kmh
            color = (0, 0, 255) if violation else (0, 255, 0)
            label = f"ID {det.track_id}"
            if known_speed is not None:
                label += f" {known_speed:.0f} km/h" + (" VIOLATION" if violation else "")

            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            cv2.putText(
                frame,
                label,
                (det.x1, max(det.y1 - 8, 0)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

        if writer:
            writer.write(frame)
        frame_idx += 1

    if writer:
        writer.release()

    print(f"Processed {frame_idx} frames from {args.video}")
    print(f"Calibration: line1_y={line1_y}, line2_y={line2_y}, distance={args.distance_m}m, fps={source.fps:.2f}")
    print(f"Speed limit: {args.limit_kmh} km/h")
    print(f"Vehicles with computed speed: {len(speeds)}")
    for tid in sorted(speeds):
        v = speeds[tid]
        flag = "VIOLATION" if v > args.limit_kmh else "ok"
        print(f"  ID {tid}: {v:.1f} km/h [{flag}]")


if __name__ == "__main__":
    main()
