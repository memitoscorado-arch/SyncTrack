"""Starts the REAL portal (same UI as 8001/8002) on a new port, pre-loaded
with the fines/notifications already produced by an earlier full run on
IMG_8850.MOV -- for a fast, reliable demo that still uses the normal
interface, without waiting for live reprocessing.
"""

import shutil
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

from main import find_free_port  # noqa: E402
from synctrack import portal  # noqa: E402
from synctrack.notifications import generate_notifications  # noqa: E402

# (track_id, plate, speed_kmh, evidence_filename) -- from the real IMG_8850.MOV run
RESULTS = [
    (2, "3", 41.6, "IMG_8850_track2_frame121.jpg"),
    (1, "?", 52.6, "IMG_8850_track1_frame132.jpg"),
    (7, "3", 44.5, "IMG_8850_track7_frame150.jpg"),
    (8, "1", 42.7, "IMG_8850_track8_frame165.jpg"),
    (9, "23", 39.0, "IMG_8850_track9_frame267.jpg"),
    (10, "M", 50.7, "IMG_8850_track10_frame270.jpg"),
    (11, "DIB", 35.1, "IMG_8850_track11_frame358.jpg"),
    (15, "?", 51.8, "IMG_8850_track15_frame427.jpg"),
    (14, "S", 35.7, "IMG_8850_track14_frame437.jpg"),
    (12, "LU", 33.9, "IMG_8850_track12_frame466.jpg"),
    (17, "?", 41.9, "IMG_8850_track17_frame496.jpg"),
    (16, "2", 27.1, "IMG_8850_track16_frame591.jpg"),
]
LIMIT_KMH = 25.0
DEMO_VIDEO_SRC = Path(r"C:\Users\usuario\Downloads\IMG_8850_deteccion.mp4")


def preload():
    # Evidence photos already exist in portal.EVIDENCE_DIR from that run.
    for track_id, plate, speed, evidence_filename in RESULTS:
        fine = portal.registry.register(
            plate=plate,
            speed_kmh=speed,
            limit_kmh=LIMIT_KMH,
            evidence_path=evidence_filename,
            track_id=track_id,
        )
        portal.notifications_log.extend(generate_notifications(fine))

    dest = portal.UPLOAD_DIR / DEMO_VIDEO_SRC.name
    shutil.copy(DEMO_VIDEO_SRC, dest)
    source_param = urllib.parse.quote(str(dest), safe="")
    portal.last_video_url = f"/replay?path={source_param}"
    portal.processing_status = "completado"


if __name__ == "__main__":
    preload()
    port = find_free_port()
    print(f"\nPortal (precargado) en http://127.0.0.1:{port}\n")
    uvicorn.run(portal.app, host="127.0.0.1", port=port)
