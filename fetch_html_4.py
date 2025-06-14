import os
import pandas as pd
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Chuyển URL thành tên file an toàn
def url_to_filename(url):
    return re.sub(r'[^a-zA-Z0-9]', '_', url) + '.html'

# Tạo driver cho một lần sử dụng
def get_html_with_selenium(url):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        html = driver.page_source

        driver.quit()
        return html, None
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return None, str(e)

# Đọc danh sách URL
df = pd.read_csv("openphish_feed_05_06.csv")
urls = df['phishing_url'].tolist()

# Thư mục lưu HTML
output_folder = "html_pages_no8_05_06"
os.makedirs(output_folder, exist_ok=True)

# Danh sách mapping URL -> file hoặc lỗi
mapping = []

for url in urls:
    file_name = url_to_filename(url)
    file_path = os.path.join(output_folder, file_name)

    try:
        # Kiểm tra trạng thái HTTP
        response = requests.get(url, timeout=5)
        if response.status_code >= 400:
            raise Exception(f"Offline (status {response.status_code})")

        # Nếu trang có ít script, có thể là HTML tĩnh
        if response.text.count("<script") < 3:
            html = response.text
        else:
            html, error = get_html_with_selenium(url)
            if error:
                raise Exception(error)

        # Lưu HTML ra file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)

        mapping.append({
            "url": url,
            "file_name": file_name
        })

    except Exception as e:
        mapping.append({
            "url": url,
            "file_name": f"ERROR: {str(e)}"
        })

# Ghi file mapping
pd.DataFrame(mapping).to_csv("html_mapping_9_05_06.csv", index=False)
print("✅ Đã hoàn tất. Chỉ lưu các URL còn online.")
