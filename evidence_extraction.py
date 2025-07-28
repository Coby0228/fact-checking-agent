import argparse
import json
from pathlib import Path
import re

from utils import *
from PromptH import PromptHandler

def gather_evidence_in_single_session(claim, label, event_id, evidence_extractor, user_proxy, handler, max_reports_target, max_turns_limit):
    """
    透過一次性的、長對話的 Agent 互動來搜集所有證據。
    """
    # 新的提示，指示 Agent 自行完成所有迭代
    base_prompt = handler.handle_prompt('Evidence_Extraction_Iterative_en') 
    
    session_prompt = base_prompt.format(
        claim=claim,
        max_reports=max_reports_target
    )

    print(f"\n{'='*20} Starting Evidence Gathering Session {'='*20}")
    print(f"Claim: {claim}")
    print(f"Agent max_turns set to: {max_turns_limit}")

    res = user_proxy.initiate_chat(
        recipient=evidence_extractor,
        clear_history=True,
        message=session_prompt,
        max_turns=max_turns_limit,
    )

    # 嘗試從最後一條非空的訊息中提取內容
    final_response = None
    for msg in reversed(res.chat_history):
        if msg.get("content") and "{" in msg.get("content"):
            final_response = msg["content"]
            break
    
    if not final_response:
        print("Error: No valid JSON content found in agent response.")
        # 返回一個空的 dossier 結構以避免後續錯誤
        return {
            "event_id": event_id, "claim": claim, "label": label, 
            "reports": [], "search_history": []
        }

    try:
        json_match = re.search(r'\{.*\}', final_response, re.DOTALL)
        if not json_match:
            raise json.JSONDecodeError("No JSON object found in the response.", final_response, 0)
        
        # Agent 應該回傳完整的 dossier
        final_dossier = json.loads(json_match.group())
        
        # 為了格式統一，手動補上我們已知的資訊
        final_dossier["event_id"] = event_id
        final_dossier["claim"] = claim
        final_dossier["label"] = label

        print(f"\nFinished gathering evidence. Total reports found: {len(final_dossier.get('reports', []))}")
        return final_dossier

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing final agent response: {e}")
        print(f"Raw response was: {final_response}")
        return {
            "event_id": event_id, "claim": claim, "label": label, 
            "reports": [], "search_history": []
        }


def main():
    parser = argparse.ArgumentParser(description="Gather evidence for claims in a single session.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to load')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'dataset',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load')
    parser.add_argument('--dataset', type=str, choices=['GuardEval', 'RAWFC'], default='RAWFC',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_gathering',
                        help='Output directory to save the gathered evidence')
    parser.add_argument('--max_reports', type=int, default=3,
                        help='Target number of evidence reports to ask the agent to find.')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_extractor, user_proxy = setup_agents('Evidence_Extractor')
    handler = PromptHandler()
    output_dir = Path(args.output_dir) / args.dataset / args.task
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in data:
        claim = item['claim']
        label = item.get('label', 'unknown')
        event_id = item['event_id'].replace('.json', '')    
        max_turns_for_session = args.max_reports * 5

        final_dossier = gather_evidence_in_single_session(
            claim=claim,
            label=label,
            event_id=event_id,
            evidence_extractor=evidence_extractor,
            user_proxy=user_proxy,
            handler=handler,
            max_reports_target=args.max_reports,
            max_turns_limit=max_turns_for_session
        )
        
        # 儲存搜集到的所有證據
        output_file = output_dir / f'{event_id}.json'
        save_data_to_json(final_dossier, output_file)
        print(f"✅ Evidence gathering for event {event_id} complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
