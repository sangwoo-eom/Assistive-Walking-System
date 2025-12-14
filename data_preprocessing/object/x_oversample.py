import os
import argparse
from collections import defaultdict
import shutil
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor


# -------------------------------------------------------------
# Argument parsing
# -------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument(
    "--dataset",
    type=str,
    required=True,
    help="Path to dataset (must contain images/train, labels/train)",
)
parser.add_argument(
    "--split",
    type=str,
    default="train",
    help="Dataset split to process (train / val)",
)
parser.add_argument(
    "--times",
    type=int,
    default=5,
    help="Number of oversampled copies per rare-class image",
)
parser.add_argument(
    "--min_ratio",
    type=float,
    default=0.01,
    help="Rare class threshold (rare if class ratio < min_ratio)",
)
parser.add_argument(
    "--workers",
    type=int,
    default=8,
    help="Number of CPU workers for file operations",
)
args = parser.parse_args()

DATASET = args.dataset
SPLIT = args.split
WORKERS = args.workers

LABEL_DIR = os.path.join(DATASET, "labels", SPLIT)
IMAGE_DIR = os.path.join(DATASET, "images", SPLIT)

# Output dataset paths
SAVE_ROOT = DATASET.rstrip("/") + "_oversampled"
SAVE_IMG_DIR = os.path.join(SAVE_ROOT, "images", SPLIT)
SAVE_LBL_DIR = os.path.join(SAVE_ROOT, "labels", SPLIT)

os.makedirs(SAVE_IMG_DIR, exist_ok=True)
os.makedirs(SAVE_LBL_DIR, exist_ok=True)


# -------------------------------------------------------------
# Load class names (optional)
# -------------------------------------------------------------
classes_path = os.path.join(DATASET, "classes.txt")
class_names = {}

if os.path.exists(classes_path):
    with open(classes_path, "r") as f:
        for i, line in enumerate(f):
            class_names[i] = line.strip()
else:
    print("WARNING: classes.txt not found — using numeric class IDs only")


# -------------------------------------------------------------
# Step 1. Count class frequencies
# -------------------------------------------------------------
print("\nCounting class frequencies...")

class_counts = defaultdict(int)
label_files = [f for f in os.listdir(LABEL_DIR) if f.endswith(".txt")]

def count_label(lf):
    """Count class occurrences in a single label file"""
    local = defaultdict(int)
    with open(os.path.join(LABEL_DIR, lf), "r") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            cls_id = int(parts[0])
            local[cls_id] += 1
    return local

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for local_counts in tqdm(
        ex.map(count_label, label_files),
        total=len(label_files),
    ):
        for k, v in local_counts.items():
            class_counts[k] += v

total_boxes = sum(class_counts.values())

print(f"\nTotal bounding boxes: {total_boxes}\n")


# -------------------------------------------------------------
# Step 2. Identify rare classes
# -------------------------------------------------------------
rare_classes = [
    cid for cid, cnt in class_counts.items()
    if cnt / total_boxes < args.min_ratio
]

print("================== RARE CLASSES ==================")
if rare_classes:
    for cid in rare_classes:
        name = class_names.get(cid, f"class_{cid}")
        pct = class_counts[cid] / total_boxes * 100
        print(f" - {cid:2d} ({name:20}) : {class_counts[cid]} boxes ({pct:.3f}%)")
else:
    print("No rare classes found (consider lowering --min_ratio)")
print("=================================================\n")


# -------------------------------------------------------------
# Step 3. Copy original dataset (parallel)
# -------------------------------------------------------------
print("Copying original dataset...\n")

def copy_original(lf):
    """Copy original image-label pair"""
    src_lbl = os.path.join(LABEL_DIR, lf)
    src_img = os.path.join(IMAGE_DIR, lf.replace(".txt", ".jpg"))

    if not os.path.exists(src_img):
        return 0

    shutil.copy(src_lbl, os.path.join(SAVE_LBL_DIR, lf))
    shutil.copy(
        src_img,
        os.path.join(SAVE_IMG_DIR, lf.replace(".txt", ".jpg")),
    )
    return 1

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    list(
        tqdm(
            ex.map(copy_original, label_files),
            total=len(label_files),
        )
    )

print("Original dataset copied.\n")


# -------------------------------------------------------------
# Step 4. Oversample images containing rare classes (parallel)
# -------------------------------------------------------------
print("Oversampling rare-class images...\n")

def oversample_file(lf):
    """Duplicate images that contain at least one rare class"""
    label_path = os.path.join(LABEL_DIR, lf)
    src_img = os.path.join(IMAGE_DIR, lf.replace(".txt", ".jpg"))

    if not os.path.exists(src_img):
        return 0

    # Check if the image contains any rare class
    has_rare = False
    with open(label_path, "r") as f:
        for line in f:
            cls = int(line.split()[0])
            if cls in rare_classes:
                has_rare = True
                break

    if not has_rare:
        return 0

    count = 0
    for i in range(args.times):
        new_lbl = lf.replace(".txt", f"_os{i}.txt")
        new_img = lf.replace(".txt", f"_os{i}.jpg")

        dst_lbl = os.path.join(SAVE_LBL_DIR, new_lbl)
        dst_img = os.path.join(SAVE_IMG_DIR, new_img)

        if os.path.exists(dst_img):
            continue

        shutil.copy(label_path, dst_lbl)
        shutil.copy(src_img, dst_img)
        count += 1

    return count

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    results = list(
        tqdm(
            ex.map(oversample_file, label_files),
            total=len(label_files),
        )
    )

oversample_count = sum(results)

print(f"\nOversampling complete: {oversample_count} new images added.\n")


# -------------------------------------------------------------
# Step 5. Copy classes.txt
# -------------------------------------------------------------
if os.path.exists(classes_path):
    shutil.copy(classes_path, os.path.join(SAVE_ROOT, "classes.txt"))
    print("classes.txt copied.\n")

print("Final oversampled dataset saved to:")
print(SAVE_ROOT)
print("\nAll done.\n")
