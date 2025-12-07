import os
import shutil
from tqdm import tqdm

# =======================
# PATH 설정
# =======================
BASE = "/data2/prml513_dir/sangw/aihub_download/data3"

SRC_ORI = f"{BASE}/full_dataset"
SRC_COPY = f"{BASE}/copy_dataset"
OUT = f"{BASE}/final_dataset"

for sub in ["images/train", "labels/train"]:
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)

# =======================
# Helper
# =======================
def copy_files(src_img_dir, src_lbl_dir, prefix=""):
    imgs = [f for f in os.listdir(src_img_dir) if f.endswith(".jpg")]

    for img in tqdm(imgs):
        lbl = img.replace(".jpg", ".txt")

        src_i = os.path.join(src_img_dir, img)
        src_l = os.path.join(src_lbl_dir, lbl)

        new_name = prefix + img

        shutil.copy(src_i, os.path.join(OUT, "images/train", new_name))
        shutil.copy(src_l, os.path.join(OUT, "labels/train", new_name.replace(".jpg", ".txt")))

# =======================
# STEP 1: Copy original
# =======================
print("📦 Copying rebalance_dataset...")
copy_files(
    os.path.join(SRC_ORI, "images/train"),
    os.path.join(SRC_ORI, "labels/train"),
    prefix=""
)

# =======================
# STEP 2: Copy augmented
# =======================
print("\n➕ Merging copy_dataset...")
copy_files(
    os.path.join(SRC_COPY, "images/train"),
    os.path.join(SRC_COPY, "labels/train"),
    prefix="aug_"
)

# =======================
# STEP 3: classes.txt
# =======================
shutil.copy(os.path.join(SRC_ORI, "classes.txt"),
            os.path.join(OUT, "classes.txt"))

print("\n✅ Merge finished!")
print("Final dataset:", OUT)
