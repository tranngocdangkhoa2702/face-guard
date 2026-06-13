# -*- coding: utf-8 -*-
"""Đăng ký khuôn mặt một người vào kho (nhiều người tin cậy).

Chạy:  python enroll.py "Tên người"            (thêm/cập nhật người này)
       python enroll.py "Tên người" --primary  (đánh dấu là CHỦ CHÍNH)
       python enroll.py                          (sẽ hỏi tên ngay trong cửa sổ)

Ngồi trước webcam, nhìn vào camera và xoay nhẹ đầu các hướng (trái/phải/lên/xuống,
có kính & không kính nếu hay đeo). Chương trình chụp ~40 mẫu, tính "dấu vân tay số"
rồi LƯU MÃ HÓA vào data/people.dat. Người đã có cùng tên sẽ bị ghi đè (đăng ký lại).

CHỦ CHÍNH: chỉ một người, là người được TỰ HỌC thêm mặt theo thời gian. Người tin
cậy khác (người nhà...) vẫn được coi như chủ máy (không khóa) nhưng không tự học.

Phím: Q = thoát sớm (vẫn lưu nếu đã đủ >= 15 mẫu).
"""
import sys
import time

import cv2

from face_common import (
    boost_if_dark,
    detect_faces,
    embed,
    is_dark,
    load_people,
    models_ready,
    open_camera,
    save_people,
    load_config,
)

TARGET_SAMPLES = 40
MIN_SAMPLES = 15
CAPTURE_GAP = 0.15  # giây giữa 2 lần chụp, để có nhiều góc mặt khác nhau


def parse_args():
    args = [a for a in sys.argv[1:]]
    primary = "--primary" in args
    args = [a for a in args if a != "--primary"]
    name = args[0].strip() if args else ""
    return name, primary


def capture_embeddings(name):
    cfg = load_config()
    cap = open_camera(cfg["camera_index"])
    if not cap.isOpened():
        print("[LOI] Khong mo duoc webcam (camera_index =", cfg["camera_index"], ")")
        sys.exit(1)

    embeddings = []
    last_capture = 0.0
    print(f"Bat dau chup {TARGET_SAMPLES} mau cho '{name}'. Nhin vao camera, xoay nhe dau...")
    while len(embeddings) < TARGET_SAMPLES:
        ok, frame = cap.read()
        if not ok:
            continue
        dark = is_dark(frame)
        work = boost_if_dark(frame)
        faces = detect_faces(work)
        if len(faces) == 0 and dark:
            faces = detect_faces(work, relaxed=True)

        if len(faces) == 1 and time.time() - last_capture >= CAPTURE_GAP:
            embeddings.append(embed(work, faces[0]).tolist())
            last_capture = time.time()

        for f in faces:
            x, y, w, h = f[:4].astype(int)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        msg = f"Da chup: {len(embeddings)}/{TARGET_SAMPLES}"
        if len(faces) == 0:
            msg += "  (khong thay mat - lai gan camera hon)"
        elif len(faces) > 1:
            msg += "  (chi 1 nguoi trong khung hinh thoi!)"
        cv2.putText(frame, msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(f"Dang ky: {name} - nhan Q de thoat", frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break

    cap.release()
    cv2.destroyAllWindows()
    return embeddings


def save_person(name, primary, embeddings):
    if len(embeddings) < MIN_SAMPLES:
        print(f"[LOI] Chi co {len(embeddings)} mau, can it nhat {MIN_SAMPLES}. Chay lai nhe.")
        sys.exit(1)
    people = load_people()
    people = [p for p in people if p["name"].lower() != name.lower()]  # ghi đè nếu trùng tên
    if primary:
        for p in people:
            p["primary"] = False  # chỉ một chủ chính
    people.append({"name": name, "primary": primary,
                   "embeddings": embeddings, "base_count": len(embeddings)})
    save_people(people)
    vai_tro = "CHU CHINH" if primary else "nguoi tin cay"
    print(f"[OK] Da luu '{name}' ({vai_tro}) voi {len(embeddings)} mau (da ma hoa).")
    print("Tong nguoi trong kho:", ", ".join(
        f"{p['name']}{' *' if p.get('primary') else ''}" for p in people))


def main():
    if not models_ready():
        print("[LOI] Chua co model AI. Chay truoc:  python download_models.py")
        sys.exit(1)

    name, primary = parse_args()
    people = load_people()
    if not name:
        name = input("Ten nguoi can dang ky: ").strip()
        if not name:
            print("Chua nhap ten. Thoat.")
            sys.exit(1)
    # Chưa có chủ chính nào -> người đầu tiên mặc định là chủ chính
    has_primary = any(p.get("primary") for p in people)
    if not has_primary and not primary:
        primary = True
        print(f"(Chua co chu chinh -> '{name}' se la CHU CHINH.)")

    save_person(name, primary, capture_embeddings(name))
    print("Xong! Canh gac se dung khuon mat moi o lan kiem tra ke tiep.")


if __name__ == "__main__":
    main()
