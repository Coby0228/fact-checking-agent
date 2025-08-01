import argparse
from pathlib import Path
import shutil

from utils import *

AGENT_NAME = "Evidence_Verifier"


def verify_evidence(item, evidence_verifier, user_proxy):
    """
    Verifies the evidence for a single claim item.
    """
    results_data = {
        'event_id': item['event_id'],
        'claim': item['claim'],
        'label': item['label']
    }
    meta_message, meta_evidence = create_meta_message(item)

    message = (f"{meta_message}\n"
               f"Let's analyze this step by step.")

    res = user_proxy.initiate_chat(
        recipient=evidence_verifier,
        clear_history=True,
        message=message,
        cache=None,
        summary_method="last_msg",
        max_turns=1
    )
    summary = res.summary

    summary = extract_outermost_json(summary)
    evidence = extract_values(summary)

    results_data['verified_evidence'] = evidence
    return results_data


def main():
    parser = argparse.ArgumentParser(description="Verify evidence for claims.")
    parser.add_argument('--model_name', type=str, default='gpt4o_mini',
                        help='Name of the model to load (e.g., gpt4o_mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'results' / 'evidence_extraction',
                        help='Directory containing the datasets with extracted evidence')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test', ''], default='',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, choices=['CFEVER', 'RAWFC', 'TFC'], default='CFEVER',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_verify',
                        help='Output directory to save the verified evidence')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_verifier, user_proxy = setup_agents(AGENT_NAME, model_name=args.model_name)

    output_dir = Path(args.output_dir) / args.dataset / args.task
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for item in data:
        event_id = item['event_id'].replace('.json', '')

        verified_data = verify_evidence(
            item=item,
            evidence_verifier=evidence_verifier,
            user_proxy=user_proxy
        )
        
        output_file = output_dir / f'{event_id}.json'
        save_data_to_json(verified_data, output_file)
        print(f"✅ Evidence verification for event {event_id} complete. Results saved to {output_file}")


if __name__ == "__main__":
    main()
