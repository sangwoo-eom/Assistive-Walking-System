📂 전체 파이프라인 개요

build_surface_seg_dataset.py
AIHub Surface XML 어노테이션을 Segmentation 학습용 데이터셋으로 변환하는 전처리 스크립트

AIHub Surface XML
↓
Segmentation Dataset (Image / Mask / Label)

================================================================================

1️⃣ Step 1 — Segmentation Dataset 생성
(XML → Mask / Label 변환)

🎯 목적

AIHub Surface XML 어노테이션을 segmentation 학습용 데이터로 변환

Polygon annotation을 pixel-level mask로 변환

YOLO Segmentation 형식의 label 생성

Train / Val / Test 데이터 자동 분할

학습용 설정 파일(surface.yaml) 자동 생성

▶ 실행 명령어

python build_surface_seg_dataset.py
--src ~/aihub_download/surface
--dst ~/aihub_download/data2/seg_dataset
--train-ratio 0.8
--val-ratio 0.1
--seed 42

✅ 생성 디렉토리 구조

seg_dataset/
├ images/
│ ├ train/
│ ├ val/
│ └ test/
├ masks/
│ ├ train/
│ ├ val/
│ └ test/
├ labels/
│ ├ train/
│ ├ val/
│ └ test/
├ classes.txt
└ surface.yaml

🏷 Class Mapping

CLASSES = {
"alley": 0,
"roadway": 1,
"sidewalk": 2,
"bike_lane": 3,
"braille_guide_blocks": 4,
"caution_zone": 5
}

✅ 주요 처리 기능

Surface_* 디렉토리 전체 스캔

XML 기반 polygon annotation 파싱

Polygon → Mask rasterization

z_order 기준 polygon 덮어쓰기 처리

YOLO Segmentation 형식 label 생성

원본 이미지 그대로 복사

classes.txt 자동 생성

surface.yaml 자동 생성

================================================================================

📄 surface.yaml 예시

path: ~/aihub_download/data2/seg_dataset
train: images/train
val: images/val

names:
0: alley
1: roadway
2: sidewalk
3: bike_lane
4: braille_guide_blocks
5: caution_zone

================================================================================

🖊 Label Format (YOLO Segmentation)

<class_id> x1 y1 x2 y2 x3 y3 ...

polygon 좌표는 이미지 기준으로 0~1 범위로 정규화

polygon은 최소 3개 점(좌표 6개) 이상 필요

================================================================================

🎭 Mask Format

PNG grayscale 이미지

pixel value = class index

background = 0

================================================================================

이 문서는
AIHub Surface 데이터셋을 segmentation 학습용 데이터로 변환하기 위한
전처리 파이프라인을 설명한다.
모든 변환 과정은 스크립트 단일 실행으로 자동 수행된다.