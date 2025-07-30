import argparse
import json
from pathlib import Path
import re

from utils import *
from prompt.PromptH import PromptHandler

AGENT_NAME = "Evidence_Extractor"


def gather_evidence_in_single_session(claim, label, event_id, evidence_extractor, user_proxy, handler, max_reports_target, max_turns_limit):
    """
    透過一次性的、長對話的 Agent 互動來搜集所有證據。
    """
    base_prompt = handler.handle_prompt(AGENT_NAME + '_User') 
    session_prompt = base_prompt.format(
        claim=claim,
        max_reports=max_reports_target
    )

    res = user_proxy.initiate_chat(
        recipient=evidence_extractor,
        clear_history=True,
        message=session_prompt,
        max_turns=max_turns_limit,
    )

    final_response = res.summary.strip()
    final_dossier = {
        "event_id": event_id,
        "claim": claim,
        "label": label,
        "reports": [],
        "search_history": []
    }

    try:
        json_match = re.search(r'\{.*\}', final_response, re.DOTALL)
        if not json_match:
            raise json.JSONDecodeError("No JSON object found in the response.", final_response, 0)
        
        # 解析 Agent 回傳的 dossier 內容
        agent_dossier = json.loads(json_match.group())
        final_dossier.update(agent_dossier)

        print(f"\nFinished gathering evidence. Total reports found: {len(final_dossier.get('reports', []))}")
        return final_dossier

    except (json.JSONDecodeError, KeyError) as e:
        return final_dossier


def main():
    parser = argparse.ArgumentParser(description="Gather evidence for claims in a single session.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to load')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'dataset',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test', ''], default='test',
                        help='Task type to load')
    parser.add_argument('--dataset', type=str, choices=['GuardEval', 'RAWFC', 'TFC'], default='RAWFC',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_extraction',
                        help='Output directory to save the gathered evidence')
    parser.add_argument('--max_reports', type=int, default=3,
                        help='Target number of evidence reports to ask the agent to find.')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_extractor, user_proxy = setup_agents(AGENT_NAME)
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
        
        output_file = output_dir / f'{event_id}.json'
        save_data_to_json(final_dossier, output_file)
        print(f"✅ Evidence gathering for event {event_id} complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
