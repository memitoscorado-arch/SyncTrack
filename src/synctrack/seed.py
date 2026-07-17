"""Optional preload of REAL results from a completed IMG_8850.MOV run, so
the portal's fines/notifications table isn't empty right after a restart
while waiting for a fresh video to process. Not fabricated data -- these
are the actual detections/speeds from an earlier real pipeline run.
Runtime-only (never written to a file, never committed).
"""

import shutil
import urllib.parse
from pathlib import Path

from synctrack import portal
from synctrack.notifications import generate_notifications

# (track_id, plate, speed_kmh, evidence_filename) -- from the real IMG_8850.MOV run
REAL_RESULTS = [
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


def seed_real_results():
    for track_id, plate, speed, evidence_filename in REAL_RESULTS:
        fine = portal.registry.register(
            plate=plate,
            speed_kmh=speed,
            limit_kmh=LIMIT_KMH,
            evidence_path=evidence_filename,
            track_id=track_id,
        )
        portal.notifications_log.extend(generate_notifications(fine))

    if DEMO_VIDEO_SRC.exists():
        dest = portal.UPLOAD_DIR / DEMO_VIDEO_SRC.name
        shutil.copy(DEMO_VIDEO_SRC, dest)
        source_param = urllib.parse.quote(str(dest), safe="")
        portal.last_video_url = f"/replay?path={source_param}"
        portal.last_download_path = str(dest)
        portal.processing_status = "completado"
        portal.progress["done"] = True
