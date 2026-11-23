"""Giao dịch kho: lớp trừu tượng GiaoDichKho + PhieuNhap/PhieuXuat (kế thừa, đa hình, ghi đè phương thức)."""
from abc import ABC, abstractmethod

from exceptions import DuLieuKhongHopLe, LoiNghiepVu
from services.tien_ich import dinh_dang_so
from services.validators import bat_buoc, chuyen_so, parse_ngay


class GiaoDichKho(ABC):
    LOAI = ""          # "NHAP" / "XUAT"
    TRUONG_GIA = ""    # tên khóa đơn giá trong từng dòng

    def __init__(self, ma_giao_dich, ngay_giao_dich, nguoi_thuc_hien):
        self.ma_giao_dich = bat_buoc(ma_giao_dich, "Mã giao dịch")
        parse_ngay(ngay_giao_dich)
        self.ngay_giao_dich = str(ngay_giao_dich).strip()
        self.nguoi_thuc_hien = bat_buoc(nguoi_thuc_hien, "Người thực hiện")

    @abstractmethod
    def thuc_hien_giao_dich(self, kho):
        """Áp dụng giao dịch lên kho. Phải kiểm tra TOÀN BỘ dòng trước khi thay đổi tồn kho."""

    @abstractmethod
    def danh_sach_dong(self):
        """Các dòng chi tiết: [{'ma_nl':..., 'so_luong':...}, ...]"""

    @abstractmethod
    def ghi_chu(self):
        """Ghi chú hiển thị (nhà cung cấp / lý do xuất)."""

    @abstractmethod
    def to_dict(self):
        ...

    def tong_gia_tri(self):
        return sum(float(d.get("so_luong", 0)) * float(d.get(self.TRUONG_GIA, 0) or 0) for d in self.danh_sach_dong())

    def mo_ta(self, kho=None):
        phan = []
        for d in self.danh_sach_dong():
            ten, dv = d["ma_nl"], ""
            if kho is not None:
                nl = kho.tim_nguyen_lieu_theo_ma(d["ma_nl"])
                if nl:
                    ten, dv = nl.ten_nguyen_lieu, nl.don_vi
            phan.append(f"{ten} x{dinh_dang_so(d['so_luong'])}{dv}")
        return "; ".join(phan)


class PhieuNhap(GiaoDichKho):
    LOAI = "NHAP"
    TRUONG_GIA = "gia_nhap"

    def __init__(self, ma_giao_dich, ngay_giao_dich, nguoi_thuc_hien, ma_ncc, danh_sach_nhap):
        super().__init__(ma_giao_dich, ngay_giao_dich, nguoi_thuc_hien)
        self.ma_ncc = str(ma_ncc or "").strip().upper()
        self.danh_sach_nhap = danh_sach_nhap    # [{"ma_nl","so_luong","gia_nhap"?,"han_su_dung"?}]

    def danh_sach_dong(self):
        return self.danh_sach_nhap

    def ghi_chu(self):
        return f"NCC: {self.ma_ncc}" if self.ma_ncc else ""

    def thuc_hien_giao_dich(self, kho):
        if not self.danh_sach_nhap:
            raise LoiNghiepVu("Phiếu nhập phải có ít nhất một dòng nguyên liệu.")
        if self.ma_ncc:
            kho.lay_nha_cung_cap(self.ma_ncc)
        ke_hoach = []
        for dong in self.danh_sach_nhap:                      # bước 1: kiểm tra hết, chưa sửa gì
            nl = kho.lay_nguyen_lieu(dong.get("ma_nl", ""))
            sl = chuyen_so(dong.get("so_luong"), f"Số lượng nhập của '{nl.ten_nguyen_lieu}'", 0, lon_hon=True)
            gia = dong.get("gia_nhap")
            gia = nl.gia_nhap if gia in (None, "") else chuyen_so(gia, "Giá nhập", 0)
            han = (dong.get("han_su_dung") or "").strip()
            if han:
                parse_ngay(han)
            ke_hoach.append((nl, sl, gia, han, dong))
        for nl, sl, gia, han, dong in ke_hoach:               # bước 2: áp dụng
            nl.so_luong = nl.so_luong + sl
            nl.gia_nhap = gia
            if han:
                nl.han_su_dung = han
            if self.ma_ncc:
                nl.ma_ncc = self.ma_ncc
            dong["so_luong"], dong["gia_nhap"] = sl, gia

    def to_dict(self):
        return {"loai": self.LOAI, "ma_giao_dich": self.ma_giao_dich, "ngay_giao_dich": self.ngay_giao_dich,
                "nguoi_thuc_hien": self.nguoi_thuc_hien, "ma_ncc": self.ma_ncc, "danh_sach": self.danh_sach_nhap}


