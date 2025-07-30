from tools.client import MCPFetchClient, load_log, save_log

LOG_PATH = "logs/fetch_logs/claim.json"
mcp_client = MCPFetchClient()


def fetch_url(
    url: str,
    max_length: int = 8000,
    start_index: int = 0,
    raw: bool = False
) -> str:
    """
    使用 MCP fetch server 從網路擷取內容，並記錄每次呼叫。
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
    
    content_text = result.content[0].text if result.content else ""

    logs = load_log(LOG_PATH)
    
    logs.append({
        "url": url,
        "content": content_text,
        "max_length": max_length,
        "start_index": start_index,
        "raw": raw,
    })
    
    save_log(logs, LOG_PATH)

    return content_text
