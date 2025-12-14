import os
import shutil
import argparse
import xml.etree.ElementTree as ET
from tqdm import tqdm
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed


def convert_to_yolo(size, box):
    """Convert pixel bbox to YOLO format"""
    img_w, img_h = size
    xmin, ymin, xmax, ymax = box
    xc = ((xmin + xmax) / 2) / img_w
    yc = ((ymin + ymax) / 2) / img_h
    w = (xmax - xmin) / img_w
    h = (ymax - ymin) / img_h
    return xc, yc, w, h


def scan_classes_one(folder_path):
    """Scan class labels from a single sequence folder"""
    classes = set()
    xml_files = [f for f in os.listdir(folder_path) if f.endswith(".xml")]
    if not xml_files:
        return classes

    root = ET.parse(os.path.join(folder_path, xml_files[0])).getroot()
    for image in root.findall("image"):
        for box in image.findall("box"):
            classes.add(box.get("label"))

    return classes


def load_global_class_list_parallel(bbox_root, workers=8):
    """Collect global class list using parallel folder scanning"""
    folders = [
        os.path.join(bbox_root, f)
        for f in sorted(os.listdir(bbox_root))
        if os.path.isdir(os.path.join(bbox_root, f))
    ]

    classes = set()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(scan_classes_one, f) for f in folders]

        for f in tqdm(
            as_completed(futures),
            total=len(folders),
            desc="Scanning global classes",
        ):
            classes |= f.result()

    class_list = sorted(list(classes))
    class_to_id = {c: i for i, c in enumerate(class_list)}
    return class_list, class_to_id


def scan_rare_one(args):
    """Find frames containing rare classes in a single sequence"""
    seq_path, rare_classes = args
    found = []

    xml_files = [f for f in os.listdir(seq_path) if f.endswith(".xml")]
    if not xml_files:
        return []

    root = ET.parse(os.path.join(seq_path, xml_files[0])).getroot()

    for image in root.findall("image"):
        for box in image.findall("box"):
            if box.get("label") in rare_classes:
                found.append((seq_path, image))
                break

    return found


def find_rare_frames_parallel(bbox_root, rare_classes, workers=8):
    """Search rare-class frames across all sequences in parallel"""
    folders = [
        os.path.join(bbox_root, f)
        for f in sorted(os.listdir(bbox_root))
        if os.path.isdir(os.path.join(bbox_root, f))
    ]

    selected = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(scan_rare_one, (f, rare_classes))
            for f in folders
        ]

        for f in tqdm(
            as_completed(futures),
            total=len(folders),
            desc="Finding rare frames",
        ):
            selected.extend(f.result())

    return selected


def export_one(args):
    """Export a single image and its annotations to YOLO format"""
    seq_path, image, save_dir, class_to_id = args

    img_dir = os.path.join(save_dir, "images/train")
    lbl_dir = os.path.join(save_dir, "labels/train")

    img_name = image.get("name")
    img_w = int(image.get("width"))
    img_h = int(image.get("height"))

    src_img = os.path.join(seq_path, img_name)
    if not os.path.exists(src_img):
        return False

    seq_name = os.path.basename(seq_path)
    save_name = f"{seq_name}_{img_name}"

    shutil.copy(src_img, os.path.join(img_dir, save_name))

    lines = []
    for box in image.findall("box"):
        label = box.get("label")
        xtl, ytl = float(box.get("xtl")), float(box.get("ytl"))
        xbr, ybr = float(box.get("xbr")), float(box.get("xbr"))

        xc, yc, w, h = convert_to_yolo(
            (img_w, img_h),
            (xtl, ytl, xbr, ybr),
        )
        cid = class_to_id[label]
        lines.append(f"{cid} {xc} {yc} {w} {h}")

    label_path = os.path.join(lbl_dir, save_name.replace(".jpg", ".txt"))
    with open(label_path, "w") as f:
        f.write("\n".join(lines))

    return True


def generate_yolo_dataset_parallel(selected_frames, save_dir, class_to_id, workers=8):
    """Generate YOLO dataset from selected frames using parallel workers"""
    img_dir = os.path.join(save_dir, "images/train")
    lbl_dir = os.path.join(save_dir, "labels/train")

    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(lbl_dir, exist_ok=True)

    tasks = [
        (seq_path, image, save_dir, class_to_id)
        for seq_path, image in selected_frames
    ]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(export_one, t) for t in tasks]

        for _ in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Exporting YOLO dataset",
        ):
            pass


def write_yaml(save_dir, class_list):
    """Write YOLO dataset YAML"""
    yaml_path = os.path.join(save_dir, "dataset.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"train: {save_dir}/images/train\n")
        f.write(f"val: {save_dir}/images/train\n")
        f.write("names:\n")
        for i, c in enumerate(class_list):
            f.write(f"  {i}: {c}\n")
    print("YAML generated:", yaml_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bbox_dir", required=True)
    parser.add_argument("--save_dir", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    RARE_CLASSES = {
        "bench",
        "fire_hydrant",
        "carrier",
        "scooter",
        "stroller",
        "dog",
        "cat",
        "wheelchair",
    }

    print("\nStep 1. Loading global class list")
    class_list, class_to_id = load_global_class_list_parallel(
        args.bbox_dir,
        workers=args.workers,
    )

    print("\nStep 2. Finding rare frames")
    frames = find_rare_frames_parallel(
        args.bbox_dir,
        RARE_CLASSES,
        workers=args.workers,
    )
    print(f"Rare frames found: {len(frames)}")

    print("\nStep 3. Exporting YOLO dataset")
    generate_yolo_dataset_parallel(
        frames,
        args.save_dir,
        class_to_id,
        workers=args.workers,
    )

    print("\nStep 4. Saving classes.txt")
    os.makedirs(args.save_dir, exist_ok=True)
    with open(os.path.join(args.save_dir, "classes.txt"), "w") as f:
        for c in class_list:
            f.write(c + "\n")

    print("\nStep 5. Writing YAML")
    write_yaml(args.save_dir, class_list)

    print("\nextract_rare_frames completed.")
