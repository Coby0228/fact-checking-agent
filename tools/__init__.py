"""
工具整合模組 - 統一匯入所有 AutoGen 工具
"""

from .fetch import fetch_url
from .search import search_web

def test_tools():
    """測試工具函數是否可用"""
    try:
        search_web("test", claim="test")
        print(f"✅ search_web 測試成功")
        return True
    except Exception as e:
        print(f"❌ search_web 測試失敗: {e}")
        return False

def get_tool_functions():
    """
    返回所有可用的工具函數
    
    Returns:
        dict: 工具函數字典，可直接用於 AutoGen function_map
    """
    return {
        "search_web": search_web,
        "fetch_url": fetch_url
    }

tool_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "進行網路搜尋，找到相關來源",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋的關鍵字或查詢"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "回傳的搜尋結果數量"
                    },
                    "claim": {
                        "type": "string",
                        "description": "與搜尋相關的聲明或主題"
                    }
                },
                "required": ["query", "num_results", "claim"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "從 URL 擷取頁面內容",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要提取內容的 URL"
                    },
                    "max_length": {
                        "type": "integer",
                        "description": "限制提取的內容長度"
                    },
                    "start_index": {
                        "type": "integer",
                        "description": "從哪個位置開始提取內容"
                    }
                },
                "required": ["url"]
            }
        }
    }
]
