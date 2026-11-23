# -*- coding: utf-8 -*-
"""Tab nhập/xuất kho: lập phiếu nhiều dòng, xem lịch sử (lọc loại + khoảng ngày), xuất báo cáo nhập/xuất."""
import copy
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
from exceptions import DuLieuKhongHopLe
from models.giao_dich import PhieuNhap, PhieuXuat
from services import report
from services.nhat_ky import ghi_nhat_ky
from services.tien_ich import dinh_dang_so, dinh_dang_tien
from services.validators import chuyen_so, parse_ngay
from ui.helpers import an_toan, dat_trang_thai, lay_ma_tu_combobox, tao_o_nhap
from ui.widgets import DataTree, DateEntry

COT_TAM = [("ma", "Mã NL", 70), ("ten", "Tên", 170), ("sl", "Số lượng", 80, "e"), ("dv", "ĐV", 50, "center"),
           ("gia", "Giá nhập", 90, "e"), ("hsd", "Hạn SD mới", 90, "center")]
COT_LS = [("ma", "Mã GD", 70), ("loai", "Loại", 60, "center"), ("ngay", "Ngày", 90, "center"), ("nguoi", "Người TH", 90),
          ("ct", "Chi tiết", 360), ("gt", "Giá trị (đ)", 100, "e"), ("gc", "Ghi chú", 170)]
LOC_LOAI = {"Tất cả": None, "Nhập": "NHAP", "Xuất": "XUAT"}


