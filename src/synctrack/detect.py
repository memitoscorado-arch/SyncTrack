from dataclasses import dataclass

from ultralytics import YOLO

# COCO class ids for vehicle-like classes
VEHICLE_CLASS_IDS = [2, 3, 5, 7]  # car, motorcycle, bus, truck
VEHICLE_CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass
class VehicleDetection:
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def centroid(self):
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class VehicleTracker:
    def __init__(self, model_path="yolo11n.pt"):
        self.model = YOLO(model_path)

    def track_frame(self, frame):
        results = self.model.track(
            frame,
            persist=True,
            classes=VEHICLE_CLASS_IDS,
            verbose=False,
        )
        result = results[0]
        detections = []
        if result.boxes is None or result.boxes.id is None:
            return detections

        boxes = result.boxes.xyxy.cpu().numpy()
        track_ids = result.boxes.id.cpu().numpy().astype(int)
        class_ids = result.boxes.cls.cpu().numpy().astype(int)
        confs = result.boxes.conf.cpu().numpy()

        for box, tid, cid, conf in zip(boxes, track_ids, class_ids, confs):
            x1, y1, x2, y2 = box
            detections.append(
                VehicleDetection(
                    track_id=int(tid),
                    class_id=int(cid),
                    class_name=VEHICLE_CLASS_NAMES.get(int(cid), "vehicle"),
                    confidence=float(conf),
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                )
            )
        return detections
