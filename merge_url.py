import pandas as pd

df1 = pd.read_csv("phishing_link(Sheet1).csv", encoding="latin1")
df2 = pd.read_csv("op_phishing_urls(op_phishing_urls).csv", encoding="latin1")

df1_clean = df1.dropna(subset=['label'])
df2_clean = df2.dropna(subset=['label'])

combined_df = pd.concat([df1_clean, df2_clean], ignore_index=True)
combined_df.to_csv("combined_labeled_urls.csv", index=False)

print("✅ Đã lưu file: combined_labeled_urls.csv")
