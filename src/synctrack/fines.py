from dataclasses import dataclass
from datetime import datetime

FINE_AMOUNT_GTQ = 500.0  # placeholder simulated fine amount


@dataclass
class Fine:
    id: int
    plate: str
    speed_kmh: float
    limit_kmh: float
    timestamp: str
    evidence_path: str
    track_id: int
    fine_amount_gtq: float = FINE_AMOUNT_GTQ


class FineRegistry:
    def __init__(self):
        self.fines: list[Fine] = []
        self._next_id = 1

    def register(self, plate, speed_kmh, limit_kmh, evidence_path, track_id):
        fine = Fine(
            id=self._next_id,
            plate=plate,
            speed_kmh=speed_kmh,
            limit_kmh=limit_kmh,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            evidence_path=evidence_path,
            track_id=track_id,
        )
        self._next_id += 1
        self.fines.append(fine)
        return fine
