import re
from dataclasses import dataclass

import cv2
import easyocr

# Guatemalan plates (post-2021, Mercosur-style): 1 letter + 3 digits + 3 letters,
# e.g. P123ABC. Kept loose (0/O, 1/I confusions) since OCR misreads are expected
# under motion blur / glare in real street footage.
PLATE_REGEX = re.compile(r"^[A-Z][0-9O]{3}[A-Z]{3}$")

_READER = None


def get_reader():
    global _READER
    if _READER is None:
        _READER = easyocr.Reader(["en"], gpu=False)
    return _READER


def normalize_plate_text(text):
    text = text.upper()
    return re.sub(r"[^A-Z0-9]", "", text)


@dataclass
class PlateReading:
    raw_text: str
    normalized_text: str
    confidence: float
    matches_format: bool


def _preprocess_variants(crop):
    """Yield a few upscaled/denoised variants of a plate crop.

    Real street footage plates are often only a few pixels tall — a single
    fixed preprocessing rarely works, so we try a couple of scales and keep
    whichever OCR reading scores highest. Cheap relative to a live demo,
    since crops are small.
    """
    for scale in (2, 4):
        up = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 50, 50)
        yield up
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield otsu


def read_plate(crop):
    """Run OCR on a vehicle crop and return the best plate reading, if any."""
    if crop.size == 0:
        return None

    reader = get_reader()
    readings = []

    for variant in _preprocess_variants(crop):
        results = reader.readtext(
            variant,
            low_text=0.3,
            text_threshold=0.4,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        )
        for _, text, conf in results:
            normalized = normalize_plate_text(text)
            if not normalized:
                continue
            readings.append(
                PlateReading(
                    raw_text=text,
                    normalized_text=normalized,
                    confidence=float(conf),
                    matches_format=bool(PLATE_REGEX.match(normalized)),
                )
            )

    if not readings:
        return None

    matching = [r for r in readings if r.matches_format]
    if matching:
        return max(matching, key=lambda r: r.confidence)
    return max(readings, key=lambda r: r.confidence)
