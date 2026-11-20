# -*- coding: utf-8 -*-
"""Điểm khởi động:  python main.py [--reset-data] [--version]

--reset-data : xóa kho.json hiện có (đã sao lưu) và sinh lại dữ liệu mẫu.
"""
import sys

import config
from exceptions import LoiUngDung
from services.auth import AuthManager
from services.kho import Kho
from services.sample_data import tao_du_lieu_mau


def khoi_tao_du_lieu(reset=False):
    """Đọc dữ liệu; nếu chưa có (hoặc --reset-data) thì sinh dữ liệu mẫu để ứng dụng luôn chạy được."""
    auth = AuthManager()
    auth.doc()
    kho = Kho(tu_dong_luu=False)
    co_du_lieu = kho.doc_du_lieu_json()
    if reset or not co_du_lieu or kho.trong():
        if co_du_lieu:
            kho.sao_luu()
        tao_du_lieu_mau(kho, seed=2026)
        kho.luu_du_lieu_json()
        print("Đã sinh dữ liệu mẫu.")
    kho.tu_dong_luu = True           # từ đây mọi thay đổi được ghi ngay xuống file JSON
    return kho, auth


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if sys.version_info < (3, 8):
        print(f"Cần Python >= 3.8 (đang dùng {sys.version.split()[0]}).", file=sys.stderr)
        return 1
    if "--version" in argv:
        print(f"{config.TEN_UNG_DUNG} - Python {sys.version.split()[0]} - {sys.platform}")
        return 0
    try:
        kho, auth = khoi_tao_du_lieu(reset="--reset-data" in argv)
    except LoiUngDung as e:
        print(f"Không khởi động được: {e}", file=sys.stderr)
        return 2
    import tkinter                                   # import muộn: chế độ --version không cần có màn hình
    from ui.app import UngDung
    try:
        UngDung(kho, auth).mainloop()
    except tkinter.TclError as e:
        print(f"Không mở được giao diện: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
