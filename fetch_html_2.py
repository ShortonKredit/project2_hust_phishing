import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
import time
import os
import csv
import urllib.parse
import hashlib
import re
from webdriver_manager.chrome import ChromeDriverManager  # Thêm import

# --- Cấu hình ---
CSV_FILE = "PhiUSIIL_Phishing_URL_Dataset.csv"
NUM_URLS_TO_FETCH = None  # Để thử nghiệm, thay đổi thành None để lấy tất cả
RAW_HTML_DIR = "raw_html_data_2"
MAPPING_FILE = "url_html_mapping_2.csv"
LABEL_COLUMN = "label"  # Thay đổi nếu tên cột label khác
ERROR_PATTERNS = [
    r"404 not found",
    r"403 forbidden",
    r"410 gone",
    r"503 service unavailable",
    r"error 403",
    r"error 404",
    r"error 410",
    r"error 503",
    r"access denied",
    r"temporarily unavailable",
    r"page not found",
    r"422 unprocessable content",  # Thêm lỗi mới
    r"site not found",            # Thêm lỗi mới
    r"400 bad request"             # Thêm lỗi mới
]
CLOUDFLARE_PATTERN = re.compile(r"Just a moment\.\.\.", re.IGNORECASE)  # Phát hiện trang Cloudflare
WEBSITEWS_PATTERN = re.compile(r"<title>WEBSITE\.WS", re.IGNORECASE)  # Phát hiện trang WEBSITE.WS
GLITCH_PATTERN = re.compile(r"<title>Oops! This project isn't running.", re.IGNORECASE) # Phát hiện trang Glitch
SITE_FROZEN_PATTERN = re.compile(r"<title>530 - Site is frozen</title>", re.IGNORECASE) # Phát hiện trang "Site is frozen"
EMPTY_HTML_PATTERN = re.compile(r"<html><head></head><body></body></html>", re.IGNORECASE) # Phát hiện trang rỗng
BUCKET_NOT_FOUND_PATTERN = re.compile(r"\"code\":\"BucketNotFound\"", re.IGNORECASE) # Phát hiện lỗi Bucket Not Found
BAD_GATEWAY_PATTERN = re.compile(r"<title>502 Bad Gateway</title>", re.IGNORECASE) # Phát hiện lỗi 502 Bad Gateway
COMBINED_ERROR_PATTERN = re.compile("|".join(ERROR_PATTERNS), re.IGNORECASE)  # Compile regex

# --- Cấu hình Selenium ---
# CHROME_DRIVER_PATH = None  # Không cần nếu dùng webdriver_manager
HEADLESS = True  # Chạy trình duyệt ẩn
WAIT_TIME = 5  # Tăng thời gian chờ để xử lý Cloudflare/WEBSITE.WS/Glitch (giây)
PAGE_LOAD_STRATEGY = "eager"  # "normal", "eager", "none".  "eager" tải HTML nhưng bỏ qua ảnh/css.
DISABLE_IMAGES = False # Bật/tắt tải ảnh

# --- Hàm tiện ích ---
def create_safe_filename(url):
    """Tạo tên file an toàn từ URL."""
    url = urllib.parse.urlparse(url).netloc + urllib.parse.urlparse(url).path + urllib.parse.urlparse(url).query
    safe_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else "_" for c in url)
    max_length = 200
    if len(safe_filename) > max_length:
        hash_object = hashlib.md5(url.encode())
        hash_hex = hash_object.hexdigest()
        safe_filename = f"{safe_filename[:max_length - 33]}_{hash_hex}"
    return safe_filename

