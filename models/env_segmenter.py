# models/env_segmenter.py

from ultralytics import YOLO
import logging


class EnvSegmenter:
    def __init__(self, weights_path=None, device="cpu", dummy=False):
        self.weights_path = weights_path
        self.device = device
        self.dummy = dummy
        self.model = None

        if not dummy:
            self._load_model()
        else:
            logging.warning("EnvSegmenter running in DUMMY mode")

    def _load_model(self):
        self.model = YOLO(self.weights_path)
        self.model.to(self.device)
        logging.info(f"✅ EnvSegmenter loaded: {self.weights_path}")

    def predict(self, image):
        if self.model is None:
            return {"env": {}}

        try:
            results = self.model(image, verbose=False)[0]
        except Exception as e:
            logging.error(f"[EnvSegmenter] inference error: {e}")
            return {"env": {}}

        if results.boxes is None:
            return {"env": {}}

        names = results.names
        class_ids = results.boxes.cls.cpu().numpy().astype(int)
        classes = [names[i] for i in class_ids]

        # 환경 종류
        danger_set = {"roadway", "caution_zone"}
        safe_set = {"sidewalk", "braille_guide_blocks"}

        detected = set(classes)

        return {
            "env": {
                "danger_zones": sorted(list(detected & danger_set)),
                "safe_zones": sorted(list(detected & safe_set)),
                "raw_classes": list(detected)
            }
        }
