import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource


def main():
    parser = argparse.ArgumentParser(description="Detect and track vehicles in a video.")
    parser.add_argument("video", help="Path to input video")
    parser.add_argument("--output", default=None, help="Path to write annotated output video")
    args = parser.parse_args()

    source = VideoSource(args.video)
    tracker = VehicleTracker()

    writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.output, fourcc, source.fps, (source.width, source.height))

    id_frame_indices = defaultdict(list)
    frame_idx = 0

    for frame in source.frames():
        detections = tracker.track_frame(frame)
        for det in detections:
            id_frame_indices[det.track_id].append(frame_idx)
            color = (0, 255, 0)
            cv2.rectangle(frame, (det.x1, det.y1), (det.x2, det.y2), color, 2)
            label = f"ID {det.track_id} {det.class_name} {det.confidence:.2f}"
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
    print(f"FPS: {source.fps:.2f}, resolution: {source.width}x{source.height}")
    print(f"Unique vehicle track IDs seen: {len(id_frame_indices)}")
    for tid in sorted(id_frame_indices):
        frames_list = id_frame_indices[tid]
        print(
            f"  ID {tid}: {len(frames_list)} frames, "
            f"frame range {frames_list[0]}-{frames_list[-1]}"
        )


if __name__ == "__main__":
    main()
