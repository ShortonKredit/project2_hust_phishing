import os
import pandas as pd
import re
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
options.add_argument("--headless")  # Run Chrome in headless mode
options.add_argument("--disable-gpu")  # Disable GPU acceleration (optional)

# Install and start Chrome driver using Service
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Tạo bảng mapping
mapping = []

for url in urls[:100]:  # chỉ lấy 100 URL đầu tiên
    file_name = url_to_filename(url)
    file_path = os.path.join(output_folder, file_name)

    try:
        driver.get(url)

        # Wait for the page to load completely (adjust the condition as needed)
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

print("✅ Đã hoàn tất. HTML được lưu trong thư mục html_pages/, mapping nằm ở html_mapping.csv")
