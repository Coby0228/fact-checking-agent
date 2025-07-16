from modules.serp import SerperClient
from modules.web_crawl import crawl_all, save_to_json
import asyncio

OUTPUT_FILE = "output.json"

def main():
    client = SerperClient()
    query = "國軍 軍事新聞"
    url_list = client.run(query)
    save_to_json(url_list, "data/organic_pairs.json")

    final_result = asyncio.run(crawl_all(url_list))
    save_to_json(final_result, f"data/"+OUTPUT_FILE)
    print(f"✅ 共 {len(final_result)} 筆資料已成功儲存")
    
if __name__ == "__main__":
    main()