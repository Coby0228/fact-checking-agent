import asyncio
import json
import requests
from bs4 import BeautifulSoup
from readability import Document

INPUT_FILE = "data/organic_pairs.json"
OUTPUT_FILE = "data/output.json"

def load_input_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_to_json(data, filename=OUTPUT_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_readable_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = res.apparent_encoding  # 嘗試自動判別編碼

        doc = Document(res.text)
        title = doc.short_title()
        html = doc.summary()

        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator="\n", strip=True)

        return {
            "title": title,
            "text": text
        }
    except Exception as e:
        return {
            "title": "",
            "text": f"❌ Error extracting content: {e}"
        }

async def crawl_all(url_list):
    results = []
    for entry in url_list:
        link = entry["link"]
        print(f"🚀 Extracting: {link}")
        content = extract_readable_content(link)

        results.append({
            "domain": entry.get("domain", ""),
            "link": link,
            "title": content["title"],
            "content": content["text"]
        })

    return results

if __name__ == "__main__":
    url_list = load_input_json(INPUT_FILE)
    final_result = asyncio.run(crawl_all(url_list))
    save_to_json(final_result)
    print(f"✅ 共 {len(final_result)} 筆資料已成功儲存到 {OUTPUT_FILE}")
