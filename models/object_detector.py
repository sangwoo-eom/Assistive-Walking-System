# models/object_detector.py

from ultralytics import YOLO
import logging
import numpy as np


class ObjectDetector:
    def __init__(self, weights_path=None, device="cpu", dummy=False, tracking=False):
        self.weights_path = weights_path
        self.device = device
        self.dummy = dummy
        self.tracking = tracking
        self.model = None

        if not dummy:
            self._load_model()
        else:
            logging.warning("ObjectDetector running in dummy mode")

    def _load_model(self):
        self.model = YOLO(self.weights_path)
        self.model.to(self.device)
        logging.info(f"Object detector loaded: {self.weights_path}")

    def predict(self, image_bgr: np.ndarray, track=False):
        if self.dummy:
            return {"objects": []}

        try:
            if track or self.tracking:
                results = self.model.track(
                    image_bgr,
                    persist=True,
                    verbose=False
                )[0]
            else:
                results = self.model(
                    image_bgr,
                    verbose=False
                )[0]
        except Exception as e:
            logging.error(f"[ObjectDetector] inference error: {e}")
            return {"objects": []}

        objects = []

        if results.boxes is None:
            return {"objects": []}

        for box in results.boxes:
            try:
                cls_id = int(box.cls[0])
                cls_name = results.names[cls_id]
                score = float(box.conf[0])
                bbox = box.xyxy[0].tolist()
            except Exception:
                continue

            # Tracking ID (if enabled)
            track_id = None
            if self.tracking or track:
                try:
                    if box.id is not None:
                        track_id = int(box.id[0])
                except Exception:
                    track_id = None

            objects.append({
                "id": track_id,
                "class": cls_name,
                "score": score,
                "bbox": bbox
            })

        return {"objects": objects}
