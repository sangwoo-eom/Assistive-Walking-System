routes — FastAPI API Endpoints

이 디렉토리는 서비스의 외부 인터페이스(API) 를 담당합니다.
Web, App, 디바이스 등 모든 클라이언트의 HTTP 요청은 이 계층을 통해 처리됩니다.

routes는 core 비즈니스 로직과 models 추론 모듈을 연결하는
Controller 레이어로, 요청 검증과 응답 구성에 집중합니다.

Directory Structure

routes/
├── identity.py
├── inference.py
├── stt.py
└── init.py

1. identity.py — 위치 인식 및 장소 안내 API

Kakao Local API를 기반으로 한 위치 인식 및 주변 정보 안내 API입니다.
현재 위치를 사람에게 이해하기 쉬운 문장 형태로 변환하여 제공합니다.

제공 기능
기능	설명
현재 위치 요약	행정구역 및 주요 시설 기준 위치 설명
상세 주소	도로명 / 지번 주소 반환
주변 건물	학교, 관공서 등 주요 랜드마크 탐색
시설 검색	병원, 지하철역 등 카테고리 기반 검색
시스템 상태	현재 경고 객체 및 환경 상태 조회
Endpoint 목록
Method	Path	설명
POST	/summary	현재 위치 요약
POST	/address	상세 주소 반환
POST	/landmark	주변 주요 건물 조회
POST	/facility	특정 시설 검색
GET	/status	현재 시스템 상태
Request Schema

LocationRequest

{
  "lat": 37.1234,
  "lng": 127.5678
}


FacilityRequest

{
  "lat": 37.1234,
  "lng": 127.5678,
  "category_code": "HP8"
}

Response 예시
{
  "mode": "summary",
  "message": "현재 위치는 서울특별시 광진구 능동이며 어린이대공원역 인근입니다."
}

내부 연동 모듈

core.location_identity

core.warning.warning_manager

Kakao Local REST API

2. inference.py — 메인 AI 추론 API

객체 탐지, 환경 인식, 위험 판단을 통합 수행하는 핵심 추론 API입니다.
실시간 모드와 업로드 모드를 모두 지원합니다.

주요 기능
기능	설명
객체 인식	YOLO 기반 객체 탐지 및 추적
환경 분석	Segmentation 기반 보행 환경 판별
위험 계산	접근 방향 및 거리 기반 위험도 계산
자동 경고	위험 객체 또는 환경에 대한 음성 경고
시각화	업로드 모드에서 bbox 포함 이미지 반환
Endpoint 목록
Method	Path	설명
POST	/infer	이미지 추론
GET	/nearby_objects	근처 객체 요약
GET	/env/danger	위험 환경 안내
GET	/env/safe	안전 환경 안내
GET	/health	헬스 체크
POST	/env/toggle	환경 경고 ON / OFF
메인 추론 API

POST /infer
multipart/form-data 형태의 이미지 업로드

Query Parameter

이름	설명
mode	realtime / upload
Response 예시
{
  "objects": [...],
  "environment": {...},
  "warnings": ["정면에서 차량이 접근하고 있습니다."],
  "image": "<base64>" 
}

위험 처리 흐름

객체 탐지 (Tracking 포함)

이전 프레임과 Bounding Box 비교

위험 요소 계산 (거리, 방향 등)

접근 여부 판단

위험 후보 객체 선정

우선순위 기반 경고 1건 출력

환경 위험 요소 추가 판정

경고 제한 정책
구분	전략
객체별 쿨다운	동일 객체 반복 경고 방지
전역 쿨다운	짧은 시간 내 다중 경고 차단
환경 쿨다운	동일 환경 반복 알림 방지
수동 Mute	특정 환경 알림 비활성화
내부 연동 모듈

core.model_manager

core.risk

core.env_risk

core.warning

core.tts

models.object_detector

models.env_segmenter

3. stt.py — 음성 인식 API

Whisper 기반 음성 인식 API로,
짧은 음성 명령을 텍스트 및 의도(Intent)로 변환합니다.

Endpoint

POST /stt
오디오 파일 업로드 방식

Response 예시
{
  "intent": "location_summary",
  "raw": "여기 어디야?",
  "norm": "여기어디야"
}

내부 처리 흐름

음성 데이터 수신

Whisper 기반 STT 처리

한국어 정규화

Intent 분류

JSON 응답 반환

내부 연동 모듈

core.stt

Whisper Model

역할 정리

routes 디렉토리는 다음 역할만을 수행합니다.

HTTP 요청 처리

요청 데이터 검증

core 로직 호출

응답 JSON 구성

예외 처리

클라이언트 인터페이스 제공

