# -*- coding: utf-8 -*-
"""Lớp dữ liệu NguyenLieu: đóng gói thuộc tính bằng property, kiểm tra dữ liệu trong setter."""
from datetime import date

import config
from exceptions import DuLieuKhongHopLe
from services.tien_ich import dinh_dang_so, dinh_dang_tien
from services.validators import bat_buoc, chuyen_so, kiem_tra_ma, parse_ngay


class NguyenLieu:
    TRUONG_SUA = ("ten_nguyen_lieu", "so_luong", "don_vi", "gia_nhap", "han_su_dung", "ma_ncc", "muc_toi_thieu")

    def __init__(self, ma_nguyen_lieu, ten_nguyen_lieu, so_luong, don_vi, gia_nhap, han_su_dung,
                 ma_ncc="", muc_toi_thieu=config.MUC_TOI_THIEU_MAC_DINH):
        self.ma_nguyen_lieu = ma_nguyen_lieu
        self.ten_nguyen_lieu = ten_nguyen_lieu
        self.so_luong = so_luong
        self.don_vi = don_vi
        self.gia_nhap = gia_nhap
        self.han_su_dung = han_su_dung
        self.ma_ncc = ma_ncc
        self.muc_toi_thieu = muc_toi_thieu

    # ---------- Thuộc tính có kiểm tra ----------
    @property
    def ma_nguyen_lieu(self):
        return self._ma

    @ma_nguyen_lieu.setter
    def ma_nguyen_lieu(self, v):
        v = str(v or "").strip().upper()
        if not kiem_tra_ma(v, "NL"):
            raise DuLieuKhongHopLe("Mã nguyên liệu phải có dạng NL001 (NL + ít nhất 3 chữ số).")
        self._ma = v

    @property
    def ten_nguyen_lieu(self):
        return self._ten

    @ten_nguyen_lieu.setter
    def ten_nguyen_lieu(self, v):
        self._ten = bat_buoc(v, "Tên nguyên liệu")

    @property
    def so_luong(self):
        return self._so_luong

    @so_luong.setter
    def so_luong(self, v):
        self._so_luong = round(chuyen_so(v, "Số lượng", 0), 3)

    @property
    def don_vi(self):
        return self._don_vi

    @don_vi.setter
    def don_vi(self, v):
        self._don_vi = bat_buoc(v, "Đơn vị")

    @property
    def gia_nhap(self):
        return self._gia_nhap

    @gia_nhap.setter
    def gia_nhap(self, v):
        self._gia_nhap = chuyen_so(v, "Giá nhập", 0)

    @property
    def han_su_dung(self):
        return self._han

    @han_su_dung.setter
    def han_su_dung(self, v):
        parse_ngay(v)                      # ném lỗi nếu sai định dạng/ngày không có thật
        self._han = str(v).strip()

    @property
    def ma_ncc(self):
        return self._ma_ncc

    @ma_ncc.setter
    def ma_ncc(self, v):
        v = str(v or "").strip().upper()
        if v and not kiem_tra_ma(v, "NCC"):
            raise DuLieuKhongHopLe("Mã nhà cung cấp phải có dạng NCC001 (hoặc để trống).")
        self._ma_ncc = v

    @property
    def muc_toi_thieu(self):
        return self._muc

    @muc_toi_thieu.setter
    def muc_toi_thieu(self, v):
        self._muc = chuyen_so(v, "Mức tồn tối thiểu", 0)


# ---------- Nghiệp vụ ----------------------------------
    def gia_tri(self):
        return self.so_luong * self.gia_nhap

    def so_ngay_con_lai(self, ngay=None):
        return (parse_ngay(self.han_su_dung) - (ngay or date.today())).days

    def kiem_tra_so_luong(self, muc=None):
        """True nếu tồn kho <= mức tối thiểu (mặc định dùng mức của chính nguyên liệu)."""
        return self.so_luong <= (self.muc_toi_thieu if muc is None else muc)

    def kiem_tra_han_su_dung(self, so_ngay=0):
        """True nếu ĐÃ hết hạn hoặc sẽ hết hạn trong vòng so_ngay ngày tới."""
        return self.so_ngay_con_lai() <= so_ngay

    def trang_thai(self, so_ngay=config.SO_NGAY_CANH_BAO_MAC_DINH):
        con = self.so_ngay_con_lai()
        if con < 0:
            return "Đã hết hạn"
        if con <= so_ngay:
            return "Sắp hết hạn"
        if self.kiem_tra_so_luong():
            return "Sắp hết hàng"
        return "Bình thường"

    def hien_thi_thong_tin(self):
        return (f"[{self.ma_nguyen_lieu}] {self.ten_nguyen_lieu}: {dinh_dang_so(self.so_luong)} {self.don_vi} "
                f"x {dinh_dang_tien(self.gia_nhap)}đ | HSD {self.han_su_dung} | NCC {self.ma_ncc or '-'}")

    def cap_nhat_thong_tin(self, **thay_doi):
        """Cập nhật 'nguyên tử': nếu có trường sai thì đối tượng giữ nguyên như cũ."""
        khong_hop_le = set(thay_doi) - set(self.TRUONG_SUA)
        if khong_hop_le:
            raise DuLieuKhongHopLe(f"Không thể cập nhật trường: {', '.join(sorted(khong_hop_le))}")
        du_lieu = self.to_dict()
        du_lieu.update(thay_doi)
        moi = NguyenLieu.from_dict(du_lieu)                     # kiểm tra toàn bộ trước
        self.__dict__.update(moi.__dict__)

    # ---------- JSON ----------
    def to_dict(self):
        return {"ma_nguyen_lieu": self.ma_nguyen_lieu, "ten_nguyen_lieu": self.ten_nguyen_lieu,
                "so_luong": self.so_luong, "don_vi": self.don_vi, "gia_nhap": self.gia_nhap,
                "han_su_dung": self.han_su_dung, "ma_ncc": self.ma_ncc, "muc_toi_thieu": self.muc_toi_thieu}

    @classmethod
    def from_dict(cls, d):
        return cls(d["ma_nguyen_lieu"], d["ten_nguyen_lieu"], d["so_luong"], d["don_vi"], d["gia_nhap"],
                   d["han_su_dung"], d.get("ma_ncc", ""), d.get("muc_toi_thieu", config.MUC_TOI_THIEU_MAC_DINH))


