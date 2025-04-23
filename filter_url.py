import pandas as pd

# Đọc file CSV gốc
df = pd.read_csv("html_mapping_2.csv")

# Lọc bỏ các dòng có 'ERROR' trong cột file_name
df_filtered = df[~df['file_name'].str.contains("ERROR", na=False)]

# Ghi đè lên file cũ
df_filtered.to_csv("html_mapping_2.csv_filter", index=False)

print("✅ Đã ghi đè file html_mapping_1.csv .")
