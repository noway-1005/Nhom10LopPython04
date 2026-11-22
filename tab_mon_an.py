# -*- coding: utf-8 -*-
"""Tab món ăn: CRUD món + định mức, tính nguyên liệu cần theo số suất, chế biến (tự xuất kho)."""
import tkinter as tk
from tkinter import messagebox, ttk

import config
from exceptions import DuLieuKhongHopLe
from models.mon_an import MonAn
from services.nhat_ky import ghi_nhat_ky
from services.tien_ich import dinh_dang_so
from services.validators import chuyen_so
from ui.helpers import an_toan, dat_trang_thai, lay_ma_tu_combobox, tao_o_nhap
from ui.widgets import DataTree

COT_MON = [("ma", "Mã", 70), ("ten", "Tên món", 200), ("so", "Số NL", 60, "center")]
COT_DM = [("ma", "Mã NL", 70), ("ten", "Nguyên liệu", 170), ("dm", "Định mức/suất", 100, "e"), ("dv", "ĐV", 50, "center"), ("ton", "Tồn kho", 80, "e")]


class TabMonAn(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self._ma_chon = None
        self.dinh_muc_tam = {}
        self._dung_giao_dien()
        self.lam_moi()
        self._lam_trong()
        self.ap_dung_quyen()

    def _dung_giao_dien(self):
        tren = ttk.Frame(self)
        tren.pack(fill="both", expand=True)
        # --- trái: danh sách món
        trai = ttk.LabelFrame(tren, text="Danh sách món ăn", padding=6)
        trai.pack(side="left", fill="both", expand=False)
        self.v_tim = tk.StringVar()
        e = ttk.Entry(trai, textvariable=self.v_tim, width=24)
        e.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        e.bind("<Return>", lambda _e: self.lam_moi())
        ttk.Button(trai, text="Tìm", command=self.lam_moi).grid(row=0, column=1, padx=4, pady=(0, 4))
        self.bang_mon = DataTree(trai, COT_MON, height=7)
        self.bang_mon.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.bang_mon.tree.bind("<<TreeviewSelect>>", self._chon_mon)
        trai.rowconfigure(1, weight=1)
        trai.columnconfigure(0, weight=1)
        # --- phải: form + định mức
        phai = ttk.LabelFrame(tren, text="Thông tin món & định mức nguyên liệu (cho 1 suất)", padding=6)
        phai.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.e_ma = tao_o_nhap(phai, "Mã (MA001):", 0, 0, ttk.Entry(phai, width=12))
        self.e_ten = tao_o_nhap(phai, "Tên món:", 0, 1, ttk.Entry(phai, width=28))
        self.cb_nl = tao_o_nhap(phai, "Nguyên liệu:", 1, 0, ttk.Combobox(phai, state="readonly", width=28))
        self.e_dm = tao_o_nhap(phai, "Định mức/suất:", 1, 1, ttk.Entry(phai, width=10))
        nut_dm = ttk.Frame(phai)
        nut_dm.grid(row=2, column=0, columnspan=4, pady=4)
        ttk.Button(nut_dm, text="Thêm/sửa dòng định mức", command=self.them_dong_dm).grid(row=0, column=0, padx=4)
        ttk.Button(nut_dm, text="Xóa dòng chọn", command=self.xoa_dong_dm).grid(row=0, column=1, padx=4)
        self.bang_dm = DataTree(phai, COT_DM, height=4)
        self.bang_dm.grid(row=3, column=0, columnspan=4, sticky="nsew")
        phai.rowconfigure(3, weight=1)
        phai.columnconfigure(3, weight=1)
        nut = ttk.Frame(phai)
        nut.grid(row=4, column=0, columnspan=4, pady=(6, 0))
        self.b_them = ttk.Button(nut, text="Thêm món", style="Accent.TButton", command=self.them)
        self.b_sua = ttk.Button(nut, text="Cập nhật món", command=self.cap_nhat)
        self.b_xoa = ttk.Button(nut, text="Xóa món", command=self.xoa)
        for i, b in enumerate((self.b_them, self.b_sua, self.b_xoa)):
            b.grid(row=0, column=i, padx=4)
        ttk.Button(nut, text="Làm trống form", command=self._lam_trong).grid(row=0, column=3, padx=4)
        # --- dưới: tính & chế biến
        duoi = ttk.LabelFrame(self, text="Tính nguyên liệu & chế biến", padding=6)
        duoi.pack(fill="x", pady=(8, 0), side="bottom", before=tren)
        ttk.Label(duoi, text="Số suất:").grid(row=0, column=0, padx=(6, 3))
        self.v_suat = tk.StringVar(value="10")
        ttk.Spinbox(duoi, from_=1, to=1000, textvariable=self.v_suat, width=7).grid(row=0, column=1)
        ttk.Button(duoi, text="Tính nguyên liệu cần", command=self.tinh).grid(row=0, column=2, padx=8)
        self.b_che_bien = ttk.Button(duoi, text="Chế biến (tự xuất kho)", style="Accent.TButton", command=self.che_bien)
        self.b_che_bien.grid(row=0, column=3)
        self.txt = tk.Text(duoi, height=6, font=("Courier New", 10), state="disabled", wrap="none")
        self.txt.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(6, 0))
        self.txt.tag_configure("thieu", foreground="#c0392b")
        self.txt.tag_configure("dam", font=("Courier New", 10, "bold"))
        duoi.columnconfigure(4, weight=1)

    # ---------- Hiển thị ----------
    def lam_moi(self):
        self.cb_nl["values"] = [f"{n.ma_nguyen_lieu} - {n.ten_nguyen_lieu} ({n.don_vi})" for n in self.kho.danh_sach_nguyen_lieu]
        self.bang_mon.nap([(m.ma_mon, [m.ma_mon, m.ten_mon, len(m.dinh_muc_nguyen_lieu)]) for m in self.kho.tim_kiem_mon_an(self.v_tim.get())])
        self._hien_dm()

    def _hien_dm(self):
        hang = []
        for ma, dm in self.dinh_muc_tam.items():
            nl = self.kho.tim_nguyen_lieu_theo_ma(ma)
            hang.append((ma, [ma, nl.ten_nguyen_lieu if nl else "?", dinh_dang_so(dm), nl.don_vi if nl else "", dinh_dang_so(nl.so_luong) if nl else "0"]))
        self.bang_dm.nap(hang)

    @staticmethod
    def _dat(entry, gia_tri):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, gia_tri)

    def _chon_mon(self, _e=None):
        ma = self.bang_mon.chon()
        mon = next((m for m in self.kho.danh_sach_mon_an if m.ma_mon == ma), None) if ma else None
        if mon is None:
            return
        self._ma_chon = ma
        self._dat(self.e_ma, mon.ma_mon)
        self.e_ma.configure(state="readonly")
        self._dat(self.e_ten, mon.ten_mon)
        self.dinh_muc_tam = dict(mon.dinh_muc_nguyen_lieu)
        self._hien_dm()

    def _lam_trong(self):
        self._ma_chon, self.dinh_muc_tam = None, {}
        self._dat(self.e_ten, "")
        self._dat(self.e_dm, "")
        self._dat(self.e_ma, self.kho.sinh_ma("MA"))
        if self.bang_mon.chon():
            self.bang_mon.tree.selection_remove(self.bang_mon.chon())
        self._hien_dm()

    # ---------- Định mức tạm ----------
    @an_toan
    def them_dong_dm(self):
        ma = lay_ma_tu_combobox(self.cb_nl.get())
        if not ma:
            raise DuLieuKhongHopLe("Hãy chọn nguyên liệu cho dòng định mức.")
        self.dinh_muc_tam[ma] = chuyen_so(self.e_dm.get(), "Định mức", 0, lon_hon=True)
        self._hien_dm()
        self._dat(self.e_dm, "")

    def xoa_dong_dm(self):
        ma = self.bang_dm.chon()
        if ma:
            self.dinh_muc_tam.pop(ma, None)
            self._hien_dm()

    # ---------- CRUD món ----------
    @an_toan
    def them(self):
        self.mh.auth.yeu_cau_quyen("sua_mon_an")
        mon = MonAn(self.e_ma.get(), self.e_ten.get(), dict(self.dinh_muc_tam))
        self.kho.them_mon_an(mon)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Thêm món {mon.ma_mon}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()
        messagebox.showinfo("Thành công", f"Đã thêm món '{mon.ten_mon}'.")

    @an_toan
    def cap_nhat(self):
        self.mh.auth.yeu_cau_quyen("sua_mon_an")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một món trong danh sách trước khi cập nhật.")
        self.kho.cap_nhat_mon_an(self._ma_chon, self.e_ten.get(), dict(self.dinh_muc_tam))
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Cập nhật món {self._ma_chon}")
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", "Đã cập nhật món ăn.")

    @an_toan
    def xoa(self):
        self.mh.auth.yeu_cau_quyen("sua_mon_an")
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một món trong danh sách trước khi xóa.")
        mon = self.kho.lay_mon_an(self._ma_chon)
        if not messagebox.askyesno("Xác nhận xóa", f"Xóa món '{mon.ten_mon}'?"):
            return
        self.kho.xoa_mon_an(mon.ma_mon)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Xóa món {mon.ma_mon}")
        self.mh.lam_moi_tat_ca()
        self._lam_trong()

    # ---------- Tính & chế biến ----------
    def _mon_dang_chon(self):
        if not self._ma_chon:
            raise DuLieuKhongHopLe("Hãy chọn một món trong danh sách bên trái.")
        return self.kho.lay_mon_an(self._ma_chon)

    @an_toan
    def tinh(self):
        mon = self._mon_dang_chon()
        can = mon.tinh_nguyen_lieu_can(self.v_suat.get())
        du, _ = mon.kiem_tra_kha_nang_che_bien(self.kho, self.v_suat.get())
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("end", f"{mon.ten_mon} x {self.v_suat.get()} suất\n", "dam")
        self.txt.insert("end", f"{'Nguyên liệu':<24}{'Cần':>10}{'Tồn':>10}{'Thiếu':>10}\n")
        for ma, c in can.items():
            nl = self.kho.tim_nguyen_lieu_theo_ma(ma)
            ton = nl.so_luong if nl else 0
            thieu = max(0, c - ton)
            ten = (nl.ten_nguyen_lieu if nl else ma)[:22]
            self.txt.insert("end", f"{ten:<24}{dinh_dang_so(c):>10}{dinh_dang_so(ton):>10}{dinh_dang_so(thieu):>10}\n", "thieu" if thieu > 0 else ())
        self.txt.insert("end", "=> ĐỦ nguyên liệu để chế biến." if du else "=> KHÔNG ĐỦ nguyên liệu, cần nhập thêm.", "dam" if du else "thieu")
        self.txt.configure(state="disabled")

    @an_toan
    def che_bien(self):
        self.mh.auth.yeu_cau_quyen("che_bien")
        mon = self._mon_dang_chon()
        so = self.v_suat.get()
        mon.tinh_nguyen_lieu_can(so)                     # kiểm tra số suất hợp lệ trước khi hỏi
        if not messagebox.askyesno("Xác nhận chế biến", f"Chế biến {so} suất '{mon.ten_mon}'?\nNguyên liệu sẽ được trừ khỏi kho."):
            return
        phieu = mon.che_bien(self.kho, so, self.mh.auth.ten_hien_tai())
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Chế biến {so} suất {mon.ten_mon} -> {phieu.ma_giao_dich}")
        self.mh.lam_moi_tat_ca()
        self.tinh()
        messagebox.showinfo("Thành công", f"Đã tạo phiếu xuất {phieu.ma_giao_dich} và trừ nguyên liệu khỏi kho.")

    def ap_dung_quyen(self):
        dat_trang_thai([self.b_them, self.b_sua, self.b_xoa], self.mh.auth.co_quyen("sua_mon_an"))
        dat_trang_thai([self.b_che_bien], self.mh.auth.co_quyen("che_bien"))
