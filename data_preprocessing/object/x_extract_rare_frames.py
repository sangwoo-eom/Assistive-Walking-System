import os
import shutil
import argparse
import xml.etree.ElementTree as ET
from tqdm import tqdm

# ===========================================================
# YOLO 변환
# ===========================================================
def convert_to_yolo(size, box):
    img_w, img_h = size
    xmin, ymin, xmax, ymax = box
    xc = ((xmin + xmax) / 2) / img_w
    yc = ((ymin + ymax) / 2) / img_h
    w = (xmax - xmin) / img_w
    h = (ymax - ymin) / img_h
    return xc, yc, w, h


# ===========================================================
# 클래스 목록 확보
# ===========================================================
def load_global_class_list(bbox_root):
    classes = set()
    for folder in tqdm(sorted(os.listdir(bbox_root)), desc="🔍 Scanning global classes"):
        folder_path = os.path.join(bbox_root, folder)
        if not os.path.isdir(folder_path):
            continue

        xml_files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
        if not xml_files:
            continue

        root = ET.parse(os.path.join(folder_path, xml_files[0])).getroot()
        for image in root.findall("image"):
            for box in image.findall("box"):
                classes.add(box.get("label"))

    class_list = sorted(list(classes))
    class_to_id = {c: i for i, c in enumerate(class_list)}
    return class_list, class_to_id


# ===========================================================
# 희소 프레임 스캔
# ===========================================================
def find_rare_frames(bbox_root, rare_classes):
    selected = []
    folders = sorted(os.listdir(bbox_root))

    for folder in tqdm(folders, desc="🟣 Finding rare frames"):
        seq_path = os.path.join(bbox_root, folder)
        if not os.path.isdir(seq_path):
            continue

        xml_files = [f for f in os.listdir(seq_path) if f.endswith(".xml")]
        if not xml_files:
            continue

        root = ET.parse(os.path.join(seq_path, xml_files[0])).getroot()
        for image in root.findall("image"):
            for box in image.findall("box"):
                if box.get("label") in rare_classes:
                    selected.append((seq_path, image))
                    break

    return selected


# ===========================================================
# YOLO dataset 생성
# ===========================================================
def generate_yolo_dataset(selected_frames, save_dir, class_to_id):
    img_dir = os.path.join(save_dir, "images/train")
    lbl_dir = os.path.join(save_dir, "labels/train")

    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)

    for seq_path, image in tqdm(selected_frames, desc="🚀 Exporting YOLO dataset"):
        img_name = image.get("name")
        img_w = int(image.get("width"))
        img_h = int(image.get("height"))

        src_img = os.path.join(seq_path, img_name)
        if not os.path.exists(src_img):
            continue

        seq_name = os.path.basename(seq_path)
        save_name = f"{seq_name}_{img_name}"

        shutil.copy(src_img, os.path.join(img_dir, save_name))

        lines = []
        for box in image.findall("box"):
            label = box.get("label")
            xtl, ytl = float(box.get("xtl")), float(box.get("ytl"))
            xbr, ybr = float(box.get("xbr")), float(box.get("ybr"))

            xc, yc, w, h = convert_to_yolo((img_w, img_h), (xtl, ytl, xbr, ybr))
            cid = class_to_id[label]
            lines.append(f"{cid} {xc} {yc} {w} {h}")

        label_path = os.path.join(lbl_dir, save_name.replace(".jpg", ".txt"))
        with open(label_path, "w") as f:
            f.write("\n".join(lines))


# ===========================================================
# YAML 생성
# ===========================================================
def write_yaml(save_dir, class_list):
    yaml_path = os.path.join(save_dir, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"train: {save_dir}/images/train\n")
        f.write(f"val: {save_dir}/images/train\n")
        f.write("names:\n")
        for i, c in enumerate(class_list):
            f.write(f"  {i}: {c}\n")
    print("📄 YAML 생성 완료:", yaml_path)


# ===========================================================
# main
# ===========================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbox_dir", required=True)
    parser.add_argument("--save_dir", required=True)
    args = parser.parse_args()

    # 희소 클래스
    RARE_CLASSES = {
        "bench", "fire_hydrant", "carrier", "scooter",
        "stroller", "dog", "cat", "wheelchair"
    }

    print("\n📌 Step 1. 클래스 목록 로드")
    class_list, class_to_id = load_global_class_list(args.bbox_dir)

    print("\n📌 Step 2. 희소 프레임 검색")
    frames = find_rare_frames(args.bbox_dir, RARE_CLASSES)
    print(f"✔ 희소 프레임 수: {len(frames)}")

    print("\n📌 Step 3. YOLO dataset 생성")
    generate_yolo_dataset(frames, args.save_dir, class_to_id)

    print("\n📌 Step 4. classes.txt 저장")
    os.makedirs(args.save_dir, exist_ok=True)
    with open(os.path.join(args.save_dir, "classes.txt"), "w") as f:
        for c in class_list:
            f.write(c + "\n")

    print("\n📌 Step 5. YAML 저장")
    write_yaml(args.save_dir, class_list)

    print("\n✅ extract_rare_frames 완료!")
