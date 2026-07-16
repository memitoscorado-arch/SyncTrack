import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2
import glob

from synctrack.detect import VehicleTracker
from synctrack.ingest import VideoSource

tracker = VehicleTracker()

for video_path in sorted(glob.glob("data/videos/raw/*.MOV")):
    source = VideoSource(video_path)
    best = None  # (height, frame_idx, det)
    frame_idx = 0
    frames_cache = {}
    for frame in source.frames():
        detections = tracker.track_frame(frame)
        for det in detections:
            h = det.y2 - det.y1
            # only care about detections not touching the very bottom edge
            # (would mean the plate itself may be cropped off-frame)
            if det.y2 >= source.height - 5:
                continue
            if best is None or h > best[0]:
                best = (h, frame_idx, det)
                frames_cache = {"frame": frame.copy()}
        frame_idx += 1

    name = Path(video_path).stem
    if best is None:
        print(f"{name}: no valid (non-edge-clipped) detections")
        continue
    h, fidx, det = best
    print(f"{name}: best crop height={h}px at frame {fidx}, track {det.track_id}, "
          f"bbox=({det.x1},{det.y1},{det.x2},{det.y2})")
    crop = frames_cache["frame"][det.y1:det.y2, det.x1:det.x2]
    out_path = f"data/videos/samples/best_{name}.jpg"
    cv2.imwrite(out_path, crop)
    print(f"  saved -> {out_path}")
