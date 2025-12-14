전체 데이터 전처리 파이프라인 정리

x_count_distribution.py        : 클래스 분포 분석 및 데이터 진단
1_build_full_dataset.py        : XML → YOLO Full Dataset 생성
2_copy_paste_augmentation.py   : 희소 객체 Copy-Paste 증강
3_merge_copy_dataset.py        : 원본 + 증강 데이터 병합
4_split_train_val.py           : Train / Val 분할 및 dataset.yaml 생성
x_extract_rare_frames.py       : 희소 클래스 전용 데이터셋 생성 (실험/분석용)
x_oversample.py                : 희소 클래스 이미지 단순 복제 (보조 실험용)

================================================================================

Step 0. 클래스 분포 분석 (진단 단계)

목적
- 전체 데이터셋의 클래스 분포 확인
- 희소 클래스 식별
- 라벨 품질 점검

실행 명령어
python -m x_count_distribution \
  --dataset ~/aihub_download/data/full_dataset \
  --split train \
  --save_csv

주요 처리 내용
- 클래스별 bounding box 개수 집계
- 전체 대비 비율 계산
- threshold 이하 클래스 표시
- empty label, invalid annotation 파일 탐지
- CSV / JSON 결과 저장 가능

출력 파일
- class_distribution_train.csv
- class_distribution_train.json

================================================================================

Step 1. Full Dataset 생성 (XML → YOLO 변환)

목적
- AIHub XML 전체를 YOLO 형식으로 변환
- 학습용 기본 데이터셋 생성
- 클래스 목록 자동 생성

실행 명령어
python -m 1_build_full_dataset \
  --bbox_dir ~/aihub_download/bbox \
  --save_dir ~/aihub_download/data/full_dataset

생성 구조
full_dataset/
 ├ images/train/
 ├ labels/train/
 └ classes.txt

특징
- 모든 Surface 시퀀스 폴더 순회
- XML 기반 bounding box 파싱
- YOLO bbox 포맷으로 변환
- 전체 클래스 목록 자동 스캔
- 클래스별 분포 요약 출력

================================================================================

Step 2. Copy-Paste Augmentation (희소 클래스 강화)

목적
- 희소 객체를 다른 배경 이미지에 삽입
- 희소 클래스 데이터 다양성 확보

실행 명령어
python -m 2_copy_paste_augmentation \
  --src ~/aihub_download/data/full_dataset \
  --save ~/aihub_download/data/copy_dataset \
  --copies 3 \
  --threshold 0.005

주요 처리 내용
- classes.txt 기반 클래스 매핑 유지
- 클래스 분포 기준 희소 클래스 자동 탐지
- YOLO 좌표 → pixel 좌표 변환
- 객체 crop 후 랜덤 배경 위치에 삽입
- bounding box 재계산
- 병렬 처리 적용

출력 구조
copy_dataset/
 ├ images/train/
 ├ labels/train/
 └ classes.txt

================================================================================

Step 3. 원본 + 증강 데이터 병합

목적
- Full Dataset과 Copy-Paste Dataset 통합
- 최종 학습 데이터 구성

실행 방법
python -m 3_merge_copy_dataset

경로 설정
- SRC_ORI  : 원본 데이터셋 경로
- SRC_COPY : 증강 데이터셋 경로

출력 구조
final_dataset/
 ├ images/train/
 ├ labels/train/
 └ classes.txt

================================================================================

Step 4. Train / Val 분할 및 YAML 생성

목적
- YOLO 학습에 바로 사용 가능한 데이터셋 구성

실행 명령어
python -m 4_split_train_val \
  --dataset ~/aihub_download/data3/final_dataset \
  --out ~/aihub_download/data3/final_dataset_split \
  --ratio 0.8 \
  --seed 42

생성 구조
final_dataset_split/
 ├ images/train/
 ├ images/val/
 ├ labels/train/
 ├ labels/val/
 ├ classes.txt
 └ dataset.yaml

dataset.yaml
- train / val 경로 자동 설정
- classes.txt 기반 클래스 이름 매핑

================================================================================

(선택) 희소 클래스 전용 데이터셋 생성

목적
- 희소 클래스가 포함된 프레임만 추출
- Fine-tuning 또는 분석 실험용 데이터셋 구성

실행 명령어
python -m x_extract_rare_frames \
  --bbox_dir ~/aihub_download/bbox \
  --save_dir ~/aihub_download/data/rare_dataset

특징
- 사전 정의된 희소 클래스 기준 필터링
- XML 기반 프레임 단위 검색
- 병렬 처리로 YOLO 데이터셋 생성

================================================================================

(선택) Oversampling (이미지 단순 복제)

목적
- Copy-Paste 대비 성능 비교용 실험
- 데이터 수량만 증가시키는 방식

실행 명령어
python -m x_oversample \
  --dataset ~/aihub_download/data/copy_dataset \
  --split train \
  --times 5 \
  --min_ratio 0.01

특징
- 희소 클래스 포함 이미지 단순 복제
- bounding box 수정 없음
- 분포 변화 실험 목적

================================================================================

YOLO 학습 예시 (YOLO11-M)

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
