from tools.client import SerperClient, load_log, save_log


LOG_PATH = "logs/serp_logs/claim.json"
serper_client = SerperClient()


def search_web(query: str, num_results: int = 5, claim: str = None) -> list:
    """
    Searches the web for a given query and logs the results, avoiding duplicates for the same claim.

    Args:
        query (str): The search keywords to use for the web search.
        num_results (int): The desired number of search results to return. Defaults to 5.
        claim (str): The claim being investigated. This is used to group search results and prevent fetching the same URL multiple times for the same claim.

    Returns:
        list: A list of search result items from the search provider.
    """
    result = serper_client.run(query, num_results)
    if not result:
        print("⚠️ 無搜尋結果")
        return []

    logs = load_log(LOG_PATH)

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
    save_log(logs, LOG_PATH)

    return result
