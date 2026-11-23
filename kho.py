# -*- coding: utf-8 -*-
"""Lớp quản lý tổng thể Kho: CRUD, giao dịch, cảnh báo, thống kê và lưu/đọc JSON."""
import difflib

import config
from exceptions import DuLieuKhongHopLe, LoiFile, LoiNghiepVu
from models.giao_dich import GiaoDichKho, giao_dich_tu_dict
from models.mon_an import MonAn
from models.nguyen_lieu import NguyenLieu
from models.nha_cung_cap import NhaCungCap
from services.file_handler import JsonFile
from services.tien_ich import bo_dau
from services.validators import parse_ngay

_LOI_DOC = (DuLieuKhongHopLe, LoiNghiepVu, KeyError, TypeError, ValueError, AttributeError)


class Kho:
    def __init__(self, duong_dan=config.FILE_KHO, tu_dong_luu=False):
        self.danh_sach_nguyen_lieu = []
        self.danh_sach_nha_cung_cap = []
        self.danh_sach_mon_an = []
        self.lich_su_giao_dich = []
        self.canh_bao_doc = []
        self.tu_dong_luu = tu_dong_luu
        self._file = JsonFile(duong_dan)

    def _luu(self):
        if self.tu_dong_luu:
            self.luu_du_lieu_json()

    def trong(self):
        return not (self.danh_sach_nguyen_lieu or self.danh_sach_nha_cung_cap or self.danh_sach_mon_an)

    def xoa_toan_bo(self):
        self.danh_sach_nguyen_lieu, self.danh_sach_nha_cung_cap = [], []
        self.danh_sach_mon_an, self.lich_su_giao_dich = [], []

    # ================= Tra cứu & sinh mã =================
    def tim_nguyen_lieu_theo_ma(self, ma):
        ma = (ma or "").strip().upper()
        return next((n for n in self.danh_sach_nguyen_lieu if n.ma_nguyen_lieu == ma), None)

    def lay_nguyen_lieu(self, ma):
        nl = self.tim_nguyen_lieu_theo_ma(ma)
        if nl is None:
            raise LoiNghiepVu(f"Không tìm thấy nguyên liệu có mã '{ma}'.")
        return nl

    def tim_ncc_theo_ma(self, ma):
        ma = (ma or "").strip().upper()
        return next((n for n in self.danh_sach_nha_cung_cap if n.ma_ncc == ma), None)

    def lay_nha_cung_cap(self, ma):
        ncc = self.tim_ncc_theo_ma(ma)
        if ncc is None:
            raise LoiNghiepVu(f"Không tìm thấy nhà cung cấp có mã '{ma}'.")
        return ncc

    def lay_mon_an(self, ma):
        ma = (ma or "").strip().upper()
        mon = next((m for m in self.danh_sach_mon_an if m.ma_mon == ma), None)
        if mon is None:
            raise LoiNghiepVu(f"Không tìm thấy món ăn có mã '{ma}'.")
        return mon

    def sinh_ma(self, tien_to):
        nguon = {"NL": [n.ma_nguyen_lieu for n in self.danh_sach_nguyen_lieu],
                 "NCC": [n.ma_ncc for n in self.danh_sach_nha_cung_cap],
                 "MA": [m.ma_mon for m in self.danh_sach_mon_an],
                 "PN": [g.ma_giao_dich for g in self.lich_su_giao_dich if g.LOAI == "NHAP"],
                 "PX": [g.ma_giao_dich for g in self.lich_su_giao_dich if g.LOAI == "XUAT"]}[tien_to]
        so = [int(m[len(tien_to):]) for m in nguon if m.startswith(tien_to) and m[len(tien_to):].isdigit()]
        return f"{tien_to}{(max(so) if so else 0) + 1:03d}"

    # ================= CRUD nguyên liệu =================
    def them_nguyen_lieu(self, nguyen_lieu):
        if self.tim_nguyen_lieu_theo_ma(nguyen_lieu.ma_nguyen_lieu):
            raise LoiNghiepVu(f"Mã nguyên liệu '{nguyen_lieu.ma_nguyen_lieu}' đã tồn tại.")
        if nguyen_lieu.ma_ncc:
            self.lay_nha_cung_cap(nguyen_lieu.ma_ncc)
        self.danh_sach_nguyen_lieu.append(nguyen_lieu)
        self._luu()

    def cap_nhat_nguyen_lieu(self, ma, **thay_doi):
        nl = self.lay_nguyen_lieu(ma)
        if thay_doi.get("ma_ncc"):
            self.lay_nha_cung_cap(thay_doi["ma_ncc"])
        nl.cap_nhat_thong_tin(**thay_doi)
        self._luu()

    def xoa_nguyen_lieu(self, ma):
        nl = self.lay_nguyen_lieu(ma)
        dung_trong = [m.ten_mon for m in self.danh_sach_mon_an if nl.ma_nguyen_lieu in m.dinh_muc_nguyen_lieu]
        if dung_trong:
            raise LoiNghiepVu(f"Không thể xóa '{nl.ten_nguyen_lieu}' vì đang nằm trong định mức món: "
                              f"{', '.join(dung_trong)}. Hãy sửa/xóa món ăn trước.")
        self.danh_sach_nguyen_lieu.remove(nl)
        self._luu()

    def tim_kiem_nguyen_lieu(self, tu_khoa="", tieu_chi="tat_ca", trang_thai="Tất cả", gan_dung=False,
                             so_ngay=config.SO_NGAY_CANH_BAO_MAC_DINH):
        """Tìm theo mã/tên/nhà cung cấp (không phân biệt hoa thường, dấu), lọc theo trạng thái, hỗ trợ gần đúng."""
        if tieu_chi not in ("tat_ca", "ma", "ten", "ncc"):
            raise DuLieuKhongHopLe(f"Tiêu chí tìm kiếm không hợp lệ: {tieu_chi}")
        kw = bo_dau(tu_khoa.strip())

        def khop(nl):
            ncc = self.tim_ncc_theo_ma(nl.ma_ncc)
            truong = {"ma": [nl.ma_nguyen_lieu], "ten": [nl.ten_nguyen_lieu],
                      "ncc": [nl.ma_ncc, ncc.ten_ncc if ncc else ""]}
            truong["tat_ca"] = truong["ma"] + truong["ten"] + truong["ncc"]
            return any(kw in bo_dau(t) for t in truong[tieu_chi])

        kq = [n for n in self.danh_sach_nguyen_lieu if not kw or khop(n)]
        if kw and not kq and gan_dung:
            bang = {bo_dau(n.ten_nguyen_lieu): n for n in self.danh_sach_nguyen_lieu}
            kq = [bang[t] for t in difflib.get_close_matches(kw, list(bang), n=10, cutoff=0.5)]
        loc = {"Tất cả": lambda n: True,
               "Sắp hết hàng": lambda n: n.kiem_tra_so_luong(),
               "Sắp hết hạn": lambda n: 0 <= n.so_ngay_con_lai() <= so_ngay,
               "Đã hết hạn": lambda n: n.so_ngay_con_lai() < 0}
        if trang_thai not in loc:
            raise DuLieuKhongHopLe(f"Bộ lọc trạng thái không hợp lệ: {trang_thai}")
        return [n for n in kq if loc[trang_thai](n)]

    # ================= CRUD nhà cung cấp =================
    def them_nha_cung_cap(self, ncc):
        if self.tim_ncc_theo_ma(ncc.ma_ncc):
            raise LoiNghiepVu(f"Mã nhà cung cấp '{ncc.ma_ncc}' đã tồn tại.")
        self.danh_sach_nha_cung_cap.append(ncc)
        self._luu()

    def cap_nhat_nha_cung_cap(self, ma, **thay_doi):
        self.lay_nha_cung_cap(ma).cap_nhat_thong_tin(**thay_doi)
        self._luu()

    def xoa_nha_cung_cap(self, ma_ncc):
        ncc = self.lay_nha_cung_cap(ma_ncc)
        dang_dung = [n.ten_nguyen_lieu for n in self.danh_sach_nguyen_lieu if n.ma_ncc == ncc.ma_ncc]
        if dang_dung:
            raise LoiNghiepVu(f"Không thể xóa '{ncc.ten_ncc}' vì đang cung cấp: {', '.join(dang_dung)}.")
        self.danh_sach_nha_cung_cap.remove(ncc)
        self._luu()

    def tim_kiem_nha_cung_cap(self, tu_khoa="", tieu_chi="tat_ca"):
        if tieu_chi not in ("tat_ca", "ma", "ten", "sdt"):
            raise DuLieuKhongHopLe(f"Tiêu chí tìm kiếm không hợp lệ: {tieu_chi}")
        kw = bo_dau(tu_khoa.strip())

        def khop(n):
            truong = {"ma": [n.ma_ncc], "ten": [n.ten_ncc], "sdt": [n.so_dien_thoai]}
            truong["tat_ca"] = truong["ma"] + truong["ten"] + truong["sdt"] + [n.email]
            return any(kw in bo_dau(t) for t in truong[tieu_chi])
        return [n for n in self.danh_sach_nha_cung_cap if not kw or khop(n)]

    # ================= CRUD món ăn =================
    def them_mon_an(self, mon):
        if any(m.ma_mon == mon.ma_mon for m in self.danh_sach_mon_an):
            raise LoiNghiepVu(f"Mã món '{mon.ma_mon}' đã tồn tại.")
        for ma in mon.dinh_muc_nguyen_lieu:
            self.lay_nguyen_lieu(ma)
        self.danh_sach_mon_an.append(mon)
        self._luu()

    def cap_nhat_mon_an(self, ma, ten_mon=None, dinh_muc=None):
        mon = self.lay_mon_an(ma)
        for m in (dinh_muc or {}):
            self.lay_nguyen_lieu(m)
        mon.cap_nhat_mon_an(ten_mon, dinh_muc)
        self._luu()

    def xoa_mon_an(self, ma):
        self.danh_sach_mon_an.remove(self.lay_mon_an(ma))
        self._luu()

    def tim_kiem_mon_an(self, tu_khoa=""):
        kw = bo_dau(tu_khoa.strip())
        return [m for m in self.danh_sach_mon_an if kw in bo_dau(m.ten_mon) or kw in bo_dau(m.ma_mon)]

    # ================= Giao dịch =================
    def ghi_nhan_giao_dich(self, giao_dich: GiaoDichKho):
        """Đa hình: PhieuNhap tăng tồn, PhieuXuat giảm tồn."""
        if any(g.ma_giao_dich == giao_dich.ma_giao_dich for g in self.lich_su_giao_dich):
            raise LoiNghiepVu(f"Mã giao dịch '{giao_dich.ma_giao_dich}' đã tồn tại.")
        giao_dich.thuc_hien_giao_dich(self)
        self.lich_su_giao_dich.append(giao_dich)
        self._luu()

    def loc_giao_dich(self, loai=None, tu_ngay="", den_ngay=""):
        tu = parse_ngay(tu_ngay) if tu_ngay else None
        den = parse_ngay(den_ngay) if den_ngay else None
        if tu and den and tu > den:
            raise DuLieuKhongHopLe("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
        kq = []
        for g in self.lich_su_giao_dich:
            d = parse_ngay(g.ngay_giao_dich)
            if (loai and g.LOAI != loai) or (tu and d < tu) or (den and d > den):
                continue
            kq.append(g)
        return kq

    # ================= Cảnh báo & thống kê =================
    def canh_bao_sap_het_hang(self, muc_toi_thieu=None):
        return [n for n in self.danh_sach_nguyen_lieu if n.kiem_tra_so_luong(muc_toi_thieu)]

    def canh_bao_sap_het_han(self, so_ngay=config.SO_NGAY_CANH_BAO_MAC_DINH):
        """Gồm cả nguyên liệu ĐÃ hết hạn; sắp xếp hết hạn sớm nhất lên đầu."""
        ds = [n for n in self.danh_sach_nguyen_lieu if n.kiem_tra_han_su_dung(so_ngay)]
        return sorted(ds, key=lambda n: n.so_ngay_con_lai())

    def tinh_tong_gia_tri_kho(self):
        return sum(n.gia_tri() for n in self.danh_sach_nguyen_lieu)

    def thong_ke_gia_tri_theo_nguyen_lieu(self):
        return sorted(((n.ten_nguyen_lieu, n.gia_tri()) for n in self.danh_sach_nguyen_lieu),
                      key=lambda x: x[1], reverse=True)

    def thong_ke_tieu_thu(self, tu_ngay="", den_ngay=""):
        """{ma_nl: {'ten','don_vi','so_luong','gia_tri'}} tính trên các phiếu xuất."""
        kq = {}
        for g in self.loc_giao_dich("XUAT", tu_ngay, den_ngay):
            for d in g.danh_sach_dong():
                ma = d["ma_nl"]
                nl = self.tim_nguyen_lieu_theo_ma(ma)
                m = kq.setdefault(ma, {"ten": nl.ten_nguyen_lieu if nl else ma, "don_vi": nl.don_vi if nl else "",
                                       "so_luong": 0.0, "gia_tri": 0.0})
                m["so_luong"] += float(d["so_luong"])
                m["gia_tri"] += float(d["so_luong"]) * float(d.get("don_gia", 0) or 0)
        return kq

    def thong_ke_nhap_xuat(self):
        tk = {"NHAP": {"so_phieu": 0, "gia_tri": 0.0}, "XUAT": {"so_phieu": 0, "gia_tri": 0.0}}
        for g in self.lich_su_giao_dich:
            tk[g.LOAI]["so_phieu"] += 1
            tk[g.LOAI]["gia_tri"] += g.tong_gia_tri()
        return tk

    # ================= File JSON =================
    def luu_du_lieu_json(self, ten_file=None):
        tep = JsonFile(ten_file) if ten_file else self._file
        tep.ghi({"phien_ban": 1,
                 "nguyen_lieu": [n.to_dict() for n in self.danh_sach_nguyen_lieu],
                 "nha_cung_cap": [n.to_dict() for n in self.danh_sach_nha_cung_cap],
                 "mon_an": [m.to_dict() for m in self.danh_sach_mon_an],
                 "giao_dich": [g.to_dict() for g in self.lich_su_giao_dich]})

    def doc_du_lieu_json(self, ten_file=None):
        """Đọc dữ liệu. Trả về False nếu chưa có dữ liệu (file không tồn tại/rỗng). Bản ghi lỗi bị bỏ qua và ghi vào canh_bao_doc."""
        tep = JsonFile(ten_file) if ten_file else self._file
        du_lieu = tep.doc(mac_dinh=None)
        self.canh_bao_doc = [tep.thong_bao] if tep.thong_bao else []
        if du_lieu is None:
            return False
        if not isinstance(du_lieu, dict):
            raise LoiFile("Cấu trúc file dữ liệu không đúng (cần là một đối tượng JSON).")
        self.xoa_toan_bo()
        # Thứ tự nạp quan trọng: nhà cung cấp -> nguyên liệu -> món ăn -> giao dịch
        self._nap(du_lieu, "nha_cung_cap", NhaCungCap.from_dict, self.danh_sach_nha_cung_cap)
        self._nap(du_lieu, "nguyen_lieu", NguyenLieu.from_dict, self.danh_sach_nguyen_lieu)
        self._nap(du_lieu, "mon_an", MonAn.from_dict, self.danh_sach_mon_an)
        self._nap(du_lieu, "giao_dich", giao_dich_tu_dict, self.lich_su_giao_dich)
        return True

    def _nap(self, du_lieu, khoa, ham_tao, dich):
        ds = du_lieu.get(khoa, [])
        if not isinstance(ds, list):
            self.canh_bao_doc.append(f"Mục '{khoa}' sai định dạng nên bị bỏ qua.")
            return
        for i, d in enumerate(ds):
            try:
                dich.append(ham_tao(d))
            except _LOI_DOC as e:
                self.canh_bao_doc.append(f"Bỏ qua bản ghi {khoa}[{i}] bị lỗi: {e}")

    def sao_luu(self):
        return self._file.sao_luu()

    def danh_sach_sao_luu(self):
        return self._file.danh_sach_sao_luu()

    def khoi_phuc_tu_sao_luu(self, ten_ban_sao):
        self._file.khoi_phuc(ten_ban_sao)
        self.doc_du_lieu_json()
