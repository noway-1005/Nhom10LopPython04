"""Lớp xử lý file JSON an toàn: đọc/ghi/cập nhật/sao lưu/khôi phục."""
import json
import os
import shutil
from datetime import datetime

import config
from exceptions import LoiFile


class JsonFile:
    """Đọc/ghi một file JSON.

    - Ghi an toàn: serialize trước -> sao lưu bản cũ -> ghi file tạm -> os.replace (nguyên tử).
    - Đọc: xử lý file chưa tồn tại, file rỗng, sai định dạng (tự khôi phục từ bản sao lưu), không có quyền.
    """

    def __init__(self, duong_dan, thu_muc_sao_luu=None):
        self.duong_dan = duong_dan
        self.thu_muc_sao_luu = thu_muc_sao_luu or os.path.join(os.path.dirname(duong_dan), "backup")
        self.thong_bao = ""      # thông điệp cảnh báo sau lần đọc gần nhất (nếu có)

    @property
    def _tien_to(self):
        return os.path.splitext(os.path.basename(self.duong_dan))[0]

    # ---------- Đọc ----------
    def doc(self, mac_dinh=None):
        self.thong_bao = ""
        if not os.path.exists(self.duong_dan):
            return mac_dinh
        try:
            with open(self.duong_dan, "r", encoding="utf-8") as f:
                noi_dung = f.read()
        except PermissionError:
            raise LoiFile(f"Không có quyền đọc file '{self.duong_dan}'.") from None
        except (OSError, UnicodeDecodeError) as e:
            raise LoiFile(f"Không đọc được file '{self.duong_dan}': {e}") from None
        if not noi_dung.strip():
            return mac_dinh                      # file rỗng
        try:
            return json.loads(noi_dung)
        except json.JSONDecodeError as e:
            return self._xu_ly_file_hong(e, mac_dinh)

    def _xu_ly_file_hong(self, loi, mac_dinh):
        nhan = datetime.now().strftime("%Y%m%d_%H%M%S")
        ten_hong = f"{self.duong_dan}.hong_{nhan}"
        try:
            os.replace(self.duong_dan, ten_hong)   # giữ lại file hỏng, không bị ghi đè
        except OSError:
            ten_hong = "(không đổi tên được)"
        for ten in self.danh_sach_sao_luu():
            try:
                with open(os.path.join(self.thu_muc_sao_luu, ten), "r", encoding="utf-8") as f:
                    du_lieu = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            self.thong_bao = (f"File '{os.path.basename(self.duong_dan)}' sai định dạng JSON (dòng {loi.lineno}). "
                              f"Đã khôi phục từ bản sao lưu '{ten}'. File lỗi được giữ tại: {ten_hong}")
            return du_lieu
        self.thong_bao = (f"File '{os.path.basename(self.duong_dan)}' sai định dạng JSON (dòng {loi.lineno}) "
                          f"và không có bản sao lưu. File lỗi được giữ tại: {ten_hong}")
        return mac_dinh

    # ---------- Ghi ----------
    def ghi(self, du_lieu):
        try:
            noi_dung = json.dumps(du_lieu, ensure_ascii=False, indent=2)   # lỗi ở đây chưa đụng tới file thật
        except (TypeError, ValueError) as e:
            raise LoiFile(f"Dữ liệu không thể chuyển sang JSON: {e}") from None
        try:
            os.makedirs(os.path.dirname(self.duong_dan) or ".", exist_ok=True)
            self.sao_luu()
            tam = self.duong_dan + ".tmp"
            with open(tam, "w", encoding="utf-8") as f:
                f.write(noi_dung)
            os.replace(tam, self.duong_dan)
        except PermissionError:
            raise LoiFile(f"Không có quyền ghi file '{self.duong_dan}'.") from None
        except OSError as e:
            raise LoiFile(f"Không ghi được file '{self.duong_dan}': {e}") from None

    def cap_nhat(self, ham_cap_nhat, mac_dinh=None):
        """Đọc -> áp dụng ham_cap_nhat(du_lieu) -> ghi lại."""
        du_lieu = self.doc(mac_dinh)
        du_lieu = ham_cap_nhat(du_lieu)
        self.ghi(du_lieu)

    # ---------- Sao lưu / khôi phục ----------
    def sao_luu(self):
        """Sao lưu bản hiện tại (nếu có). Trả về tên file sao lưu hoặc None."""
        if not os.path.exists(self.duong_dan) or os.path.getsize(self.duong_dan) == 0:
            return None
        try:
            os.makedirs(self.thu_muc_sao_luu, exist_ok=True)
            ten = f"{self._tien_to}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
            shutil.copyfile(self.duong_dan, os.path.join(self.thu_muc_sao_luu, ten))
            for cu in self.danh_sach_sao_luu()[config.SO_BAN_SAO_LUU_TOI_DA:]:
                os.remove(os.path.join(self.thu_muc_sao_luu, cu))
            return ten
        except OSError as e:
            raise LoiFile(f"Không sao lưu được: {e}") from None

    def danh_sach_sao_luu(self):
        """Tên các bản sao lưu, mới nhất trước."""
        if not os.path.isdir(self.thu_muc_sao_luu):
            return []
        ds = [t for t in os.listdir(self.thu_muc_sao_luu) if t.startswith(self._tien_to + "_") and t.endswith(".json")]
        return sorted(ds, reverse=True)

    def khoi_phuc(self, ten_ban_sao):
        nguon = os.path.join(self.thu_muc_sao_luu, ten_ban_sao)
        if not os.path.isfile(nguon):
            raise LoiFile(f"Không tìm thấy bản sao lưu '{ten_ban_sao}'.")
        try:
            with open(nguon, "r", encoding="utf-8") as f:
                json.load(f)                      # kiểm tra bản sao lưu hợp lệ trước khi đè
            self.sao_luu()
            shutil.copyfile(nguon, self.duong_dan)
        except json.JSONDecodeError:
            raise LoiFile("Bản sao lưu bị hỏng, không thể khôi phục.") from None
        except OSError as e:
            raise LoiFile(f"Không khôi phục được: {e}") from None
