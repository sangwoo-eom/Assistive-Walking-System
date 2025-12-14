import os
import random
import shutil
import argparse
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed


# argument parsing
parser = argparse.ArgumentParser()
parser.add_argument(
    "--dataset",
    type=str,
    required=True,
    help="Path to YOLO dataset root (must contain images/train, labels/train)",
)
parser.add_argument(
    "--out",
    type=str,
    required=True,
    help="Output directory for split dataset (new path)",
)
parser.add_argument(
    "--ratio",
    type=float,
    default=0.8,
    help="Train split ratio",
)
parser.add_argument(
    "--seed",
    type=int,
    default=42,
    help="Random seed",
)
args = parser.parse_args()

DATASET = args.dataset
OUT = args.out

TRAIN_IMG_IN = os.path.join(DATASET, "images/train")
TRAIN_LBL_IN = os.path.join(DATASET, "labels/train")

OUT_IMG_TRAIN = os.path.join(OUT, "images/train")
OUT_IMG_VAL = os.path.join(OUT, "images/val")
OUT_LBL_TRAIN = os.path.join(OUT, "labels/train")
OUT_LBL_VAL = os.path.join(OUT, "labels/val")


# create output directories
for d in [OUT_IMG_TRAIN, OUT_IMG_VAL, OUT_LBL_TRAIN, OUT_LBL_VAL]:
    os.makedirs(d, exist_ok=True)


# scan input images
EXT = {".jpg", ".png", ".jpeg"}

all_imgs = [
    f for f in os.listdir(TRAIN_IMG_IN)
    if os.path.splitext(f)[1].lower() in EXT
]

if len(all_imgs) == 0:
    raise RuntimeError(f"No images found in: {TRAIN_IMG_IN}")

print(f"\nFound {len(all_imgs)} images\n")


# shuffle and split
random.seed(args.seed)
random.shuffle(all_imgs)

split_idx = int(len(all_imgs) * args.ratio)
train_imgs = all_imgs[:split_idx]
val_imgs = all_imgs[split_idx:]

print(f"Train: {len(train_imgs)}")
print(f"Val:   {len(val_imgs)}\n")


def copy_one(img_name, dst_img_dir, dst_lbl_dir):
    """Copy one image-label pair"""
    base = os.path.splitext(img_name)[0]
    lbl_name = base + ".txt"

    src_img = os.path.join(TRAIN_IMG_IN, img_name)
    src_lbl = os.path.join(TRAIN_LBL_IN, lbl_name)

    if not os.path.exists(src_lbl):
        return f"Label missing for {img_name}"

    shutil.copy(src_img, os.path.join(dst_img_dir, img_name))
    shutil.copy(src_lbl, os.path.join(dst_lbl_dir, lbl_name))
    return None


def copy_pair(img_list, dst_img_dir, dst_lbl_dir, workers=8):
    """Copy multiple image-label pairs using multi-threading"""
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(copy_one, img, dst_img_dir, dst_lbl_dir)
            for img in img_list
        ]
        for f in tqdm(as_completed(futures), total=len(futures)):
            res = f.result()
            if res:
                print(res)


print("\nCopying TRAIN split...")
copy_pair(train_imgs, OUT_IMG_TRAIN, OUT_LBL_TRAIN, workers=8)

print("\nCopying VAL split...")
copy_pair(val_imgs, OUT_IMG_VAL, OUT_LBL_VAL, workers=8)


# copy class list
classes_src = os.path.join(DATASET, "classes.txt")
classes_dst = os.path.join(OUT, "classes.txt")

if not os.path.exists(classes_src):
    raise FileNotFoundError("classes.txt missing in original dataset.")

shutil.copy(classes_src, classes_dst)


# generate dataset YAML
YAML_OUT = os.path.join(OUT, "dataset.yaml")

with open(classes_dst, "r") as f:
    class_list = [c.strip() for c in f.readlines()]

print("\nGenerating YAML:", YAML_OUT)

with open(YAML_OUT, "w") as f:
    f.write(f"train: {OUT}/images/train\n")
    f.write(f"val: {OUT}/images/val\n")
    f.write("names:\n")
    for i, c in enumerate(class_list):
        f.write(f"  {i}: {c}\n")

print("\nSplit and YAML generation complete.")
print("Output dataset:", OUT)
print("YAML:", YAML_OUT)
print("All done.")
