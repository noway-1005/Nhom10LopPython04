"""Tab quản lý nguyên liệu: CRUD + tìm kiếm (theo mã/tên/NCC, gần đúng) + lọc trạng thái + sắp xếp."""
import tkinter as tk
from tkinter import messagebox, ttk

import config
from exceptions import DuLieuKhongHopLe
from models.nguyen_lieu import NguyenLieu
from services.nhat_ky import ghi_nhat_ky
from services.tien_ich import dinh_dang_so, dinh_dang_tien
from ui.helpers import an_toan, dat_trang_thai, lay_ma_tu_combobox, tao_o_nhap
from ui.widgets import DataTree, DateEntry

TIEU_CHI = {"Tất cả": "tat_ca", "Mã": "ma", "Tên": "ten", "Nhà cung cấp": "ncc"}
BO_LOC = ["Tất cả", "Sắp hết hàng", "Sắp hết hạn", "Đã hết hạn"]
TAG = {"Đã hết hạn": "het_han", "Sắp hết hạn": "sap_het_han", "Sắp hết hàng": "sap_het_hang"}
COT = [("ma", "Mã", 70), ("ten", "Tên nguyên liệu", 170), ("sl", "Tồn", 70, "e"), ("dv", "ĐV", 50, "center"),
       ("gia", "Giá nhập", 90, "e"), ("hsd", "Hạn SD", 90, "center"), ("ncc", "NCC", 70, "center"),
       ("min", "Tối thiểu", 70, "e"), ("gt", "Giá trị (đ)", 100, "e"), ("tt", "Trạng thái", 100)]


