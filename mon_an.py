# -*- coding: utf-8 -*-
"""Lớp MonAn: định mức nguyên liệu cho 1 suất, tính nhu cầu và chế biến (xuất kho tự động)."""
import math

from exceptions import DuLieuKhongHopLe, LoiNghiepVu
from models.giao_dich import PhieuXuat
from services.validators import bat_buoc, chuyen_so, hom_nay_str, kiem_tra_ma


class MonAn:
    def __init__(self, ma_mon, ten_mon, dinh_muc_nguyen_lieu):
        self.ma_mon = str(ma_mon or "").strip().upper()
        if not kiem_tra_ma(self.ma_mon, "MA"):
            raise DuLieuKhongHopLe("Mã món ăn phải có dạng MA001.")
        self.ten_mon = bat_buoc(ten_mon, "Tên món ăn")
        self.dinh_muc_nguyen_lieu = self._chuan_hoa(dinh_muc_nguyen_lieu)

    @staticmethod
    def _chuan_hoa(dinh_muc):
        if not isinstance(dinh_muc, dict) or not dinh_muc:
            raise DuLieuKhongHopLe("Món ăn phải có ít nhất một nguyên liệu trong định mức.")
        return {str(ma).strip().upper(): round(chuyen_so(sl, f"Định mức của {ma}", 0, lon_hon=True), 4)
                for ma, sl in dinh_muc.items()}

    def cap_nhat_mon_an(self, ten_mon=None, dinh_muc=None):
        ten = self.ten_mon if ten_mon is None else bat_buoc(ten_mon, "Tên món ăn")
        dm = self.dinh_muc_nguyen_lieu if dinh_muc is None else self._chuan_hoa(dinh_muc)
        self.ten_mon, self.dinh_muc_nguyen_lieu = ten, dm

    @staticmethod
    def _so_suat(so_luong_mon):
        so = chuyen_so(so_luong_mon, "Số suất", 0, lon_hon=True)
        if so != math.floor(so):
            raise DuLieuKhongHopLe("Số suất phải là số nguyên.")
        return int(so)

    def tinh_nguyen_lieu_can(self, so_luong_mon):
        """{ma_nl: tổng lượng cần cho so_luong_mon suất}"""
        so = self._so_suat(so_luong_mon)
        return {ma: round(dm * so, 4) for ma, dm in self.dinh_muc_nguyen_lieu.items()}

    def kiem_tra_kha_nang_che_bien(self, kho, so_luong_mon):
        """Trả về (đủ_hay_không, danh_sách_thiếu[(ma_nl, cần, có)])."""
        thieu = []
        for ma, can in self.tinh_nguyen_lieu_can(so_luong_mon).items():
            nl = kho.tim_nguyen_lieu_theo_ma(ma)
            co = nl.so_luong if nl else 0.0
            if can > co + 1e-9:
                thieu.append((ma, can, co))
        return (not thieu), thieu

    def che_bien(self, kho, so_luong_mon, nguoi_thuc_hien):
        """Tạo PhieuXuat tự động và ghi nhận qua kho (đa hình). Trả về phiếu xuất."""
        du, thieu = self.kiem_tra_kha_nang_che_bien(kho, so_luong_mon)
        if not du:
            chi_tiet = ", ".join(f"{m} (cần {c:g}, có {h:g})" for m, c, h in thieu)
            raise LoiNghiepVu(f"Không đủ nguyên liệu để chế biến: {chi_tiet}.")
        so = self._so_suat(so_luong_mon)
        dong = [{"ma_nl": ma, "so_luong": sl} for ma, sl in self.tinh_nguyen_lieu_can(so).items()]
        phieu = PhieuXuat(kho.sinh_ma("PX"), hom_nay_str(), nguoi_thuc_hien, dong, f"Chế biến {so} suất {self.ten_mon}")
        kho.ghi_nhan_giao_dich(phieu)
        return phieu

    def to_dict(self):
        return {"ma_mon": self.ma_mon, "ten_mon": self.ten_mon, "dinh_muc_nguyen_lieu": self.dinh_muc_nguyen_lieu}

    @classmethod
    def from_dict(cls, d):
        return cls(d["ma_mon"], d["ten_mon"], d["dinh_muc_nguyen_lieu"])