def save_html_to_file(url, html_content, base_dir=RAW_HTML_DIR, mapping_file=MAPPING_FILE):
    """Lưu nội dung HTML vào file và tạo entry trong file ánh xạ."""
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    filename = create_safe_filename(url) + ".html"
    filepath = os.path.join(base_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Lỗi khi lưu {url}: {e}")
        return False

    try:
        file_exists = os.path.isfile(mapping_file)
        with open(mapping_file, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["url", "html_filename"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({"url": url, "html_filename": filename})
        return True
    except Exception as e:
        print(f"Lỗi khi cập nhật file ánh xạ: {e}")
        return False

def contains_error_message(html_content, error_pattern=COMBINED_ERROR_PATTERN):
    """Kiểm tra xem nội dung HTML có chứa thông báo lỗi không."""
    return bool(error_pattern.search(html_content))

def is_cloudflare_page(html_content, cloudflare_pattern=CLOUDFLARE_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là trang Cloudflare không."""
    return bool(cloudflare_pattern.search(html_content))

def is_website_ws_page(html_content, websitews_pattern=WEBSITEWS_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là trang WEBSITE.WS không."""
    return bool(websitews_pattern.search(html_content))

def is_glitch_page(html_content, glitch_pattern=GLITCH_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là trang Glitch không."""
    return bool(glitch_pattern.search(html_content))

def is_site_frozen_page(html_content, site_frozen_pattern=SITE_FROZEN_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là trang "Site is frozen" không."""
    return bool(site_frozen_pattern.search(html_content))

def is_empty_html(html_content, empty_html_pattern=EMPTY_HTML_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là trang HTML rỗng không."""
    return bool(empty_html_pattern.search(html_content))

def is_bucket_not_found(html_content, bucket_not_found_pattern=BUCKET_NOT_FOUND_PATTERN):
    """Kiểm tra xem nội dung HTML có phải là lỗi Bucket Not Found không."""
    return bool(bucket_not_found_pattern.search(html_content))

def is_bad_gateway(html_content, bad_gateway_pattern=BAD_GATEWAY_PATTERN):
     """Kiểm tra xem nội dung HTML có phải là lỗi 502 Bad Gateway không."""
     return bool(bad_gateway_pattern.search(html_content))

def get_content_from_frame(driver):
    """Lấy nội dung từ iframe hoặc frameset."""
    try:
        # Chờ frame tải
        WebDriverWait(driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "frame")))
        # Lấy nội dung từ frame
        html_content = driver.page_source
        # Quay lại nội dung chính
        driver.switch_to.default_content()
        return html_content
    except TimeoutException:
        print("Không tìm thấy frame hoặc không thể chuyển sang frame")
        driver.switch_to.default_content() # Đảm bảo quay lại nội dung chính
        return ""

def load_existing_mappings(mapping_file=MAPPING_FILE, raw_html_dir=RAW_HTML_DIR):
    """Tải các ánh xạ URL-HTML filename hiện có từ file mapping."""
    existing_mappings = {}
    if os.path.exists(mapping_file):
        try:
            with open(mapping_file, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    url = row["url"]
                    html_filename = row["html_filename"]
                    html_filepath = os.path.join(raw_html_dir, html_filename)  # Tạo đường dẫn đầy đủ
                    if os.path.exists(html_filepath):  # Kiểm tra xem file có tồn tại
                        existing_mappings[url] = html_filepath
                    else:
                        print(f"WARNING: File {html_filename} được ánh xạ tới URL {url} không tồn tại. Bỏ qua.")
        except Exception as e:
            print(f"Lỗi khi đọc file ánh xạ: {e}")
    return existing_mappings

# --- Main ---
if __name__ == "__main__":
    # Đọc dữ liệu từ CSV
    df = pd.read_csv(CSV_FILE)

    # Lọc chỉ URL có label=0
    df_filtered = df[df[LABEL_COLUMN] == 0]

    # Lấy số lượng URL cần xử lý (None để lấy tất cả)
    if NUM_URLS_TO_FETCH is None:
        urls_to_fetch = df_filtered["URL"].tolist()
        total_urls = len(urls_to_fetch)
    else:
        urls_to_fetch = df_filtered["URL"].head(NUM_URLS_TO_FETCH).tolist()
        total_urls = min(NUM_URLS_TO_FETCH, len(df_filtered))

    # Tải các ánh xạ hiện có
    existing_mappings = load_existing_mappings()

    # Cấu hình Chrome Options
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.page_load_strategy = PAGE_LOAD_STRATEGY  # Tùy chỉnh chiến lược tải trang
    if DISABLE_IMAGES:
        chrome_options.add_argument("--blink-settings=imagesEnabled=false") # Tắt ảnh

    # Khởi tạo WebDriver với webdriver_manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Lặp qua URL và lưu HTML
    with tqdm(total=total_urls, desc="Đang tải HTML") as pbar:  # Sử dụng tqdm để hiển thị thanh tiến trình
        for url in urls_to_fetch:
            if url in existing_mappings:
                print(f"Bỏ qua {url} vì đã tồn tại file {existing_mappings[url]}.")
                pbar.update(1)  # Cập nhật thanh tiến trình
                continue  # Chuyển sang URL tiếp theo

            try:
                driver.get(url)
                html_content = ""  # Khởi tạo biến

                if is_website_ws_page(driver.page_source): # Kiểm tra Website.WS
                    html_content = get_content_from_frame(driver) # Lấy nội dung từ frame
                    if not html_content:
                        print(f"Không thể lấy nội dung từ frame của {url}")

                else: # Không phải Website.WS, xử lý như bình thường
                    try:
                        # Chờ cho <body> xuất hiện (tối đa WAIT_TIME giây)
                        WebDriverWait(driver, WAIT_TIME).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        html_content = driver.page_source
                    except TimeoutException:
                        print(f"Không thể tải trang đầy đủ sau {WAIT_TIME} giây.")
                        html_content = driver.page_source  # Lấy những gì đã tải được


                if html_content: # Đảm bảo có nội dung trước khi kiểm tra
                    if not is_cloudflare_page(html_content) and not is_glitch_page(html_content) and not is_site_frozen_page(html_content) and not is_empty_html(html_content) and not is_bucket_not_found(html_content) and not is_bad_gateway(html_content) and not contains_error_message(html_content):  # Kiểm tra lỗi và Cloudflare
                        success = save_html_to_file(url, html_content)
                        if not success:
                            print(f"Không thể lưu HTML cho {url}")
                    else:
                        print(f"Bỏ qua {url} vì chứa thông báo lỗi, trang Cloudflare, trang Glitch, trang Site is frozen, trang rỗng, lỗi Bucket Not Found hoặc lỗi 502 Bad Gateway.")
                else:
                    print(f"Không thể tải nội dung cho {url}")

            except Exception as e:
                print(f"Lỗi khi tải {url}: {e}")

            pbar.update(1)  # Cập nhật thanh tiến trình sau mỗi lần lặp

    # Đóng trình duyệt
    driver.quit()

    print("Hoàn thành!")