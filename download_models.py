# -*- coding: utf-8 -*-
"""Tải 2 model AI nhận diện khuôn mặt về data/models/ (chạy 1 lần lúc cài đặt).

Chạy:  python download_models.py

- YuNet  (~345 KB): dò vị trí khuôn mặt + mắt/mũi/miệng.
- SFace  (~37 MB) : biến khuôn mặt thành "dấu vân tay số" 128 chiều để so khớp.

Model nằm trên ổ D (thư mục data/models). Không commit lên git (xem .gitignore).
"""
import os
import sys

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")

# Tải từ kho chính thức OpenCV Zoo
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}


def download(name, url, dest):
    print(f"Tai {name} ...", flush=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r  {pct:3d}%  ({done // 1024} KB)", end="", flush=True)
        print()
    os.replace(tmp, dest)


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    for name, url in MODELS.items():
        dest = os.path.join(MODELS_DIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print(f"Da co {name}, bo qua.")
            continue
        try:
            download(name, url, dest)
        except Exception as e:
            print(f"[LOI] Khong tai duoc {name}: {e}")
            print("Kiem tra mang roi chay lai:  python download_models.py")
            sys.exit(1)
    print("[OK] Da co du model trong data/models/")


if __name__ == "__main__":
    main()
