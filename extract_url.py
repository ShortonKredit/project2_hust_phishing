import os
import pandas as pd
from bs4 import BeautifulSoup

# Đường dẫn
html_folder = "RAW_HTML_DATA"
data_file = "combined_data.csv"
output_mapping_file = "URL_HTML_MAPPING_new.csv"

# Đọc danh sách URL gốc có label == 1
df = pd.read_csv(data_file)
url_list = df[df['label'] == 1]['url'].dropna().unique()

def extract_possible_url(html_path):
    """Dự đoán URL từ nội dung file HTML."""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')

        base = soup.find('base', href=True)
        if base:
            return base['href']

        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            return canonical['href']

        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            return og_url['content']
    except Exception as e:
        print(f"⚠️ Lỗi khi đọc {html_path}: {e}")
    return None

# Tạo danh sách ánh xạ
mapping = []

for idx, original_url in enumerate(url_list):
    filename = f"url_{idx}.html"
    html_path = os.path.join(html_folder, filename)

    if not os.path.exists(html_path):
        print(f"❌ Không tìm thấy file: {filename}")
        continue

    inferred_url = extract_possible_url(html_path)

    mapping.append({
        "index": idx,
        "original_url": original_url,
        "filename": filename,
        "inferred_url": inferred_url
    })

# Ghi ra file mapping
pd.DataFrame(mapping).to_csv(output_mapping_file, index=False)
print(f"✅ Đã lưu mapping vào: {output_mapping_file}")
