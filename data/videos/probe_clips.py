import cv2
import glob
import os

for path in sorted(glob.glob("data/videos/raw/*.MOV")):
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"{os.path.basename(path)}: FAILED TO OPEN")
        continue
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    duration = frame_count / fps if fps else 0
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"{os.path.basename(path)}: {int(width)}x{int(height)} @ {fps:.2f}fps, "
          f"{frame_count:.0f} frames, ~{duration:.1f}s, codec={codec}, {size_mb:.1f}MB")
    cap.release()