class TabNguyenLieu(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self._ma_chon = None
        self._dung_giao_dien()
        self.lam_moi()
        self._lam_trong()
        self.ap_dung_quyen()

    def _dung_giao_dien(self):
        # --- Khung tìm kiếm & lọc
        kt = ttk.LabelFrame(self, text="Tìm kiếm & lọc", padding=6)
        kt.pack(fill="x")
        self.v_tu_khoa, self.v_tieu_chi = tk.StringVar(), tk.StringVar(value="Tất cả")
        self.v_loc, self.v_gan_dung = tk.StringVar(value="Tất cả"), tk.BooleanVar()
        e = tao_o_nhap(kt, "Từ khóa:", 0, 0, ttk.Entry(kt, textvariable=self.v_tu_khoa, width=22))
        e.bind("<Return>", lambda _e: self.tim())
        c1 = tao_o_nhap(kt, "Tìm theo:", 0, 1, ttk.Combobox(kt, textvariable=self.v_tieu_chi, values=list(TIEU_CHI), state="readonly", width=13))
        c2 = tao_o_nhap(kt, "Trạng thái:", 0, 2, ttk.Combobox(kt, textvariable=self.v_loc, values=BO_LOC, state="readonly", width=13))
        for c in (c1, c2):
            c.bind("<<ComboboxSelected>>", lambda _e: self.tim())
        ttk.Checkbutton(kt, text="Gần đúng", variable=self.v_gan_dung, command=self.tim).grid(row=0, column=6, padx=6)
        ttk.Button(kt, text="Tìm", command=self.tim).grid(row=0, column=7, padx=2)
        ttk.Button(kt, text="Làm mới", command=self.lam_moi_nut).grid(row=0, column=8, padx=2)

        # --- Bảng dữ liệu
        self.bang = DataTree(self, COT, height=7)
        self.bang.pack(fill="both", expand=True, pady=6)
        self.bang.tree.bind("<<TreeviewSelect>>", self._chon)
        ttk.Label(self, foreground="#666666",
                  text="Màu dòng: đỏ = đã hết hạn · vàng = sắp hết hạn · cam = sắp hết hàng. Bấm tiêu đề cột để sắp xếp."
                  ).pack(fill="x")

        # --- Biểu mẫu
        fm = ttk.LabelFrame(self, text="Thông tin nguyên liệu", padding=6)
        fm.pack(fill="x", pady=(6, 0), side="bottom", before=self.bang)   # giữ chỗ cho form ở cuối, bảng lấy phần còn lại
        self.e_ma = tao_o_nhap(fm, "Mã (NL001):", 0, 0, ttk.Entry(fm, width=14))
        self.e_ten = tao_o_nhap(fm, "Tên:", 0, 1, ttk.Entry(fm, width=22))
        self.e_sl = tao_o_nhap(fm, "Số lượng:", 0, 2, ttk.Entry(fm, width=12))
        self.cb_dv = tao_o_nhap(fm, "Đơn vị:", 0, 3, ttk.Combobox(fm, values=config.DON_VI, width=10))
        self.e_gia = tao_o_nhap(fm, "Giá nhập (đ):", 1, 0, ttk.Entry(fm, width=14))
        self.d_han = tao_o_nhap(fm, "Hạn sử dụng:", 1, 1, DateEntry(fm))
        self.cb_ncc = tao_o_nhap(fm, "Nhà cung cấp:", 1, 2, ttk.Combobox(fm, state="readonly", width=24))
        self.e_min = tao_o_nhap(fm, "Tồn tối thiểu:", 1, 3, ttk.Entry(fm, width=10))
        nut = ttk.Frame(fm)
        nut.grid(row=2, column=0, columnspan=8, pady=(8, 0))
        self.b_them = ttk.Button(nut, text="Thêm mới", style="Accent.TButton", command=self.them)
        self.b_sua = ttk.Button(nut, text="Cập nhật", command=self.cap_nhat)
        self.b_xoa = ttk.Button(nut, text="Xóa", command=self.xoa)
        for i, b in enumerate((self.b_them, self.b_sua, self.b_xoa)):
            b.grid(row=0, column=i, padx=4)
        ttk.Button(nut, text="Làm trống form", command=self._lam_trong).grid(row=0, column=3, padx=4)
        self._o_form = [self.e_ma, self.e_ten, self.e_sl, self.cb_dv, self.e_gia, self.d_han, self.cb_ncc, self.e_min]
        for i in range(8):
            fm.columnconfigure(i, weight=1 if i % 2 else 0)

    # ---------- Hiển thị ----------
    def lam_moi(self):
        self.cb_ncc["values"] = ["(không)"] + [f"{n.ma_ncc} - {n.ten_ncc}" for n in self.kho.danh_sach_nha_cung_cap]
        self.tim()

    def lam_moi_nut(self):
        self.v_tu_khoa.set("")
        self.v_tieu_chi.set("Tất cả")
        self.v_loc.set("Tất cả")
        self.v_gan_dung.set(False)
        self.lam_moi()

    @an_toan
    def tim(self):
        ds = self.kho.tim_kiem_nguyen_lieu(self.v_tu_khoa.get(), TIEU_CHI[self.v_tieu_chi.get()], self.v_loc.get(), self.v_gan_dung.get())
        self.bang.nap([(n.ma_nguyen_lieu,
                        [n.ma_nguyen_lieu, n.ten_nguyen_lieu, dinh_dang_so(n.so_luong), n.don_vi, dinh_dang_tien(n.gia_nhap),
                         n.han_su_dung, n.ma_ncc, dinh_dang_so(n.muc_toi_thieu), dinh_dang_tien(n.gia_tri()), n.trang_thai()],
                        TAG.get(n.trang_thai())) for n in ds])
        self.mh.dat_thong_bao(f"Hiển thị {len(ds)}/{len(self.kho.danh_sach_nguyen_lieu)} nguyên liệu")

    def _chon(self, _e=None):
        ma = self.bang.chon()
        if not ma:
            return
        n = self.kho.tim_nguyen_lieu_theo_ma(ma)
        if n is None:
            return
        self._ma_chon = ma
        self._dat(self.e_ma, n.ma_nguyen_lieu)
        self.e_ma.configure(state="readonly")        # không cho đổi mã khi sửa
        self._dat(self.e_ten, n.ten_nguyen_lieu)
        self._dat(self.e_sl, dinh_dang_so(n.so_luong))
        self.cb_dv.set(n.don_vi)
        self._dat(self.e_gia, dinh_dang_so(n.gia_nhap))
        self.d_han.set(n.han_su_dung)
        ncc = self.kho.tim_ncc_theo_ma(n.ma_ncc)
        self.cb_ncc.set(f"{ncc.ma_ncc} - {ncc.ten_ncc}" if ncc else "(không)")
        self._dat(self.e_min, dinh_dang_so(n.muc_toi_thieu))

    @staticmethod
    def _dat(entry, gia_tri):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, gia_tri)

    def _lam_trong(self):
        self._ma_chon = None
        for e in (self.e_ma, self.e_ten, self.e_sl, self.e_gia, self.e_min):
            self._dat(e, "")
        self._dat(self.e_ma, self.kho.sinh_ma("NL"))
        self._dat(self.e_min, dinh_dang_so(config.MUC_TOI_THIEU_MAC_DINH))
        self.cb_dv.set(config.DON_VI[0])
        self.cb_ncc.set("(không)")
        self.d_han.set("")
        if self.bang.chon():
            self.bang.tree.selection_remove(self.bang.chon())

    def _doc_form(self):
        return {"ma_nguyen_lieu": self.e_ma.get(), "ten_nguyen_lieu": self.e_ten.get(), "so_luong": self.e_sl.get(),
                "don_vi": self.cb_dv.get(), "gia_nhap": self.e_gia.get(), "han_su_dung": self.d_han.get(),
                "ma_ncc": lay_ma_tu_combobox(self.cb_ncc.get()), "muc_toi_thieu": self.e_min.get()}

    # ---------- Thao tác ----------
    @an_toan
    def them(self):
        self.mh.auth.yeu_cau_quyen("sua_nguyen_lieu")
        nl = NguyenLieu(**self._doc_form())
        self.kho.them_nguyen_lieu(nl)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Thêm nguyên liệu {nl.ma_nguyen_lieu}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()
        messagebox.showinfo("Thành công", f"Đã thêm nguyên liệu '{nl.ten_nguyen_lieu}'.")

    @an_toan
    def cap_nhat(self):
        self.mh.auth.yeu_cau_quyen("sua_nguyen_lieu")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một nguyên liệu trong bảng trước khi cập nhật.")
        du_lieu = self._doc_form()
        du_lieu.pop("ma_nguyen_lieu")
        self.kho.cap_nhat_nguyen_lieu(self._ma_chon, **du_lieu)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Cập nhật nguyên liệu {self._ma_chon}")
        ma = self._ma_chon
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", f"Đã cập nhật nguyên liệu {ma}.")

    @an_toan
    def xoa(self):
        self.mh.auth.yeu_cau_quyen("sua_nguyen_lieu")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một nguyên liệu trong bảng trước khi xóa.")
        nl = self.kho.lay_nguyen_lieu(self._ma_chon)
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa nguyên liệu '{nl.ten_nguyen_lieu}' ({nl.ma_nguyen_lieu})?\nThao tác không thể hoàn tác."):
            return
        self.kho.xoa_nguyen_lieu(nl.ma_nguyen_lieu)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Xóa nguyên liệu {nl.ma_nguyen_lieu}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()

    def ap_dung_quyen(self):
        bat = self.mh.auth.co_quyen("sua_nguyen_lieu")
        dat_trang_thai([self.b_them, self.b_sua, self.b_xoa], bat)
