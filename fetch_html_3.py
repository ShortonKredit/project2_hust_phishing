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

# Hàm chuyển URL thành tên file an toàn
def url_to_filename(url):
    return re.sub(r'[^a-zA-Z0-9]', '_', url) + '.html'

# Đọc file CSV chứa danh sách URL
df = pd.read_csv("openphish_feed.csv")
urls = df['phishing_url'].tolist()

# Tạo thư mục chứa các file HTML
output_folder = "html_pages"
os.makedirs(output_folder, exist_ok=True)

# Set up Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")

# Install and start Chrome driver using Service
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Tạo bảng mapping
mapping = []

for url in urls:  # chỉ lấy 100 URL đầu tiên
    file_name = url_to_filename(url)
    file_path = os.path.join(output_folder, file_name)

    try:
        # Kiểm tra trạng thái URL trước bằng requests
        response = requests.get(url, timeout=5)
        if response.status_code >= 400:
            raise Exception(f"Offline (status {response.status_code})")

        # Truy cập và lưu HTML bằng Selenium nếu URL còn sống
        driver.get(url)

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        html = driver.page_source

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

# Quit the driver
driver.quit()

# Ghi file mapping ra CSV
pd.DataFrame(mapping).to_csv("html_mapping.csv", index=False)

print("✅ Đã hoàn tất. Chỉ lưu các URL còn online.")
