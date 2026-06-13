# -*- coding: utf-8 -*-
"""Canh gác máy bằng khuôn mặt — camera CHỈ BẬT KHI CẦN.

Chạy:  python guard.py          (có cửa sổ console, Ctrl+C để dừng)
hoặc:  pythonw guard.py         (chạy ngầm, không hiện gì)

Bình thường camera TẮT, chỉ theo dõi bàn phím/chuột:
- Máy im lặng một lúc rồi CÓ NGƯỜI gõ phím/đụng chuột
    -> bật cam vài giây kiểm tra: người tin cậy -> tắt cam; người lạ/không thấy mặt -> KHÓA.
- Máy im lặng quá `absence_lock_seconds`
    -> bật cam kiểm tra: còn người tin cậy ngồi (xem phim...) -> tắt cam, lát kiểm lại;
       không thấy ai -> KHÓA.
- Máy ĐANG ĐƯỢC DÙNG liên tục -> mỗi `active_recheck_seconds` xác nhận lại 1 lần.
- Máy đang khóa -> cam tắt hoàn toàn, chờ mở khóa bằng mật khẩu.

Nhận diện: YuNet (dò mặt) + SFace (dấu vân tay số). Nhiều người tin cậy, ai cũng được
coi như chủ máy. Chỉ CHỦ CHÍNH được tự học thêm mặt. Có chống ảnh giả (dò chuyển động).
"""
import ctypes
import datetime
import os
import sys
import time

import cv2
import numpy as np

