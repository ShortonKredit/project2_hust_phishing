import requests
import pandas as pd

# Tải dữ liệu từ feed
url = "https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt"
response = requests.get(url)
urls = response.text.strip().split('\n')

# Tạo DataFrame và lưu thành CSV
df = pd.DataFrame(urls, columns=["phishing_url"])
df.to_csv("openphish_feed_05_06.csv", index=False)
print("Đã lưu file: openphish_feed_05_06.csv")
