from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from synctrack.fines import FineRegistry
from synctrack.notifications import MockNotification

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = BASE_DIR / "data" / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SyncTrack - Portal SIMULADO de Multas de Transito")
# NOTE: FastAPI's own Jinja2Templates wrapper hits a real bug with this
# environment's Starlette/Jinja2 versions (TypeError: unhashable type: dict
# inside its template cache) -- using plain Jinja2 directly sidesteps it.
_jinja_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")

# In-memory store, shared for the life of one demo run (see STACK.md rationale).
registry = FineRegistry()
notifications_log: list[MockNotification] = []


@app.get("/", response_class=HTMLResponse)
def index():
    template = _jinja_env.get_template("index.html")
    html = template.render(
        fines=list(reversed(registry.fines)),
        notifications=list(reversed(notifications_log)),
    )
    return HTMLResponse(html)


@app.get("/api/fines")
def api_fines():
    return [fine.__dict__ for fine in registry.fines]
