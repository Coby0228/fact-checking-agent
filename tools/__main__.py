from . import fetch_url, search_web

if __name__ == "__main__":
    print("=== 測試所有工具 ===")
    
    # 測試 fetch
    print("\n1. 測試 fetch_url:")
    result = fetch_url("https://example.com", max_length=500)
    print("成功" if "成功" in result else "失敗")
    
    # 測試 search
    print("\n2. 測試 search_web:")
    result = search_web("AI technology", num_results=2)
    print("成功" if "搜尋" in result else "失敗")
    
    print("\n✅ 所有測試完成")