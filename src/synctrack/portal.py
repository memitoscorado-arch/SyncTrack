import shutil
import sys
import urllib.parse
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from synctrack.fines import FineRegistry
from synctrack.notifications import MockNotification

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = BASE_DIR / "data" / "evidence"
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

app = FastAPI(title="SyncTrack - Portal SIMULADO de Multas de Transito")
# NOTE: FastAPI's own Jinja2Templates wrapper hits a real bug with this
# environment's Starlette/Jinja2 versions (TypeError: unhashable type: dict
# inside its template cache) -- using plain Jinja2 directly sidesteps it.
_jinja_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# In-memory store, shared for the life of one demo run (see STACK.md rationale).
registry = FineRegistry()
notifications_log: list[MockNotification] = []
last_video_url = None
processing_status = None


@app.get("/", response_class=HTMLResponse)
def index():
    template = _jinja_env.get_template("index.html")
    html = template.render(
        fines=list(reversed(registry.fines)),
        notifications=list(reversed(notifications_log)),
        video_url=last_video_url,
        processing_status=processing_status,
    )
    return HTMLResponse(html)


@app.get("/api/fines")
def api_fines():
    return [fine.__dict__ for fine in registry.fines]


@app.post("/upload")
async def upload_video(file: UploadFile = File(...), limit_kmh: float = Form(30.0)):
    """Accept an uploaded clip, save it, then point the "Camara del
    corredor" preview at the SAME annotated MJPEG stream used for the live
    camera (/live) -- one single pass draws the boxes/lines/speed/plate AND
    registers fines, instead of processing the file twice."""
    global last_video_url, processing_status

    dest = UPLOAD_DIR / file.filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    source_param = urllib.parse.quote(str(dest), safe="")
    last_video_url = f"/live?source={source_param}&limit_kmh={limit_kmh}"
    processing_status = "en vivo (procesando este video)"

    return RedirectResponse(url="/", status_code=303)


@app.get("/live-view", response_class=HTMLResponse)
def live_view(source: str = "0", limit_kmh: float = 30.0, distance_m: float = 12.0):
    """A camera source (webcam device index, or an http/rtsp URL -- e.g. an
    iPhone exposed as an IP camera via a webcam-bridging app) streamed and
    processed frame-by-frame in real time, MJPEG over HTTP."""
    return HTMLResponse(f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>SyncTrack - EN VIVO</title>
<style>
  body {{ margin:0; background:#0b0b0b; font-family: Arial, sans-serif; }}
  .bar {{ color:white; padding:10px 16px; display:flex; gap:16px; align-items:center; }}
  .bar a {{ color:#7dd3fc; }}
  .dot {{ width:10px; height:10px; border-radius:50%; background:#ef4444; display:inline-block;
          animation: pulse 1.2s infinite; margin-right:6px; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.3; }} }}
  img {{ width:100%; display:block; }}
</style></head>
<body>
  <div class="bar"><span class="dot"></span> EN VIVO -- fuente: {source} | limite: {limit_kmh} km/h
    <a href="/">&larr; volver al portal</a></div>
  <img src="/live?source={source}&limit_kmh={limit_kmh}&distance_m={distance_m}">
</body></html>""")


@app.get("/live")
def live_stream(source: str = "0", limit_kmh: float = 30.0, distance_m: float = 12.0):
    from synctrack.live import generate_mjpeg

    return StreamingResponse(
        generate_mjpeg(source, distance_m=distance_m, limit_kmh=limit_kmh),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
