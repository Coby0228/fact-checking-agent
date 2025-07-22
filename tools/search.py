import os
import json
import tempfile
from pathlib import Path
from tools.client import SerperClient

LOG_PATH = "serp_logs/claim.json"
serper_client = SerperClient()

def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log(data):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def search_web(query: str, num_results: int = 5, claim: str = None) -> list:

    print(f"🔍 搜尋: {query} (返回數量: {num_results})")
    result = serper_client.run(query, num_results)
    if not result:
        print("⚠️ 無搜尋結果")
        return []

    logs = load_log()

    # 尋找 claim entry
    for entry in logs:
        if entry["claim"] == claim:
            break
    else:
        entry = {"claim": claim, "evidence": []}
        logs.append(entry)

    # 去重 url（已存在的）
    existing_urls = {e["url"] for e in entry["evidence"]}

    new_evidence = [
        item for item in result
        if item["url"] not in existing_urls
    ]

    entry["evidence"].extend(new_evidence)
    save_log(logs)

    return new_evidence

if __name__ == "__main__":

    claim = "OpenAI 是由誰創辦的？"

    search_web("OpenAI company founders", num_results=3, claim=claim)
    search_web("Who started OpenAI", num_results=3, claim=claim)

    print(f"✅ 測試完成，請查看 {LOG_PATH}")
