# -*- coding: utf-8 -*-
"""Sinh dữ liệu mẫu bằng module random (có seed để tái lập được khi kiểm thử)."""
import random
from datetime import date, timedelta

import config
from models.giao_dich import PhieuNhap, PhieuXuat
from models.mon_an import MonAn
from models.nguyen_lieu import NguyenLieu
from models.nha_cung_cap import NhaCungCap
from services.validators import dinh_dang_ngay

NCC_MAU = [("Thực phẩm sạch An Phú", "0901234567", "anphu@thucpham.vn"),
           ("Chợ đầu mối Thủ Đức", "0912345678", "thuduc@chodaumoi.vn"),
           ("Hải sản Biển Xanh", "0987654321", "bienxanh@haisan.vn"),
           ("Đại lý gia vị Hương Việt", "0933456789", "")]
# (tên, đơn vị, giá nhập, chỉ số NCC (1-based), mức tối thiểu)
NL_MAU = [("Thịt bò", "kg", 250000, 1, 5), ("Thịt gà", "kg", 90000, 1, 8), ("Thịt heo", "kg", 130000, 1, 8),
          ("Cá hồi", "kg", 380000, 3, 3), ("Tôm sú", "kg", 280000, 3, 3), ("Trứng gà", "quả", 3500, 1, 30),
          ("Gạo thơm", "kg", 22000, 2, 20), ("Bún tươi", "kg", 18000, 2, 10), ("Cà chua", "kg", 25000, 2, 5),
          ("Hành tây", "kg", 20000, 2, 5), ("Tỏi", "kg", 60000, 2, 2), ("Rau muống", "kg", 15000, 2, 5),
          ("Nước mắm", "lít", 45000, 4, 3), ("Dầu ăn", "lít", 45000, 4, 5)]
MON_MAU = [("Cơm gà", {"Gạo thơm": 0.15, "Thịt gà": 0.2, "Hành tây": 0.03, "Tỏi": 0.01}),
           ("Bún bò", {"Bún tươi": 0.2, "Thịt bò": 0.15, "Hành tây": 0.05, "Nước mắm": 0.02}),
           ("Trứng chiên cà chua", {"Trứng gà": 2, "Cà chua": 0.1, "Dầu ăn": 0.02, "Hành tây": 0.02}),
           ("Rau muống xào tỏi", {"Rau muống": 0.2, "Tỏi": 0.01, "Dầu ăn": 0.02}),
           ("Tôm rang", {"Tôm sú": 0.15, "Tỏi": 0.01, "Nước mắm": 0.02}),
           ("Cá hồi áp chảo", {"Cá hồi": 0.2, "Dầu ăn": 0.02, "Tỏi": 0.01})]


def tao_du_lieu_mau(kho, seed=None, nguoi_thuc_hien="admin"):
    """Xóa dữ liệu hiện có trong bộ nhớ và sinh lại bộ dữ liệu mẫu (ngẫu nhiên theo seed)."""
    rnd = random.Random(seed)
    hom_nay = date.today()
    kho.xoa_toan_bo()
    for i, (ten, sdt, email) in enumerate(NCC_MAU, 1):
        kho.them_nha_cung_cap(NhaCungCap(f"NCC{i:03d}", ten, sdt, email))
    ma_theo_ten = {}
    for i, (ten, dv, gia, ncc, toi_thieu) in enumerate(NL_MAU, 1):
        sl = round(rnd.uniform(0.6, 4.0) * toi_thieu, 1)            # vài nguyên liệu sẽ rơi xuống mức cảnh báo
        han = hom_nay + timedelta(days=rnd.choice([rnd.randint(-2, 6), rnd.randint(10, 60), rnd.randint(10, 90)]))
        ma = f"NL{i:03d}"
        kho.them_nguyen_lieu(NguyenLieu(ma, ten, sl, dv, gia, dinh_dang_ngay(han), f"NCC{ncc:03d}", toi_thieu))
        ma_theo_ten[ten] = ma
    for i, (ten, dm) in enumerate(MON_MAU, 1):
        kho.them_mon_an(MonAn(f"MA{i:03d}", ten, {ma_theo_ten[t]: sl for t, sl in dm.items()}))
    for k in range(1, 5):                                           # lịch sử nhập
        nl = rnd.sample(kho.danh_sach_nguyen_lieu, 3)
        dong = [{"ma_nl": n.ma_nguyen_lieu, "so_luong": round(rnd.uniform(1, 10), 1), "gia_nhap": n.gia_nhap} for n in nl]
        ngay = dinh_dang_ngay(hom_nay - timedelta(days=rnd.randint(3, 30)))
        kho.ghi_nhan_giao_dich(PhieuNhap(f"PN{k:03d}", ngay, nguoi_thuc_hien, nl[0].ma_ncc, dong))
    for k in range(1, 5):                                           # lịch sử xuất (xuất ≤ 15% tồn để luôn hợp lệ)
        nl = rnd.sample(kho.danh_sach_nguyen_lieu, 3)
        dong = [{"ma_nl": n.ma_nguyen_lieu, "so_luong": max(0.1, round(n.so_luong * rnd.uniform(0.03, 0.15), 1))} for n in nl]
        ngay = dinh_dang_ngay(hom_nay - timedelta(days=rnd.randint(0, 25)))
        kho.ghi_nhan_giao_dich(PhieuXuat(f"PX{k:03d}", ngay, nguoi_thuc_hien, dong, rnd.choice(config.LY_DO_XUAT)))
    return kho
