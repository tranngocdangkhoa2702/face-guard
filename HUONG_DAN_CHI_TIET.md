# 📖 Hướng dẫn sử dụng chi tiết — BaoVe_Lap

> Khóa máy Windows tự động bằng nhận diện khuôn mặt qua webcam, điều khiển từ xa
> bằng bot Telegram. Tài liệu này hướng dẫn **từng bước một**, kể cả khi bạn chưa
> rành kỹ thuật. Cứ làm tuần tự từ trên xuống là chạy được.

---

## Mục lục

1. [Nó hoạt động thế nào? (đọc 1 phút cho dễ hình dung)](#1-nó-hoạt-động-thế-nào)
2. [Chuẩn bị máy](#2-chuẩn-bị-máy)
3. [Cài đặt từng bước](#3-cài-đặt-từng-bước)
4. [Đăng ký khuôn mặt](#4-đăng-ký-khuôn-mặt)
5. [Chạy thử để kiểm tra](#5-chạy-thử-để-kiểm-tra)
6. [Chạy ngầm + tự khởi động cùng Windows](#6-chạy-ngầm--tự-khởi-động-cùng-windows)
7. [Thiết lập bot Telegram (điều khiển từ điện thoại)](#7-thiết-lập-bot-telegram)
8. [Bảng lệnh bot Telegram](#8-bảng-lệnh-bot-telegram)
9. [Thêm / xóa người tin cậy](#9-thêm--xóa-người-tin-cậy)
10. [Tinh chỉnh config.json](#10-tinh-chỉnh-configjson)
11. [Dừng / bật lại canh gác](#11-dừng--bật-lại-canh-gác)
12. [Xử lý sự cố thường gặp](#12-xử-lý-sự-cố-thường-gặp)
13. [Gỡ cài đặt sạch sẽ](#13-gỡ-cài-đặt-sạch-sẽ)
14. [Quyền riêng tư & giới hạn](#14-quyền-riêng-tư--giới-hạn)

---

## 1. Nó hoạt động thế nào?

- **Bình thường camera TẮT.** Chương trình chỉ lặng lẽ theo dõi bàn phím/chuột (không
  tốn CPU, không quay lén).
- Khi nghi ngờ — bạn vừa rời đi, hoặc ai đó đụng máy sau một lúc im lặng — chương trình
  **bật webcam vài giây** để nhìn xem ai đang ngồi:
  - Là **bạn / người tin cậy** → tắt cam, không làm gì.
  - Là **người lạ / không thấy mặt** → **khóa máy** (như bấm `Win + L`) và gửi cảnh báo
    kèm ảnh về Telegram (nếu đã cài bot).
- Nhận diện bằng 2 model AI nhỏ chạy trên CPU: **YuNet** (tìm khuôn mặt) + **SFace**
  (biến mặt thành "dấu vân tay số" để so khớp). Không cần GPU, không cần internet để nhận diện.
- Dữ liệu khuôn mặt được **mã hóa** gắn với tài khoản Windows của bạn — copy sang máy
  khác là vô dụng.

> Đây là lớp **răn đe + tiện lợi**, KHÔNG thay thế mật khẩu Windows mạnh và mã hóa ổ đĩa
> (BitLocker). Hãy dùng kèm, đừng dùng thay.

---

## 2. Chuẩn bị máy

Bạn cần:

| Thứ | Ghi chú |
|-----|---------|
| **Windows 10 hoặc 11** | Bắt buộc (dùng các API riêng của Windows). |
| **Python 3.9 trở lên** | Đã chạy thật trên Python 3.14. |
| **Webcam** | Webcam laptop tích hợp là đủ. |
| **Tài khoản Telegram** | *Tùy chọn* — chỉ cần nếu muốn điều khiển từ điện thoại. |
| **Git** | *Tùy chọn* — để `git clone`. Không có thì tải file ZIP về cũng được. |

### Kiểm tra đã có Python chưa

Mở **Command Prompt** (bấm phím Windows, gõ `cmd`, Enter) rồi gõ:

```bat
python --version
```

- Hiện ra `Python 3.x.x` → OK, bỏ qua.
- Báo lỗi "không tìm thấy" → tải Python tại <https://www.python.org/downloads/>.
  **Khi cài nhớ tích ô "Add Python to PATH"** ở màn hình đầu tiên.

> 💡 **Mẹo nhẹ ổ C:** Nên đặt cả dự án này lên một ổ khác ổ C (ví dụ ổ D) để không
> chiếm dung lượng ổ hệ thống. Môi trường Python (`.venv`) và model AI (~37 MB) sẽ nằm
> trong thư mục dự án.

---

## 3. Cài đặt từng bước

Mở **Command Prompt**, rồi làm lần lượt. (Thay `D:\` bằng ổ bạn muốn.)

```bat
:: 1) Vào ổ đĩa muốn đặt dự án rồi tải mã nguồn về
D:
git clone https://github.com/<tài-khoản>/face-guard.git BaoVe_Lap
cd BaoVe_Lap
```

> Không có Git? Vào trang GitHub của dự án → nút **Code** → **Download ZIP**, giải nén
> ra, rồi `cd` vào thư mục đó.

```bat
:: 2) Tạo môi trường Python riêng cho dự án (không đụng Python hệ thống)
python -m venv .venv

:: 3) Cài thư viện cần thiết (OpenCV, numpy, requests)
.venv\Scripts\python -m pip install -r requirements.txt

:: 4) Tải 2 model AI về (~37 MB, chỉ chạy MỘT LẦN lúc cài)
.venv\Scripts\python download_models.py
```

Bước 4 sẽ in tiến độ `%`. Khi thấy `[OK] Da co du model trong data/models/` là xong.
Nếu mạng lỗi giữa chừng, cứ chạy lại lệnh đó — nó tự bỏ qua file đã tải.

> 🧹 Muốn gọn ổ đĩa, sau khi cài xong có thể dọn cache pip:
> `.venv\Scripts\python -m pip cache purge`

---

## 4. Đăng ký khuôn mặt

Đây là bước "dạy" cho máy biết mặt bạn. Chạy:

```bat
.venv\Scripts\python enroll.py "Tên bạn"
```

(Ví dụ: `.venv\Scripts\python enroll.py "An"`. Có thể gõ tiếng Việt không dấu cho chắc.)

Một cửa sổ webcam hiện lên. Hãy:

1. Ngồi cách camera khoảng **40–60 cm**, ánh sáng đủ (đừng ngồi ngược sáng).
2. **Nhìn vào camera và xoay nhẹ đầu**: trái → phải → lên → xuống. Nếu hay đeo kính,
   chụp cả lúc có kính và không kính.
3. Góc trên cửa sổ hiện `Da chup: X/40`. Cứ xoay đầu chậm cho nó đủ **40 mẫu**.
4. Đủ mẫu là tự lưu và đóng. (Muốn dừng sớm bấm **Q** — vẫn lưu nếu đã đủ ≥ 15 mẫu.)

Lưu xong bạn sẽ thấy dòng `[OK] Da luu '...' (... ) voi N mau (da ma hoa).`

### Chủ chính vs người tin cậy

- **Người đầu tiên** bạn đăng ký mặc định là **chủ chính** (👑).
- **Chủ chính** là người duy nhất được **tự học** thêm theo thời gian (cắt tóc, đổi kính
  dần vẫn nhận ra).
- Người khác (người nhà, đồng nghiệp) là **người tin cậy** — vẫn được coi như chủ máy
  (không bị khóa) nhưng không tự học.

```bat
:: Thêm một người tin cậy (người nhà)
.venv\Scripts\python enroll.py "Tên người nhà"

:: Chỉ định ai đó làm chủ chính (chỉ 1 người được làm chủ chính)
.venv\Scripts\python enroll.py "Tên bạn" --primary
```

> Đăng ký lại cùng một tên → ghi đè người cũ (dùng khi muốn chụp lại cho nét hơn).
> Đăng ký tên khác → thêm người mới, **không** xóa ai.

---

## 5. Chạy thử để kiểm tra

Trước khi để chạy ngầm, nên test xem máy nhận ra bạn không:

```bat
.venv\Scripts\python test_recognition.py
```

Nó bật cam ~8 giây, soi mặt rồi in ra tên khớp + điểm giống (cosine, **càng cao càng
giống**). Mặt bạn thường đạt **0.6–0.9**. Nếu thấy đúng tên mình → tuyệt, sẵn sàng dùng.

Muốn xem canh gác chạy thật **kèm cửa sổ log** để hiểu nó làm gì:

```bat
.venv\Scripts\python guard.py
```

Cửa sổ console sẽ in từng bước (đang theo dõi, bật cam kiểm tra, khớp ai...). Bấm
**Ctrl + C** để dừng. Khi đã yên tâm thì chuyển sang chạy ngầm ở mục 6.

---

## 6. Chạy ngầm + tự khởi động cùng Windows

### Chạy ngầm ngay bây giờ (không cửa sổ, kèm cả bot Telegram)

```bat
wscript.exe start_guard_hidden.vbs
```

Lệnh này bật **cả canh gác lẫn bot** chạy ẩn. Có chống chạy trùng (bật 2 lần không sao,
lần sau tự thoát).

### Cho tự bật mỗi khi mở máy

1. Bấm **Windows + R**, gõ `shell:startup`, Enter → mở thư mục Startup.
2. Tạo **shortcut** trỏ tới file `start_guard_hidden.vbs` trong thư mục dự án
   (chuột phải file → *Tạo shortcut* → kéo shortcut vào thư mục Startup vừa mở).

Từ lần sau, cứ đăng nhập Windows là canh gác tự chạy ngầm.

> 💡 Có thể tạo thêm vài shortcut Desktop cho tiện: trỏ tới `start_guard_hidden.vbs`
> ("Bật canh gác"), `stop_guard.bat` ("Tắt canh gác"), `enroll.bat` ("Đăng ký lại mặt").

---

## 7. Thiết lập bot Telegram

Bước này **tùy chọn** — chỉ làm nếu muốn xem trạng thái / khóa máy / chụp ảnh từ điện thoại.

### 7.1. Tạo bot và lấy token

1. Mở Telegram, tìm **@BotFather** (có dấu tích xanh).
2. Nhắn `/newbot`, làm theo hướng dẫn (đặt tên + username kết thúc bằng `bot`).
3. BotFather trả về một **token** dạng `1234567890:ABCdef...`. Giữ kỹ, **đừng cho ai**.

### 7.2. Lấy chat_id của bạn

1. Bấm vào link bot vừa tạo, nhắn cho nó **một tin bất kỳ** (ví dụ "hi").
2. Mở trình duyệt, vào địa chỉ (thay `<TOKEN>` bằng token thật):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Tìm đoạn `"chat":{"id":123456789,` — con số đó là **chat_id** của bạn.

### 7.3. Điền vào secrets.json

Trong thư mục dự án, **copy** file `secrets.example.json` thành `secrets.json`, rồi mở
bằng Notepad và điền:

```json
{
    "telegram_token": "DÁN_TOKEN_VÀO_ĐÂY",
    "telegram_chat_id": 123456789
}
```

- `telegram_token`: để trong dấu nháy kép.
- `telegram_chat_id`: số, **không** có nháy.

Lưu lại. Khởi động lại canh gác (mục 11) là bot hoạt động.

> ⚠️ **Tuyệt đối không** đẩy `secrets.json` lên git — file `.gitignore` đã chặn sẵn.
> Lỡ lộ token thì vào @BotFather gõ `/revoke` để hủy token cũ.
>
> 🔒 Bot **chỉ nghe đúng chat_id của bạn**. Người lạ nhắn vào bot sẽ bị lờ đi và ghi log.

---

## 8. Bảng lệnh bot Telegram

Trong khung chat với bot, gõ `/` sẽ hiện menu chọn nhanh.

| Lệnh | Việc |
|------|------|
| `/status` | Canh gác đang chạy không? Máy đang khóa hay mở? |
| `/photo` | Chụp 1 tấm xem ai đang ngồi trước máy (ảnh gửi về Telegram). |
| `/lock` | Khóa máy ngay lập tức từ xa. |
| `/log` | Xem 10 dòng nhật ký mới nhất. |
| `/people` | Liệt kê những người đã được đăng ký + vai trò. |
| `/xoa_nguoi <tên>` | Xóa 1 người khỏi kho. VD: `/xoa_nguoi An`. |
| `/stop` | Dừng canh gác (bot vẫn sống để còn bật lại). |
| `/start_guard` | Bật lại canh gác. |

Ngoài ra, **gửi hoặc forward một tấm ảnh** vào bot → ảnh được tải về thư mục `inbox\`
trên máy (tiện gửi nhanh ảnh từ điện thoại về máy tính).

---

## 9. Thêm / xóa người tin cậy

**Thêm:** chạy lại `enroll.py` với tên mới (xem [mục 4](#4-đăng-ký-khuôn-mặt)). Canh gác
sẽ tự nạp người mới ở lần kiểm tra kế tiếp, **không cần khởi động lại**.

**Xóa:**
- Từ điện thoại: `/xoa_nguoi <tên>` qua bot.
- Hoặc đăng ký lại từ đầu (đăng ký trùng tên = ghi đè).

Xem ai đang trong kho: gõ `/people` trên bot.

---

## 10. Tinh chỉnh config.json

Mọi thông số nằm trong `config.json`, **mỗi dòng đều có chú thích tiếng Việt** ngay bên
cạnh. Vài thông số hay chỉnh nhất:

| Khóa | Ý nghĩa | Khi nào chỉnh |
|------|---------|---------------|
| `match_threshold` | Độ giống tối thiểu (0.30–0.45) để coi là đúng người. | **Khóa nhầm chính bạn** → GIẢM (vd 0.30). **Người lạ lọt qua** → TĂNG (vd 0.42). |
| `liveness_min_motion` | Mức nhúc nhích tối thiểu để qua cửa chống ảnh giả. | Hay bị khóa oan khi ngồi yên → GIẢM. Muốn chặt hơn → TĂNG. |
| `idle_gap_seconds` | Im lặng bao lâu rồi có người đụng máy thì mới soi cam. | Thấy phiền vì soi quá thường → TĂNG. |
| `absence_lock_seconds` | Vắng mặt bao lâu thì kiểm tra để khóa. | — |
| `active_recheck_seconds` | Đang dùng máy thì bao lâu soi xác nhận lại 1 lần (0 = tắt). | — |
| `liveness_enabled` | Bật/tắt chống ảnh giả (`true`/`false`). | — |

> ⚠️ **Sửa `config.json` xong phải khởi động lại canh gác** (mục 11) mới có tác dụng.
> Riêng việc thêm/xóa người thì không cần — canh gác tự nạp lại.

---

## 11. Dừng / bật lại canh gác

**Dừng** (ví dụ cho mượn máy chơi game):

```bat
stop_guard.bat
```
hoặc nhắn `/stop` cho bot. (Lưu ý: lúc này máy **không được bảo vệ**.)

**Bật lại:**

```bat
wscript.exe start_guard_hidden.vbs
```
hoặc nhắn `/start_guard` cho bot, hoặc khởi động lại máy (nếu đã đặt tự chạy ở mục 6).

**Khởi động lại sau khi sửa config** (PowerShell):

```powershell
Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
wscript.exe start_guard_hidden.vbs
```

---

## 12. Xử lý sự cố thường gặp

| Hiện tượng | Cách xử lý |
|------------|-----------|
| **Không mở được webcam** | App khác (Zoom/Meet/Camera) đang giữ cam → đóng chúng. Hoặc webcam không phải số 0 → đổi `camera_index` trong `config.json` (thử 1, 2). |
| **Hay khóa nhầm chính bạn** | GIẢM `match_threshold` (vd 0.30) hoặc GIẢM `liveness_min_motion`. Hoặc đăng ký lại mặt cho nhiều mẫu/đủ sáng hơn. |
| **Người lạ không bị khóa** | TĂNG `match_threshold` (vd 0.42). |
| **Phòng tối không nhận ra mặt** | Webcam thường không có hồng ngoại → cần chút ánh sáng. Đăng ký thêm mẫu trong điều kiện sáng yếu cũng giúp. |
| **Bot không phản hồi** | Kiểm tra `secrets.json` đúng token + chat_id chưa; `/status` xem guard có chạy; xem `bot.log`. Phản hồi chậm thường do **mạng ra Telegram lag**. |
| **Không chắc đang chạy không** | Mở Task Manager tìm tiến trình `pythonw.exe` (1 guard thường hiện 2 dòng `pythonw`). Hoặc nhắn `/status`. |
| **Xem nhật ký** | Mở `guard.log` (canh gác) hoặc `bot.log` (bot) trong thư mục dự án. |

---

## 13. Gỡ cài đặt sạch sẽ

1. Dừng canh gác: chạy `stop_guard.bat`, rồi đóng cả bot:
   ```powershell
   Get-Process pythonw -ErrorAction SilentlyContinue | Stop-Process -Force
   ```
2. Xóa shortcut trong `shell:startup` (nếu đã tạo ở mục 6).
3. Xóa nguyên thư mục dự án `BaoVe_Lap`.

Chương trình **không** ghi gì vào Registry hay ổ C (trừ shortcut Startup bạn tự tạo).
Dữ liệu khuôn mặt nằm trong `data\` của dự án, xóa thư mục là sạch.

---

## 14. Quyền riêng tư & giới hạn

**Riêng tư:**
- Camera **tắt** trừ vài giây mỗi lần kiểm tra. Không quay/lưu video.
- "Dấu vân tay số" khuôn mặt được **mã hóa** (Windows DPAPI), lưu ở `data\people.dat`.
  Không lưu ảnh mặt thô.
- Token bot và dữ liệu khuôn mặt **không bao giờ** được đẩy lên git.

**Giới hạn (nói thật cho minh bạch):**
- Webcam thường không có hồng ngoại → phòng **tối hẳn** sẽ không nhận được mặt.
- Chống ảnh giả ở mức **nhẹ** (dò chuyển động) — không phải cấp ngân hàng; người cố tình
  giơ video chuyển động vẫn có thể qua.
- Đây là lớp **răn đe + tiện lợi**, **không thay thế** mật khẩu Windows mạnh và mã hóa ổ
  đĩa (BitLocker). Hãy bật cả hai.

---

*Có lỗi hay góp ý? Mở Issue trên GitHub. Chúc bạn dùng vui! 🛡️*