class TabGiaoDich(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self.dong_tam = []
        self.v_loai = tk.StringVar(value="XUAT")
        self._dung_giao_dien()
        self.lam_moi()
        self.ap_dung_quyen()
        self._doi_loai()

    def _dung_giao_dien(self):
        f = ttk.LabelFrame(self, text="Lập phiếu", padding=6)
        f.pack(fill="x")
        rd = ttk.Frame(f)
        rd.grid(row=0, column=0, columnspan=2, sticky="w")
        self.rb_nhap = ttk.Radiobutton(rd, text="Nhập kho", value="NHAP", variable=self.v_loai, command=self._doi_loai)
        self.rb_xuat = ttk.Radiobutton(rd, text="Xuất kho", value="XUAT", variable=self.v_loai, command=self._doi_loai)
        self.rb_nhap.grid(row=0, column=0, padx=(6, 12))
        self.rb_xuat.grid(row=0, column=1)
        self.d_ngay = tao_o_nhap(f, "Ngày:", 0, 1, DateEntry(f))
        self.lbl_nguoi = tao_o_nhap(f, "Người thực hiện:", 0, 2, ttk.Label(f, font=config.FONT_DAM))
        self.cb_nl = tao_o_nhap(f, "Nguyên liệu:", 1, 0, ttk.Combobox(f, state="readonly", width=34))
        self.cb_nl.bind("<<ComboboxSelected>>", self._chon_nl)
        self.e_sl = tao_o_nhap(f, "Số lượng:", 1, 1, ttk.Entry(f, width=12))
        self.e_gia = tao_o_nhap(f, "Giá nhập (đ):", 2, 0, ttk.Entry(f, width=14))
        self.d_han = tao_o_nhap(f, "Hạn SD mới:", 2, 1, DateEntry(f, hom_nay=False))
        self.cb_ncc = tao_o_nhap(f, "Nhà cung cấp:", 2, 2, ttk.Combobox(f, state="readonly", width=26))
        self.cb_ly_do = tao_o_nhap(f, "Lý do xuất:", 3, 0, ttk.Combobox(f, values=config.LY_DO_XUAT, state="readonly", width=20))
        self.cb_ly_do.current(0)
        nut = ttk.Frame(f)
        nut.grid(row=4, column=0, columnspan=6, pady=(6, 0))
        ttk.Button(nut, text="Thêm dòng vào phiếu", command=self.them_dong).grid(row=0, column=0, padx=4)
        ttk.Button(nut, text="Xóa dòng chọn", command=self.xoa_dong).grid(row=0, column=1, padx=4)
        self.b_luu = ttk.Button(nut, text="Lưu phiếu", style="Accent.TButton", command=self.luu_phieu)
        self.b_luu.grid(row=0, column=2, padx=4)
        ttk.Button(nut, text="Hủy phiếu", command=self.huy_phieu).grid(row=0, column=3, padx=4)
        for i in (1, 3, 5):
            f.columnconfigure(i, weight=1)
        self._o_nhap = [self.e_gia, self.d_han, self.cb_ncc]

        self.bang_tam = DataTree(self, COT_TAM, height=3)
        self.bang_tam.pack(fill="x", pady=6)

        ls = ttk.LabelFrame(self, text="Lịch sử giao dịch", padding=6)
        ls.pack(fill="both", expand=True)
        loc = ttk.Frame(ls)
        loc.pack(fill="x")
        self.v_loc = tk.StringVar(value="Tất cả")
        c = tao_o_nhap(loc, "Loại:", 0, 0, ttk.Combobox(loc, textvariable=self.v_loc, values=list(LOC_LOAI), state="readonly", width=8))
        c.bind("<<ComboboxSelected>>", lambda _e: self.lam_moi())
        self.d_tu = tao_o_nhap(loc, "Từ ngày:", 0, 1, DateEntry(loc, hom_nay=False))
        self.d_den = tao_o_nhap(loc, "Đến ngày:", 0, 2, DateEntry(loc, hom_nay=False))
        ttk.Button(loc, text="Lọc", command=self.lam_moi).grid(row=0, column=6, padx=4)
        ttk.Button(loc, text="Xuất báo cáo nhập/xuất (CSV)", command=self.xuat_bao_cao).grid(row=0, column=7, padx=4)
        self.bang_ls = DataTree(ls, COT_LS, height=5)
        self.bang_ls.pack(fill="both", expand=True, pady=(6, 0))

    # ---------- Hiển thị ----------
    def lam_moi(self):
        self.lbl_nguoi.configure(text=self.mh.auth.ten_hien_tai())
        self.cb_nl["values"] = [f"{n.ma_nguyen_lieu} - {n.ten_nguyen_lieu} ({n.don_vi})" for n in self.kho.danh_sach_nguyen_lieu]
        self.cb_ncc["values"] = ["(không)"] + [f"{n.ma_ncc} - {n.ten_ncc}" for n in self.kho.danh_sach_nha_cung_cap]
        if not self.cb_ncc.get():
            self.cb_ncc.set("(không)")
        self._hien_lich_su()

    @an_toan
    def _hien_lich_su(self):
        ds = self.kho.loc_giao_dich(LOC_LOAI[self.v_loc.get()], self.d_tu.get(), self.d_den.get())
        self.bang_ls.nap([(g.ma_giao_dich, [g.ma_giao_dich, "Nhập" if g.LOAI == "NHAP" else "Xuất", g.ngay_giao_dich, g.nguoi_thuc_hien,
                                           g.mo_ta(self.kho), dinh_dang_tien(g.tong_gia_tri()), g.ghi_chu()]) for g in reversed(ds)])

    def _hien_tam(self):
        hang = []
        for i, d in enumerate(self.dong_tam):
            nl = self.kho.tim_nguyen_lieu_theo_ma(d["ma_nl"])
            hang.append((str(i), [d["ma_nl"], nl.ten_nguyen_lieu if nl else "?", dinh_dang_so(d["so_luong"]), nl.don_vi if nl else "",
                                  dinh_dang_tien(d["gia_nhap"]) if "gia_nhap" in d else "", d.get("han_su_dung", "")]))
        self.bang_tam.nap(hang)

    def _doi_loai(self):
        nhap = self.v_loai.get() == "NHAP"
        dat_trang_thai(self._o_nhap, nhap)
        dat_trang_thai([self.cb_ly_do], not nhap)
        self.dong_tam.clear()
        self._hien_tam()

    def _chon_nl(self, _e=None):
        nl = self.kho.tim_nguyen_lieu_theo_ma(lay_ma_tu_combobox(self.cb_nl.get()))
        if nl and self.v_loai.get() == "NHAP":
            self.e_gia.configure(state="normal")
            self.e_gia.delete(0, "end")
            self.e_gia.insert(0, dinh_dang_so(nl.gia_nhap))

    # ---------- Thao tác ----------
    @an_toan
    def them_dong(self):
        ma = lay_ma_tu_combobox(self.cb_nl.get())
        if not ma:
            raise DuLieuKhongHopLe("Hãy chọn nguyên liệu.")
        nl = self.kho.lay_nguyen_lieu(ma)
        dong = {"ma_nl": ma, "so_luong": chuyen_so(self.e_sl.get(), "Số lượng", 0, lon_hon=True)}
        if self.v_loai.get() == "NHAP":
            gia = self.e_gia.get().strip()
            dong["gia_nhap"] = chuyen_so(gia, "Giá nhập", 0) if gia else nl.gia_nhap
            han = self.d_han.get()
            if han:
                parse_ngay(han)
                dong["han_su_dung"] = han
        self.dong_tam.append(dong)
        self._hien_tam()
        self.e_sl.delete(0, "end")

    def xoa_dong(self):
        i = self.bang_tam.chon()
        if i is not None:
            del self.dong_tam[int(i)]
            self._hien_tam()

    def huy_phieu(self):
        if self.dong_tam and messagebox.askyesno("Hủy phiếu", "Xóa toàn bộ các dòng đang soạn?"):
            self.dong_tam.clear()
            self._hien_tam()

    @an_toan
    def luu_phieu(self):
        if not self.dong_tam:
            raise DuLieuKhongHopLe("Phiếu chưa có dòng nào. Hãy thêm nguyên liệu vào phiếu trước.")
        nhap = self.v_loai.get() == "NHAP"
        self.mh.auth.yeu_cau_quyen("nhap_kho" if nhap else "xuat_kho")
        nguoi, dong = self.mh.auth.ten_hien_tai(), copy.deepcopy(self.dong_tam)
        if nhap:
            phieu = PhieuNhap(self.kho.sinh_ma("PN"), self.d_ngay.get(), nguoi, lay_ma_tu_combobox(self.cb_ncc.get()), dong)
        else:
            phieu = PhieuXuat(self.kho.sinh_ma("PX"), self.d_ngay.get(), nguoi, dong, self.cb_ly_do.get())
        if not messagebox.askyesno("Xác nhận", f"Lưu phiếu {'nhập' if nhap else 'xuất'} {phieu.ma_giao_dich} gồm {len(dong)} dòng?"):
            return
        self.kho.ghi_nhan_giao_dich(phieu)               # đa hình: Nhập tăng tồn / Xuất giảm tồn
        ghi_nhat_ky(nguoi, f"Lập phiếu {phieu.ma_giao_dich}: {phieu.mo_ta(self.kho)}")
        self.dong_tam.clear()
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", f"Đã lưu phiếu {phieu.ma_giao_dich}.")

    @an_toan
    def xuat_bao_cao(self):
        self.mh.auth.yeu_cau_quyen("xuat_bao_cao")
        duong_dan = filedialog.asksaveasfilename(title="Lưu báo cáo nhập/xuất", defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                                 initialdir=config.EXPORT_DIR if os.path.isdir(config.EXPORT_DIR) else config.BASE_DIR,
                                                 initialfile="bao_cao_nhap_xuat.csv")
        if not duong_dan:
            return
        so = report.xuat_nhap_xuat_csv(self.kho, duong_dan, LOC_LOAI[self.v_loc.get()], self.d_tu.get(), self.d_den.get())
        messagebox.showinfo("Thành công", f"Đã xuất {so} phiếu ra:\n{duong_dan}")

    def ap_dung_quyen(self):
        dat_trang_thai([self.rb_nhap], self.mh.auth.co_quyen("nhap_kho"))
        if not self.mh.auth.co_quyen("nhap_kho"):
            self.v_loai.set("XUAT")
