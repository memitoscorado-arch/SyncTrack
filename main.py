"""SyncTrack demo entrypoint: process a video end-to-end, then serve the
results in the portal.

Usage:
    python main.py data/videos/raw/IMG_8853.MOV --limit-kmh 30
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn

from scripts.run_pipeline import run as run_pipeline  # noqa: E402
from synctrack import portal  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Run the SyncTrack demo end-to-end.")
    parser.add_argument("video")
    parser.add_argument("--line1-y", type=int, default=None)
    parser.add_argument("--line2-y", type=int, default=None)
    parser.add_argument("--distance-m", type=float, default=12.0)
    parser.add_argument("--limit-kmh", type=float, default=30.0)
    parser.add_argument("--annotated-output", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--serve-only", action="store_true", help="Skip processing, just serve current results")
    args = parser.parse_args()

    if not args.serve_only:
        run_pipeline(
            args.video,
            args.line1_y,
            args.line2_y,
            args.distance_m,
            args.limit_kmh,
            args.annotated_output,
        )

    print(f"\nStarting portal at http://{args.host}:{args.port}\n")
    uvicorn.run(portal.app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
