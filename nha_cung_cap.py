"""Lớp dữ liệu NhaCungCap, kiểm tra SĐT/email/mã bằng Regular Expression."""
from exceptions import DuLieuKhongHopLe
from services.validators import kiem_tra_email, kiem_tra_ma, kiem_tra_sdt


class NhaCungCap:
    def __init__(self, ma_ncc, ten_ncc, so_dien_thoai, email=""):
        self.ma_ncc = str(ma_ncc or "").strip().upper()
        self.ten_ncc = str(ten_ncc or "").strip()
        self.so_dien_thoai = str(so_dien_thoai or "").strip()
        self.email = str(email or "").strip()
        loi = self.kiem_tra_du_lieu_regex()
        if loi:
            raise DuLieuKhongHopLe(" ".join(loi))

    def kiem_tra_du_lieu_regex(self):
        """Trả về danh sách lỗi (rỗng = hợp lệ). Dùng module re thông qua services.validators."""
        loi = []
        if not kiem_tra_ma(self.ma_ncc, "NCC"):
            loi.append("Mã nhà cung cấp phải có dạng NCC001.")
        if not self.ten_ncc:
            loi.append("Tên nhà cung cấp không được để trống.")
        if not kiem_tra_sdt(self.so_dien_thoai):
            loi.append("Số điện thoại phải gồm 10 số bắt đầu bằng 0 (hoặc +84 và 9 số).")
        if self.email and not kiem_tra_email(self.email):
            loi.append("Email không đúng định dạng (ví dụ ten@congty.vn).")
        return loi

    def hien_thi_thong_tin(self):
        return f"[{self.ma_ncc}] {self.ten_ncc} - {self.so_dien_thoai} - {self.email or 'không có email'}"

    def cap_nhat_thong_tin(self, ten_ncc=None, so_dien_thoai=None, email=None):
        moi = NhaCungCap(self.ma_ncc,
                         self.ten_ncc if ten_ncc is None else ten_ncc,
                         self.so_dien_thoai if so_dien_thoai is None else so_dien_thoai,
                         self.email if email is None else email)
        self.__dict__.update(moi.__dict__)

    def to_dict(self):
        return {"ma_ncc": self.ma_ncc, "ten_ncc": self.ten_ncc, "so_dien_thoai": self.so_dien_thoai, "email": self.email}

    @classmethod
    def from_dict(cls, d):
        return cls(d["ma_ncc"], d["ten_ncc"], d["so_dien_thoai"], d.get("email", ""))
