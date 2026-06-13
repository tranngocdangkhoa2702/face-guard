# BaoVe_Lap — Khóa máy Windows bằng khuôn mặt 🛡️

Tự động khóa máy tính Windows khi **không phải bạn** (hoặc người tin cậy) ngồi trước
webcam. Camera **chỉ bật khi cần** (vài giây mỗi lần kiểm tra) nên riêng tư và nhẹ máy.
Điều khiển từ xa qua **bot Telegram**.

> *Auto-lock your Windows PC when someone who isn't you sits in front of the webcam.
> The camera only turns on for a few seconds when a check is needed. Controlled via a
> Telegram bot. Vietnamese UI.*

## ✨ Tính năng

- **Nhận diện khuôn mặt AI** bằng YuNet (dò mặt) + SFace (so khớp) — chạy trên CPU, mượt.
- **Camera chỉ bật khi cần**: bình thường chỉ theo dõi bàn phím/chuột (không tốn pin/CPU,
  không quay lén). Có người lạ đụng máy / bạn rời đi → mới bật cam vài giây.
- **Nhiều người tin cậy**: thêm người nhà vào danh sách, họ dùng máy không bị khóa.
- **Chống ảnh giả** (liveness): mặt phải nhúc nhích tự nhiên — giơ ảnh in/màn hình không qua.
- **Mã hóa dữ liệu khuôn mặt** theo tài khoản Windows (DPAPI): copy sang máy khác là vô dụng.
- **Tự học**: chủ chính cắt tóc/đổi kính dần vẫn nhận ra (chỉ học khi cực kỳ chắc chắn).
- **Bot Telegram**: xem trạng thái, khóa máy, chụp ảnh xem ai trước máy, xem nhật ký... từ điện thoại.
- **Hỗ trợ thiếu sáng**: tự tăng sáng/tương phản khi phòng tối.

## 📋 Yêu cầu

- Windows 10/11
- Python 3.9+ (đã chạy thật trên 3.14)
- Webcam
- (Tùy chọn) Tài khoản Telegram nếu muốn điều khiển từ xa

## 🚀 Cài đặt

```bat
:: 1. Tải mã nguồn rồi vào thư mục dự án
git clone <repo-url> BaoVe_Lap
cd BaoVe_Lap

:: 2. Tạo môi trường Python (nên đặt trên ổ khác ổ C cho nhẹ ổ hệ thống)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

:: 3. Tải 2 model AI (~37MB, một lần)
.venv\Scripts\python download_models.py

:: 4. Đăng ký khuôn mặt chủ máy
.venv\Scripts\python enroll.py "Tên bạn"
```

### (Tùy chọn) Thiết lập bot Telegram

1. Nhắn **@BotFather** trên Telegram → `/newbot` → lấy **token**.
2. Nhắn 1 tin cho bot vừa tạo, rồi mở
   `https://api.telegram.org/bot<TOKEN>/getUpdates` để lấy **chat_id** của bạn.
3. Copy `secrets.example.json` thành `secrets.json`, điền `telegram_token` và `telegram_chat_id`.

> ⚠️ **KHÔNG** commit `secrets.json` lên git (đã có sẵn trong `.gitignore`). Lộ token thì
> vào @BotFather gõ `/revoke`.

## 🎮 Chạy

```bat
:: Canh gác (có cửa sổ console để xem log)
.venv\Scripts\python guard.py

:: Hoặc chạy ngầm không cửa sổ (kèm bot Telegram)
wscript.exe start_guard_hidden.vbs
```

Thêm người tin cậy / chủ chính:

```bat
.venv\Scripts\python enroll.py "Tên người nhà"            :: người tin cậy
.venv\Scripts\python enroll.py "Tên bạn" --primary        :: chủ chính (chỉ 1 người)
```

### Lệnh bot Telegram

| Lệnh | Việc |
|------|------|
| `/status` | Canh gác đang chạy? Máy khóa chưa? |
| `/photo` | Chụp 1 tấm xem ai đang trước máy |
| `/lock` | Khóa máy ngay |
| `/log` | 10 dòng nhật ký mới nhất |
| `/people` | Danh sách người được nhận diện |
| `/xoa_nguoi <tên>` | Xóa 1 người |
| `/stop` / `/start_guard` | Dừng / bật lại canh gác |

Gửi/forward một **tấm ảnh** vào bot → ảnh được lưu về thư mục `inbox\` trên máy.

## ⚙️ Cấu hình

Mọi thông số nằm trong `config.json`, mỗi khóa có chú thích tiếng Việt. Vài khóa quan trọng:

- `match_threshold` (0.30–0.45): độ giống tối thiểu để coi là đúng người. **Cao** = chặt hơn.
- `liveness_min_motion`: mức chuyển động tối thiểu để qua cửa chống ảnh giả.
- `idle_gap_seconds`, `absence_lock_seconds`, `active_recheck_seconds`: nhịp kiểm tra.

> Sửa `config.json` xong nhớ **khởi động lại** canh gác mới có tác dụng.

## 🔒 Quyền riêng tư

- Camera **tắt** trừ vài giây mỗi lần kiểm tra. Không quay/lưu video.
- "Dấu vân tay số" khuôn mặt được **mã hóa** (Windows DPAPI), lưu ở `data/people.dat`.
- Token bot và dữ liệu khuôn mặt **không bao giờ lên git**.

## ⚠️ Giới hạn

- Webcam thường **không có hồng ngoại** → phòng **tối hẳn** (0 ánh sáng) sẽ không nhận được.
- Chống ảnh giả ở mức **nhẹ** (dò chuyển động) — không phải chống giả cấp ngân hàng.
- Đây là lớp **răn đe/tiện lợi**, không thay thế mật khẩu mạnh + mã hóa ổ đĩa (BitLocker).

## 📄 Giấy phép

[MIT](LICENSE)
