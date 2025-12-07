📂 전체 파이프라인 개요

build_surface_seg_dataset.py
→ AIHub Surface XML
→ Segmentation Dataset 생성

==================================================================================

1️⃣ Step 1 — Segmentation Dataset 생성 (XML → Mask / Label 변환)

🎯 목적
- AIHub Surface XML을 segmentation 학습용 데이터로 변환
- Polygon → Mask 생성
- YOLO-SEG 형식 Label 생성
- Train / Val / Test 자동 분할
- surface.yaml 생성

▶ 실행 명령어
python build_surface_seg_dataset.py \
 --src ~/aihub_download/surface \
 --dst ~/aihub_download/data2/seg_dataset \
 --train-ratio 0.8 \
 --val-ratio 0.1 \
 --seed 42

✅ 생성 구조
seg_dataset/
 ├ images/
 │   ├ train/
 │   ├ val/
 │   └ test/
 ├ masks/
 │   ├ train/
 │   ├ val/
 │   └ test/
 ├ labels/
 │   ├ train/
 │   ├ val/
 │   └ test/
 ├ classes.txt
 └ surface.yaml

🏷 Class Mapping
CLASSES = {
    "alley": 0,
    "roadway": 1,
    "sidewalk": 2,
    "bike_lane": 3,
    "braille_guide_blocks": 4,
    "caution_zone": 5,
}

✅ 주요 기능
- Surface XML 전체 스캔
- polygon → mask rasterization
- z_order 기반 덮어쓰기 처리
- YOLO segmentation label 생성
- 이미지 그대로 복사
- classes.txt 자동 저장
- surface.yaml 자동 생성

==================================================================================

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

==================================================================================

🖊 Label Format (YOLO Segmentation)

<class_id> x1 y1 x2 y2 x3 y3 ...
polygon 좌표 (normalize: 0~1)

==================================================================================

🎭 Mask Format
- PNG grayscale
- pixel value = class index
- background = 0