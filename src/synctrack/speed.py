"""Two-line (VASCAR-style) speed estimation.

Given two horizontal reference lines in the frame and the real-world
distance between them (measured/estimated against the actual filmed
street — e.g. lane-marking length, or a Google Maps distance check), a
vehicle's speed is computed from the elapsed time between crossing line 1
and crossing line 2, using the video's own frame rate as the clock.

This only needs to be accurate in the local region between the two lines
(not a full-frame perspective transform), which is why it works without
camera calibration hardware.
"""

from dataclasses import dataclass, field


@dataclass
class SpeedCalibration:
    line1_y: int
    line2_y: int
    distance_m: float
    fps: float

    def __post_init__(self):
        if self.line1_y == self.line2_y:
            raise ValueError("line1_y and line2_y must differ")
        # Direction of travel: line1 is crossed first if vehicles move
        # top -> bottom (increasing y) in this camera's framing.
        self.moving_down = self.line2_y > self.line1_y


@dataclass
class TrackCrossing:
    track_id: int
    line1_frame: float | None = None
    line2_frame: float | None = None


class SpeedEstimator:
    """Tracks centroid crossings of two calibration lines per track_id."""

    def __init__(self, calibration: SpeedCalibration):
        self.cal = calibration
        self._crossings: dict[int, TrackCrossing] = {}
        self._last_y: dict[int, float] = {}
        self._last_frame: dict[int, int] = {}

    def update(self, track_id, centroid_y, frame_idx):
        """Feed one frame's centroid position for a track. Returns speed_kmh
        the moment both crossings are known, else None."""
        crossing = self._crossings.setdefault(track_id, TrackCrossing(track_id))
        prev_y = self._last_y.get(track_id)
        prev_frame = self._last_frame.get(track_id)

        if prev_y is not None:
            crossing.line1_frame = crossing.line1_frame or self._interp_cross(
                prev_y, centroid_y, prev_frame, frame_idx, self.cal.line1_y
            )
            crossing.line2_frame = crossing.line2_frame or self._interp_cross(
                prev_y, centroid_y, prev_frame, frame_idx, self.cal.line2_y
            )

        self._last_y[track_id] = centroid_y
        self._last_frame[track_id] = frame_idx

        if crossing.line1_frame is not None and crossing.line2_frame is not None:
            elapsed_frames = abs(crossing.line2_frame - crossing.line1_frame)
            if elapsed_frames == 0:
                return None
            elapsed_s = elapsed_frames / self.cal.fps
            speed_m_s = self.cal.distance_m / elapsed_s
            return speed_m_s * 3.6
        return None

    @staticmethod
    def _interp_cross(prev_y, curr_y, prev_frame, curr_frame, line_y):
        """Return the (fractional) frame index where the segment prev->curr
        crosses line_y, or None if it doesn't cross this step."""
        if prev_y is None or prev_frame is None:
            return None
        if (prev_y - line_y) * (curr_y - line_y) > 0:
            return None  # both same side, no crossing
        if curr_y == prev_y:
            return None
        t = (line_y - prev_y) / (curr_y - prev_y)
        return prev_frame + t * (curr_frame - prev_frame)