from face_common import (
    LOG_PATH,
    PEOPLE_PATH,
    boost_if_dark,
    detect_faces,
    embed,
    is_dark,
    load_config,
    load_people,
    models_ready,
    open_camera,
    people_embeddings,
    save_people,
)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
DESKTOP_SWITCHDESKTOP = 0x0100


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    """Bao nhiêu giây rồi không ai gõ phím / đụng chuột."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(lii))
    ticks = (kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
    return ticks / 1000.0


MAX_LOG_BYTES = 1_000_000  # log quá 1 MB thì tự cắt gọn
KEEP_LOG_LINES = 300       # giữ lại bấy nhiêu dòng mới nhất


def _trim_log_if_big():
    try:
        if os.path.getsize(LOG_PATH) <= MAX_LOG_BYTES:
            return
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(f"(log qua dai - da tu cat, giu {KEEP_LOG_LINES} dong moi nhat)\n")
            f.writelines(lines[-KEEP_LOG_LINES:])
    except OSError:
        pass


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        _trim_log_if_big()
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def lock_workstation(reason):
    log(f"KHOA MAY: {reason}")
    user32.LockWorkStation()


def notify_telegram(cfg, text, frame=None):
    """Gửi cảnh báo về điện thoại chủ máy (kèm ảnh nếu có). Lỗi mạng -> bỏ qua êm."""
    token = cfg.get("telegram_token")
    chat = cfg.get("telegram_chat_id")
    if not token or not chat:
        return
    import requests
    api = f"https://api.telegram.org/bot{token}"
    jpg_bytes = None
    if frame is not None:
        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            jpg_bytes = jpg.tobytes()
    for attempt in range(3):  # cảnh báo quan trọng -> mạng lag thì thử lại
        try:
            if jpg_bytes is not None:
                requests.post(
                    f"{api}/sendPhoto",
                    data={"chat_id": chat, "caption": text},
                    files={"photo": ("alert.jpg", jpg_bytes, "image/jpeg")},
                    timeout=30,
                )
            else:
                requests.post(f"{api}/sendMessage",
                              data={"chat_id": chat, "text": text}, timeout=20)
            return
        except Exception as e:
            log(f"LOI gui canh bao Telegram (lan {attempt + 1}/3): {e}")
            time.sleep(3)


def is_locked():
    """Máy đang ở màn hình khóa? (mở input desktop thất bại = đang khóa)"""
    hdesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if hdesk:
        user32.CloseDesktop(hdesk)
        return False
    return True


def ensure_single_instance():
    """Nếu guard đã chạy rồi thì bản mới tự thoát (tránh tranh camera)."""
    kernel32.CreateMutexW(None, False, "BaoVe_Lap_Guard_Mutex")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        log("Guard da chay san roi - ban nay tu thoat.")
        sys.exit(0)


def face_center(face_row):
    x, y, w, h = face_row[:4]
    return np.array([x + w / 2.0, y + h / 2.0], dtype=np.float32)


class Guard:
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_learn = 0.0       # lần cuối tự học mẫu mới
        self.last_frame = None      # khung hình màu gần nhất lúc soi (cho cảnh báo)
        self.people_mtime = 0.0
        self._reload_people()

    # ----- kho khuôn mặt -----
    def _reload_people(self):
        self.people = load_people()
        self.mat, self.names, self.primaries = people_embeddings(self.people)
        try:
            self.people_mtime = os.path.getmtime(PEOPLE_PATH)
        except OSError:
            self.people_mtime = 0.0
        log(f"Da nap kho khuon mat: {len(self.people)} nguoi, "
            f"{self.mat.shape[0]} mau (" +
            ", ".join(f"{p['name']}{'*' if p.get('primary') else ''}"
                      for p in self.people) + ")")

    def _reload_people_if_changed(self):
        try:
            if os.path.getmtime(PEOPLE_PATH) != self.people_mtime:
                self._reload_people()
        except OSError:
            pass

    def alert(self, text):
        stamp = datetime.datetime.now().strftime("%H:%M %d/%m")
        notify_telegram(self.cfg, f"🚨 {text} (lúc {stamp}). Đã khóa máy!",
                        self.last_frame)

    # ----- tự học (chỉ CHỦ CHÍNH) -----
    def maybe_learn(self, emb, score):
        cfg = self.cfg
        if not cfg.get("auto_learn", False):
            return
        if score < cfg.get("auto_learn_min_similarity", 0.55):
            return
        if time.time() - self.last_learn < cfg["auto_learn_min_gap_minutes"] * 60:
            return
        primary = next((p for p in self.people if p.get("primary")), None)
        if primary is None:
            return
        try:
            embs = primary.setdefault("embeddings", [])
            base = primary.get("base_count", len(embs))
            embs.append([float(x) for x in emb])
            # cắt bớt mẫu tự học cũ nhất nếu vượt trần (mẫu gốc base luôn giữ)
            cap = cfg.get("auto_learn_max_samples", 50)
            while len(embs) - base > cap:
                embs.pop(base)
            save_people(self.people)
            self.people_mtime = os.path.getmtime(PEOPLE_PATH)
            self.mat, self.names, self.primaries = people_embeddings(self.people)
            self.last_learn = time.time()
            log(f"Tu hoc mau moi cho '{primary['name']}' (giong {score:.2f}) - "
                f"tong {len(embs)} mau, trong do {len(embs) - base} tu hoc")
        except (OSError, KeyError, ValueError) as e:
            log(f"LOI tu hoc mau (bo qua, khong anh huong canh gac): {e}")

    def verify(self, reason):
        """Bật cam tối đa `verify_seconds` giây để xem ai đang ngồi trước máy.

        Trả về: "owner" (người tin cậy) | "stranger" | "nobody"
        """
        cfg = self.cfg
        thr = cfg.get("match_threshold", 0.36)
        log(f"Bat cam kiem tra: {reason}")
        cap = open_camera(cfg["camera_index"])
        if not cap.isOpened():
            cap.release()
            log("LOI: khong mo duoc webcam (app khac dang dung?) - bo qua lan nay.")
            return "owner"  # không khóa oan khi đang họp Zoom/Meet

        self._reload_people_if_changed()
        if self.mat.shape[0] == 0:
            cap.release()
            log("LOI: kho khuon mat trong - chay enroll.py. Bo qua lan nay.")
            return "owner"

        stranger_hits = 0
        result = "nobody"
        best_emb, best_score, best_name, best_primary = None, -1.0, None, False
        centers = []  # vị trí mặt người tin cậy qua các frame -> đo chuyển động (chống giả)
        deadline = time.time() + cfg["verify_seconds"]
        try:
            while time.time() < deadline:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.2)
                    continue
                self.last_frame = frame
                dark = is_dark(frame)
                work = boost_if_dark(frame)
                faces = detect_faces(work)
                relaxed_pass = False
                if len(faces) == 0 and dark:
                    faces = detect_faces(work, relaxed=True)
                    relaxed_pass = True

                owner_here = stranger_here = False
                for row in faces:
                    emb = embed(work, row)
                    scores = self.mat @ emb
                    j = int(np.argmax(scores))
                    if scores[j] >= thr:
                        owner_here = True
                        centers.append(face_center(row))
                        if scores[j] > best_score:
                            best_emb, best_score = emb, float(scores[j])
                            best_name, best_primary = self.names[j], self.primaries[j]
                    elif not relaxed_pass:
                        # Mặt chỉ thấy nhờ NỚI tiêu chí trong tối mà không khớp ai
                        # -> rất có thể là nhiễu, không kết tội "người lạ".
                        stranger_here = True
                if owner_here and (not stranger_here or cfg["skip_lock_if_owner_present"]):
                    result = "owner"
                    break
                if stranger_here:
                    stranger_hits += 1
                    if stranger_hits >= cfg["stranger_strikes_to_lock"]:
                        result = "stranger"
                        break
                time.sleep(0.3)
        finally:
            cap.release()  # LUÔN tắt cam ngay khi xong

        # --- Chống ảnh giả: người tin cậy phải nhúc nhích tự nhiên ---
        if result == "owner" and cfg.get("liveness_enabled", True):
            if not self._is_alive(centers):
                log(f"NGHI ANH GIA: thay '{best_name}' (giong {best_score:.2f}) nhung "
                    f"mat gan nhu dung im -> coi la dang ngo.")
                result = "stranger"
                best_emb = None  # không tự học từ ảnh nghi giả

        if result == "nobody" and stranger_hits > 0:
            result = "stranger"
        log(f"Ket qua kiem tra: {result} (cam da tat)"
            + (f" - '{best_name}' giong {best_score:.2f}" if best_name and result == "owner" else ""))
        if result == "owner" and best_primary and best_emb is not None:
            self.maybe_learn(best_emb, best_score)
        return result

    def _is_alive(self, centers):
        """Mặt có chuyển động tự nhiên không? Quá ít frame -> cho qua (tránh khóa nhầm)."""
        if len(centers) < 3:
            return True  # không đủ dữ liệu để kết tội -> tin tưởng
        steps = [float(np.linalg.norm(centers[i] - centers[i - 1]))
                 for i in range(1, len(centers))]
        avg_motion = sum(steps) / len(steps)
        return avg_motion >= self.cfg.get("liveness_min_motion", 1.5)

    def run(self):
        cfg = self.cfg
        idle_gap = cfg["idle_gap_seconds"]
        absence_limit = cfg["absence_lock_seconds"]
        recheck = cfg["idle_recheck_seconds"]
        active_recheck = cfg.get("active_recheck_seconds", 300)
        trust_grace = cfg.get("trust_after_verify_seconds", 75)
        interval = cfg["check_interval_seconds"]
        cooldown = cfg["resume_cooldown_seconds"]

        log(
            f"Bat dau canh gac (cam thuong TAT; vang {absence_limit}s -> kiem tra; "
            f"co nguoi dung may sau {idle_gap}s im lang -> kiem tra; "
            f"dang dung lien tuc -> xac nhan lai moi {active_recheck}s)"
        )

        was_locked = False
        next_idle_check = None
        prev_idle = 0.0
        last_owner_ok = time.time()

        while True:
            if is_locked():
                if not was_locked:
                    log("May dang khoa - tam nghi.")
                    was_locked = True
                time.sleep(2)
                continue

            if was_locked:
                log(f"Da mo khoa. Cho {cooldown}s roi canh tiep (cam van tat).")
                time.sleep(cooldown)
                was_locked = False
                next_idle_check = None
                prev_idle = get_idle_seconds()
                last_owner_ok = time.time()
                continue

            idle = get_idle_seconds()

            if prev_idle >= idle_gap and idle < prev_idle:
                since_ok = time.time() - last_owner_ok
                if since_ok <= trust_grace:
                    log(f"Co nguoi dung may sau {int(prev_idle)}s im lang, nhung "
                        f"vua xac nhan {int(since_ok)}s truoc -> khong soi lai.")
                    next_idle_check = None
                    prev_idle = idle
                    time.sleep(interval)
                    continue
                result = self.verify("co nguoi dung may sau khi im lang "
                                     f"{int(prev_idle)}s - ai day?")
                if result == "owner":
                    next_idle_check = None
                    last_owner_ok = time.time()
                else:
                    lock_workstation(
                        "nguoi la dung may" if result == "stranger"
                        else "co nguoi dung may nhung khong thay mat tin cay"
                    )
                    self.alert("Người lạ đụng vào máy" if result == "stranger"
                               else "Có người dùng máy nhưng không thấy mặt")
                    prev_idle = 0.0
                    continue

            elif idle >= absence_limit:
                due = next_idle_check is None or time.time() >= next_idle_check
                if due:
                    result = self.verify(f"may im lang {int(idle)}s - con ai do khong?")
                    if result == "owner":
                        next_idle_check = time.time() + recheck
                        last_owner_ok = time.time()
                    else:
                        lock_workstation(
                            "nguoi la truoc may" if result == "stranger"
                            else f"khong thay ai truoc may sau {int(idle)}s im lang"
                        )
                        if result == "stranger":
                            self.alert("Người lạ lảng vảng trước máy")
                        prev_idle = 0.0
                        continue

            elif (
                active_recheck > 0
                and idle < idle_gap
                and time.time() - last_owner_ok >= active_recheck
            ):
                result = self.verify(
                    "xac nhan dinh ky: may dang duoc dung lien tuc - van la nguoi tin cay?"
                )
                if result == "owner":
                    last_owner_ok = time.time()
                else:
                    lock_workstation(
                        "nguoi la dang dung may" if result == "stranger"
                        else "may dang duoc dung nhung khong thay mat tin cay"
                    )
                    self.alert("Người lạ đang dùng máy" if result == "stranger"
                               else "Máy đang được dùng nhưng không thấy mặt người tin cậy")
                    prev_idle = 0.0
                    continue
            else:
                next_idle_check = None

            prev_idle = idle
            time.sleep(interval)


def main():
    ensure_single_instance()
    cfg = load_config()
    if not models_ready():
        log("CHUA CO MODEL AI. Chay truoc:  python download_models.py")
        sys.exit(1)
    if not load_people():
        log("CHUA CO KHUON MAT nao. Chay truoc:  python enroll.py \"Ten ban\"")
        sys.exit(1)
    try:
        Guard(cfg).run()
    except KeyboardInterrupt:
        log("Dung canh gac (Ctrl+C).")


if __name__ == "__main__":
    main()
