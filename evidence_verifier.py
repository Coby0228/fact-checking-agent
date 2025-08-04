from pathlib import Path
import shutil
from tqdm import tqdm

from modules.paths import ROOT
from modules.utils import (
    load_data, 
    save_data_to_json, 
    create_argument_parser,
)
from modules.agent_setup import setup_agents
from modules.parsers import extract_from_string, extract_outermost_json
from modules.message_generator import MessageGenerator, MessageGenerator

AGENT_NAME = "Evidence_Verifier"
message_generator = MessageGenerator()

def verify_evidence(item, evidence_verifier, user_proxy):
    """
    Verifies the evidence for a single claim item.
    """
    results_data = {
        'event_id': item['event_id'],
        'claim': item['claim'],
        'label': item['label']
    }
    message = message_generator.create_verifier_message(item)

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
    evidence = extract_from_string(summary, 'evidence')

    results_data['verified_evidence'] = evidence
    return results_data


def main():
    parser = create_argument_parser()
    parser.set_defaults(
        data_dir=ROOT / 'results' / 'evidence_extraction',
        output_dir=ROOT / 'results' / 'evidence_verify'
    )
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_verifier, user_proxy = setup_agents(AGENT_NAME, model_name=args.model_name)

    output_dir = Path(args.output_dir) / args.dataset / args.task
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for item in tqdm(data, desc="Verifying evidence"):
        event_id = item['event_id']

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
