# models/env_segmenter.py

from ultralytics import YOLO
import logging


class EnvSegmenter:
    """
    Environment segmentation wrapper.

    - YOLO 기반 segmentation 모델 로드
    - 도로 / 보행로 등 환경 클래스를 위험·안전 영역으로 분류
    - dummy 모드 지원 (모델 미로드 상태)
    """

    def __init__(self, weights_path=None, device="cpu", dummy=False):
        self.weights_path = weights_path
        self.device = device
        self.dummy = dummy
        self.model = None

        if not dummy:
            self._load_model()
        else:
            logging.warning("EnvSegmenter initialized in DUMMY mode")

    def _load_model(self):
        """Load YOLO segmentation model"""
        self.model = YOLO(self.weights_path)
        self.model.to(self.device)
        logging.info(f"EnvSegmenter loaded: {self.weights_path}")

    def predict(self, image):
        """
        Run environment segmentation.

        Returns:
            {
                "env": {
                    "danger_zones": [...],
                    "safe_zones": [...],
                    "raw_classes": [...]
                }
            }
        """
        if self.model is None:
            return {"env": {}}

        try:
            results = self.model(image, verbose=False)[0]
        except Exception as e:
            logging.error(f"[EnvSegmenter] Inference failed: {e}")
            return {"env": {}}

        if results.boxes is None:
            return {"env": {}}

        # Class name mapping
        names = results.names
        class_ids = results.boxes.cls.cpu().numpy().astype(int)
        classes = [names[i] for i in class_ids]

        # Environment category definitions
        danger_set = {"roadway", "caution_zone"}
        safe_set = {"sidewalk", "braille_guide_blocks"}

        detected = set(classes)

        return {
            "env": {
                "danger_zones": sorted(detected & danger_set),
                "safe_zones": sorted(detected & safe_set),
                "raw_classes": list(detected),
            }
        }
