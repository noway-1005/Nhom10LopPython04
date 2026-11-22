# -*- coding: utf-8 -*-
"""Custom widget kế thừa từ widget Tkinter chuẩn: DateEntry (Frame), DataTree (Frame + Treeview), BarChart (Canvas)."""
import calendar
import tkinter as tk
from datetime import date, datetime
from tkinter import ttk

import config
from exceptions import DuLieuKhongHopLe
from services import validators as vd


class DateEntry(ttk.Frame):
    """Ô nhập ngày dd/mm/yyyy: kiểm tra bằng Regex khi rời ô (chữ đỏ nếu sai) + lịch chọn ngày dạng popup."""

    def __init__(self, cha, hom_nay=True, width=11, **kw):
        super().__init__(cha, **kw)
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.nut = ttk.Button(self, text="▾", width=2, command=self._mo_lich)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.nut.grid(row=0, column=1, padx=(2, 0))
        self.columnconfigure(0, weight=1)
        self._popup = None
        self.entry.bind("<FocusOut>", lambda _e: self._kiem_tra())
        if hom_nay:
            self.var.set(vd.hom_nay_str())

    def get(self):
        return self.var.get().strip()

    def set(self, gia_tri):
        self.var.set(gia_tri or "")
        self._kiem_tra()

    def dat_trang_thai(self, bat):
        self.entry.configure(state="normal" if bat else "disabled")
        self.nut.configure(state="normal" if bat else "disabled")

    def _kiem_tra(self):
        hop_le = (not self.get()) or vd.kiem_tra_ngay(self.get())
        self.entry.configure(foreground="black" if hop_le else "red")

    def _mo_lich(self):
        if self._popup is not None and self._popup.winfo_exists():
            self._popup.destroy()
            return
        try:
            d = vd.parse_ngay(self.get())
        except DuLieuKhongHopLe:
            d = date.today()
        self._thang, self._nam = d.month, d.year
        p = tk.Toplevel(self)
        p.title("Chọn ngày")
        p.resizable(False, False)
        p.transient(self.winfo_toplevel())
        p.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        self._popup = p
        self._ve_lich()

    def _ve_lich(self):
        p = self._popup
        for w in p.winfo_children():
            w.destroy()
        dau = ttk.Frame(p)
        dau.grid(row=0, column=0, pady=4)
        ttk.Button(dau, text="◀", width=3, command=lambda: self._doi_thang(-1)).grid(row=0, column=0)
        ttk.Label(dau, text=f"Tháng {self._thang}/{self._nam}", anchor="center", width=16).grid(row=0, column=1)
        ttk.Button(dau, text="▶", width=3, command=lambda: self._doi_thang(1)).grid(row=0, column=2)
        than = ttk.Frame(p)
        than.grid(row=1, column=0, padx=4, pady=(0, 4))
        for c, t in enumerate(["T2", "T3", "T4", "T5", "T6", "T7", "CN"]):
            ttk.Label(than, text=t, width=4, anchor="center").grid(row=0, column=c)
        for r, tuan in enumerate(calendar.monthcalendar(self._nam, self._thang), start=1):
            for c, ngay in enumerate(tuan):
                if ngay:
                    ttk.Button(than, text=str(ngay), width=4, command=lambda n=ngay: self._chon(n)).grid(row=r, column=c)

    def _doi_thang(self, delta):
        thang = self._thang + delta
        if thang < 1:
            thang, self._nam = 12, self._nam - 1
        elif thang > 12:
            thang, self._nam = 1, self._nam + 1
        self._thang = thang
        self._ve_lich()

    def _chon(self, ngay):
        self.var.set(f"{ngay:02d}/{self._thang:02d}/{self._nam}")
        self._popup.destroy()
        self._kiem_tra()