class PhieuXuat(GiaoDichKho):
    LOAI = "XUAT"
    TRUONG_GIA = "don_gia"

    def __init__(self, ma_giao_dich, ngay_giao_dich, nguoi_thuc_hien, danh_sach_xuat, ly_do_xuat):
        super().__init__(ma_giao_dich, ngay_giao_dich, nguoi_thuc_hien)
        self.danh_sach_xuat = danh_sach_xuat    # [{"ma_nl","so_luong","don_gia"?}]
        self.ly_do_xuat = bat_buoc(ly_do_xuat, "Lý do xuất")

    def danh_sach_dong(self):
        return self.danh_sach_xuat

    def ghi_chu(self):
        return self.ly_do_xuat

    def thuc_hien_giao_dich(self, kho):
        if not self.danh_sach_xuat:
            raise LoiNghiepVu("Phiếu xuất phải có ít nhất một dòng nguyên liệu.")
        can, so_luong_dong = {}, []
        for dong in self.danh_sach_xuat:                      # bước 1: kiểm tra
            nl = kho.lay_nguyen_lieu(dong.get("ma_nl", ""))
            sl = chuyen_so(dong.get("so_luong"), f"Số lượng xuất của '{nl.ten_nguyen_lieu}'", 0, lon_hon=True)
            can[nl.ma_nguyen_lieu] = can.get(nl.ma_nguyen_lieu, 0) + sl
            so_luong_dong.append((dong, nl, sl))
        for ma, tong in can.items():
            nl = kho.lay_nguyen_lieu(ma)
            if tong > nl.so_luong + 1e-9:
                raise LoiNghiepVu(f"Không đủ '{nl.ten_nguyen_lieu}' trong kho: cần {dinh_dang_so(tong)} "
                                  f"{nl.don_vi}, chỉ còn {dinh_dang_so(nl.so_luong)} {nl.don_vi}.")
        for dong, nl, sl in so_luong_dong:                    # bước 2: trừ kho
            nl.so_luong = max(0.0, round(nl.so_luong - sl, 3))
            dong["so_luong"], dong["don_gia"] = sl, nl.gia_nhap

    def to_dict(self):
        return {"loai": self.LOAI, "ma_giao_dich": self.ma_giao_dich, "ngay_giao_dich": self.ngay_giao_dich,
                "nguoi_thuc_hien": self.nguoi_thuc_hien, "ly_do_xuat": self.ly_do_xuat, "danh_sach": self.danh_sach_xuat}


def giao_dich_tu_dict(d):
    """Nhà máy (factory) dựng lại đúng lớp con từ JSON — không áp dụng lại lên tồn kho."""
    loai = d.get("loai")
    if loai == "NHAP":
        return PhieuNhap(d["ma_giao_dich"], d["ngay_giao_dich"], d["nguoi_thuc_hien"], d.get("ma_ncc", ""), d["danh_sach"])
    if loai == "XUAT":
        return PhieuXuat(d["ma_giao_dich"], d["ngay_giao_dich"], d["nguoi_thuc_hien"], d["danh_sach"], d["ly_do_xuat"])
    raise DuLieuKhongHopLe(f"Loại giao dịch không hợp lệ: {loai!r}")
