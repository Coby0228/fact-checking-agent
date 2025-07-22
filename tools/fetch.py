import asyncio
from tools.client import MCPFetchClient

mcp_client = MCPFetchClient()


def run_async_fetch(url: str, max_length: int, start_index: int, raw: bool):
    """同步包裝器，用於 AutoGen"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import threading
            result = None
            exception = None
            
            def run_in_thread():
                nonlocal result, exception
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(
                        mcp_client.fetch_content(url, max_length, start_index, raw)
                    )
                    new_loop.close()
                except Exception as e:
                    exception = e
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if exception:
                raise exception
            return result
        else:
            return loop.run_until_complete(
                mcp_client.fetch_content(url, max_length, start_index, raw)
            )
    except Exception as e:
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"執行錯誤: {str(e)}"}]
        }
# result = run_async_fetch(url, max_length=8000, start_index=0, raw=False)

def fetch_url(
    url: str,
    max_length: int = 8000,
    start_index: int = 0,
    raw: bool = False
) -> str:
    """
    使用 MCP fetch server 從網路擷取內容。
    Args:
        url: 目標網址
        max_length: 最大字元數 (500-50000)
        start_index: 起始位置，用於分段讀取
        raw: 是否返回原始HTML (False=markdown格式)
    
    Returns:
        str: 擷取的內容
    """
    result = mcp_client.fetch_sync(
        url,
        max_length=max_length,
        start_index=start_index,
        raw=raw
    )
    
    # return result
    return result.content[0].text

# 測試
if __name__ == "__main__":
    print("=== 測試 MCP fetch_url ===")
    result = fetch_url("https://example.com", max_length=1000)
    print(result)
    print("✅ MCP fetch 工具測試完成")