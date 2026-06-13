# -*- coding: utf-8 -*-
"""Bot Telegram điều khiển canh gác từ điện thoại.

Chạy ngầm:  pythonw bot.py   (tự khởi động cùng guard qua start_guard_hidden.vbs)

Lệnh (chỉ nghe từ đúng chat_id của chủ máy, người khác nhắn -> lờ đi):
  /status  - guard chạy không, máy khóa chưa
  /lock    - khóa máy ngay từ xa
  /stop    - tạm dừng canh gác (bot vẫn sống để còn /start lại)
  /start_guard - bật lại canh gác
  /log     - 10 dòng nhật ký mới nhất
  /photo   - chụp 1 tấm từ webcam xem ai đang ngồi trước máy
"""
import ctypes
import datetime
import os
import queue
import subprocess
import sys
import threading
import time

import cv2
import requests

from face_common import BASE_DIR, LOG_PATH, load_config, load_people, open_camera, save_people

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
DESKTOP_SWITCHDESKTOP = 0x0100
SYNCHRONIZE = 0x00100000
PYTHONW = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
GUARD_PY = os.path.join(BASE_DIR, "guard.py")
BOT_LOG = os.path.join(BASE_DIR, "bot.log")
INBOX_DIR = os.path.join(BASE_DIR, "inbox")  # ảnh chủ máy gửi vào bot rơi về đây


def log(msg):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        if os.path.exists(BOT_LOG) and os.path.getsize(BOT_LOG) > 500_000:
            os.remove(BOT_LOG)  # bot.log gọn nhẹ: quá 500KB thì làm mới
        with open(BOT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ensure_single_instance():
    kernel32.CreateMutexW(None, False, "BaoVe_Lap_Bot_Mutex")
    if kernel32.GetLastError() == 183:
        log("Bot da chay san roi - ban nay tu thoat.")
        sys.exit(0)


def guard_is_running():
    """Guard đang chạy? — thử mở mutex của guard."""
    h = kernel32.OpenMutexW(SYNCHRONIZE, False, "BaoVe_Lap_Guard_Mutex")
    if h:
        kernel32.CloseHandle(h)
        return True
    return False


def machine_is_locked():
    hdesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if hdesk:
        user32.CloseDesktop(hdesk)
        return False
    return True


def stop_guard():
    """Tắt đúng tiến trình guard.py (không đụng bot)."""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | "
         "Where-Object { $_.CommandLine -match 'guard\\.py' } | "
         "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def start_guard():
    subprocess.Popen([PYTHONW, GUARD_PY], creationflags=subprocess.CREATE_NO_WINDOW)


def tail_log(n=10):
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:]) or "(log trong)"
    except OSError:
        return "(chua co log)"


