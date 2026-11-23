"""Hàm tiện ích định dạng và chuẩn hóa chuỗi."""
import unicodedata


def bo_dau(chuoi):
    """Chuyển về chữ thường không dấu: 'Cà Chua' -> 'ca chua' (phục vụ tìm kiếm tiếng Việt)."""
    chuoi = (chuoi or "").replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", chuoi)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def dinh_dang_so(x):
    """2.0 -> '2', 2.5 -> '2.5'."""
    s = f"{float(x):.3f}".rstrip("0").rstrip(".")
    return s or "0"


def dinh_dang_tien(x):
    """1250000 -> '1.250.000'."""
    return f"{float(x):,.0f}".replace(",", ".")
