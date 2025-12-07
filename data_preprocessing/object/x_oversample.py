import os
import argparse
from collections import defaultdict
import shutil
from tqdm import tqdm

# =============================================================
#  argparse
# =============================================================
parser = argparse.ArgumentParser()
parser.add_argument("--dataset", type=str, required=True,
                    help="Path to dataset (must contain images/train, labels/train)")
parser.add_argument("--split", type=str, default="train",
                    help="train / val")
parser.add_argument("--times", type=int, default=5,
                    help="How many times to oversample each rare-class image")
parser.add_argument("--min_ratio", type=float, default=0.01,
                    help="Rare class threshold (rare if < 1%)")
args = parser.parse_args()

DATASET = args.dataset
SPLIT = args.split

LABEL_DIR = os.path.join(DATASET, "labels", SPLIT)
IMAGE_DIR = os.path.join(DATASET, "images", SPLIT)

# 출력 경로
SAVE_ROOT = DATASET.rstrip("/") + "_oversampled"
SAVE_IMG_DIR = os.path.join(SAVE_ROOT, "images", SPLIT)
SAVE_LBL_DIR = os.path.join(SAVE_ROOT, "labels", SPLIT)

os.makedirs(SAVE_IMG_DIR, exist_ok=True)
os.makedirs(SAVE_LBL_DIR, exist_ok=True)

# =============================================================
#  Load class names
# =============================================================
classes_path = os.path.join(DATASET, "classes.txt")
class_names = {}
if os.path.exists(classes_path):
    with open(classes_path, "r") as f:
        for i, line in enumerate(f):
            class_names[i] = line.strip()
else:
    print("⚠ WARNING: classes.txt not found → class IDs only")

# =============================================================
#  STEP 1: Count classes
# =============================================================
print("\n🔍 Counting class frequencies...")

class_counts = defaultdict(int)
label_files = [f for f in os.listdir(LABEL_DIR) if f.endswith(".txt")]

for lf in tqdm(label_files):
    with open(os.path.join(LABEL_DIR, lf), "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            class_counts[cls_id] += 1

total_boxes = sum(class_counts.values())

print(f"\n📦 Total boxes: {total_boxes}\n")

# =============================================================
#  STEP 2: Identify rare classes
# =============================================================
rare_classes = [cid for cid, cnt in class_counts.items()
                if cnt / total_boxes < args.min_ratio]

print("================== RARE CLASSES ==================")
if rare_classes:
    for cid in rare_classes:
        name = class_names.get(cid, f"class_{cid}")
        pct = class_counts[cid] / total_boxes * 100
        print(f" ➤ {cid:2d} ({name:20}) : {class_counts[cid]} boxes ({pct:.3f}%)")
else:
    print("🚫 No rare classes! (Try lowering --min_ratio)")
print("====================================================\n")

# =============================================================
#  STEP 3: Copy original dataset
# =============================================================
print("📁 Copying original dataset...\n")

for lf in tqdm(label_files):
    src_lbl = os.path.join(LABEL_DIR, lf)
    src_img = os.path.join(IMAGE_DIR, lf.replace(".txt", ".jpg"))

    if not os.path.exists(src_img):
        continue

    shutil.copy(src_lbl, os.path.join(SAVE_LBL_DIR, lf))
    shutil.copy(src_img, os.path.join(SAVE_IMG_DIR, lf.replace(".txt", ".jpg")))

print("✔ Original dataset copied!\n")

# =============================================================
#  STEP 4: Oversample rare-class images
# =============================================================
print("🚀 Oversampling images containing rare classes...\n")

oversample_count = 0

for lf in tqdm(label_files):
    label_path = os.path.join(LABEL_DIR, lf)

    # Check if label file contains a rare class
    has_rare = False
    with open(label_path, "r") as f:
        for line in f:
            cls = int(line.split()[0])
            if cls in rare_classes:
                has_rare = True
                break

    if not has_rare:
        continue

    # Oversample: duplicate N times
    for i in range(args.times):
        new_lbl_name = lf.replace(".txt", f"_os{i}.txt")
        new_img_name = lf.replace(".txt", f"_os{i}.jpg")

        src_img = os.path.join(IMAGE_DIR, lf.replace(".txt", ".jpg"))
        dst_lbl = os.path.join(SAVE_LBL_DIR, new_lbl_name)
        dst_img = os.path.join(SAVE_IMG_DIR, new_img_name)

        if os.path.exists(dst_img):
            continue

        shutil.copy(label_path, dst_lbl)
        shutil.copy(src_img, dst_img)
        oversample_count += 1

print(f"\n🎉 Oversampling complete! {oversample_count} new images added.\n")

# =============================================================
#  STEP 5: Copy classes.txt
# =============================================================
if os.path.exists(classes_path):
    shutil.copy(classes_path, os.path.join(SAVE_ROOT, "classes.txt"))
    print("📄 classes.txt copied.\n")

print("📁 Final oversampled dataset saved to:")
print(SAVE_ROOT)
print("\n🥳 All Done!\n")
