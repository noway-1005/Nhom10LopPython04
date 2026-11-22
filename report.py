# -*- coding: utf-8 -*-
"""Xuất báo cáo ra CSV / JSON / TXT."""
import csv
import json
import os
from datetime import datetime

import config
from exceptions import LoiFile
from services.tien_ich import dinh_dang_so, dinh_dang_tien


def _mo(duong_dan, che_do="w", **kw):
    os.makedirs(os.path.dirname(os.path.abspath(duong_dan)), exist_ok=True)
    return open(duong_dan, che_do, encoding="utf-8-sig" if kw.pop("bom", False) else "utf-8", **kw)


def xuat_ton_kho_csv(kho, duong_dan):
    try:
        with _mo(duong_dan, newline="", bom=True) as f:          # utf-8-sig để Excel đọc đúng tiếng Việt
            w = csv.writer(f)
            w.writerow(["Mã", "Tên nguyên liệu", "Số lượng", "Đơn vị", "Giá nhập", "Giá trị", "Hạn sử dụng", "NCC", "Trạng thái"])
            for n in kho.danh_sach_nguyen_lieu:
                w.writerow([n.ma_nguyen_lieu, n.ten_nguyen_lieu, dinh_dang_so(n.so_luong), n.don_vi,
                            int(n.gia_nhap), int(n.gia_tri()), n.han_su_dung, n.ma_ncc, n.trang_thai()])
    except OSError as e:
        raise LoiFile(f"Không ghi được file báo cáo: {e}") from None


def xuat_ton_kho_json(kho, duong_dan):
    try:
        with _mo(duong_dan) as f:
            json.dump({"ngay_xuat": datetime.now().isoformat(timespec="seconds"),
                       "tong_gia_tri": kho.tinh_tong_gia_tri_kho(),
                       "nguyen_lieu": [n.to_dict() for n in kho.danh_sach_nguyen_lieu]}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        raise LoiFile(f"Không ghi được file báo cáo: {e}") from None


def xuat_nhap_xuat_csv(kho, duong_dan, loai=None, tu_ngay="", den_ngay=""):
    ds = kho.loc_giao_dich(loai, tu_ngay, den_ngay)
    try:
        with _mo(duong_dan, newline="", bom=True) as f:
            w = csv.writer(f)
            w.writerow(["Mã GD", "Loại", "Ngày", "Người thực hiện", "Mã NL", "Tên NL", "Số lượng", "Đơn vị", "Đơn giá", "Thành tiền", "Ghi chú"])
            for g in ds:
                for d in g.danh_sach_dong():
                    nl = kho.tim_nguyen_lieu_theo_ma(d["ma_nl"])
                    gia = float(d.get(g.TRUONG_GIA, 0) or 0)
                    w.writerow([g.ma_giao_dich, "Nhập" if g.LOAI == "NHAP" else "Xuất", g.ngay_giao_dich, g.nguoi_thuc_hien,
                                d["ma_nl"], nl.ten_nguyen_lieu if nl else "", dinh_dang_so(d["so_luong"]),
                                nl.don_vi if nl else "", int(gia), int(gia * float(d["so_luong"])), g.ghi_chu()])
    except OSError as e:
        raise LoiFile(f"Không ghi được file báo cáo: {e}") from None
    return len(ds)


def xuat_bao_cao_tong_hop_txt(kho, duong_dan, so_ngay=config.SO_NGAY_CANH_BAO_MAC_DINH):
    dong = [f"BÁO CÁO KHO NGUYÊN LIỆU - {datetime.now():%d/%m/%Y %H:%M}", "=" * 60,
            f"Số loại nguyên liệu : {len(kho.danh_sach_nguyen_lieu)}",
            f"Tổng giá trị kho    : {dinh_dang_tien(kho.tinh_tong_gia_tri_kho())} đ", "",
            "NGUYÊN LIỆU SẮP HẾT HÀNG:"]
    dong += [f"  - {n.ten_nguyen_lieu}: còn {dinh_dang_so(n.so_luong)} {n.don_vi} (tối thiểu {dinh_dang_so(n.muc_toi_thieu)})"
             for n in kho.canh_bao_sap_het_hang()] or ["  (không có)"]
    dong += ["", f"NGUYÊN LIỆU HẾT HẠN / SẮP HẾT HẠN (≤ {so_ngay} ngày):"]
    dong += [f"  - {n.ten_nguyen_lieu}: HSD {n.han_su_dung} ({n.so_ngay_con_lai()} ngày)" for n in kho.canh_bao_sap_het_han(so_ngay)] or ["  (không có)"]
    tk = kho.thong_ke_nhap_xuat()
    dong += ["", "NHẬP/XUẤT:",
             f"  Nhập: {tk['NHAP']['so_phieu']} phiếu, {dinh_dang_tien(tk['NHAP']['gia_tri'])} đ",
             f"  Xuất: {tk['XUAT']['so_phieu']} phiếu, {dinh_dang_tien(tk['XUAT']['gia_tri'])} đ", "", "NGUYÊN LIỆU TIÊU THỤ NHIỀU NHẤT:"]
    top = sorted(kho.thong_ke_tieu_thu().values(), key=lambda m: m["gia_tri"], reverse=True)[:5]
    dong += [f"  - {m['ten']}: {dinh_dang_so(m['so_luong'])} {m['don_vi']} (~{dinh_dang_tien(m['gia_tri'])} đ)" for m in top] or ["  (chưa có phiếu xuất)"]
    try:
        with _mo(duong_dan) as f:
            f.write("\n".join(dong) + "\n")
    except OSError as e:
        raise LoiFile(f"Không ghi được file báo cáo: {e}") from None
