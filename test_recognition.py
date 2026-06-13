# -*- coding: utf-8 -*-
"""Test nhanh: máy có nhận ra bạn không? Chạy: python test_recognition.py

Bật cam 8 giây, dò mặt bằng YuNet, so với kho khuôn mặt (SFace cosine).
In ra mỗi khung: người khớp nhất + độ giống, kết luận theo match_threshold.
"""
import time

import numpy as np

from face_common import (
    DARK_MEAN,
    boost_if_dark,
    detect_faces,
    embed,
    is_dark,
    load_config,
    load_people,
    models_ready,
    open_camera,
    people_embeddings,
)

cfg = load_config()
if not models_ready():
    raise SystemExit("Chua co model AI. Chay:  python download_models.py")
people = load_people()
if not people:
    raise SystemExit('Kho khuon mat trong. Chay:  python enroll.py "Ten ban"')

mat, names, primaries = people_embeddings(people)
thr = cfg.get("match_threshold", 0.36)
cap = open_camera(cfg["camera_index"])
results = []
brightness = []
t0 = time.time()
while time.time() - t0 < 8 and len(results) < 5:
    ok, frame = cap.read()
    if not ok:
        continue
    brightness.append(np.asarray(frame).mean())
    dark = is_dark(frame)
    work = boost_if_dark(frame)
    faces = detect_faces(work)
    if len(faces) == 0 and dark:
        faces = detect_faces(work, relaxed=True)
    for row in faces:
        scores = mat @ embed(work, row)
        j = int(np.argmax(scores))
        results.append((names[j], float(scores[j])))
    time.sleep(0.3)
cap.release()

if results:
    for name, s in results:
        verdict = f"LA {name}" if s >= thr else "NGUOI LA"
        print(f"giong nhat: {name}  cosine = {s:.2f}  ->  {verdict}  (nguong {thr})")
else:
    print("Khong thay khuon mat nao trong 8 giay")
if brightness:
    b = sum(brightness) / len(brightness)
    note = "  (THIEU SANG - da tu dong tang sang khi do)" if b < DARK_MEAN else ""
    print(f"do sang trung binh khung hinh: {b:.0f}/255{note}")
