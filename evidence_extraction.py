import argparse
import json
from pathlib import Path

from utils import *

def load_evidence_from_json(claim):
    """從 serp_logs/claim.json 載入證據資料"""
    evidence_file = Path("serp_logs") / "claim.json"
    
    if not evidence_file.exists():
        return []
    
    try:
        with open(evidence_file, 'r', encoding='utf-8') as f:
            evidence_data = json.load(f)
        
        for item in evidence_data:
            print(f"Checking claim: {item.get('claim')}")
            print(f"Against provided claim: {claim}")
            if item.get('claim') == claim:
                return item.get('evidence', [])
        return []
        
    except Exception:
        return []

def extract_evidence_from_urls(claim, evidence_list, evidence_extractor, user_proxy):
    """從證據列表中提取每個URL的相關證據"""
    if not evidence_list:
        print(f"No evidence found for claim: {claim}")
        return []

    urls_info = []
    for idx, evidence_item in enumerate(evidence_list, 1):
        url = evidence_item.get('link', '')
        title = evidence_item.get('title', '')
        snippet = evidence_item.get('snippet', '')
        urls_info.append(f"URL{idx}: {url}\nTitle: {title}\nSnippet: {snippet}")
    
    evidence_message = (
        f"Extract evidence for claim: {claim}\n\n"
        f"Sources to analyze:\n" + "\n\n".join(urls_info) + "\n\n"
        f"Instructions:\n"
        f"1. For each URL, evaluate if the snippet is relevant to the claim\n"
        f"2. If relevance is high or medium, use fetch_url(url) to get the full content\n"
        f"3. Extract relevant evidence from the fetched content\n"
        f"4. If relevance is low, skip fetching and mark as no evidence\n\n"
        f"Process all URLs systematically. When finished with all URLs, return final results.\n\n"
        f"Return JSON format:\n"
        f"{{\n"
        f'  "detailed_results": [\n'
        f'    {{\n'
        f'      "url": "URL address",\n'
        f'      "title": "page title",\n'
        f'      "relevance_score": "high/medium/low",\n'
        f'      "fetched_content": true/false,\n'
        f'      "have_evidence": true/false,\n'
        f'      "evidence": "extracted evidence text or explanation",\n'
        f'      "confidence_level": "high/medium/low"\n'
        f'    }}\n'
        f'  ]\n'
        f"}}"
    )

    try:
        res = user_proxy.initiate_chat(
            recipient=evidence_extractor,
            clear_history=True,
            message=evidence_message,
            cache=None,
            summary_method="last_msg",
            max_turns=len(evidence_list) * 2 + 3
        )

        final_response = res.chat_history[-1]['content']
        try:
            import re
            json_match = re.search(r'\{.*\}', final_response, re.DOTALL)
            if json_match:
                evidence_json = json.loads(json_match.group())
            else:
                evidence_json = json.loads(final_response)
        except Exception:
            evidence_json = {"detailed_results": []}

        evidence_results = []
        detailed_results = evidence_json.get('detailed_results', [])
        
        for idx, evidence_item in enumerate(evidence_list):
            if idx < len(detailed_results):
                result = detailed_results[idx]
            else:
                result = {
                    "url": evidence_item.get('link', ''),
                    "title": evidence_item.get('title', ''),
                    "relevance_score": "low",
                    "fetched_content": False,
                    "have_evidence": False,
                    "evidence": "",
                    "confidence_level": "low"
                }
            evidence_results.append(result)

        return evidence_results

    except Exception:
        return []

def perform_search_for_claim(claim, evidence_extractor, user_proxy):
    """執行搜尋階段，返回URL列表"""
    search_message = (
        f"Please analyze the following claim and use search_web to find relevant sources.\n\n"
        f"Claim: \"{claim}\"\n\n"
        f"Generate appropriate search queries and perform up to 3 searches. "
    )

    user_proxy.initiate_chat(
        recipient=evidence_extractor,
        clear_history=True,
        message=search_message,
        cache=None,
        summary_method="last_msg",
        max_turns=2
    )
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to load (e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'dataset',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, choices=['GuardEval', 'RAWFC'], default='RAWFC',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_extraction',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_extractor, user_proxy = setup_agents('Evidence_Extractor')
    output_dir = Path(args.output_dir) / args.dataset / args.task
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in data:
        print(f"Claim: {item['claim']}")
        claim = item['claim']
        
        results_data = {
            'event_id': item['event_id'],
            'claim': item['claim'],
            'label': item['label'],
            'search_results': [],
            'evidence_results': []
        }
        
        # 第一階段：搜尋階段
        search_success = perform_search_for_claim(claim, evidence_extractor, user_proxy)
        if search_success:
            # 從JSON檔案載入搜尋結果
            evidence_list = load_evidence_from_json(claim)
            results_data['search_results'] = evidence_list
            
            if evidence_list:
                # 第二階段：證據提取階段
                print('==' * 20)
                print(f"Step 2: Extracting evidence from URLs for claim: {claim}")
                print('==' * 20)
                evidence_results = extract_evidence_from_urls(claim, evidence_list, evidence_extractor, user_proxy)
                results_data['evidence_results'] = evidence_results
        
        # 保存結果
        json_name = results_data['event_id'].replace('.json', '')
        output_file = output_dir / f'{json_name}.json'
        save_data_to_json(results_data, output_file)

if __name__ == "__main__":
    main()