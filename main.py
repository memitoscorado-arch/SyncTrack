"""SyncTrack demo entrypoint: optionally process a video end-to-end, then
serve the results in the portal (which also has its own /upload flow).

Usage:
    python main.py                                   # portal only, upload from the web UI
    python main.py data/videos/raw/IMG_8853.MOV       # process a clip first, then serve
"""

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn

from scripts.run_pipeline import run as run_pipeline  # noqa: E402
from synctrack import portal  # noqa: E402


def find_free_port(start=8000, end=8100):
    """Avoid "port already in use" friction during rapid demo debugging --
    just pick the first free port instead of failing/needing a manual kill."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def main():
    parser = argparse.ArgumentParser(description="Run the SyncTrack demo end-to-end.")
    parser.add_argument("video", nargs="?", default=None)
    parser.add_argument("--line1-y", type=int, default=None)
    parser.add_argument("--line2-y", type=int, default=None)
    parser.add_argument("--distance-m", type=float, default=12.0)
    parser.add_argument("--limit-kmh", type=float, default=30.0)
    parser.add_argument("--annotated-output", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="Default: auto-pick a free port")
    parser.add_argument("--seed", action="store_true", help="Preload fines/notifications from a real prior run")
    args = parser.parse_args()

    if args.seed:
        from synctrack.seed import seed_real_results

        seed_real_results()

    if args.video:
        run_pipeline(
            args.video,
            args.line1_y,
            args.line2_y,
            args.distance_m,
            args.limit_kmh,
            args.annotated_output,
        )

    port = args.port if args.port is not None else find_free_port()
    print(f"\nStarting portal at http://{args.host}:{port}\n")
    uvicorn.run(portal.app, host=args.host, port=port)


if __name__ == "__main__":
    main()
