Assistive Walking System (보행 보조 인식 시스템)

본 프로젝트는 시각장애인 및 노약자를 위한 AI 기반 보행 보조 시스템이다.
실시간 객체 인식, 환경 인식, 위험 판단, 음성 안내(STT/TTS), 위치 인식을
하나의 파이프라인으로 통합한 End-to-End Assistive AI System을 목표로 한다.


1. 주요 기능 개요

1) 실시간 객체 인식
- YOLO 기반 보행자, 차량, 위험 객체 탐지
- 객체 추적(ID 유지)을 통해 접근 여부 판단

2) 환경 인식 (Segmentation)
- 도로, 보행로, 점자 보도, 위험 구역 인식
- 현재 위치 기준 위험 환경 / 안전 환경 자동 분류

3) 위험 판단 시스템
- Bounding box 크기 변화 기반 거리 추정
- 객체 이동 방향을 고려한 충돌 가능성 판단
- TTC(Time-to-Collision) 기반 위험 점수 계산

4) 자동 음성 경고 (TTS)
- 접근 중인 객체에 대한 자동 경고
- 위험 환경 진입 시 자동 알림
- 객체 종류, 방향, 위치를 반영한 자연어 문장 생성

5) 음성 제어 (STT)
- Whisper 기반 음성 인식
- 음성 명령을 통한 시스템 제어

지원 명령 예시:
- "시작해"
- "근처 객체 알려줘"
- "위험한 환경 알려줘"
- "여기 어디야"
- "주소 알려줘"
- "경고 꺼"
- "사진 분석"

6) 위치 인식 (Kakao API)
- 현재 위치 주소 안내
- 주변 건물 안내
- 시설 검색 (지하철, 병원, 약국, 마트 등)

7) 이미지 업로드 분석
- 사진 업로드 시 객체 탐지 및 위험 안내 수행


2. 디렉토리 구성

PBDL/
│
├── core/                    # 핵심 로직
│   ├── config.py            # 환경 설정 및 키 관리
│   ├── model_manager.py     # 모델 호출 관리
│   ├── risk.py              # 위험 계산 (TTC, 접근성)
│   ├── env_risk.py          # 환경 위험 판단
│   ├── warning.py           # 경고 상태 머신
│   ├── stt.py               # Whisper 기반 음성 인식
│   ├── tts.py               # 음성 출력 문장 생성
│   ├── location_identity.py # 위치 인식 로직
│   └── utils.py
│
├── models/
│   ├── object_detector.py   # YOLO 객체 인식
│   └── env_segmenter.py     # YOLO 환경 분할
│
├── routes/
│   ├── inference.py         # 메인 추론 API
│   ├── identity.py          # 위치 관련 API
│   └── stt.py               # 음성 인식 API
│
├── static/
│   ├── css/style.css        # UI 스타일
│   └── js/app.js            # 프론트엔드 로직
│
├── templates/
│   └── index.html           # 웹 UI
│
├── weights/                 # 학습된 모델 가중치
│   ├── object_detector.pt
│   └── env_segmenter.pt
│
├── main.py                  # FastAPI 엔트리 포인트
└── README.md                # 프로젝트 설명 문서


3. 실행 방법

1) 가상환경 활성화
conda activate tf_server

2) 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

3) 외부 접근 (Cloudflare Tunnel)
./cloudflared tunnel --url http://localhost:8000


4. API 엔드포인트

1) 추론 API
POST /api/infer
- 실시간 프레임 분석
- 자동 경고 포함
- upload 모드 지원

2) 위치 서비스
POST /api/identity/summary
POST /api/identity/address
POST /api/identity/landmark
POST /api/identity/facility

3) 음성 인식
POST /api/stt

4) 환경 안내
GET /api/env/danger
GET /api/env/safe


5. 위험 판단 알고리즘 요약

위험 점수 계산식:
Risk = Wc × Da × Ad × Tr

항목 설명
- Wc : 객체 종류 가중치
- Da : 거리 변화
- Ad : 중앙 접근 여부
- Tr : TTC 기반 계수


6. 경고 시스템 구조

객체 상태 머신
- SAFE
- NEARBY
- APPROACHING

쿨타임 제어
- 객체별 경고 쿨타임
- 전역 경고 쿨타임
- 환경 경고 쿨타임


7. 학습 데이터 파이프라인 (YOLO)

전체 흐름:
x_count_distribution.py
    ↓
1_build_full_dataset.py
    ↓
2_copy_paste_augmentation.py
    ↓
3_merge_copy_dataset.py
    ↓
4_split_train_val.py

선택적 실험용 스크립트:
- x_extract_rare_frames.py
- x_oversample.py


8. 설치 패키지

pip install fastapi uvicorn ultralytics opencv-python numpy torch pillow whisper requests


9. 필수 환경 설정

.env 파일 생성:
KAKAO_REST_API_KEY=YOUR_API_KEY


10. 프로젝트 목표

본 프로젝트는 단순한 인식 시스템이 아닌,
실제 보행 환경에서 사용자를 보조할 수 있는 실용적인 시스템 구현을 목표로 한다.
시각 정보를 음성 기반으로 전달함으로써 보행자의 상황 인식을 돕는 것을 지향한다.


11. 향후 계획
- 웨어러블 디바이스 연동
- 진동 기반 경고 추가
- GPS 연동 고도화
- 다중 객체 우선순위 판단 개선
- VLM 기반 상황 인식 확장
- CLDS 기반 인식 성능 개선 연구
