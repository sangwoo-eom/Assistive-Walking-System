import os
import random
import argparse
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw
from tqdm import tqdm


# 클래스 매핑
CLASSES = {
    "alley": 0,
    "roadway": 1,
    "sidewalk": 2,
    "bike_lane": 3,
    "braille_guide_blocks": 4,
    "caution_zone": 5,
}
BACKGROUND_INDEX = 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="AIHub Surface XML → Segmentation dataset builder"
    )
    parser.add_argument(
        "--src",
        type=str,
        default="/data2/prml513_dir/sangw/aihub_download/surface",
        help="AIHub surface 원본 데이터 루트",
    )
    parser.add_argument(
        "--dst",
        type=str,
        default="/data2/prml513_dir/sangw/aihub_download/data2/seg_dataset",
        help="생성될 segmentation 데이터셋 경로",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8, help="train 비율"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.1, help="val 비율"
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
    """Surface_* 디렉토리에서 이미지/어노테이션 쌍 수집"""
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

    print(f"총 이미지 개수: {len(samples)}")
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

    print(f"train: {len(train)}, val: {len(val)}, test: {len(test)}")
    return {"train": train, "val": val, "test": test}


def rasterize_mask_from_img_tag(img_tag, width, height):
    """polygon annotation을 mask 이미지로 변환"""
    mask_img = Image.new("L", (width, height), BACKGROUND_INDEX)
    draw = ImageDraw.Draw(mask_img)

    polygons = []
    for poly in img_tag.findall("polygon"):
        label = poly.attrib.get("label", "")
        points_str = poly.attrib.get("points", "")
        if label not in CLASSES:
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

    polygons.sort(key=lambda x: x[0])

    for _, cls_idx, pts in polygons:
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
            continue

        lines.append(f"{cls_id} " + " ".join(pts))

    with open(save_txt_path, "w") as f:
        f.write("\n".join(lines))


def build_dataset(src_root, dst_root, train_ratio, val_ratio, seed=42):
    samples = collect_samples(src_root)
    splits = split_samples(samples, train_ratio, val_ratio, seed=seed)
    ensure_dirs(dst_root)

    xml_cache = {}

    for split, items in splits.items():
        print(f"{split} split 생성 중 ({len(items)}장)")
        for s in tqdm(items, desc=split):
            img_path = s["img_path"]
            img_name = s["img_name"]
            xml_path = s["xml_path"]

            if xml_path not in xml_cache:
                tree = ET.parse(xml_path)
                xml_cache[xml_path] = tree.getroot()
            root = xml_cache[xml_path]

            img_tag = None
            for it in root.findall("image"):
                if it.attrib.get("name") == img_name:
                    img_tag = it
                    break
            if img_tag is None:
                continue

            w, h = int(img_tag.attrib["width"]), int(img_tag.attrib["height"])
            mask = rasterize_mask_from_img_tag(img_tag, w, h)

            dst_img_path = os.path.join(dst_root, "images", split, img_name)
            dst_mask_path = os.path.join(
                dst_root, "masks", split, img_name.replace(".jpg", ".png")
            )
            dst_txt_path = os.path.join(
                dst_root, "labels", split, img_name.replace(".jpg", ".txt")
            )
            os.makedirs(os.path.dirname(dst_txt_path), exist_ok=True)

            write_yolo_seg_label(img_tag, w, h, dst_txt_path)

            img = Image.open(img_path).convert("RGB")
            img.save(dst_img_path)

            Image.fromarray(mask, mode="L").save(dst_mask_path)

    class_txt = os.path.join(dst_root, "classes.txt")
    with open(class_txt, "w") as f:
        for name, idx in sorted(CLASSES.items(), key=lambda x: x[1]):
            f.write(f"{idx}: {name}\n")

    write_yaml(dst_root)
    print("데이터셋 생성 완료")
    print(f"출력 경로: {dst_root}")
    print(f"클래스 정보: {class_txt}")


def write_yaml(dst_root):
    yaml_path = os.path.join(dst_root, "surface.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {dst_root}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("\nnames:\n")
        for name, idx in sorted(CLASSES.items(), key=lambda x: x[1]):
            f.write(f"  {idx}: {name}\n")

    print(f"YAML 생성 완료: {yaml_path}")


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
