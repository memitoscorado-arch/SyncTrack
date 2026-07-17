"""Standalone demo server: serves an ALREADY-PROCESSED annotated video
instantly (no live reprocessing lag) -- for showing "how the project works"
quickly and reliably, separate from the live/upload ports (8001/8002).
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from main import find_free_port  # noqa: E402

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
DEMO_VIDEO_NAME = "IMG_8850_deteccion.mp4"
DEMO_VIDEO_PATH = DEMO_DIR / DEMO_VIDEO_NAME
shutil.copy(r"C:\Users\usuario\Downloads\IMG_8850_deteccion.mp4", DEMO_VIDEO_PATH)

app = FastAPI(title="SyncTrack - Demo (video ya procesado)")


def replay_mjpeg(path, loop=True):
    """Re-stream an already-annotated video file as MJPEG. Browsers can't
    reliably play the mp4v codec OpenCV writes directly in a <video> tag,
    but a plain JPEG-per-frame stream (like the live camera view) always
    works -- no re-processing here, just reading and re-encoding frames."""
    while True:
        cap = cv2.VideoCapture(str(path))
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            ok2, jpeg = cv2.imencode(".jpg", frame)
            if ok2:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        cap.release()
        if not loop:
            break


@app.get("/demo-stream")
def demo_stream():
    return StreamingResponse(
        replay_mjpeg(DEMO_VIDEO_PATH),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

PAGE = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>SyncTrack - Demo</title>
<style>
  body {{ font-family: Arial, sans-serif; background:#f2f2f2; margin:0; }}
  .disclaimer {{ background:#fde68a; color:#7c4a03; text-align:center; font-weight:bold; padding:10px; }}
  header {{ background:#14213d; color:white; padding:20px 24px; }}
  main {{ max-width:700px; margin:24px auto; padding:0 16px; }}
  section {{ background:white; border-radius:8px; padding:16px 20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,.1); }}
  video {{ width:100%; border-radius:6px; background:#000; }}
  form {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
  button {{ background:#14213d; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; }}
</style></head>
<body>
<div class="disclaimer">SIMULADO — Prototipo de hackathon. No es un sistema oficial de multas.</div>
<header><h1>SyncTrack</h1><p>Demo -- video ya procesado (deteccion, velocidad, placa, lineas de calibracion)</p></header>
<main>
<section>
  <h2>Cargar video</h2>
  <form action="/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="file" accept="video/*" required>
    <button type="submit">Analizar (demo)</button>
  </form>
  <p><small>Para esta demo, el resultado mostrado es un analisis ya completado
  (mismo pipeline: YOLO + tracking + OCR + velocidad + multa), para evitar la
  espera del procesamiento en vivo.</small></p>
</section>
<section>
  <h2>Resultado</h2>
  <img src="/demo-stream" style="width:100%;border-radius:6px;background:#000">
</section>
</main>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(PAGE)


@app.post("/upload", response_class=HTMLResponse)
async def upload(file: UploadFile = File(...)):
    return HTMLResponse(PAGE)


if __name__ == "__main__":
    port = find_free_port()
    print(f"\nDemo server at http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
