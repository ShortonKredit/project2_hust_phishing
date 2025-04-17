import os
import re
import pandas as pd
import urllib.parse
import hashlib
import csv

# --- Cấu hình ---
HTML_DIR = "raw_html_data_2"  # Thay bằng thư mục chứa file HTML
MAPPING_FILE = "url_html_mapping_2.csv" # Thay bằng file ánh xạ URL-HTML
OUTPUT_CSV = "labeled_data.csv" # File CSV để lưu kết quả gán nhãn

# --- Các biểu thức chính quy (regex) ---
# ... (giữ lại các regex từ code trước, ví dụ: CLOUDFLARE_PATTERN, WEBSITEWS_PATTERN, v.v.)
CREDENTIAL_HARVESTING_INPUT_PASSWORD = re.compile(r'<input.*?type="password"', re.IGNORECASE)
CREDENTIAL_HARVESTING_KEYWORDS = re.compile(r"(login|signin|verify|account)", re.IGNORECASE)
FINANCIAL_CVV_KEYWORD = re.compile(r"(cvv|cvc|cid)", re.IGNORECASE)
FINANCIAL_ACCOUNT_NUMBER = re.compile(r"(\d{8,})", re.IGNORECASE)  # Dò tìm chuỗi số có ít nhất 8 chữ số
MALWARE_LINK_EXTENSIONS = re.compile(r"\.(exe|apk|scr|bat|msi|js)$", re.IGNORECASE)
MALWARE_DOWNLOAD_KEYWORDS = re.compile(r"(download|update)", re.IGNORECASE)
PII_INPUT_FIELDS = re.compile(r"(name|address|email|phone|ssn|dob)", re.IGNORECASE)

# --- Hàm ---
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

def load_existing_mappings(mapping_file=MAPPING_FILE, raw_html_dir=HTML_DIR):
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

def analyze_html(html_content, url):
    """Phân tích nội dung HTML và URL để gán nhãn."""
    label = "OTH" # Mặc định là OTH (Other Phishing)

    # 1. Kiểm tra FIN
    if FINANCIAL_CVV_KEYWORD.search(html_content) or FINANCIAL_ACCOUNT_NUMBER.search(html_content) or "payment" in url.lower():
        label = "FIN"
    # 2. Kiểm tra MW
    elif MALWARE_LINK_EXTENSIONS.search(html_content) or MALWARE_DOWNLOAD_KEYWORDS.search(url.lower()):
        label = "MW"
    # 3. Kiểm tra CH
    elif CREDENTIAL_HARVESTING_INPUT_PASSWORD.search(html_content) and CREDENTIAL_HARVESTING_KEYWORDS.search(url.lower()):
        label = "CH"
    # 4. Kiểm tra PII
    elif PII_INPUT_FIELDS.findall(html_content): # Tìm tất cả các trường PII
        label = "PII"

    # Kiểm tra Cloudflare, Glitch, WebsiteWS, etc.
    elif CLOUDFLARE_PATTERN.search(html_content) or WEBSITEWS_PATTERN.search(html_content) or GLITCH_PATTERN.search(html_content):
        label = "LEG"  # Hoặc OTH, tùy thuộc vào bạn muốn xử lý các trang này như thế nào

    return label

# --- Main ---
if __name__ == "__main__":
    # Tải ánh xạ URL-HTML
    existing_mappings = load_existing_mappings()

    # Tạo danh sách để lưu trữ kết quả
    results = []

    # Lặp qua các file HTML trong thư mục
    for url, html_filepath in existing_mappings.items():
        try:
            with open(html_filepath, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Phân tích HTML và gán nhãn
            label = analyze_html(html_content, url)

            # Lưu kết quả
            results.append({"url": url, "html_filename": html_filepath, "label": label})

        except Exception as e:
            print(f"Lỗi khi xử lý {html_filepath}: {e}")
            results.append({"url": url, "html_filename": html_filepath, "label": "ERROR"})

    # Lưu kết quả vào file CSV
    df_results = pd.DataFrame(results)
    df_results.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    print(f"Đã lưu kết quả vào {OUTPUT_CSV}")