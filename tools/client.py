import requests
import json
import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

def load_log(LOG_PATH):
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_log(data, LOG_PATH):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

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
            title = item.get("title")
            url = item.get("link")
            snippet = item.get("snippet")
            if title and url:
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })

        return results


class MCPFetchClient:
    """MCP fetch server 客戶端"""
    
    def __init__(self):
        self.server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server_fetch"]
        )
    
    async def fetch_content(self, url: str, max_length: int = 8000, start_index: int = 0, raw: bool = False):
        """使用 MCP server 擷取內容"""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool("fetch", {
                        "url": url,
                        "max_length": max_length,
                        "start_index": start_index,
                        "raw": raw
                    })
                    
                    return result
        except Exception as e:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"MCP 連線錯誤: {str(e)}"}]
            }
    
    def fetch_sync(self, url: str, max_length: int = 8000, start_index: int = 0, raw: bool = False):
        """同步包裝器，用於 AutoGen"""
        return asyncio.run(self.fetch_content(url, max_length, start_index, raw))
    
if __name__ == "__main__":
    # 測試 SerperClient
    client = SerperClient()
    results = client.run("OpenAI company founders", num_results=3)
    print(json.dumps(results, indent=2, ensure_ascii=False))
