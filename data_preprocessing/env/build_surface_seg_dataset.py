import os
import random
import argparse
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from tqdm import tqdm

# --------- 설정 ---------
# 기본 class 매핑 (필요하면 여기서 추가/수정)
CLASSES = {
    "alley": 0,
    "roadway": 1,
    "sidewalk": 2,
    "bike_lane": 3,
    "braille_guide_blocks": 4,
    "caution_zone": 5,
}
BACKGROUND_INDEX = 0

# ------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="AIHub Surface XML → Segmentation Dataset Builder"
    )
    parser.add_argument(
        "--src",
        type=str,
        default="/data2/prml513_dir/sangw/aihub_download/surface",
        help="원본 surface 데이터 루트 경로 (Surface_001, Surface_002 ... 상위 폴더)",
    )
    parser.add_argument(
        "--dst",
        type=str,
        default="/data2/prml513_dir/sangw/aihub_download/data2/seg_dataset",
        help="seg 학습용 데이터셋을 생성할 경로",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8, help="train 비율"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.1, help="val 비율 (나머지는 test)"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="random seed"
    )
    return parser.parse_args()


def ensure_dirs(dst_root):
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(dst_root, "images", split), exist_ok=True)
        os.makedirs(os.path.join(dst_root, "masks", split), exist_ok=True)
        os.makedirs(os.path.join(dst_root, "labels", split), exist_ok=True)


def collect_samples(src_root):
    """모든 Surface_* 폴더의 XML을 읽어 (jpg_path, xml_path, image_tag) 리스트를 만든다."""
    samples = []

    surface_dirs = sorted(
        d for d in os.listdir(src_root)
        if d.startswith("Surface_") and os.path.isdir(os.path.join(src_root, d))
    )

    for sd in tqdm(surface_dirs, desc="Scanning Surface_* folders"):
        surf_dir = os.path.join(src_root, sd)
        xml_files = [f for f in os.listdir(surf_dir) if f.endswith(".xml")]
        if not xml_files:
            continue

        xml_path = os.path.join(surf_dir, xml_files[0])
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for img_tag in root.findall("image"):
            img_name = img_tag.attrib["name"]
            img_path = os.path.join(surf_dir, img_name)
            if not os.path.exists(img_path):
                # JPG가 없으면 스킵
                continue

            samples.append({
                "surf_dir": surf_dir,
                "xml_path": xml_path,
                "img_name": img_name,
                "img_path": img_path,
                "width": int(img_tag.attrib["width"]),
                "height": int(img_tag.attrib["height"]),
                "img_tag": img_tag,
            })

    print(f"✅ 총 이미지 개수: {len(samples)}")
    return samples


def split_samples(samples, train_ratio, val_ratio, seed=42):
    random.seed(seed)
    random.shuffle(samples)

    n = len(samples)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train = samples[:n_train]
    val = samples[n_train:n_train + n_val]
    test = samples[n_train + n_val:]

    print(f"🔹 train: {len(train)}, val: {len(val)}, test: {len(test)}")
    return {"train": train, "val": val, "test": test}


def rasterize_mask_from_img_tag(img_tag, width, height):
    """
    단일 image 태그에서 polygon들을 읽어
    (H, W) uint8 mask로 rasterize.
    0: background, 1~N: classes
    """
    mask_img = Image.new("L", (width, height), BACKGROUND_INDEX)
    draw = ImageDraw.Draw(mask_img)

    # z_order 기준으로 정렬 (없으면 0)
    polygons = []
    for poly in img_tag.findall("polygon"):
        label = poly.attrib.get("label", "")
        points_str = poly.attrib.get("points", "")
        if label not in CLASSES:
            # 정의되지 않은 label은 무시 (원하면 warn)
            # print("Unknown label:", label)
            continue

        z = int(poly.attrib.get("z_order", "0"))
        pts = []
        for p in points_str.split(";"):
            if not p.strip():
                continue
            x_str, y_str = p.split(",")
            pts.append((float(x_str), float(y_str)))
        if len(pts) >= 3:
            polygons.append((z, CLASSES[label], pts))

    # z_order 오름차순으로 그리기 (낮은 것 먼저, 높은 것이 덮어씀)
    polygons.sort(key=lambda x: x[0])

    for z, cls_idx, pts in polygons:
        draw.polygon(pts, fill=cls_idx)

    return np.array(mask_img, dtype=np.uint8)

