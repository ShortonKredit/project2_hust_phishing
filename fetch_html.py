import pandas as pd
import os
import csv
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

# Đọc các URL đã được xử lý trước đó (nếu có)
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
# Chặn tải ảnh và font để tăng tốc
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

try:
    for idx, original_url in enumerate(url_list):
        if original_url in done_urls:
            print(f"⏩ Bỏ qua (đã tải): {original_url}")
            continue

        url_https = "https://" + original_url if not original_url.startswith("http") else original_url
        url_http = "http://" + original_url if not original_url.startswith("http") else original_url
        success = False

        for url in [url_https, url_http]:
            try:
                driver.get(url)

                # Đợi phần thân trang xuất hiện (thay cho sleep)
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                html = driver.page_source
                file_index = len(os.listdir(output_folder))
                filename = f"url_{file_index}.html"
                filepath = os.path.join(output_folder, filename)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html)

                print(f"✅ Đã lưu: {filename} từ {url}")
                record = {"original_url": original_url, "final_url": url, "filename": filename}
                append_mapping(record)
                success = True
                break
            except Exception as e:
                print(f"⚠️ Lỗi với {url}: {e}")
                continue

        if not success:
            print(f"❌ Không thể truy cập URL: {original_url}")

except KeyboardInterrupt:
    print("\n🛑 Bạn đã dừng thủ công. Dừng an toàn...")

finally:
    driver.quit()
    print("📄 Đã đóng trình duyệt.")