class DataTree(ttk.Frame):
    """Treeview có thanh cuộn, bấm tiêu đề cột để sắp xếp (nhận biết số/ngày/chữ), tô màu dòng theo tag."""

    def __init__(self, cha, cot, height=10, **kw):
        super().__init__(cha, **kw)
        self.tree = ttk.Treeview(self, columns=[c[0] for c in cot], show="headings", height=height, selectmode="browse")
        for c in cot:
            id_, tieu_de, rong = c[:3]
            self.tree.heading(id_, text=tieu_de, command=lambda i=id_: self.sap_xep(i))
            self.tree.column(id_, width=rong, minwidth=40, anchor=c[3] if len(c) > 3 else "w")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self._nguoc = {}
        for tag, mau in (("het_han", config.MAU_HET_HAN), ("sap_het_han", config.MAU_SAP_HET_HAN),
                         ("sap_het_hang", config.MAU_SAP_HET_HANG)):
            self.tree.tag_configure(tag, background=mau)

    def nap(self, hang):
        """hang: iterable các bộ (iid, [giá trị cột], tag?)"""
        self.tree.delete(*self.tree.get_children())
        for h in hang:
            self.tree.insert("", "end", iid=h[0], values=h[1], tags=(h[2],) if len(h) > 2 and h[2] else ())

    def chon(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    @staticmethod
    def _khoa(gia_tri):
        s = str(gia_tri)
        for chuyen in (lambda x: float(x), lambda x: float(x.replace(".", "")),
                       lambda x: datetime.strptime(x, config.DINH_DANG_NGAY).toordinal()):
            try:
                return (0, chuyen(s))
            except ValueError:
                continue
        return (1, s.lower())

    def sap_xep(self, cot):
        nguoc = self._nguoc[cot] = not self._nguoc.get(cot, True)
        ds = sorted(((self.tree.set(k, cot), k) for k in self.tree.get_children("")),
                    key=lambda x: self._khoa(x[0]), reverse=nguoc)
        for vi_tri, (_, k) in enumerate(ds):
            self.tree.move(k, "", vi_tri)


class BarChart(tk.Canvas):
    """Biểu đồ cột vẽ bằng Canvas, tự vẽ lại khi đổi kích thước. du_lieu: [(nhãn, giá trị, cảnh_báo?)]"""

    def __init__(self, cha, **kw):
        kw.setdefault("bg", "white")
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", "#cccccc")
        super().__init__(cha, **kw)
        self._du_lieu, self._tieu_de, self._don_vi = [], "", ""
        self.bind("<Configure>", lambda _e: self._ve())

    def ve(self, du_lieu, tieu_de="", don_vi=""):
        self._du_lieu, self._tieu_de, self._don_vi = list(du_lieu), tieu_de, don_vi
        self._ve()

    @staticmethod
    def _dinh_dang(v):
        return f"{v:,.0f}".replace(",", ".") if abs(v) >= 100 else f"{v:.1f}"

    def _ve(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 120 or h < 120:
            return
        self.create_text(w / 2, 14, text=f"{self._tieu_de}  {('(' + self._don_vi + ')') if self._don_vi else ''}", font=config.FONT_DAM)
        if not self._du_lieu:
            self.create_text(w / 2, h / 2, text="Chưa có dữ liệu để vẽ", fill="#888888", font=config.FONT)
            return
        trai, phai, tren, duoi = 70, 20, 34, 70
        vw, vh = w - trai - phai, h - tren - duoi
        max_v = max(d[1] for d in self._du_lieu) or 1
        for i in range(6):
            y = tren + vh - vh * i / 5
            self.create_line(trai, y, w - phai, y, fill="#e6e6e6")
            self.create_text(trai - 6, y, text=self._dinh_dang(max_v * i / 5), anchor="e", font=config.FONT_NHO, fill="#555555")
        self.create_line(trai, tren, trai, tren + vh, fill="#999999")
        self.create_line(trai, tren + vh, w - phai, tren + vh, fill="#999999")
        slot = vw / len(self._du_lieu)
        rong = min(slot * 0.6, 56)
        for i, d in enumerate(self._du_lieu):
            nhan, gia_tri = d[0], d[1]
            canh_bao = len(d) > 2 and d[2]
            x0 = trai + i * slot + (slot - rong) / 2
            y1 = tren + vh
            y0 = y1 - vh * gia_tri / max_v
            self.create_rectangle(x0, y0, x0 + rong, y1, fill=config.MAU_COT_CANH_BAO if canh_bao else config.MAU_COT, outline="")
            self.create_text(x0 + rong / 2, y0 - 8, text=self._dinh_dang(gia_tri), font=config.FONT_NHO)
            self.create_text(x0 + rong / 2, y1 + 6, text=nhan if len(nhan) <= 12 else nhan[:11] + "…",
                             angle=30, anchor="ne", font=config.FONT_NHO)
