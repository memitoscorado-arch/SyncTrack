import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cv2

from synctrack.plates import read_plate

image_path = sys.argv[1]
x1, y1, x2, y2 = map(int, sys.argv[2:6])

img = cv2.imread(image_path)
crop = img[y1:y2, x1:x2]

out_path = str(Path(image_path).with_suffix("")) + "_crop.jpg"
cv2.imwrite(out_path, crop)
print("Saved crop to", out_path)

reading = read_plate(crop)
if reading:
    print(f"OCR: raw='{reading.raw_text}' normalized='{reading.normalized_text}' "
          f"conf={reading.confidence:.2f} matches_format={reading.matches_format}")
else:
    print("OCR: no text found")
