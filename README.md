🚶‍♂️ Assistive Walking System (보행 보조 인식 시스템)

본 프로젝트는 시각장애인·노약자를 위한 AI 기반 보행 보조 시스템으로,
실시간 객체 인식, 환경 탐지, 위험 판단, 음성 안내(STT/TTS), 위치 인식을 통합한
End-to-End Assistive AI System 입니다.

📌 주요 기능 요약
✅ 실시간 객체 인식
- YOLO 기반 보행자, 차량, 위험 객체 탐지
- 객체 추적(ID 유지)으로 접근 여부 판단

✅ 환경 인식 (Segmentation)
- 도로 / 보행로 / 점자 보도 / 위험 구역 인식
- 현재 위치의 “위험 환경 vs 안전 환경” 자동 판단

✅ 위험 판단 시스템
- bbox 크기 변화 → 거리 추정
- 이동 방향 → 충돌 가능성 판별
- TTC (Time-to-Collision) 기반 위험 점수 계산

✅ 자동 음성 경고 (TTS)
- 접근 객체 자동 경고
- 환경 위험 자동 알림
- 객체 종류 / 방향 / 위치 기반 자연어 출력

✅ 음성 제어 (STT)
- Whisper 기반 음성 인식

말로 조작
- "시작해"
- "근처 객체 알려줘"
- "위험한 환경 알려줘"
- "여기 어디야"
- "주소 알려줘"
- "경고 꺼"
- "사진 분석"

✅ 위치 인식 (Kakao API)
- 현재 주소 출력
- 주변 건물 안내
- 시설(지하철/병원/약국/마트 등) 검색

✅ 이미지 업로드 분석
- 사진 업로드 → 객체 탐지 + 위험 안내

📂 디렉토리 구성
PBDL/
│
├── core/               # 모든 로직의 중심
│   ├── config.py       # 환경설정 및 키 관리
│   ├── model_manager.py
│   ├── risk.py         # 위험 계산(TTC, 접근성)
│   ├── env_risk.py     # 환경 위험 판단
│   ├── warning.py      # 경고 상태 머신
│   ├── stt.py          # Whisper 기반 음성 인식
│   ├── tts.py          # 음성 출력 문장 생성
│   ├── location_identity.py
│   └── utils.py
│
├── models/
│   ├── object_detector.py   # YOLO 객체 인식
│   └── env_segmenter.py     # YOLO 환경 분할
│
├── routes/
│   ├── inference.py     # 메인 추론 API
│   ├── identity.py      # 위치 API
│   └── stt.py           # 음성 인식 API
│
├── static/
│   ├── css/style.css    # UI 스타일
│   └── js/app.js        # 프론트 JS
│
├── templates/
│   └── index.html       # UI
│
├── weights/             # 학습된 모델 가중치
│   ├── object_detector.pt
│   └── env_segmenter.pt
│
├── main.py              # FastAPI Entry
└── README.md            # ← 이 파일

⚙️ 실행 방법

1️⃣ 가상환경 활성화
conda activate tf_server

2️⃣ 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

3️⃣ Cloudflare Tunnel (외부 접근)
./cloudflared tunnel --url http://localhost:8000

🌐 API 엔드포인트

🔍 추론
POST /api/infer
- 실시간 프레임 분석
- 자동 경고 포함
- upload 모드 가능

📍 위치 서비스
POST /api/identity/summary
POST /api/identity/address
POST /api/identity/landmark
POST /api/identity/facility

🎤 음성 인식
POST /api/stt

⚠ 환경 안내
GET /api/env/danger
GET /api/env/safe

🧠 위험 판단 알고리즘 요약

위험 점수 계산:
Risk = Wc * Da * Ad * Tr

항목	설명
Wc	   객체 종류 가중치
Da	   거리 변화
Ad	   중앙 접근 여부
Tr	   TTC 기반 계수

🔥 경고 시스템 구조

객체 상태 머신
- SAFE
- NEARBY
- APPROACHING

쿨타임 제어
- 객체별 쿨타임
- 전역 경고 쿨타임
- 환경 경고 쿨타임


✅ 학습 데이터 파이프라인 (YOLO)
전체 흐름
x_count_distribution.py
    ↓
1_build_full_dataset.py
    ↓
2_copy_paste_augmentation.py
    ↓
3_merge_copy_dataset.py
    ↓
4_split_train_val.py


(옵션)
x_extract_rare_frames.py
x_oversample.py

✅ 설치 패키지
pip install fastapi uvicorn ultralytics opencv-python numpy torch pillow whisper requests

✅ 필수 환경 설정

.env 생성:
KAKAO_REST_API_KEY=YOUR_API_KEY

✅ 프로젝트 목표

“보행자의 눈이 되어주는 AI”

본 프로젝트는 단순한 인식 시스템이 아니라
현실 세계에서 실제 사람을 돕는 시스템 구현을 목표로 한다.

✅ 향후 계획
- 웨어러블 디바이스 연동
- 진동 경고
- GPS 연동 강화
- 멀티 객체 우선순위 개선
- VLM 기반 상황 인식 확장
- CLDS 기반 인식 성능 개선 연구