class Bot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api = f"https://api.telegram.org/bot{cfg['telegram_token']}"
        self.chat_id = cfg["telegram_chat_id"]
        self.offset = 0
        # Dùng LẠI kết nối HTTPS thay vì bắt tay TLS mới mỗi lần -> nhanh hơn, ít timeout.
        # Hai session tách biệt: long-poll giữ kết nối 50s nên cho gửi tin một làn riêng,
        # khỏi tranh chấp với nhau giữa 2 luồng.
        self.poll_session = requests.Session()  # vòng lặp nhận lệnh (long-poll)
        self.send_session = requests.Session()  # luồng gửi tin/ảnh
        # Gửi tin ở LUỒNG NỀN: 1 tin bị lag mạng không làm kẹt việc nhận lệnh kế tiếp.
        self.outbox = queue.Queue()
        threading.Thread(target=self._sender_loop, daemon=True).start()

    def send(self, text):
        # Không gửi ngay tại đây -> đẩy vào hàng đợi, luồng nền lo gửi (vòng lặp chính
        # không phải chờ mạng). Trả về tức thì.
        self.outbox.put(("text", text, None))

    def send_photo(self, jpg_bytes, caption=""):
        self.outbox.put(("photo", caption, jpg_bytes))

    def _sender_loop(self):
        """Luồng nền: lần lượt lấy tin từ hàng đợi và gửi (giữ đúng thứ tự)."""
        while True:
            kind, text, jpg = self.outbox.get()
            try:
                if kind == "photo":
                    self._do_send_photo(jpg, text)
                else:
                    self._do_send(text)
            except Exception as e:  # 1 tin lỗi không được làm chết luồng gửi
                log(f"LOI luong gui tin: {e}")

    def _do_send(self, text):
        # Mạng chập chờn -> thử lại tối đa 3 lần, đừng để chủ máy chờ trong im lặng
        for attempt in range(3):
            try:
                self.send_session.post(f"{self.api}/sendMessage",
                                       data={"chat_id": self.chat_id, "text": text}, timeout=20)
                return
            except requests.RequestException as e:
                log(f"LOI gui tin (lan {attempt + 1}/3): {e}")
                time.sleep(3)

    def _do_send_photo(self, jpg_bytes, caption=""):
        for attempt in range(3):
            try:
                self.send_session.post(f"{self.api}/sendPhoto",
                                       data={"chat_id": self.chat_id, "caption": caption},
                                       files={"photo": ("camera.jpg", jpg_bytes, "image/jpeg")},
                                       timeout=30)
                return
            except requests.RequestException as e:
                log(f"LOI gui anh (lan {attempt + 1}/3): {e}")
                time.sleep(3)

    def setup_commands(self):
        """Đăng ký danh sách lệnh với Telegram -> gõ '/' là hiện menu chọn lệnh."""
        commands = [
            {"command": "status", "description": "Tình trạng canh gác + máy"},
            {"command": "photo", "description": "Chụp xem ai đang ngồi trước máy"},
            {"command": "lock", "description": "Khóa máy ngay"},
            {"command": "log", "description": "10 dòng nhật ký mới nhất"},
            {"command": "people", "description": "Danh sách người được nhận diện"},
            {"command": "xoa_nguoi", "description": "Xóa 1 người: /xoa_nguoi <tên>"},
            {"command": "stop", "description": "Dừng canh gác"},
            {"command": "start_guard", "description": "Bật lại canh gác"},
        ]
        try:
            self.poll_session.post(f"{self.api}/setMyCommands",
                                   json={"commands": commands}, timeout=20)
            log("Da dang ky menu lenh '/' voi Telegram.")
        except requests.RequestException as e:
            log(f"LOI dang ky menu lenh (khong sao, bot van chay): {e}")

    def save_photo(self, msg):
        """Chủ máy gửi/forward ảnh vào bot -> tải về thư mục inbox\\ trên máy."""
        try:
            file_id = msg["photo"][-1]["file_id"]  # phần tử cuối = bản nét nhất
            r = self.poll_session.get(f"{self.api}/getFile",
                                      params={"file_id": file_id}, timeout=20)
            path = r.json()["result"]["file_path"]
            token = self.cfg["telegram_token"]
            data = self.poll_session.get(
                f"https://api.telegram.org/file/bot{token}/{path}", timeout=30
            ).content
            os.makedirs(INBOX_DIR, exist_ok=True)
            name = f"anh_{datetime.datetime.now():%Y%m%d_%H%M%S}.jpg"
            with open(os.path.join(INBOX_DIR, name), "wb") as f:
                f.write(data)
            log(f"Da nhan anh tu dien thoai -> inbox\\{name}")
            self.send(f"📥 Đã lưu ảnh vào máy: inbox\\{name}")
        except Exception as e:
            log(f"LOI tai anh tu Telegram: {e}")
            self.send("⚠️ Không tải được ảnh, thử gửi lại nhé.")

    def snapshot(self):
        """Chụp 1 khung hình từ webcam, trả về bytes JPEG (không lưu ổ đĩa)."""
        cap = open_camera(self.cfg["camera_index"])
        try:
            if not cap.isOpened():
                return None
            ok, frame = False, None
            for _ in range(10):  # vài khung đầu thường tối/mờ, bỏ qua
                ok, frame = cap.read()
            if not ok:
                return None
            ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return jpg.tobytes() if ok else None
        finally:
            cap.release()

    # ----- các lệnh -----
    def cmd_status(self):
        g = "ĐANG CHẠY ✅" if guard_is_running() else "ĐANG TẮT ⛔"
        m = "ĐANG KHÓA 🔒" if machine_is_locked() else "đang mở 🔓"
        self.send(f"🛡 Canh gác: {g}\n💻 Máy: {m}")

    def cmd_lock(self):
        user32.LockWorkStation()
        self.send("🔒 Đã khóa máy!")

    def cmd_stop(self):
        stop_guard()
        time.sleep(1)
        self.send("⛔ Đã DỪNG canh gác. Máy không được bảo vệ!\n"
                  "Bật lại: /start_guard")

    def cmd_start_guard(self):
        if guard_is_running():
            self.send("🛡 Canh gác vốn đang chạy rồi.")
            return
        start_guard()
        time.sleep(2)
        ok = guard_is_running()
        self.send("🛡 Đã bật lại canh gác ✅" if ok else "⚠️ Bật không thành công, thử lại sau.")

    def cmd_log(self):
        self.send(f"📜 Nhật ký mới nhất:\n{tail_log(10)}")

    def cmd_photo(self):
        if guard_is_running() and machine_is_locked():
            pass  # máy khóa thì guard không giữ cam, chụp vô tư
        jpg = self.snapshot()
        if jpg:
            self.send_photo(jpg, f"📸 Truoc may luc {datetime.datetime.now():%H:%M:%S}")
        else:
            self.send("⚠️ Không mở được webcam (app khác đang giữ?)")

    def cmd_people(self):
        people = load_people()
        if not people:
            self.send("👥 Kho khuôn mặt đang trống. Chạy enroll.py để đăng ký.")
            return
        lines = []
        for p in people:
            vai = "👑 chủ chính" if p.get("primary") else "tin cậy"
            lines.append(f"• {p['name']} ({vai}, {len(p.get('embeddings', []))} mẫu)")
        self.send("👥 Người được nhận diện:\n" + "\n".join(lines)
                  + "\n\nXóa: /xoa_nguoi <tên>")

    def cmd_remove_person(self, name):
        name = name.strip()
        if not name:
            self.send("Cú pháp: /xoa_nguoi <tên>. Xem danh sách: /people")
            return
        people = load_people()
        kept = [p for p in people if p["name"].lower() != name.lower()]
        if len(kept) == len(people):
            self.send(f"⚠️ Không tìm thấy ai tên '{name}'. Xem /people.")
            return
        removed = next(p for p in people if p["name"].lower() == name.lower())
        save_people(kept)
        warn = "\n⚠️ Đây là CHỦ CHÍNH — nhớ đăng ký lại 1 chủ chính mới!" if removed.get("primary") else ""
        self.send(f"🗑 Đã xóa '{removed['name']}'. Còn {len(kept)} người.{warn}")

    def cmd_help(self):
        self.send("Các lệnh (gõ / để hiện menu chọn nhanh):\n"
                  "/status - tình trạng canh gác + máy\n"
                  "/lock - khóa máy ngay\n"
                  "/photo - chụp xem ai trước máy\n"
                  "/log - nhật ký mới nhất\n"
                  "/people - danh sách người được nhận diện\n"
                  "/xoa_nguoi <tên> - xóa 1 người\n"
                  "/stop - dừng canh gác\n"
                  "/start_guard - bật lại canh gác\n"
                  "Gửi/forward ẢNH vào đây → lưu về máy (thư mục inbox)")

    def handle(self, text):
        parts = text.strip().split(maxsplit=1)
        cmd = (parts[0].lower().split("@")[0]) if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd in ("/status",):       self.cmd_status()
        elif cmd in ("/lock",):       self.cmd_lock()
        elif cmd in ("/stop",):       self.cmd_stop()
        elif cmd in ("/start_guard", "/startguard"): self.cmd_start_guard()
        elif cmd in ("/log",):        self.cmd_log()
        elif cmd in ("/photo",):      self.cmd_photo()
        elif cmd in ("/people", "/nguoi"): self.cmd_people()
        elif cmd in ("/xoa_nguoi", "/xoanguoi"): self.cmd_remove_person(arg)
        else:                          self.cmd_help()

    def run(self):
        log("Bot bat dau lang nghe lenh tu Telegram...")
        self.setup_commands()
        self.send("🤖 Bot canh gác đã sẵn sàng! Gõ /status xem tình hình.")
        while True:
            try:
                r = self.poll_session.get(f"{self.api}/getUpdates",
                                          params={"offset": self.offset, "timeout": 50},
                                          timeout=60)
                for upd in r.json().get("result", []):
                    self.offset = upd["update_id"] + 1
                    msg = upd.get("message") or {}
                    text = msg.get("text", "")
                    chat = (msg.get("chat") or {}).get("id")
                    if chat != self.chat_id:
                        log(f"Bo qua tin tu nguoi la (chat {chat}): {text!r}")
                        continue
                    if msg.get("photo"):
                        self.save_photo(msg)
                        continue
                    log(f"Lenh: {text}")
                    self.handle(text)
            except requests.RequestException:
                time.sleep(10)  # mất mạng -> chờ rồi thử lại
            except Exception as e:  # không để bot chết vì 1 lỗi lẻ
                log(f"LOI bat ngo: {e}")
                time.sleep(5)


def main():
    ensure_single_instance()
    cfg = load_config()
    if not cfg.get("telegram_token") or not cfg.get("telegram_chat_id"):
        log("Chua cau hinh telegram_token / telegram_chat_id trong config.json")
        sys.exit(1)
    Bot(cfg).run()


if __name__ == "__main__":
    main()
