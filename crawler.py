# -*- coding: utf-8 -*-
"""Lấy dữ liệu món ăn + nguyên liệu từ API công khai TheMealDB (https://www.themealdb.com/api.php).

Quy trình: gọi API -> làm sạch -> chuyển đơn vị về g/ml/cái -> chia theo số suất -> lưu JSON -> nhập vào kho.
Chỉ dùng thư viện chuẩn (urllib) nên không cần cài thêm.
"""
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

import config
from exceptions import DuLieuKhongHopLe, LoiKetNoi, LoiNghiepVu
from models.mon_an import MonAn
from models.nguyen_lieu import NguyenLieu
from services.file_handler import JsonFile
from services.tien_ich import bo_dau
from services.validators import dinh_dang_ngay

RE_DINH_LUONG = re.compile(r"^\s*(?:(\d+)\s+)?(\d+/\d+|\d+(?:\.\d+)?)\s*([a-zA-Z]*)")
HE_SO_DON_VI = {"g": (1, "g"), "gram": (1, "g"), "grams": (1, "g"), "kg": (1000, "g"),
                "ml": (1, "ml"), "l": (1000, "ml"), "tbsp": (15, "ml"), "tblsp": (15, "ml"),
                "tsp": (5, "ml"), "cup": (240, "ml"), "cups": (240, "ml"), "oz": (28.35, "g"), "lb": (453.6, "g")}


def phan_tich_dinh_luong(chuoi):
    """'1 1/2 cups' -> (360.0, 'ml'); '200g' -> (200.0, 'g'); 'pinch' -> (5.0, 'g'); '3 cloves' -> (3.0, 'cái')."""
    m = RE_DINH_LUONG.match(chuoi or "")
    if not m:
        return 5.0, "g"
    nguyen, so, dv = m.groups()
    try:
        if "/" in so:
            tu, mau = so.split("/")
            gia_tri = int(tu) / int(mau)
        else:
            gia_tri = float(so)
        if nguyen:
            gia_tri += int(nguyen)
    except (ValueError, ZeroDivisionError):
        return 5.0, "g"
    he_so, don_vi = HE_SO_DON_VI.get(dv.lower(), (1, "cái"))
    return round(gia_tri * he_so, 2), don_vi


def lay_json(url, timeout=config.API_TIMEOUT):
    yeu_cau = urllib.request.Request(url, headers={"User-Agent": "KhoNguyenLieuApp/1.0 (do an hoc tap)"})
    try:
        with urllib.request.urlopen(yeu_cau, timeout=timeout) as phan_hoi:
            noi_dung = phan_hoi.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise LoiKetNoi(f"Máy chủ API trả về lỗi {e.code}.") from None
    except urllib.error.URLError as e:
        raise LoiKetNoi(f"Không kết nối được tới API (kiểm tra Internet): {e.reason}") from None
    except (TimeoutError, socket.timeout):
        raise LoiKetNoi(f"API không phản hồi sau {timeout} giây.") from None
    except (OSError, UnicodeDecodeError) as e:
        raise LoiKetNoi(f"Lỗi khi nhận dữ liệu: {e}") from None
    try:
        return json.loads(noi_dung)
    except json.JSONDecodeError:
        raise LoiKetNoi("Dữ liệu API trả về không phải JSON hợp lệ.") from None


def lam_sach_mon(meal):
    """Chuyển 1 bản ghi API thành dict gọn; trả về None nếu thiếu dữ liệu bắt buộc."""
    if not isinstance(meal, dict):
        return None
    ten, id_ = (meal.get("strMeal") or "").strip(), (meal.get("idMeal") or "").strip()
    if not ten or not id_:
        return None
    dinh_muc, da_co = [], set()
    for i in range(1, 21):
        nl = (meal.get(f"strIngredient{i}") or "").strip()
        if not nl or nl.lower() in da_co:
            continue
        da_co.add(nl.lower())
        sl, dv = phan_tich_dinh_luong(meal.get(f"strMeasure{i}"))
        dinh_muc.append({"ten": nl.title(), "so_luong": round(sl / config.SO_SUAT_GOC, 3), "don_vi": dv})
    if not dinh_muc:
        return None
    return {"id": id_, "ten_mon": ten, "dinh_muc": dinh_muc}


