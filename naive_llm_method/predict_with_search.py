import os
import json
from pathlib import Path
import autogen

from autogen import register_function
from modules.utils import load_data, save_data_to_json, create_argument_parser
from modules.paths import ROOT
from modules.parsers import extract_outermost_json, extract_from_string
from tools.search import search_web

def main():
    """
    Main function to load data, process claims with an LLM that can use search, and save results.
    """
    parser = create_argument_parser()
    parser.set_defaults(
        data_dir=ROOT / 'dataset',
        output_dir=ROOT / 'results' / 'prediction_with_search',
        dataset='CFEVER',
    )
    args = parser.parse_args()

    # 1. Setup environment
    output_dir = Path(args.output_dir) / args.dataset / args.task
    output_dir.mkdir(parents=True, exist_ok=True)

    llm_config = {
        "model": args.model_name,
        "api_key": os.getenv('OPENAI_API_KEY'),
        "base_url": os.getenv('OPENAI_API_BASE'),
        "cache_seed": 42
    }

    # 2. Load data
    data = load_data(args.data_dir, args.dataset, args.task, agent_name='Evidence_Extractor')
    if not data:
        print("No data loaded. Exiting.")
        return

    # 3. Create Agents
    system_message = (
        "You are a helpful fact-checker. Your task is to evaluate the authenticity of a given claim. "
        "First, use the `search_web` tool to find relevant information and evidence. "
        "After gathering evidence, analyze it and make a final decision. "
        "You must respond with a JSON object containing your 'prediction' and 'justification'. "
        "The prediction must be one of 'true' or 'false'. "
        "The justification should briefly explain your reasoning based on the evidence found."
        "\n\nAfter providing the JSON response, you must write the word TERMINATE on a new line."
    )

    assistant = autogen.AssistantAgent(
        name="FactChecker",
        system_message=system_message,
        llm_config=llm_config,
    )

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda msg: (msg.get("content") or "").strip().strip("'\"").endswith("TERMINATE"),
        code_execution_config=False,
    )

    # Register functions for the agents
    register_function(
            search_web,
            caller=assistant,
            executor=user_proxy,
            name="search_web",
            description="Search for information related to a claim and store results"
        )

    # 4. Process each item
    for i, item in enumerate(data, 1):
        claim = item.get('claim')
        if not claim:
            continue

        print(f"Processing item {i}/{len(data)}: {item.get('event_id', 'N/A')}")

        # Initiate chat to get prediction
        res = user_proxy.initiate_chat(
            recipient=assistant,
            message=f"Verify the following claim: {claim}",
            clear_history=True,
        )
        
        # Parse the result from the last message
        last_message = res.chat_history[-1]['content']
        summary = extract_outermost_json(last_message)
        prediction, justification = extract_from_string(summary, 'prediction', 'justification')

        # Prepare data for saving
        result_data = {
            'event_id': item.get('event_id'),
            'claim': claim,
            'label': str(item.get('label')),
            'prediction': prediction,
            'justification': justification
        }

        # Save the result
        output_file = output_dir / f"{item.get('event_id', i)}.json"
        save_data_to_json(result_data, output_file)
        print(f"✅ Result saved to {output_file}")

if __name__ == "__main__":
    main()