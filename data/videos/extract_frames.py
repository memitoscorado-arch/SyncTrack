import cv2
import os
import sys

video = sys.argv[1]
out_dir = sys.argv[2]
n_frames = int(sys.argv[3]) if len(sys.argv) > 3 else 6

os.makedirs(out_dir, exist_ok=True)
cap = cv2.VideoCapture(video)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
name = os.path.splitext(os.path.basename(video))[0]

for i in range(n_frames):
    frame_idx = int(total * i / n_frames)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    if not ok:
        continue
    out_path = os.path.join(out_dir, f"{name}_f{frame_idx:04d}.jpg")
    cv2.imwrite(out_path, frame)
    print(out_path)

cap.release()
