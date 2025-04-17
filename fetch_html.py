import pandas as pd
import os
import csv
import re
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==== Khởi tạo ====
df = pd.read_csv("combined_data.csv")
url_list = df[df['label'] == 1]['url'].dropna().unique()

output_folder = 'RAW_HTML_DATA'
os.makedirs(output_folder, exist_ok=True)

mapping_file = "URL_HTML_MAPPING_new.csv"

# Đọc các URL đã xử lý trước đó (nếu có)
if os.path.exists(mapping_file):
    try:
        existing_mapping = pd.read_csv(mapping_file)
        if 'original_url' in existing_mapping.columns:
            done_urls = set(existing_mapping['original_url'].astype(str))
        else:
            done_urls = set()
    except Exception:
        done_urls = set()
else:
    done_urls = set()

# Cấu hình trình duyệt headless tối ưu
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
prefs = {
    "profile.managed_default_content_settings.images": 2,
    "profile.managed_default_content_settings.fonts": 2,
    "profile.managed_default_content_settings.stylesheets": 1
}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Ghi file ánh xạ từng dòng (append)
def append_mapping(record):
    write_header = not os.path.exists(mapping_file) or os.path.getsize(mapping_file) == 0
    with open(mapping_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["original_url", "final_url", "filename"])
        if write_header:
            writer.writeheader()
        writer.writerow(record)

# Làm sạch tên file từ URL (tránh ký tự đặc biệt)
def clean_filename(url):
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', url)
    return name[:100]  # tránh tên quá dài

# Từ khóa lỗi phổ biến cần lọc
error_keywords = [
    "404 not found", "403 forbidden", "410 gone", "503 service unavailable",
    "error 403", "error 404", "error 410", "error 503",
    "access denied", "temporarily unavailable", "page not found"
]

try:
    for idx, original_url in enumerate(url_list):
        if original_url in done_urls:
            print(f"⏩ Bỏ qua (đã tải): {original_url}")
            continue

        # Tạo danh sách URL thử nghiệm
        if original_url.startswith("http"):
            url_variants = [original_url]
        else:
            url_variants = [f"https://{original_url}", f"http://{original_url}"]

        success = False

        for url in url_variants:
            try:
                driver.get(url)

                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                html = driver.page_source.lower()
                title = driver.title.lower()

                # Kiểm tra từ khóa lỗi trong cả title và nội dung
                if any(err in html or err in title for err in error_keywords):
                    print(f"🚫 Bỏ qua (lỗi HTTP nghi ngờ): {url}")
                    continue

                filename_base = clean_filename(original_url)
                filename = f"{filename_base}.html"
                filepath = os.path.join(output_folder, filename)

                # Nếu file đã tồn tại, thêm hậu tố để tránh ghi đè
                counter = 1
                while os.path.exists(filepath):
                    filename = f"{filename_base}_{counter}.html"
                    filepath = os.path.join(output_folder, filename)
                    counter += 1

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)

                print(f"✅ Đã lưu: {filename} từ {url}")
                record = {"original_url": original_url, "final_url": url, "filename": filename}
                append_mapping(record)
                success = True
                break

            except Exception as e:
                print(f"⚠️ Lỗi với {url}: {e}")
                continue

        if not success:
            print(f"❌ Không thể truy cập hoặc lọc: {original_url}")

except KeyboardInterrupt:
    print("\n🛑 Bạn đã dừng thủ công. Dừng an toàn...")

finally:
    driver.quit()
    print("📄 Đã đóng trình duyệt.")
