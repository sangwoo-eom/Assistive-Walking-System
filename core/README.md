# core — Runtime Logic Modules

이 디렉토리는 보행 보조 AI 시스템의 **실행 로직(core runtime)**만 모아둔 영역입니다.  
모델 관리, 위험 판단, 음성 인식, 음성 출력, 위치 식별 등 **서비스 동작에 필요한 핵심 코드**가 포함되어 있습니다.
본 문서는 각 파일이 “무엇을 담당하는지”에 초점을 맞춘 **개발자 기준 기능 설명서**입니다.

---
## 📂 File Overview

core/
├── __init__.py
├── config.py
├── model_manager.py
├── env_risk.py
├── risk.py
├── warning.py
├── stt.py
├── tts.py
├── location_identity.py
├── kakao_api.py
├── utils.py
---

## 1️⃣ config.py — Global Configuration Manager

프로젝트 전체에서 사용하는 **환경 설정 관리 모듈**입니다.

### 주요 기능
- 프로젝트 루트 경로 자동 판단
- 모델 가중치 경로 관리
- 서버 설정 (HOST / PORT)
- 업로드 파일 설정
- GPU / CPU 설정
- Kakao API Key 로딩 (.env)
- 서버 시작 시 필요한 디렉토리 자동 생성

---

## 2️⃣ model_manager.py — Model Orchestrator

객체 인식 모델과 환경 인식 모델을 통합 제어하는 **중앙 관리자**입니다.

### 주요 기능
- ObjectDetector 로딩
- EnvSegmenter 로딩
- 디바이스 자동 선택 (CPU / GPU)
- Dummy 모델 fallback 지원
- 단일 API로 모든 추론 제공

### 핵심 함수
- `load_models()`
- `get_object_detector()`
- `get_env_segmenter()`
- `run_full_inference(image)`

### 특징
- Tracking 기능 포함
- 이전 프레임 정보 저장
- 객체별 크기 변화와 위치 변화 계산

---

## 3️⃣ risk.py — Object Risk Estimator

단일 객체에 대한 **위험도 계산 모듈**입니다.

### 계산 요소
- 객체 종류 가중치
- Bounding box 증가량
- 화면 중앙 접근 여부
- TTC(Time To Collision) 기반 계수

### 핵심 함수
- `compute_ttc()`
- `compute_Da()`
- `compute_Ad()`
- `compute_Tr()`
- `compute_risk()`

---

## 4️⃣ env_risk.py — Environment Risk Analyzer

환경 segmentation 결과를 이용해 **현재 위치가 위험 환경인지 판단**합니다.

### 주요 기능
- 위험 구역 판별
- 안전 구역 판별
- 현재 가장 우세한 환경 결정

### 판단 로직
- roadway, caution_zone → 위험
- sidewalk, braille blocks → 안전
- 영역 비율 기반 평가

---

## 5️⃣ warning.py — Warning State Machine

객체 접근 상태 관리 및 경고 출력 조건을 관리합니다.

### 주요 기능
- 객체 상태 추적 (NEARBY / APPROACHING)
- 객체 접근 안정화 타이머
- 동일 객체 중복 경고 방지
- 전역 쿨다운 관리
- 환경 경고 관리
- 특정 구역 mute 기능
- 자동 객체 만료

### 관리 대상
- 객체별 상태
- 환경별 경고 상태
- 시스템 전역 경고 여부

---

## 6️⃣ stt.py — Speech Recognition & Command Parser

Whisper 기반 음성 인식 및 명령 분류 모듈입니다.

### 주요 기능
- Whisper 모델 로드
- 음성 파일 텍스트 변환
- 불필요한 표현 제거
- 명령 intent 분류

### 인식 가능한 기능
- 시스템 시작/종료
- 객체 안내 요청
- 환경 안내
- 위치 정보 요청
- 음성 속도 제어
- 경고 on/off
- 반복 요청

---

## 7️⃣ tts.py — Speech Message Builder

모델 결과를 **자연스러운 음성 문장**으로 변환합니다.

### 주요 기능
- YOLO 클래스명 → 한글 변환
- 조사(이/가) 자동 적용
- 방향 판별 (왼쪽 / 정면 / 오른쪽)
- 경고 문장 자동 생성

### 예시
"왼쪽에서 차량이 다가오고 있습니다."

---

## 8️⃣ location_identity.py — Location Intelligence

현재 위치를 사용자에게 설명 가능한 언어로 요약합니다.

### 주요 기능
- GPS 유효성 검증
- 역지오코딩
- 주변 시설 검색
- 거리 계산
- 우선순위 기반 장소 선택
- 문장 형태 요약

### 제공 메시지 유형
- 위치 요약
- 상세 주소
- 주변 주요 시설
- 가까운 건물

---

## 9️⃣ kakao_api.py — Kakao Local API Wrapper

Kakao Local API 통신 전용 모듈입니다.

### 제공 기능
- 좌표 → 주소 변환
- 키워드 검색
- 카테고리 검색

### 특징
- 공통 래퍼 구조
- 예외 처리 내장
- timeout 설정 포함

---

## 🔧 utils.py — Visualization Helpers

디버깅 및 시각화를 위한 유틸리티 모듈입니다.

### 주요 기능
- bbox 시각화
- 거리 기반 위험 판단
- 위험 객체 강조 출력

---

## ✅ Summary

| Module | Responsibility |
|--------|----------------|
| config | 설정 관리 |
| model_manager | 모델 통합 |
| risk | 객체 위험도 |
| env_risk | 환경 위험 |
| warning | 경고 제어 |
| stt | 음성 인식 |
| tts | 음성 출력 |
| location_identity | 위치 안내 |
| kakao_api | API 통신 |
| utils | 디버깅 |

---
core 디렉토리는  
> “모델은 없고, 로직만 있는 실행 엔진”

모델 구조는 `models/`, 서버는 `server.py`, 학습은 `data_preprocessing/`에서 분리 관리합니다.
---
