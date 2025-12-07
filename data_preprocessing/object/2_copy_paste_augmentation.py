import os
import cv2
import random
import shutil
import argparse
import numpy as np
from tqdm import tqdm
from collections import defaultdict

# ======================================================
# argparse
# ======================================================
parser = argparse.ArgumentParser()
parser.add_argument("--src", type=str, required=True,
                    help="Path to rebalance_dataset")
parser.add_argument("--save", type=str, required=True,
                    help="Output copy-paste augmented dataset folder")
parser.add_argument("--copies", type=int, default=3,
                    help="How many augmented images per rare object")
parser.add_argument("--threshold", type=float, default=0.005,
                    help="Rare class ratio threshold (default=0.005 → 0.5%)")
args = parser.parse_args()

SRC_DIR = args.src
SAVE_DIR = args.save
COPIES_PER_OBJECT = args.copies
THRESHOLD = args.threshold

os.makedirs(f"{SAVE_DIR}/images/train", exist_ok=True)
os.makedirs(f"{SAVE_DIR}/labels/train", exist_ok=True)

LABEL_DIR = os.path.join(SRC_DIR, "labels/train")
IMG_DIR = os.path.join(SRC_DIR, "images/train")

# ======================================================
# Load classes
# ======================================================
classes_path = os.path.join(SRC_DIR, "classes.txt")
if not os.path.exists(classes_path):
    raise FileNotFoundError("classes.txt not found")

with open(classes_path, "r") as f:
    class_names = [c.strip() for c in f]

print(f"\n📄 Loaded {len(class_names)} classes\n")

# ======================================================
# Count class frequency
# ======================================================
counts = defaultdict(int)
total = 0
label_files = [f for f in os.listdir(LABEL_DIR) if f.endswith(".txt")]

for lf in label_files:
    with open(os.path.join(LABEL_DIR, lf)) as f:
        for line in f:
            cid = int(line.split()[0])
            counts[cid] += 1
            total += 1

rare_cls_ids = [
    cid for cid, cnt in counts.items()
    if cnt / total < THRESHOLD
]

print("\n🟣 Auto-detected rare classes:")
for cid in rare_cls_ids:
    print(f" - {cid} ({class_names[cid]}): {counts[cid]/total*100:.3f}%")
print()

# ======================================================
# YOLO → pixel box
# ======================================================
def yolo_to_box(cls, xc, yc, w, h, img_w, img_h):
    xc *= img_w
    yc *= img_h
    w *= img_w
    h *= img_h
    xmin = int(xc - w / 2)
    ymin = int(yc - h / 2)
    xmax = int(xc + w / 2)
    ymax = int(yc + h / 2)
    return cls, xmin, ymin, xmax, ymax

# ======================================================
# pixel → YOLO
# ======================================================
def box_to_yolo(cls, xmin, ymin, xmax, ymax, img_w, img_h):
    xc = (xmin + xmax) / 2 / img_w
    yc = (ymin + ymax) / 2 / img_h
    w = (xmax - xmin) / img_w
    h = (ymax - ymin) / img_h
    return f"{cls} {xc} {yc} {w} {h}"

# ======================================================
# Crop rare objects
# ======================================================
rare_objects = []

print("✂ Cropping rare objects...")

for lf in tqdm(label_files):
    lbl_path = os.path.join(LABEL_DIR, lf)
    img_path = os.path.join(IMG_DIR, lf.replace(".txt", ".jpg"))

    if not os.path.exists(img_path):
        continue

    img = cv2.imread(img_path)
    if img is None:
        continue

    img_h, img_w = img.shape[:2]

    with open(lbl_path) as f:
        for line in f:
            cid, xc, yc, w, h = map(float, line.split())
            cid = int(cid)

            if cid not in rare_cls_ids:
                continue

            # filter broken bbox
            if w > 0.9 or h > 0.9:
                continue

            _, xmin, ymin, xmax, ymax = yolo_to_box(cid, xc, yc, w, h, img_w, img_h)

            xmin, ymin = max(0, xmin), max(0, ymin)
            xmax, ymax = min(img_w - 1, xmax), min(img_h - 1, ymax)

            if xmax <= xmin or ymax <= ymin:
                continue

            crop = img[ymin:ymax, xmin:xmax]
            if crop.size == 0:
                continue

            rare_objects.append((crop, cid))

print(f"\n📌 Cropped rare objects: {len(rare_objects)}\n")

# ======================================================
# Copy-Paste
# ======================================================
bg_files = [f for f in os.listdir(IMG_DIR) if f.endswith(".jpg")]
print(f"🖼 Background frames: {len(bg_files)}")

aug_count = 0

print("\n🚀 Generating augmented dataset...")

for idx, (crop, cid) in enumerate(tqdm(rare_objects)):
    ch, cw = crop.shape[:2]

    for k in range(COPIES_PER_OBJECT):
        bg_name = random.choice(bg_files)
        bg_path = os.path.join(IMG_DIR, bg_name)
        bg = cv2.imread(bg_path)

        if bg is None:
            continue

        img_h, img_w = bg.shape[:2]

        if cw >= img_w or ch >= img_h:
            continue

        x_min = random.randint(0, img_w - cw - 1)
        y_min = random.randint(0, img_h - ch - 1)
        x_max = x_min + cw
        y_max = y_min + ch

        bg[y_min:y_max, x_min:x_max] = crop

        out_img = f"copy_{idx}_{k}.jpg"
        out_lbl = out_img.replace(".jpg", ".txt")

        cv2.imwrite(os.path.join(SAVE_DIR, "images/train", out_img), bg)

        label_line = box_to_yolo(cid, x_min, y_min, x_max, y_max, img_w, img_h)
        with open(os.path.join(SAVE_DIR, "labels/train", out_lbl), "w") as f:
            f.write(label_line)

        aug_count += 1

print(f"\n🎉 Copy-Paste Done: {aug_count} images generated")

# ======================================================
# Copy classes.txt
# ======================================================
shutil.copy(classes_path, os.path.join(SAVE_DIR, "classes.txt"))
print("📄 classes.txt copied")

print("\n✅ All Done!")
