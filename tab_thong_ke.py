# -*- coding: utf-8 -*-
"""Tab thống kê & cảnh báo: biểu đồ cột Canvas, tổng giá trị kho, danh sách cảnh báo, xuất báo cáo tổng hợp."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
from services import report
from services.tien_ich import dinh_dang_so, dinh_dang_tien
from ui.helpers import an_toan
from ui.widgets import BarChart

CHE_DO = [("Giá trị tồn kho theo nguyên liệu", "gia_tri"), ("Tồn kho so với mức tối thiểu (%)", "ti_le"),
          ("Nguyên liệu tiêu thụ (giá trị xuất)", "tieu_thu")]


class TabThongKe(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self.v_che_do, self.v_ngay = tk.StringVar(value="gia_tri"), tk.StringVar(value=str(config.SO_NGAY_CANH_BAO_MAC_DINH))
        self.v_tong, self.v_so_nl, self.v_het_hang, self.v_het_han = (tk.StringVar() for _ in range(4))
        tong = ttk.Frame(self)
        tong.pack(fill="x")
        for i, (nhan, bien) in enumerate((("Tổng giá trị kho (đ)", self.v_tong), ("Số loại nguyên liệu", self.v_so_nl),
                                          ("Sắp hết hàng", self.v_het_hang), ("Hết/sắp hết hạn", self.v_het_han))):
            o = ttk.LabelFrame(tong, text=nhan, padding=6)
            o.grid(row=0, column=i, sticky="ew", padx=4)
            ttk.Label(o, textvariable=bien, font=config.FONT_TIEU_DE, foreground=config.MAU_CHINH).pack()
            tong.columnconfigure(i, weight=1)
        dk = ttk.Frame(self)
        dk.pack(fill="x", pady=6)
        for i, (nhan, gt) in enumerate(CHE_DO):
            ttk.Radiobutton(dk, text=nhan, value=gt, variable=self.v_che_do, command=self.lam_moi).grid(row=0, column=i, padx=6)
        ttk.Label(dk, text="Cảnh báo hạn trong (ngày):").grid(row=0, column=3, padx=(16, 3))
        ttk.Spinbox(dk, from_=0, to=365, textvariable=self.v_ngay, width=5, command=self.lam_moi).grid(row=0, column=4)
        ttk.Button(dk, text="Cập nhật", command=self.lam_moi).grid(row=0, column=5, padx=6)
        ttk.Button(dk, text="Xuất báo cáo tổng hợp (.txt)", command=self.xuat_txt).grid(row=0, column=6, padx=4)
        ttk.Button(dk, text="Xuất tồn kho (.csv)", command=self.xuat_csv).grid(row=0, column=7, padx=4)
        self.bieu_do = BarChart(self, height=200)
        self.bieu_do.pack(fill="both", expand=True)
        cb = ttk.LabelFrame(self, text="Danh sách cảnh báo", padding=6)
        cb.pack(fill="x", pady=(6, 0), side="bottom", before=self.bieu_do)
        self.ds = tk.Listbox(cb, height=5, font=config.FONT, activestyle="none")
        sb = ttk.Scrollbar(cb, orient="vertical", command=self.ds.yview)
        self.ds.configure(yscrollcommand=sb.set)
        self.ds.grid(row=0, column=0, sticky="ew")
        sb.grid(row=0, column=1, sticky="ns")
        cb.columnconfigure(0, weight=1)
        self.lam_moi()

    def _so_ngay(self):
        try:
            return max(0, int(self.v_ngay.get()))
        except ValueError:
            return config.SO_NGAY_CANH_BAO_MAC_DINH       # ô nhập sai -> dùng giá trị mặc định thay vì báo lỗi liên tục

    def lam_moi(self):
        kho, so_ngay = self.kho, self._so_ngay()
        het_hang, het_han = kho.canh_bao_sap_het_hang(), kho.canh_bao_sap_het_han(so_ngay)
        self.v_tong.set(dinh_dang_tien(kho.tinh_tong_gia_tri_kho()))
        self.v_so_nl.set(str(len(kho.danh_sach_nguyen_lieu)))
        self.v_het_hang.set(str(len(het_hang)))
        self.v_het_han.set(str(len(het_han)))
        che_do = self.v_che_do.get()
        if che_do == "gia_tri":
            du_lieu = [(n.ten_nguyen_lieu, n.gia_tri(), n.kiem_tra_so_luong()) for n in kho.danh_sach_nguyen_lieu]
            du_lieu = sorted(du_lieu, key=lambda x: x[1], reverse=True)[:12]
            self.bieu_do.ve(du_lieu, "Giá trị tồn kho (cột đỏ: sắp hết hàng)", "đ")
        elif che_do == "ti_le":
            du_lieu = [(n.ten_nguyen_lieu, n.so_luong / n.muc_toi_thieu * 100, n.kiem_tra_so_luong())
                       for n in kho.danh_sach_nguyen_lieu if n.muc_toi_thieu > 0]
            du_lieu = sorted(du_lieu, key=lambda x: x[1])[:12]
            self.bieu_do.ve(du_lieu, "Tồn kho / mức tối thiểu (≤100% là cần nhập thêm)", "%")
        else:
            tk = sorted(kho.thong_ke_tieu_thu().values(), key=lambda m: m["gia_tri"], reverse=True)[:12]
            self.bieu_do.ve([(m["ten"], m["gia_tri"]) for m in tk], "Giá trị nguyên liệu đã xuất kho", "đ")
        self.ds.delete(0, "end")
        for n in het_hang:
            self.ds.insert("end", f"[Sắp hết hàng] {n.ten_nguyen_lieu}: còn {dinh_dang_so(n.so_luong)} {n.don_vi} (tối thiểu {dinh_dang_so(n.muc_toi_thieu)})")
            self.ds.itemconfig("end", foreground="#d35400")
        for n in het_han:
            con = n.so_ngay_con_lai()
            self.ds.insert("end", f"[{'ĐÃ HẾT HẠN' if con < 0 else 'Sắp hết hạn'}] {n.ten_nguyen_lieu}: HSD {n.han_su_dung} "
                                  f"({'quá ' + str(-con) if con < 0 else 'còn ' + str(con)} ngày)")
            self.ds.itemconfig("end", foreground="#c0392b" if con < 0 else "#b7950b")
        if not het_hang and not het_han:
            self.ds.insert("end", "Không có cảnh báo nào.")

    def _chon_file(self, ten, ext, loai):
        os.makedirs(config.EXPORT_DIR, exist_ok=True)
        return filedialog.asksaveasfilename(title="Lưu báo cáo", defaultextension=ext, filetypes=[(loai, "*" + ext)],
                                            initialdir=config.EXPORT_DIR, initialfile=ten)

    @an_toan
    def xuat_txt(self):
        self.mh.auth.yeu_cau_quyen("xuat_bao_cao")
        p = self._chon_file("bao_cao_kho.txt", ".txt", "Văn bản")
        if p:
            report.xuat_bao_cao_tong_hop_txt(self.kho, p, self._so_ngay())
            messagebox.showinfo("Thành công", f"Đã xuất báo cáo:\n{p}")

    @an_toan
    def xuat_csv(self):
        self.mh.auth.yeu_cau_quyen("xuat_bao_cao")
        p = self._chon_file("ton_kho.csv", ".csv", "CSV")
        if p:
            report.xuat_ton_kho_csv(self.kho, p)
            messagebox.showinfo("Thành công", f"Đã xuất tồn kho:\n{p}")
