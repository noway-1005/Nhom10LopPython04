"""Cấu hình và hằng số dùng chung toàn ứng dụng (đường dẫn, tham số mặc định, giao diện)."""
import os
import sys


def thu_muc_goc():
    """Thư mục chứa ứng dụng. Khi đóng gói bằng PyInstaller là thư mục chứa file .exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ---- Đường dẫn (tương đối theo thư mục ứng dụng, không phụ thuộc máy) ----
BASE_DIR = thu_muc_goc()
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUP_DIR = os.path.join(DATA_DIR, "backup")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
FILE_KHO = os.path.join(DATA_DIR, "kho.json")
FILE_TAI_KHOAN = os.path.join(DATA_DIR, "tai_khoan.json")
FILE_CRAWL = os.path.join(DATA_DIR, "crawl_monan.json")
FILE_NHAT_KY = os.path.join(DATA_DIR, "nhat_ky.log")
SO_BAN_SAO_LUU_TOI_DA = 10

# ---- Tham số nghiệp vụ ----
TEN_UNG_DUNG = "Quản lý kho nguyên liệu quán ăn"
DINH_DANG_NGAY = "%d/%m/%Y"
MUC_TOI_THIEU_MAC_DINH = 5
SO_NGAY_CANH_BAO_MAC_DINH = 7
DON_VI = ["kg", "g", "lít", "ml", "quả", "cái", "gói", "hộp", "chai"]
LY_DO_XUAT = ["Chế biến", "Hủy bỏ (hết hạn)", "Hư hỏng", "Chuyển chi nhánh", "Khác"]
MAT_KHAU_TOI_THIEU = 6
PBKDF2_LAN_LAP = 100_000
ADMIN_MAC_DINH = ("admin", "admin123")   # chỉ để khởi tạo lần đầu, hãy đổi mật khẩu sau khi đăng nhập

# ---- Phân quyền ----
VAI_TRO_ADMIN = "Admin"
VAI_TRO_USER = "User"
QUYEN = {
    VAI_TRO_ADMIN: {"xem", "sua_nguyen_lieu", "sua_ncc", "sua_mon_an", "nhap_kho", "xuat_kho",
                    "che_bien", "thong_ke", "xuat_bao_cao", "quan_ly_du_lieu", "quan_ly_tai_khoan"},
    VAI_TRO_USER: {"xem", "xuat_kho", "che_bien", "thong_ke", "xuat_bao_cao"},
}

# ---- API (TheMealDB: miễn phí, không cần khóa) ----
API_URL = "https://www.themealdb.com/api/json/v1/1/search.php"
API_TIMEOUT = 10
SO_SUAT_GOC = 4   # công thức của TheMealDB thường cho ~4 người -> chia để ra định mức 1 suất

# ---- Giao diện ----
FONT = ("Segoe UI", 10)
FONT_DAM = ("Segoe UI", 10, "bold")
FONT_TIEU_DE = ("Segoe UI", 13, "bold")
FONT_NHO = ("Segoe UI", 8)
MAU_CHINH = "#2b6cb0"
MAU_NEN = "#f4f6f8"
MAU_HET_HAN = "#f8d7da"
MAU_SAP_HET_HAN = "#fff3cd"
MAU_SAP_HET_HANG = "#ffe5d0"
MAU_COT = "#4a90d9"
MAU_COT_CANH_BAO = "#e4572e"
