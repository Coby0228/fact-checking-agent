import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class SerperClient:
    def __init__(self, api_key=None):
        self.url = "https://google.serper.dev/search"
        self.api_key = api_key or os.getenv('SERPER_API_KEY', '')
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

    def run(self, query: str, num_results: int = 10):
        payload = json.dumps({
            "q": query,
            "num": num_results
        })

        response = requests.post(self.url, headers=self.headers, data=payload)

        if response.status_code != 200:
            print(f"❌ 查詢失敗：{response.status_code} - {response.text}")
            return

        data = response.json()
        organic = data.get("organic", [])
        results = []

        for item in organic:
            domain = item.get("title")
            link = item.get("link")
            if domain and link:
                results.append({
                    "domain": domain,
                    "link": link
                })

        return results
