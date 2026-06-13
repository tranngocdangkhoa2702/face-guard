# -*- coding: utf-8 -*-
"""Phần dùng chung: đường dẫn, config, dò mặt (YuNet) + nhận diện (SFace).

Bộ não nhận diện đời mới (từ 13/06/2026):
- YuNet (FaceDetectorYN): dò vị trí mặt + 5 điểm mắt/mũi/miệng. Tốt cả khi nghiêng/tối.
- SFace (FaceRecognizerSF): biến mặt thành "dấu vân tay số" 128 chiều. So 2 mặt bằng
  cosine: CÀNG CAO càng giống (ngược với LBPH cũ). Cùng người: cosine >= ~0.36.
Hai model .onnx nằm ở data/models/ (chạy download_models.py để tải).
Kho khuôn mặt nhiều người được MÃ HÓA tại data/people.dat (xem crypto_store.py).
"""
import json
import os

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SECRETS_PATH = os.path.join(BASE_DIR, "secrets.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(DATA_DIR, "models")
YUNET_PATH = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
SFACE_PATH = os.path.join(MODELS_DIR, "face_recognition_sface_2021dec.onnx")
PEOPLE_PATH = os.path.join(DATA_DIR, "people.dat")  # kho khuôn mặt (đã mã hóa)
LOG_PATH = os.path.join(BASE_DIR, "guard.log")

DARK_MEAN = 60  # độ sáng trung bình khung hình dưới mức này = thiếu sáng

_GAMMA_LUT = np.array([((i / 255.0) ** 0.6) * 255 for i in range(256)], dtype=np.uint8)
_clahe = None
_detector = None
_recognizer = None


# ---------------------------------------------------------------- config
def load_config():
    """Đọc config.json rồi gộp secrets.json (token Telegram...) đè lên nếu có.

    Bí mật để riêng secrets.json (không commit git); config.json up git thoải mái.
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if os.path.exists(SECRETS_PATH):
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if not k.startswith("_"):  # bỏ qua dòng chú thích _comment
                    cfg[k] = v
    return cfg


# ---------------------------------------------------------------- camera + ánh sáng
def open_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap


def is_dark(frame):
    """Khung hình màu có thiếu sáng không (mean độ xám < DARK_MEAN)."""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean() < DARK_MEAN


def boost_if_dark(frame):
    """Khung hình màu thiếu sáng -> kéo sáng kênh độ chói để còn dò ra mặt.

    Đủ sáng thì trả về nguyên xi. Tối HẲN (không còn chút sáng) thì vẫn chịu —
    webcam thường không có hồng ngoại; màn hình chính là "đèn".
    """
    global _clahe
    if not is_dark(frame):
        return frame
    if _clahe is None:
        _clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    ycc = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycc)
    y = cv2.LUT(_clahe.apply(y), _GAMMA_LUT)
    return cv2.cvtColor(cv2.merge((y, cr, cb)), cv2.COLOR_YCrCb2BGR)


# ---------------------------------------------------------------- model YuNet/SFace
def models_ready():
    return os.path.exists(YUNET_PATH) and os.path.exists(SFACE_PATH)


def get_detector():
    """YuNet (dò mặt). Tải 1 lần rồi tái dùng. score_threshold lấy từ config."""
    global _detector
    if _detector is None:
        cfg = load_config()
        score = float(cfg.get("detect_score_threshold", 0.8))
        _detector = cv2.FaceDetectorYN.create(
            YUNET_PATH, "", (320, 320), score, 0.3, 5000)
    return _detector


def get_recognizer():
    """SFace (dấu vân tay số). Tải 1 lần rồi tái dùng."""
    global _recognizer
    if _recognizer is None:
        _recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")
    return _recognizer


def detect_faces(frame, relaxed=False):
    """Trả về mảng Nx15 các khuôn mặt (x,y,w,h, 5 điểm mốc, điểm tin cậy).

    relaxed=True: hạ ngưỡng tin cậy cho khung hình thiếu sáng (dễ bắt mặt mờ hơn,
    đổi lại dễ dính nhiễu hơn) — chỉ dùng khi tối mà cách chuẩn không thấy mặt.
    """
    det = get_detector()
    h, w = frame.shape[:2]
    det.setInputSize((w, h))
    if relaxed:
        det.setScoreThreshold(0.6)
    _, faces = det.detect(frame)
    if relaxed:
        det.setScoreThreshold(float(load_config().get("detect_score_threshold", 0.8)))
    return faces if faces is not None else np.empty((0, 15), dtype=np.float32)


def embed(frame, face_row):
    """Biến 1 khuôn mặt (1 hàng trong kết quả detect) thành vector 128 chiều,
    đã chuẩn hóa độ dài để so cosine bằng tích vô hướng."""
    rec = get_recognizer()
    aligned = rec.alignCrop(frame, face_row)
    feat = rec.feature(aligned).flatten().astype(np.float32)
    norm = np.linalg.norm(feat)
    return feat / norm if norm > 0 else feat


def cosine(a, b):
    """Độ giống giữa 2 vector đã chuẩn hóa: 1.0 = trùng khít, càng cao càng giống."""
    return float(np.dot(a, b))


# ---------------------------------------------------------------- kho khuôn mặt nhiều người
# Cấu trúc people.dat (đã mã hóa): {"version":2, "people":[{name, primary, embeddings:[[..],..]}]}
def load_people():
    import crypto_store
    data = crypto_store.load_json(PEOPLE_PATH)
    if not data:
        return []
    return data.get("people", [])


def save_people(people):
    import crypto_store
    os.makedirs(DATA_DIR, exist_ok=True)
    crypto_store.save_json(PEOPLE_PATH, {"version": 2, "people": people})


def people_embeddings(people):
    """Gộp tất cả embedding của mọi người thành (matrix Nx128, list tên, list primary)."""
    vecs, names, primaries = [], [], []
    for p in people:
        for e in p.get("embeddings", []):
            vecs.append(np.asarray(e, dtype=np.float32))
            names.append(p["name"])
            primaries.append(bool(p.get("primary", False)))
    if not vecs:
        return np.empty((0, 128), dtype=np.float32), [], []
    return np.vstack(vecs), names, primaries


def match_face(emb, mat, names, primaries, threshold):
    """So 1 khuôn mặt với kho. Trả về (name, is_primary, score) nếu khớp, else None."""
    if mat.shape[0] == 0:
        return None
    scores = mat @ emb  # cosine vì mọi vector đã chuẩn hóa
    i = int(np.argmax(scores))
    if scores[i] >= threshold:
        return names[i], primaries[i], float(scores[i])
    return None
