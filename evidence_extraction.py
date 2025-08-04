from pathlib import Path
import re
import shutil
import json

from modules.paths import ROOT
from modules.utils import (
    load_data, 
    save_data_to_json, 
    create_argument_parser
)
from modules.agent_setup import setup_agents
from prompt.PromptH import PromptHandler

AGENT_NAME = 'Evidence_Extractor'


class EvidenceGatherer:

    def __init__(self, model_name, max_reports):
        self.evidence_extractor, self.user_proxy = setup_agents(AGENT_NAME, model_name)
        self.handler = PromptHandler()
        self.max_reports_target = max_reports
        self.max_turns_limit = max_reports * 5

    def gather_evidence(self, dossier):
        """
        透過一次性的、長對話的 Agent 互動來搜集所有證據，並填充到傳入的 dossier 中。
        """
        base_prompt = self.handler.handle_prompt(AGENT_NAME + '_User')
        session_prompt = base_prompt.format(
            claim=dossier['claim'],
            max_reports=self.max_reports_target
        )

        res = self.user_proxy.initiate_chat(
            recipient=self.evidence_extractor,
            clear_history=True,
            message=session_prompt,
            max_turns=self.max_turns_limit,
        )
        summary_info = res.summary.strip()

        try:
            json_match = re.search(r'\{.*\}', summary_info, re.DOTALL)
            if not json_match:
                raise json.JSONDecodeError("No JSON object found in the response.", summary_info, 0)

            parsed_json = json.loads(json_match.group())

            dossier.update(parsed_json)

        except (json.JSONDecodeError, Exception) as e: # Catches Pydantic's validation errors too
            print(f"Error processing event {dossier['event_id']}: Failed to parse or validate agent output. Error: {e}")
        
        return dossier


def main():
    parser = create_argument_parser()
    parser.set_defaults(
        data_dir=ROOT / 'dataset',
        output_dir=ROOT / 'results' / 'evidence_extraction'
    )
    parser.add_argument('--max_reports', type=int, default=3,
                        help='Target number of evidence reports to ask the agent to find.')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task, agent_name=AGENT_NAME)
    output_dir = Path(args.output_dir) / args.dataset / args.task
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    
    gatherer = EvidenceGatherer(model_name=args.model_name, max_reports=args.max_reports)

    for item in data:
        event_id = item['event_id']
        initial_dossier = {
            "event_id": event_id,
            "claim": item['claim'],
            "label": item['label'],
            "reports": [],
            "search_history": []
        }

        final_dossier = gatherer.gather_evidence(initial_dossier)
        
        output_file = output_dir / f'{event_id}.json'
        save_data_to_json(final_dossier, output_file)
        print(f"✅ Evidence gathering for event {event_id} complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
