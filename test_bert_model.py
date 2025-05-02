import os
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from transformers import BertTokenizer, BertModel
import torch

# Load BERT model
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertModel.from_pretrained("bert-base-uncased")
model.eval()

# Đường dẫn đến folder chứa HTML và file mapping
html_folder = "html_pages_1"
mapping_file = "html_mapping_1.csv"

# Đọc file ánh xạ
df_mapping = pd.read_csv(mapping_file)

# Hàm: Trích văn bản từ HTML
def extract_useful_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

# Hàm: Lấy embedding từ BERT
def get_bert_feature(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.pooler_output.squeeze(0).numpy()  # [768]

# Duyệt từng file HTML
features = []
file_names = []
num_tokens_list = []  # thêm dòng này

for fname in tqdm(os.listdir(html_folder)):
    if fname.endswith(".html"):
        path = os.path.join(html_folder, fname)
        try:
            with open(path, encoding="utf-8") as f:
                html = f.read()
        except Exception as e:
            print(f"⚠️ Lỗi khi đọc {fname}: {e}")
            continue

        text = extract_useful_text(html)

        # Đếm token trước khi truncation
        tokenized = tokenizer(text, truncation=False)
        num_tokens = len(tokenized["input_ids"])

        vector = get_bert_feature(text)

        features.append(vector)
        file_names.append(fname)
        num_tokens_list.append(num_tokens)  # lưu số token

# Lưu kết quả ra DataFrame
df_feat = pd.DataFrame(features)
df_feat["file_name"] = file_names
df_feat["num_tokens"] = num_tokens_list  # thêm cột số token

# Merge với thông tin URL/phishing label từ mapping file (nếu có)
df_final = df_feat.merge(df_mapping, on="file_name", how="left")

# Lưu ra file CSV để huấn luyện hoặc kiểm tra
df_final.to_csv("bert_features_with_mapping.csv", index=False)
print("✅ Đã sinh xong feature và lưu vào: bert_features_with_mapping.csv")
