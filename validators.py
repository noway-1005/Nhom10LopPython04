"""Kiểm tra dữ liệu: Regular Expression (email, SĐT, mã định danh, ngày) và chuyển đổi số."""
import math
import re
from datetime import date, datetime

import config
from exceptions import DuLieuKhongHopLe

RE_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
RE_SDT = re.compile(r"^(0|\+84)\d{9}$")
RE_NGAY = re.compile(r"^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/\d{4}$")
RE_TEN_DANG_NHAP = re.compile(r"^[A-Za-z0-9_]{3,20}$")


def kiem_tra_email(s):
    return bool(RE_EMAIL.match((s or "").strip()))


def kiem_tra_sdt(s):
    return bool(RE_SDT.match((s or "").strip()))


def kiem_tra_ten_dang_nhap(s):
    return bool(RE_TEN_DANG_NHAP.match(s or ""))


def kiem_tra_ma(ma, tien_to):
    """Mã định danh dạng <TIỀN TỐ><≥3 chữ số>, ví dụ NL001, NCC012, MA005."""
    return bool(re.match(rf"^{re.escape(tien_to)}\d{{3,}}$", ma or ""))


def kiem_tra_ngay(s):
    """Đúng dạng dd/mm/yyyy (Regex) và là ngày có thật (loại 31/02...)."""
    if not RE_NGAY.match(s or ""):
        return False
    try:
        datetime.strptime(s, config.DINH_DANG_NGAY)
        return True
    except ValueError:
        return False


def parse_ngay(s):
    s = (s or "").strip()
    if not kiem_tra_ngay(s):
        raise DuLieuKhongHopLe(f"Ngày '{s}' không hợp lệ. Hãy nhập đúng dạng dd/mm/yyyy (ví dụ 25/12/2026).")
    return datetime.strptime(s, config.DINH_DANG_NGAY).date()


def dinh_dang_ngay(d):
    return d.strftime(config.DINH_DANG_NGAY)


def hom_nay_str():
    return dinh_dang_ngay(date.today())


def bat_buoc(gia_tri, ten_truong):
    s = str(gia_tri if gia_tri is not None else "").strip()
    if not s:
        raise DuLieuKhongHopLe(f"{ten_truong} không được để trống.")
    return s


def chuyen_so(gia_tri, ten_truong, toi_thieu=0.0, lon_hon=False):
    """Chuyển sang số thực, kiểm tra miền giá trị. lon_hon=True: phải > toi_thieu, ngược lại >= toi_thieu."""
    if isinstance(gia_tri, bool):
        raise DuLieuKhongHopLe(f"{ten_truong} phải là số.")
    s = str(gia_tri if gia_tri is not None else "").strip().replace(",", ".")
    if not s:
        raise DuLieuKhongHopLe(f"{ten_truong} không được để trống.")
    try:
        so = float(s)
    except ValueError:
        raise DuLieuKhongHopLe(f"{ten_truong} phải là số (ví dụ 2.5, dùng dấu chấm cho phần thập phân).") from None
    if not math.isfinite(so):
        raise DuLieuKhongHopLe(f"{ten_truong} không hợp lệ.")
    if lon_hon and so <= toi_thieu:
        raise DuLieuKhongHopLe(f"{ten_truong} phải lớn hơn {toi_thieu:g}.")
    if not lon_hon and so < toi_thieu:
        raise DuLieuKhongHopLe(f"{ten_truong} không được nhỏ hơn {toi_thieu:g}.")
    return so