def write_yolo_seg_label(img_tag, width, height, save_txt_path):
    lines = []

    for poly in img_tag.findall("polygon"):
        label = poly.attrib.get("label", "")
        if label not in CLASSES:
            continue

        cls_id = CLASSES[label]
        points_str = poly.attrib.get("points", "")
        pts = []

        for p in points_str.split(";"):
            if not p.strip():
                continue
            x, y = p.split(",")
            x = min(max(float(x) / width, 0.0), 1.0)
            y = min(max(float(y) / height, 0.0), 1.0)

            pts.append(f"{x:.6f} {y:.6f}")

        if len(pts) < 6:
            continue  # polygon은 최소 3개 점 필요

        line = f"{cls_id} " + " ".join(pts)
        lines.append(line)

    with open(save_txt_path, "w") as f:
        f.write("\n".join(lines))

def build_dataset(src_root, dst_root, train_ratio, val_ratio, seed=42):
    print("📂 데이터 수집 중...")
    samples = collect_samples(src_root)

    print("🧩 train/val/test 분할 중...")
    splits = split_samples(samples, train_ratio, val_ratio, seed=seed)

    print("📁 출력 디렉토리 생성 중...")
    ensure_dirs(dst_root)

    # 캐시: xml_path → parsed root
    xml_cache = {}

    for split, items in splits.items():
        print(f"🖼 {split} split 생성 중... (총 {len(items)}장)")
        for s in tqdm(items, desc=f"{split}"):
            img_path = s["img_path"]
            img_name = s["img_name"]
            xml_path = s["xml_path"]

            # XML 파싱 (캐시 사용)
            if xml_path not in xml_cache:
                tree = ET.parse(xml_path)
                xml_cache[xml_path] = tree.getroot()
            root = xml_cache[xml_path]

            # 해당 image 태그 다시 찾기 (id, name 기준)
            img_tag = None
            for it in root.findall("image"):
                if it.attrib.get("name") == img_name:
                    img_tag = it
                    break
            if img_tag is None:
                # 이건 거의 안 나와야 한다
                print(f"⚠ XML에서 {img_name} 찾을 수 없음, 스킵")
                continue

            w, h = int(img_tag.attrib["width"]), int(img_tag.attrib["height"])
            mask = rasterize_mask_from_img_tag(img_tag, w, h)

            # 이미지 복사 & 마스크 저장
            dst_img_path = os.path.join(dst_root, "images", split, img_name)
            dst_mask_path = os.path.join(
                dst_root, "masks", split, img_name.replace(".jpg", ".png")
            )

            dst_txt_path = os.path.join(dst_root, "labels", split, img_name.replace(".jpg", ".txt"))
            os.makedirs(os.path.dirname(dst_txt_path), exist_ok=True)

            write_yolo_seg_label(img_tag, w, h, dst_txt_path)

            # 원본 이미지 그대로 복사 (PIL 사용)
            img = Image.open(img_path).convert("RGB")
            img.save(dst_img_path)

            # mask 저장 (uint8)
            mask_img = Image.fromarray(mask, mode="L")
            mask_img.save(dst_mask_path)

    # class mapping 정보 저장
    class_txt = os.path.join(dst_root, "classes.txt")
    with open(class_txt, "w") as f:
        for name, idx in sorted(CLASSES.items(), key=lambda x: x[1]):
            f.write(f"{idx}: {name}\n")
    write_yaml(dst_root)
    print("🎉 모든 작업 완료!")
    print(f"📦 최종 데이터셋 경로: {dst_root}")
    print(f"🧾 클래스 정보: {class_txt}")

def write_yaml(dst_root):
    yaml_path = os.path.join(dst_root, "surface.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {dst_root}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        # test 쓰고 싶으면:
        # f.write("test: images/test\n")

        f.write("\nnames:\n")
        for name, idx in sorted(CLASSES.items(), key=lambda x: x[1]):
            f.write(f"  {idx}: {name}\n")

    print(f"📄 YAML 생성 완료: {yaml_path}")

def main():
    args = parse_args()
    build_dataset(
        src_root=args.src,
        dst_root=args.dst,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
