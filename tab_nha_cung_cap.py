"""Tab quản lý nhà cung cấp (CRUD + tìm kiếm). Regex kiểm tra SĐT/email nằm trong lớp NhaCungCap."""
import tkinter as tk
from tkinter import messagebox, ttk

from exceptions import DuLieuKhongHopLe
from models.nha_cung_cap import NhaCungCap
from services.nhat_ky import ghi_nhat_ky
from ui.helpers import an_toan, dat_trang_thai, tao_o_nhap
from ui.widgets import DataTree

TIEU_CHI = {"Tất cả": "tat_ca", "Mã": "ma", "Tên": "ten", "Số điện thoại": "sdt"}
COT = [("ma", "Mã", 80), ("ten", "Tên nhà cung cấp", 260), ("sdt", "Số điện thoại", 120), ("email", "Email", 240), ("sl", "Số NL cung cấp", 110, "center")]


class TabNhaCungCap(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self._ma_chon = None
        kt = ttk.LabelFrame(self, text="Tìm kiếm", padding=6)
        kt.pack(fill="x")
        self.v_tu_khoa, self.v_tieu_chi = tk.StringVar(), tk.StringVar(value="Tất cả")
        e = tao_o_nhap(kt, "Từ khóa:", 0, 0, ttk.Entry(kt, textvariable=self.v_tu_khoa, width=26))
        e.bind("<Return>", lambda _e: self.lam_moi())
        c = tao_o_nhap(kt, "Tìm theo:", 0, 1, ttk.Combobox(kt, textvariable=self.v_tieu_chi, values=list(TIEU_CHI), state="readonly", width=14))
        c.bind("<<ComboboxSelected>>", lambda _e: self.lam_moi())
        ttk.Button(kt, text="Tìm", command=self.lam_moi).grid(row=0, column=4, padx=4)

        self.bang = DataTree(self, COT, height=6)
        self.bang.pack(fill="both", expand=True, pady=6)
        self.bang.tree.bind("<<TreeviewSelect>>", self._chon)

        fm = ttk.LabelFrame(self, text="Thông tin nhà cung cấp", padding=6)
        fm.pack(fill="x", side="bottom", before=self.bang)
        self.e_ma = tao_o_nhap(fm, "Mã (NCC001):", 0, 0, ttk.Entry(fm, width=14))
        self.e_ten = tao_o_nhap(fm, "Tên:", 0, 1, ttk.Entry(fm, width=30))
        self.e_sdt = tao_o_nhap(fm, "Số điện thoại:", 1, 0, ttk.Entry(fm, width=14))
        self.e_email = tao_o_nhap(fm, "Email:", 1, 1, ttk.Entry(fm, width=30))
        nut = ttk.Frame(fm)
        nut.grid(row=2, column=0, columnspan=4, pady=(8, 0))
        self.b_them = ttk.Button(nut, text="Thêm mới", style="Accent.TButton", command=self.them)
        self.b_sua = ttk.Button(nut, text="Cập nhật", command=self.cap_nhat)
        self.b_xoa = ttk.Button(nut, text="Xóa", command=self.xoa)
        for i, b in enumerate((self.b_them, self.b_sua, self.b_xoa)):
            b.grid(row=0, column=i, padx=4)
        ttk.Button(nut, text="Làm trống form", command=self._lam_trong).grid(row=0, column=3, padx=4)
        fm.columnconfigure(3, weight=1)
        self.lam_moi()
        self._lam_trong()
        self.ap_dung_quyen()

    @staticmethod
    def _dat(entry, gia_tri):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, gia_tri)

    def lam_moi(self):
        ds = self.kho.tim_kiem_nha_cung_cap(self.v_tu_khoa.get(), TIEU_CHI[self.v_tieu_chi.get()])
        dem = {}
        for n in self.kho.danh_sach_nguyen_lieu:
            dem[n.ma_ncc] = dem.get(n.ma_ncc, 0) + 1
        self.bang.nap([(n.ma_ncc, [n.ma_ncc, n.ten_ncc, n.so_dien_thoai, n.email, dem.get(n.ma_ncc, 0)]) for n in ds])

    def _chon(self, _e=None):
        ma = self.bang.chon()
        n = self.kho.tim_ncc_theo_ma(ma) if ma else None
        if n is None:
            return
        self._ma_chon = ma
        self._dat(self.e_ma, n.ma_ncc)
        self.e_ma.configure(state="readonly")
        self._dat(self.e_ten, n.ten_ncc)
        self._dat(self.e_sdt, n.so_dien_thoai)
        self._dat(self.e_email, n.email)

    def _lam_trong(self):
        self._ma_chon = None
        for e in (self.e_ten, self.e_sdt, self.e_email):
            self._dat(e, "")
        self._dat(self.e_ma, self.kho.sinh_ma("NCC"))
        if self.bang.chon():
            self.bang.tree.selection_remove(self.bang.chon())

    @an_toan
    def them(self):
        self.mh.auth.yeu_cau_quyen("sua_ncc")
        ncc = NhaCungCap(self.e_ma.get(), self.e_ten.get(), self.e_sdt.get(), self.e_email.get())
        self.kho.them_nha_cung_cap(ncc)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Thêm NCC {ncc.ma_ncc}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()
        messagebox.showinfo("Thành công", f"Đã thêm nhà cung cấp '{ncc.ten_ncc}'.")

    @an_toan
    def cap_nhat(self):
        self.mh.auth.yeu_cau_quyen("sua_ncc")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một nhà cung cấp trong bảng trước khi cập nhật.")
        self.kho.cap_nhat_nha_cung_cap(self._ma_chon, ten_ncc=self.e_ten.get(), so_dien_thoai=self.e_sdt.get(), email=self.e_email.get())
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Cập nhật NCC {self._ma_chon}")
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", "Đã cập nhật nhà cung cấp.")

    @an_toan
    def xoa(self):
        self.mh.auth.yeu_cau_quyen("sua_ncc")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một nhà cung cấp trong bảng trước khi xóa.")
        ncc = self.kho.lay_nha_cung_cap(self._ma_chon)
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa nhà cung cấp '{ncc.ten_ncc}'?"):
            return
        self.kho.xoa_nha_cung_cap(ncc.ma_ncc)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Xóa NCC {ncc.ma_ncc}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()

    def ap_dung_quyen(self):
        dat_trang_thai([self.b_them, self.b_sua, self.b_xoa], self.mh.auth.co_quyen("sua_ncc"))
