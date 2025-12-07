import os
import shutil
import argparse
import xml.etree.ElementTree as ET
from tqdm import tqdm
from collections import defaultdict

# ==========================================================
# argparse
# ==========================================================
parser = argparse.ArgumentParser()
parser.add_argument("--bbox_dir", required=True, help="Root dir with Surface_xxx")
parser.add_argument("--save_dir", required=True, help="Output YOLO dataset dir")
parser.add_argument("--threshold", type=float, default=0.005,
                    help="Rare class ratio threshold (default=0.5%)")
args = parser.parse_args()

SRC = args.bbox_dir
OUT = args.save_dir
THRESH = args.threshold

IMG_OUT = os.path.join(OUT, "images/train")
LBL_OUT = os.path.join(OUT, "labels/train")
os.makedirs(IMG_OUT, exist_ok=True)
os.makedirs(LBL_OUT, exist_ok=True)

# ==========================================================
# helper
# ==========================================================
def convert_to_yolo(size, box):
    W, H = size
    xmin, ymin, xmax, ymax = box
    xc = ((xmin + xmax) / 2) / W
    yc = ((ymin + ymax) / 2) / H
    w = (xmax - xmin) / W
    h = (ymax - ymin) / H
    return xc, yc, w, h

# ==========================================================
# 1. scan class list
# ==========================================================
def load_classes(root):
    classes = set()
    for folder in tqdm(sorted(os.listdir(root)), desc="🔍 Scanning classes"):
        seq_dir = os.path.join(root, folder)
        if not os.path.isdir(seq_dir): continue
        xmls = [f for f in os.listdir(seq_dir) if f.endswith(".xml")]
        if not xmls: continue

        root_xml = ET.parse(os.path.join(seq_dir, xmls[0])).getroot()
        for img in root_xml.findall("image"):
            for box in img.findall("box"):
                classes.add(box.get("label"))

    class_list = sorted(list(classes))
    return class_list, {c: i for i, c in enumerate(class_list)}

# ==========================================================
# 2. export YOLO
# ==========================================================
def export_all_frames(src_root, class_to_id):
    counts = defaultdict(int)
    total = 0

    for folder in tqdm(sorted(os.listdir(src_root)), desc="📦 Exporting all frames"):
        seq_dir = os.path.join(src_root, folder)
        if not os.path.isdir(seq_dir): continue
        xmls = [f for f in os.listdir(seq_dir) if f.endswith(".xml")]
        if not xmls: continue

        root = ET.parse(os.path.join(seq_dir, xmls[0])).getroot()

        for image in root.findall("image"):
            img_name = image.get("name")
            W = int(image.get("width"))
            H = int(image.get("height"))

            src_img = os.path.join(seq_dir, img_name)
            if not os.path.exists(src_img):
                continue

            out_name = f"{folder}_{img_name}"
            shutil.copy(src_img, os.path.join(IMG_OUT, out_name))

            lines = []
            for box in image.findall("box"):
                label = box.get("label")
                xtl = float(box.get("xtl"))
                ytl = float(box.get("ytl"))
                xbr = float(box.get("xbr"))
                ybr = float(box.get("ybr"))

                xc, yc, w, h = convert_to_yolo((W, H), (xtl, ytl, xbr, ybr))
                cid = class_to_id[label]
                lines.append(f"{cid} {xc} {yc} {w} {h}")

                counts[cid] += 1
                total += 1

            with open(os.path.join(LBL_OUT, out_name.replace(".jpg", ".txt")), "w") as f:
                f.write("\n".join(lines))

    return counts, total

# ==========================================================
# main
# ==========================================================
print("\n📌 Step1. Loading class list...")
class_list, class_to_id = load_classes(SRC)

print("\n📌 Step2. Exporting all frames to YOLO...")
counts, total = export_all_frames(SRC, class_to_id)

# ==========================================================
# save class list
# ==========================================================
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "classes.txt"), "w") as f:
    for c in class_list:
        f.write(c + "\n")

# ==========================================================
# rare detection
# ==========================================================
rare = [cid for cid, cnt in counts.items() if cnt / total < THRESH]

print("\n🟣 Auto-detected rare classes:")
for cid in rare:
    print(f" - {cid}: {class_list[cid]} ({counts[cid]/total*100:.3f}%)")

print("\n✅ DONE.")
print("YOLO dataset ready:", OUT)