def crawl_mon_an(tu_khoa_ds, timeout=config.API_TIMEOUT, luu_vao=config.FILE_CRAWL):
    """Gọi API theo từng từ khóa (tiếng Anh, ví dụ 'chicken'), lưu kết quả vào JSON và trả về dict."""
    if not tu_khoa_ds:
        raise DuLieuKhongHopLe("Hãy nhập ít nhất một từ khóa (ví dụ: chicken, beef, fish).")
    mon_an, loi, da_co = [], [], set()
    for tk in tu_khoa_ds:
        try:
            du_lieu = lay_json(f"{config.API_URL}?s={urllib.parse.quote(tk)}", timeout)
        except LoiKetNoi as e:
            loi.append(f"'{tk}': {e}")
            continue
        for meal in (du_lieu.get("meals") if isinstance(du_lieu, dict) else None) or []:
            mon = lam_sach_mon(meal)
            if mon and mon["id"] not in da_co:
                da_co.add(mon["id"])
                mon_an.append(mon)
    if not mon_an:
        raise LoiKetNoi(("Không lấy được món ăn nào. " + " | ".join(loi)) if loi else "API không có món nào khớp từ khóa.")
    ket_qua = {"nguon": config.API_URL, "thoi_gian": datetime.now().isoformat(timespec="seconds"),
               "tu_khoa": list(tu_khoa_ds), "so_mon": len(mon_an), "loi": loi, "mon_an": mon_an}
    if luu_vao:
        JsonFile(luu_vao).ghi(ket_qua)
    return ket_qua


def nhap_crawl_vao_kho(kho, ket_qua):
    """Thêm món ăn và nguyên liệu (nếu chưa có) vào kho. Trả về (số món thêm, số nguyên liệu mới, số món bỏ qua)."""
    them_mon = them_nl = bo_qua = 0
    ten_da_co = {bo_dau(m.ten_mon) for m in kho.danh_sach_mon_an}
    han_mac_dinh = dinh_dang_ngay(date.today() + timedelta(days=30))
    for mon in ket_qua.get("mon_an", []):
        if bo_dau(mon.get("ten_mon", "")) in ten_da_co:
            bo_qua += 1
            continue
        moi, dinh_muc = [], {}
        try:
            for dong in mon["dinh_muc"]:
                nl = next((n for n in kho.danh_sach_nguyen_lieu if bo_dau(n.ten_nguyen_lieu) == bo_dau(dong["ten"])), None)
                if nl is None:
                    ma_moi = f"NL{int(kho.sinh_ma('NL')[2:]) + len(moi):03d}"   # các NL mới chưa nằm trong kho nên cộng thêm len(moi)
                    nl = NguyenLieu(ma_moi, dong["ten"], 0, dong["don_vi"], 0, han_mac_dinh)
                    moi.append(nl)
                dinh_muc[nl.ma_nguyen_lieu] = dinh_muc.get(nl.ma_nguyen_lieu, 0) + float(dong["so_luong"])
            mon_an = MonAn(kho.sinh_ma("MA"), mon["ten_mon"], dinh_muc)
        except (DuLieuKhongHopLe, KeyError, TypeError, ValueError):
            bo_qua += 1
            continue
        for nl in moi:
            kho.them_nguyen_lieu(nl)
        try:
            kho.them_mon_an(mon_an)
        except LoiNghiepVu:
            bo_qua += 1
            continue
        them_mon += 1
        them_nl += len(moi)
        ten_da_co.add(bo_dau(mon_an.ten_mon))
    return them_mon, them_nl, bo_qua
