import os
import argparse
from collections import defaultdict
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed


def read_classes(classes_file):
    """Load class names from classes.txt"""
    if not os.path.exists(classes_file):
        print("classes.txt not found — using numeric class IDs")
        return {}

    class_names = {}
    with open(classes_file, "r") as f:
        for i, line in enumerate(f):
            class_names[i] = line.strip()
    return class_names


def scan_one_label(path):
    """Scan a single YOLO label file"""
    counts = defaultdict(int)
    boxes = 0

    empty = False
    invalid = False

    try:
        with open(path, "r") as f:
            lines = f.readlines()

        if len(lines) == 0:
            return counts, 0, True, False

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 5:
                invalid = True
                continue

            cls_id = int(parts[0])
            counts[cls_id] += 1
            boxes += 1

    except Exception:
        invalid = True

    return counts, boxes, empty, invalid


def scan_labels_parallel(label_dir, workers=8):
    """Scan all label files in parallel"""
    counts = defaultdict(int)
    total_boxes = 0
    total_images = 0
    empty_files = []
    invalid_files = []

    label_files = [
        os.path.join(label_dir, f)
        for f in os.listdir(label_dir)
        if f.endswith(".txt")
    ]

    if len(label_files) == 0:
        return counts, 0, 0, empty_files, invalid_files

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scan_one_label, path): os.path.basename(path)
            for path in label_files
        }

        for future in as_completed(futures):
            file = futures[future]
            file_counts, file_boxes, empty, invalid = future.result()

            total_images += 1
            total_boxes += file_boxes

            if empty:
                empty_files.append(file)
            if invalid:
                invalid_files.append(file)

            for cid, cnt in file_counts.items():
                counts[cid] += cnt

    return counts, total_images, total_boxes, empty_files, invalid_files


def save_csv(report, path):
    """Save class distribution report as CSV"""
    with open(path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["class_id", "class_name", "count", "percentage"])
        for row in report:
            writer.writerow(row)


def save_json(report, path):
    """Save class distribution report as JSON"""
    json_data = [
        {
            "class_id": cid,
            "class_name": name,
            "count": count,
            "percentage": pct,
        }
        for cid, name, count, pct in report
    ]
    with open(path, "w") as f:
        json.dump(json_data, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Path to YOLO dataset root",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="train",
        help="Dataset split to analyze (train / val / both)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        help="Rare class ratio threshold",
    )
    parser.add_argument(
        "--abs-min",
        type=int,
        default=0,
        help="Minimum absolute box count for rare classes",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers",
    )
    parser.add_argument("--save_csv", action="store_true")
    parser.add_argument("--save_json", action="store_true")
    args = parser.parse_args()

    DATASET = args.dataset
    CLASSES_FILE = os.path.join(DATASET, "classes.txt")
    WORKERS = args.workers

    class_names = read_classes(CLASSES_FILE)

    splits = (
        [args.split]
        if args.split in ["train", "val"]
        else ["train", "val"]
    )

    for split in splits:
        print(f"\nAnalyzing split: {split}")
        label_dir = os.path.join(DATASET, f"labels/{split}")

        if not os.path.exists(label_dir):
            print(f"Labels not found: {label_dir}")
            continue

        counts, total_images, total_boxes, empty_files, invalid_files = (
            scan_labels_parallel(label_dir, workers=WORKERS)
        )

        print(f"\nTotal images: {total_images}")
        print(f"Total boxes : {total_boxes}")

        sorted_counts = sorted(
            counts.items(), key=lambda x: x[1], reverse=True
        )

        split_report = []

        for cid, cnt in sorted_counts:
            pct = cnt / total_boxes * 100 if total_boxes > 0 else 0
            name = class_names.get(cid, f"class_{cid}")

            print(f"{cid:2d} ({name:20}) : {cnt:7d} boxes ({pct:.3f}%)")
            split_report.append((cid, name, cnt, pct))

        print("\nRare classes:")
        for cid, name, cnt, pct in split_report:
            if pct / 100 < args.threshold or cnt < args.abs_min:
                print(
                    f"  - {cid:2d} ({name:20}) : "
                    f"{pct:.3f}% (count={cnt})"
                )

        if empty_files:
            print(f"\nEmpty label files: {len(empty_files)}")
        if invalid_files:
            print(f"Invalid annotation files: {len(invalid_files)}")

        if args.save_csv:
            path = os.path.join(DATASET, f"class_distribution_{split}.csv")
            save_csv(split_report, path)
            print(f"CSV saved: {path}")

        if args.save_json:
            path = os.path.join(DATASET, f"class_distribution_{split}.json")
            save_json(split_report, path)
            print(f"JSON saved: {path}")

    print("\nDistribution analysis complete.")
