# -*- coding: utf-8 -*-
"""Các ngoại lệ tự định nghĩa; thông điệp luôn là tiếng Việt, hiển thị trực tiếp cho người dùng."""


class LoiUngDung(Exception):
    """Lớp cha của mọi lỗi 'dự kiến trước' trong ứng dụng."""


class DuLieuKhongHopLe(LoiUngDung, ValueError):
    """Dữ liệu nhập sai định dạng, thiếu, ngoài miền giá trị."""


class LoiNghiepVu(LoiUngDung):
    """Vi phạm ràng buộc nghiệp vụ (trùng mã, không đủ tồn kho, đang được tham chiếu...)."""


class LoiFile(LoiUngDung):
    """Lỗi đọc/ghi file (không quyền, sai định dạng...)."""


class LoiKetNoi(LoiUngDung):
    """Lỗi khi gọi API/crawl (mất mạng, quá thời gian, dữ liệu sai)."""


class LoiXacThuc(LoiUngDung):
    """Sai tài khoản/mật khẩu hoặc không đủ quyền."""
