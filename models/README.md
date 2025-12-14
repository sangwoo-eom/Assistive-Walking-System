# models — AI Inference Wrappers

이 디렉토리는 학습된 AI 모델을 서비스 코드에서 직접 사용할 수 있도록 감싸는
Wrapper 모듈들로 구성되어 있다.

YOLO 기반 객체 인식 모델과 환경 인식(Segmentation) 모델을 추상화하여,
core 로직과 모델 구현을 분리하는 역할을 담당한다.

모델의 내부 구현이나 프레임워크 변경이 발생하더라도,
서비스 로직(core)에 미치는 영향을 최소화하는 것이 목적이다.

--------------------------------------------------------------------------------

## Directory Structure

models/
 ├─ object_detector.py
 ├─ env_segmenter.py
 └─ __init__.py

--------------------------------------------------------------------------------

## 1. object_detector.py — Object Detection Wrapper

YOLO 기반 객체 탐지 모델을 감싸는 Wrapper 클래스이다.

### 역할
- 객체 탐지 수행
- Bounding box, confidence score, class name 추출
- 객체 추적 ID 관리 (Tracking)
- 서비스 코드에서 바로 사용할 수 있는 dict 형태로 결과 반환

--------------------------------------------------------------------------------

### Class: ObjectDetector

ObjectDetector(weights_path, device="cpu", dummy=False, tracking=False)

### Initialization Parameters

weights_path  
- YOLO 가중치 파일 경로

device  
- 실행 디바이스 ("cpu" 또는 "cuda")

dummy  
- True일 경우 실제 모델을 로드하지 않는 더미 모드

tracking  
- True일 경우 YOLO tracking 모드 활성화

--------------------------------------------------------------------------------

### Main Method

predict(image, track=False)

YOLO 추론을 수행하고 객체 탐지 결과를 반환한다.

### Return Format

{
  "objects": [
    {
      "id": 3,
      "class": "car",
      "score": 0.91,
      "bbox": [x1, y1, x2, y2]
    }
  ]
}

--------------------------------------------------------------------------------

### Characteristics

- YOLO native API를 서비스 코드에 직접 노출하지 않음
- Tracking 활성화 시 객체 ID 자동 관리
- core 로직과 완전히 독립적인 구조
- 추론 실패 시 빈 결과 반환
- dummy 모드를 통한 서버 및 파이프라인 테스트 지원

--------------------------------------------------------------------------------

## 2. env_segmenter.py — Environment Segmentation Wrapper

보행 환경 인식을 위한 Segmentation 모델 Wrapper 클래스이다.

도로, 인도 등 환경 요소를 감지하고,
이를 위험/안전 구역으로 단순화하여 제공한다.

--------------------------------------------------------------------------------

### Class: EnvSegmenter

EnvSegmenter(weights_path, device="cpu", dummy=False)

--------------------------------------------------------------------------------

### 역할
- Segmentation 모델 로드
- 감지된 클래스 집계
- 위험 구역 / 안전 구역 분류
- 추론 결과를 단순화된 dict 형태로 반환

### Return Format

{
  "env": {
    "danger_zones": ["roadway"],
    "safe_zones": ["sidewalk"],
    "raw_classes": ["roadway", "sidewalk"]
  }
}

--------------------------------------------------------------------------------

### Environment Classification

위험 구역
- roadway
- caution_zone

안전 구역
- sidewalk
- braille_guide_blocks

--------------------------------------------------------------------------------

### Characteristics

- Segmentation 결과를 판단 로직에 적합한 형태로 변환
- YOLO 결과 구조 은닉
- 추론 실패 시 빈 결과 반환
- dummy 모드 지원

--------------------------------------------------------------------------------

## Design Philosophy

이 디렉토리는 core 로직이 모델의 존재를 직접 의식하지 않도록 하기 위한 계층이다.

core는 오직 JSON-like dict 형태의 결과만을 기대하며,
모델의 구조나 프레임워크에는 관여하지 않는다.

따라서 모델 변경, 교체, 재학습이 발생하더라도
core 코드를 수정할 필요가 없다.

--------------------------------------------------------------------------------

## Summary

Module            Responsibility
object_detector   객체 인식 및 추적
env_segmenter     환경 인식
__init__          패키지 선언

--------------------------------------------------------------------------------

## Notes

- YOLO 버전 변경 시 수정 범위는 이 디렉토리로 한정됨
- 서비스 로직(core)은 영향 없음
- dummy=True 설정을 통해 모델 없이 전체 파이프라인 검증 가능
