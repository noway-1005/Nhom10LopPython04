# -*- coding: utf-8 -*-
"""Tab 'Dữ liệu & API' (Quản trị viên): dữ liệu mẫu (random), crawl/API TheMealDB, sao lưu/khôi phục, xuất JSON."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
from exceptions import DuLieuKhongHopLe, LoiUngDung
from services import crawler, report
from services.file_handler import JsonFile
from services.nhat_ky import ghi_nhat_ky
from services.sample_data import tao_du_lieu_mau
from ui.helpers import an_toan


class TabDuLieu(ttk.Frame):
    def __init__(self, cha, mh):
        super().__init__(cha, padding=8)
        self.mh, self.kho = mh, mh.kho
        self._hang_doi, self._ket_qua = queue.Queue(), None
        # --- dữ liệu mẫu
        f1 = ttk.LabelFrame(self, text="1. Dữ liệu mẫu (sinh ngẫu nhiên bằng module random)", padding=8)
        f1.pack(fill="x")
        self.v_seed = tk.StringVar(value="2026")
        ttk.Label(f1, text="Seed (để trống = ngẫu nhiên):").grid(row=0, column=0, padx=4)
        ttk.Entry(f1, textvariable=self.v_seed, width=10).grid(row=0, column=1)
        ttk.Button(f1, text="Sinh dữ liệu mẫu (ghi đè kho hiện tại)", command=self.sinh_mau).grid(row=0, column=2, padx=10)
        # --- API
        f2 = ttk.LabelFrame(self, text="2. Lấy dữ liệu từ API TheMealDB (món ăn + nguyên liệu → JSON → kho)", padding=8)
        f2.pack(fill="x", pady=8)
        self.v_tu_khoa = tk.StringVar(value="chicken, beef, fish")
        ttk.Label(f2, text="Từ khóa (tiếng Anh, cách nhau dấu phẩy):").grid(row=0, column=0, padx=4)
        ttk.Entry(f2, textvariable=self.v_tu_khoa, width=34).grid(row=0, column=1)
        self.b_api = ttk.Button(f2, text="Lấy dữ liệu từ API", command=self.lay_api)
        self.b_api.grid(row=0, column=2, padx=6)
        self.b_nhap = ttk.Button(f2, text="Nhập vào kho", state="disabled", command=self.nhap_vao_kho)
        self.b_nhap.grid(row=0, column=3, padx=2)
        ttk.Button(f2, text="Nạp từ file đã crawl", command=self.nap_file_crawl).grid(row=0, column=4, padx=2)
        self.log = tk.Text(f2, height=7, state="disabled", wrap="word", font=config.FONT)
        self.log.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(6, 0))
        f2.columnconfigure(1, weight=1)
        # --- sao lưu
        f3 = ttk.LabelFrame(self, text="3. Sao lưu / khôi phục / xuất dữ liệu", padding=8)
        f3.pack(fill="both", expand=True)
        self.ds_sao_luu = tk.Listbox(f3, height=6, font=config.FONT, exportselection=False)
        self.ds_sao_luu.grid(row=0, column=0, rowspan=4, sticky="nsew")
        ttk.Button(f3, text="Sao lưu ngay", command=self.sao_luu).grid(row=0, column=1, sticky="ew", padx=8, pady=2)
        ttk.Button(f3, text="Khôi phục bản đang chọn", command=self.khoi_phuc).grid(row=1, column=1, sticky="ew", padx=8, pady=2)
        ttk.Button(f3, text="Xuất kho ra JSON", command=self.xuat_json).grid(row=2, column=1, sticky="ew", padx=8, pady=2)
        f3.columnconfigure(0, weight=1)
        f3.rowconfigure(0, weight=1)
        self.lam_moi()

    def lam_moi(self):
        self.ds_sao_luu.delete(0, "end")
        for t in self.kho.danh_sach_sao_luu():
            self.ds_sao_luu.insert("end", t)

    def _ghi_log(self, dong):
        self.log.configure(state="normal")
        self.log.insert("end", dong + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- Dữ liệu mẫu ----------
    @an_toan
    def sinh_mau(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        s = self.v_seed.get().strip()
        if s and not s.lstrip("-").isdigit():
            raise DuLieuKhongHopLe("Seed phải là số nguyên hoặc để trống.")
        if not messagebox.askyesno("Xác nhận", "Toàn bộ dữ liệu kho hiện tại sẽ bị thay bằng dữ liệu mẫu (có sao lưu trước khi ghi).\nTiếp tục?"):
            return
        self.kho.sao_luu()
        tao_du_lieu_mau(self.kho, int(s) if s else None, self.mh.auth.ten_hien_tai())
        self.kho.luu_du_lieu_json()
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), "Sinh dữ liệu mẫu")
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", "Đã sinh dữ liệu mẫu.")

    # ---------- API ----------
    @an_toan
    def lay_api(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        ds = [t.strip() for t in self.v_tu_khoa.get().split(",") if t.strip()]
        if not ds:
            raise DuLieuKhongHopLe("Hãy nhập ít nhất một từ khóa (ví dụ: chicken).")
        self.b_api.configure(state="disabled")
        self._ghi_log(f"Đang gọi API với từ khóa: {', '.join(ds)} ...")

        def chay():                               # chạy ở luồng riêng để giao diện không bị treo
            try:
                self._hang_doi.put(("ok", crawler.crawl_mon_an(ds)))
            except LoiUngDung as e:
                self._hang_doi.put(("loi", str(e)))
            except Exception as e:  # noqa: BLE001 - luồng nền: báo lỗi về giao diện thay vì chết âm thầm
                self._hang_doi.put(("loi", f"Lỗi không mong đợi: {e}"))
        threading.Thread(target=chay, daemon=True).start()
        self.after(200, self._cho_ket_qua)

    def _cho_ket_qua(self):
        try:
            loai, nd = self._hang_doi.get_nowait()
        except queue.Empty:
            self.after(200, self._cho_ket_qua)
            return
        self.b_api.configure(state="normal")
        if loai == "loi":
            self._ghi_log(f"LỖI: {nd}")
            return
        self._ket_qua = nd
        self._ghi_log(f"Đã lấy {nd['so_mon']} món và lưu vào {config.FILE_CRAWL}.")
        for loi in nd.get("loi", []):
            self._ghi_log(f"  (bỏ qua) {loi}")
        for m in nd["mon_an"][:8]:
            self._ghi_log(f"  - {m['ten_mon']}: {len(m['dinh_muc'])} nguyên liệu")
        self.b_nhap.configure(state="normal")

    @an_toan
    def nap_file_crawl(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        du_lieu = JsonFile(config.FILE_CRAWL).doc()
        if not isinstance(du_lieu, dict) or not du_lieu.get("mon_an"):
            raise DuLieuKhongHopLe("Chưa có file crawl hợp lệ. Hãy bấm 'Lấy dữ liệu từ API' khi có Internet.")
        self._ket_qua = du_lieu
        self._ghi_log(f"Đã nạp {len(du_lieu['mon_an'])} món từ file crawl ({du_lieu.get('thoi_gian', '?')}).")
        self.b_nhap.configure(state="normal")

    @an_toan
    def nhap_vao_kho(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        if not self._ket_qua:
            raise DuLieuKhongHopLe("Chưa có dữ liệu API để nhập.")
        mon, nl, bo = crawler.nhap_crawl_vao_kho(self.kho, self._ket_qua)
        self.kho.luu_du_lieu_json()
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Nhập dữ liệu API: {mon} món, {nl} nguyên liệu mới")
        self._ghi_log(f"Đã thêm {mon} món, {nl} nguyên liệu mới (tồn = 0, hãy nhập kho); bỏ qua {bo} món trùng/lỗi.")
        self.mh.lam_moi_tat_ca()

    # ---------- Sao lưu ----------
    @an_toan
    def sao_luu(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        self.kho.luu_du_lieu_json()
        ten = self.kho.sao_luu()
        self.lam_moi()
        messagebox.showinfo("Thành công", f"Đã sao lưu: {ten}" if ten else "Chưa có dữ liệu để sao lưu.")

    @an_toan
    def khoi_phuc(self):
        self.mh.auth.yeu_cau_quyen("quan_ly_du_lieu")
        sel = self.ds_sao_luu.curselection()
        if not sel:
            raise DuLieuKhongHopLe("Hãy chọn một bản sao lưu trong danh sách.")
        ten = self.ds_sao_luu.get(sel[0])
        if not messagebox.askyesno("Xác nhận khôi phục", f"Khôi phục dữ liệu từ '{ten}'?\nDữ liệu hiện tại sẽ được sao lưu trước."):
            return
        self.kho.khoi_phuc_tu_sao_luu(ten)
        ghi_nhat_ky(self.mh.auth.ten_hien_tai(), f"Khôi phục dữ liệu từ {ten}")
        self.mh.lam_moi_tat_ca()
        messagebox.showinfo("Thành công", "Đã khôi phục dữ liệu.")

    @an_toan
    def xuat_json(self):
        self.mh.auth.yeu_cau_quyen("xuat_bao_cao")
        os.makedirs(config.EXPORT_DIR, exist_ok=True)
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")],
                                         initialdir=config.EXPORT_DIR, initialfile="ton_kho.json")
        if p:
            report.xuat_ton_kho_json(self.kho, p)
            messagebox.showinfo("Thành công", f"Đã xuất:\n{p}")

    def ap_dung_quyen(self):
        pass
