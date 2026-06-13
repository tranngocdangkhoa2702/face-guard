# -*- coding: utf-8 -*-
"""Mã hóa dữ liệu gắn với tài khoản Windows (DPAPI - không cần mật khẩu rời).

Dùng cho kho khuôn mặt (people.dat): chỉ ĐÚNG tài khoản Windows này, TRÊN máy này
mới giải mã được. Copy file sang máy/tài khoản khác -> vô dụng.

Không cần cài gì thêm: gọi thẳng crypt32.dll của Windows qua ctypes.
"""
import ctypes
import json
import os
from ctypes import wintypes

_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data):
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    return _BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def protect(data: bytes) -> bytes:
    """Mã hóa bytes -> bytes (chỉ tài khoản Windows hiện tại giải được)."""
    src, _keep = _blob(data)
    out = _BLOB()
    if not _crypt32.CryptProtectData(
        ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)
    ):
        raise OSError("CryptProtectData that bai")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        _kernel32.LocalFree(out.pbData)


def unprotect(data: bytes) -> bytes:
    """Giải mã bytes do protect() tạo ra."""
    src, _keep = _blob(data)
    out = _BLOB()
    if not _crypt32.CryptUnprotectData(
        ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)
    ):
        raise OSError("CryptUnprotectData that bai (sai tai khoan/may?)")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        _kernel32.LocalFree(out.pbData)


def save_json(path, obj):
    """Lưu một object Python xuống file ĐÃ MÃ HÓA (ghi an toàn qua file tạm)."""
    raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(protect(raw))
    os.replace(tmp, path)


def load_json(path):
    """Đọc file mã hóa do save_json() tạo. Không có file -> trả về None."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return json.loads(unprotect(f.read()).decode("utf-8"))
