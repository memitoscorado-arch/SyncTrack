from pathlib import Path

import cv2


def resolve_source(source):
    """A source is either a file path, a webcam device index (int, or a
    string like "0"), or a stream URL (http/rtsp -- e.g. an iPhone exposed
    as an IP camera on the local WiFi via a webcam-bridging app)."""
    if isinstance(source, int):
        return source
    s = str(source)
    if s.isdigit():
        return int(s)
    return s


class VideoSource:
    def __init__(self, source):
        resolved = resolve_source(source)
        self.path = resolved if isinstance(resolved, int) else Path(resolved)
        self.is_live = isinstance(resolved, int) or str(resolved).startswith(("http://", "https://", "rtsp://"))
        self.cap = cv2.VideoCapture(resolved)
        if not self.cap.isOpened():
            raise IOError(f"Could not open video source: {source}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def frames(self):
        while True:
            ok, frame = self.cap.read()
            if not ok:
                break
            yield frame
        self.cap.release()

    def close(self):
        self.cap.release()
