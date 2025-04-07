import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from tqdm import tqdm
import time
import os
import csv
import urllib.parse
import hashlib

# --- Cấu hình ---
CSV_FILE = "PhiUSIIL_Phishing_URL_Dataset.csv"
NUM_URLS_TO_FETCH = 200  # Để thử nghiệm, thay đổi thành None để lấy tất cả
RAW_HTML_DIR = "raw_html_data"
MAPPING_FILE = "url_html_mapping.csv"
LABEL_COLUMN = "label"  # Thay đổi nếu tên cột label khác

# --- Cấu hình Selenium ---
CHROME_DRIVER_PATH = None  # Điền đường dẫn nếu ChromeDriver không nằm trong PATH. Ví dụ: "C:\\chromedriver\\chromedriver.exe"
HEADLESS = True  # Chạy trình duyệt ẩn
WAIT_TIME = 5  # Thời gian chờ để trang web tải xong (giây)

# --- Hàm tiện ích ---
def create_safe_filename(url):
    """
    Tạo tên file an toàn từ URL.
    """
    url = urllib.parse.urlparse(url).netloc + urllib.parse.urlparse(url).path + urllib.parse.urlparse(url).query
    safe_filename = "".join(c if c.isalnum() or c in ['.', '-', '_'] else "_" for c in url)

    max_length = 200
    if len(safe_filename) > max_length:
        hash_object = hashlib.md5(url.encode())
        hash_hex = hash_object.hexdigest()
        safe_filename = f"{safe_filename[:max_length - 33]}_{hash_hex}"

    return safe_filename

def save_html_to_file(url, html_content, base_dir=RAW_HTML_DIR, mapping_file=MAPPING_FILE):
    """
    Lưu nội dung HTML vào file và tạo entry trong file ánh xạ.
    """
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

# --- Main ---
if __name__ == "__main__":
    # Đọc dữ liệu từ CSV
    df = pd.read_csv(CSV_FILE)

    # Lọc chỉ URL có label=1
    df_filtered = df[df[LABEL_COLUMN] == 1]

    # Lấy số lượng URL cần xử lý (None để lấy tất cả)
    if NUM_URLS_TO_FETCH is None:
        urls_to_fetch = df_filtered["URL"].tolist()
        total_urls = len(urls_to_fetch)
    else:
        urls_to_fetch = df_filtered["URL"].head(NUM_URLS_TO_FETCH).tolist()
        total_urls = min(NUM_URLS_TO_FETCH, len(df_filtered))  # Đảm bảo không vượt quá số lượng URL có label=1

    # Cấu hình Chrome Options
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    # Khởi tạo WebDriver
    if CHROME_DRIVER_PATH:
        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    # Lặp qua URL và lưu HTML
    with tqdm(total=total_urls, desc="Đang tải HTML") as pbar:  # Sử dụng tqdm để hiển thị thanh tiến trình
        for url in urls_to_fetch:
            try:
                driver.get(url)
                time.sleep(WAIT_TIME)  # Đợi trang tải

                html_content = driver.page_source
                success = save_html_to_file(url, html_content)

                if not success:
                    print(f"Không thể lưu HTML cho {url}")

            except Exception as e:
                print(f"Lỗi khi tải {url}: {e}")

            pbar.update(1)  # Cập nhật thanh tiến trình sau mỗi lần lặp

    # Đóng trình duyệt
    driver.quit()

    print("Hoàn thành!")