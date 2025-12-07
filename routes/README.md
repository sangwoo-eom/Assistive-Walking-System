# routes — FastAPI API Endpoints

이 디렉토리는 서비스의 **외부 인터페이스(API)** 를 담당합니다.  
클라이언트(Web / App / Devices)가 접근하는 모든 HTTP 요청은 이 계층을 통과합니다.

`core` 로직과 `models` 추론 모듈을 연결하는 **Controller 레이어** 역할을 합니다.

---

## 📂 Directory Structure

routes/
├── identity.py
├── inference.py
├── stt.py
└── init.py

---

## 1️⃣ identity.py — 위치 인식 & 장소 안내 API

Kakao Local API 기반 위치 분석 API를 담당합니다.

---

### ✅ 제공 기능

| 기능 | 설명 |
|------|------|
| 현재 위치 요약 | 행정구역 + 주요 시설 기준 위치 설명 |
| 상세 주소 | 도로명 / 지번 주소 반환 |
| 주변 건물 | 학교, 관공서 등 주요 랜드마크 탐색 |
| 시설 검색 | 병원, 지하철역 등 카테고리 기반 조회 |
| 시스템 상태 | 현재 경고 객체 / 환경 상태 조회 |

---

### ✅ Endpoint 목록

| Method | Path | 설명 |
|--------|------|------|
| POST | `/summary` | 현재 위치 요약 |
| POST | `/address` | 상세 주소 반환 |
| POST | `/landmark` | 근처 주요 건물 |
| POST | `/facility` | 특정 시설 검색 |
| GET  | `/status` | 현재 시스템 상태 |

---

### ✅ Request Schema

#### 📍 LocationRequest
```json
{
  "lat": 37.1234,
  "lng": 127.5678
}
🏥 FacilityRequest

{
  "lat": 37.1234,
  "lng": 127.5678,
  "category_code": "HP8"
}

✅ Response Format 예시

{
  "mode": "summary",
  "message": "현재 위치는 서울특별시 광진구 능동으로, 어린이대공원역 근처입니다."
}

내부 연동 모듈
- core.location_identity
- core.warning.warning_manager
- Kakao REST API

2️⃣ inference.py — 메인 AI 추론 API
객체 탐지 + 환경 인식 + 위험 판단을 모두 수행하는 핵심 API입니다.

✅ 주요 기능
기능	     설명
객체 인식	  YOLO 기반 객체 탐지 및 추적
환경 분석	  Segmentation 기반 환경 판별
위험 계산	  접근 / 방향 / 거리 기반 위험도
자동 경고	  위험 객체 또는 환경 음성 경고
시각화	      업로드 모드에서 bbox 포함 이미지 반환

✅ Endpoint 목록
Method	   Path	            설명
POST	   /infer	        이미지 추론
GET	       /nearby_objects	근처 객체 요약
GET	       /env/danger	    위험 환경
GET	       /env/safe	    안전 환경
GET	       /health	        헬스 체크
POST	   /env/toggle	    환경 경고 ON / OFF

✅ 메인 추론 API
POST /infer
multipart 파일 업로드 형태

Query Param
이름	설명
mode	realtime / upload

✅ Response 예시

{
  "objects": [...],
  "environment": {...},
  "warnings": ["정면에서 차량이 다가오고 있습니다."],
  "image": "<base64>" or null
}

✅ 위험 처리 흐름
1. 객체 탐지 (tracking 포함)
2. 이전 프레임과 bbox 비교
3. TTC 계산
4. 접근 판정
5. 위험 객체 후보 선정
6. 우선순위 기반 1개 경고 출력
7. 환경 위험 추가 판정

✅ 경고 제한 정책
구분	         전략
객체별 쿨다운  	  동일 객체 반복 경고 방지
전역 쿨다운  	  짧은 시간 내 다중 경고 차단
환경 쿨다운	      동일 환경 반복 알림 방지
수동 mute	     특정 환경 알림 끄기

내부 연동 모듈
- core.model_manager
- core.risk
- core.env_risk
- core.warning
- core.tts
- models.object_detector
- models.env_segmenter

3️⃣ stt.py — 음성 인식 API
Whisper 기반 음성 명령 인식 인터페이스입니다.

✅ Endpoint
POST /stt
브라우저에서 녹음된 audio 파일 업로드

✅ Response 예시
{
  "intent": "location_summary",
  "raw": "여기 어디야?",
  "norm": "여기어디야"
}

내부 처리 흐름
1. 음성 저장 (임시 파일)
2. Whisper STT 처리
3. 한국어 normalization
4. Intent 분류
5. JSON 반환

내부 연동 모듈
- core.stt
- Whisper Model

🎯 역할 정리
routes는 아래 역할만 수행합니다:

✅ HTTP Request 처리
✅ Validation
✅ core 호출
✅ Response JSON 구성
✅ 예외 처리
✅ 클라이언트 인터페이스 제공

🧠 Summary
파일	          책임
identity.py	     위치 기반 안내
inference.py	 AI 추론 / 경고
stt.py	         음성 명령 처리



