# models — AI Inference Wrappers

이 디렉토리는 **학습된 AI 모델을 서비스 코드에서 직접 사용할 수 있도록 감싸는 Wrapper 모듈**입니다.  
YOLO 기반 객체 인식 모델과 환경 인식(Segmentation) 모델을 추상화하여,
core 로직과 모델 구현을 분리하는 역할을 합니다.

---

## 📂 Directory Structure

models/
├── object_detector.py
├── env_segmenter.py
└── init.py

---

## 1️⃣ object_detector.py — Object Detection Wrapper

YOLO 기반 객체 탐지 모델을 감싸는 클래스입니다.

### 주요 역할
- 객체 탐지 수행
- Bounding box, confidence, class name 추출
- 객체 추적 ID 관리 (Tracking)
- 서비스 코드에 친화적인 JSON 형태로 결과 제공

---

### ✅ Class: ObjectDetector

ObjectDetector(weights_path, device="cpu", dummy=False, tracking=False)

초기화 옵션
파라미터	               설명
weights_path	          YOLO 가중치 경로
device	                  "cpu" / "cuda"
dummy	                  True일 경우 더미 모드
tracking	              True일 경우 YOLO Track 모드 활성화

주요 메서드
predict(image, track=False)
YOLO 추론 수행 및 결과 반환.

반환 형식
{
  "objects": [
    {
      "id": 3,
      "class": "car",
      "score": 0.91,
      "bbox": [x1, y1, x2, y2]
    },
    ...
  ]
}

특징
- YOLO native API 직접 노출하지 않음
- tracking 활성화 시 ID 자동 관리
- 서비스 코드와 독립적인 구조
- 장애 발생 시 빈 결과 반환
- Dummy 모드 지원 (모델 미사용 상태에서도 서버 테스트 가능)

2️⃣ env_segmenter.py — Environment Segmentation Wrapper

보행 환경 인식 모델 (도로, 인도 등)용 Wrapper 클래스입니다.

✅ Class: EnvSegmenter

EnvSegmenter(weights_path, device="cpu", dummy=False)

주요 기능
- Segmentation 모델 로드
- 감지된 클래스 분석
- 위험 구역 / 안전 구역 분류
- 추론 결과를 단순화된 info dict 형태로 제공

{
  "env": {
    "danger_zones": ["roadway"],
    "safe_zones": ["sidewalk"],
    "raw_classes": ["roadway", "sidewalk"]
  }
}

환경 분류 기준

구분	클래스
위험	roadway, caution_zone
안전	sidewalk, braille_guide_blocks

특징
- Segmentation 결과를 논리적 판단용 형태로 변환
- YOLO 결과 구조 은닉
- 빈 결과 fallback 처리
- Dummy 모드 지원

🎯 Design Philosophy

✅ Core에서 모델을 직접 다루지 않는 이유

이 디렉토리는: “core가 모델을 의식하지 않고 사용하도록 만드는 레이어”

core는 오직 다음 형태만 기대 : JSON-like dict

따라서 모델 변경이 발생해도 core 코드는 직접 수정할 필요가 없습니다.

✅ Summary
Module	Responsibility
object_detector	객체 인식 + 추적
env_segmenter	환경 인식
init	패키지 선언

📌 Notes
✔ YOLO 버전 변경 시 이 디렉토리만 수정
✔ 서비스 로직(core)은 영향 없음
✔ 테스트 환경에서 dummy=True로 전체 파이프라인 검증 가능