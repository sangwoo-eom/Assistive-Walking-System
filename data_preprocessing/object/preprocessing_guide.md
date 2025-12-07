📂 전체 파이프라인 개요
x_count_distribution.py       → 클래스 분포 분석 (진단)
1_build_full_dataset.py       → XML → YOLO Full Dataset 생성 (기본 데이터 생성기)
2_copy_paste_augmentation.py  → 희소 객체 copy-paste 증강
3_merge_copy_dataset.py       → Full + Copy 데이터 병합
4_split_train_val.py          → Train / Val 분할 + dataset.yaml 자동 생성
x_extract_rare_frames.py      → 희소 클래스 전용 데이터셋 생성 (FT, 분석용)
x_oversample.py               → 희소 클래스 이미지 단순 복제 (실험용)

==================================================================================

1️⃣ Step 0 — 클래스 분포 분석 (진단 단계)

🎯 목적
- 전체 데이터의 클래스 분포 파악
- 희소 클래스 자동 탐지
- 데이터 품질 점검 (empty label, corrupt annotation 등)

▶ 실행 명령어
python -m x_count_distribution \
 --dataset ~/aihub_download/data/full_dataset \
 --split train \
 --save_csv

✅ 주요 기능
- 클래스별 Object 개수 집계
- 전체 대비 비율 계산
- threshold 이하 클래스 자동 표시
- CSV / JSON 저장 가능

==================================================================================

2️⃣ Step 1 — Full Dataset 생성 (XML → YOLO 변환)

🎯 목적
- Raw XML 전체를 YOLO 형식으로 변환
- classes.txt 생성
- 학습용 기본 Dataset 생성

▶ 실행 명령어
python -m 1_build_full_dataset \
 --bbox_dir ~/aihub_download/bbox \
 --save_dir ~/aihub_download/data/full_dataset

✅ 생성 구조
full_dataset/
 ├ images/train/*.jpg
 ├ labels/train/*.txt
 └ classes.txt

🟣 콘솔 출력

- 자동으로 희소 클래스 표시됨
- 전체 분포 요약 출력

==================================================================================

3️⃣ Step 2 — Copy-Paste Augmentation (희소 클래스 강화)

🎯 목적

- 희소 객체 crop 후 랜덤 배경에 붙여넣기
- 희소 클래스 데이터 다양성 증가
- Recall 성능 개선

▶ 실행 명령어
python -m 2_copy_paste_augmentation \
 --src ~/aihub_download/data/full_dataset \
 --save ~/aihub_download/data/copy_dataset \
 --copies 3 \
 --threshold 0.005

✅ 기능 요약

- classes.txt 기반 클래스 매핑 유지
- threshold로 희소 클래스 자동 탐지
- 객체 crop → random insert
- Bounding Box 자동 생성

📁 출력 구조
copy_dataset/
 ├ images/train/*.jpg
 ├ labels/train/*.txt
 └ classes.txt

==================================================================================

4️⃣ Step 3 — 원본 + 증강 데이터 병합

🎯 목적
- Full Dataset + Copy Dataset 통합
- 최종 학습 데이터 구성

▶ 실행 명령어
python -m 3_merge_copy_dataset


※ 경로는 코드 상단 변수(SRC_ORI, SRC_COPY)에서 수정

✅ 결과
final_dataset/
 ├ images/train/
 ├ labels/train/
 └ classes.txt

==================================================================================

5️⃣ Step 4 — Train / Val 분할 + YAML 생성

🎯 목적
- YOLO 학습용 Dataset 완성
- dataset.yaml 자동 생성

▶ 실행 명령어
python -m 4_split_train_val \
 --dataset ~/aihub_download/data3/final_dataset \
 --out ~/aihub_download/data3/final_dataset_split \
 --ratio 0.8 \
 --seed 42

✅ 생성 구조
final_dataset_split/
 ├ images/train/
 ├ images/val/
 ├ labels/train/
 ├ labels/val/
 ├ classes.txt
 └ dataset.yaml

==================================================================================

🧪 (선택) Step X — 희소 전용 Dataset 생성 (FT / 분석용)

⚠ 메인 파이프라인 아님 (실험용)

▶ 실행 명령어
python -m x_extract_rare_frames \
 --bbox_dir ~/aihub_download/bbox \
 --save_dir ~/aihub_download/data/rare_dataset

==================================================================================

🧪 (선택) Step X — Oversampling (이미지 단순 복제)

▶ 실행 명령어
python -m x_oversample \
 --dataset ~/aihub_download/data/copy_dataset \
 --split train \
 --times 5 \
 --min_ratio 0.01

==================================================================================

🎯 최종 학습 명령어 (YOLO11-M 기준)
CUDA_VISIBLE_DEVICES=4 \
yolo detect train \
  model=yolo11m.pt \
  data=~/aihub_download/data/final_dataset_split/dataset.yaml \
  imgsz=640 \
  epochs=100 \
  batch=16 \
  workers=8 \
  project=PBDL \
  name=final_copy_paste_aug