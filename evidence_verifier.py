import os
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
from PromptH import PromptHandler
import argparse
import json
from pathlib import Path
import sys
import re
from dotenv import load_dotenv

load_dotenv()
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative


def extract_outermost_json(text):
    stack = []
    start_index = None
    try:
        for i, char in enumerate(text):
            if char == '{':
                if not stack:
                    start_index = i
                stack.append(char)
            elif char == '}':
                stack.pop()
                if not stack:
                    return text[start_index:i + 1]
    except Exception as e:
        print(e)
        return None
    return None


def load_dataset(data_dir, task):
    data_dir = data_dir / task
    data_list = []

    for file_name in os.listdir(data_dir):
        if file_name.endswith('.json'):
            file_path = os.path.join(data_dir, file_name)
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                data_list.append(data)  # Assuming each file has a key 'claim'

    return data_list


def save_data_to_json(data, output_file):
    # Create directory if it doesn't exist
    os.makedirs(output_file.parent, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print('Save completed\n')


def setup_agents(model_name, dataset):
    # Initialize the prompt handler
    handler = PromptHandler()
    llm_config = {
        "model": model_name,
        "api_key": os.getenv('OPENAI_API_KEY', ''),
        "base_url": 'https://api.openai.com/v1',
        "cache_seed": 42
    }
    # Load system messages
    if dataset == "RAWFC":
        evi_ver_sys_message = handler.handle_prompt('Evidence_Verifier_en')
        name = "Evidence_Verifier"
    else:
        evi_ver_sys_message = handler.handle_prompt('Evidence_Verifier_ch')
        name = "证据审核员"
    # Initialize the agents
    evidence_verifier = AssistantAgent(
        name=name,
        system_message=evi_ver_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content"))

    user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

    return evidence_verifier, user_proxy


def clean_json_string(json_string):
    cleaned_string = ''
    inside_string = False
    escaped = False
    for char in json_string:
        if char == '"' and not escaped:
            inside_string = not inside_string
        if char == "'" and not inside_string:
            cleaned_string += '"'
        else:
            cleaned_string += char
        escaped = (char == '\\')
    return cleaned_string


def extract_evidence(json_string):
    """
    Extract the value of the 'evidence' field from the JSON string using a regular expression.

    Args:
        json_string (str): The JSON string to be processed.

    Returns:
        str: The value of the 'evidence' field if found, otherwise None.
    """
    try:
        # Define the regular expression pattern to handle different cases of quotation marks or missing quotation marks.
        evidence_pattern = r'["\']?evidence["\']?\s*:\s*(\[[^\]]*\])\s*}'
        # Perform the regular expression matching.
        evidence_match = re.search(evidence_pattern, json_string)
        # Extract the matched value, handling cases where the match might be missing.
        evidence = evidence_match.group(1) if evidence_match else None
    except (re.error, ValueError, TypeError) as e:
        print(f"Error occurred: {e}")
        evidence = None
    return evidence


def extract_values(json_string):
    """
    Extract the value of the 'evidence' field from the JSON string, trying multiple methods to improve the robustness of parsing.

    Args:
        json_string (str): The JSON string to be processed.

    Returns:
        str: The value of the 'evidence' field if found, otherwise None.
    """
    # Unify the case of the key names.
    json_string = json_string.replace('Evidence', 'evidence')
    # Clean the JSON string.
    cleaned_string = clean_json_string(json_string)

    try:
        # Try to parse the cleaned JSON string.
        data = json.loads(cleaned_string)
    except json.JSONDecodeError:
        # If parsing fails, manually extract the field value using a regular expression.
        evidence = extract_evidence(cleaned_string)
        if evidence is None:
            evidence = extract_evidence(json_string)
        return evidence

    if isinstance(data, str):
        evidence = extract_evidence(cleaned_string)
    else:
        # Extract the field value from the parsed JSON.
        evidence = data.get('evidence')

    if evidence is None:
        evidence = extract_evidence(json_string)

    return evidence

def create_meta_message(item, dataset):
    if dataset == 'RAWFC':
        evidence_header = "Evidence:\n"
        no_evidence_text = "No evidence provided\n\n"
        prompt = "Please analyze and verify the accuracy and completeness of the provided evidence in relation to the given claim.\n\n"
        claim_prefix = "Claim:"
    else:
        evidence_header = "证据:\n"
        no_evidence_text = "没有提供证据\n\n"
        prompt = "请分析并验证所提供的证据与给定主张相关的准确性和完整性。\n\n"
        claim_prefix = "主张:"

    evidence = evidence_header
    for report in item['reports']:
        if report.get('evidence') and report['evidence'] not in ['', 'None']:
            if isinstance(report['evidence'], list):
                for evidence_item in report['evidence']:
                    evidence += f"{evidence_item}\n"
            else:
                evidence += f"{report['evidence']}\n"

    if evidence == evidence_header:
        evidence = evidence_header + no_evidence_text

    message = (
        f"{prompt}"
        f"{claim_prefix}{item['claim']}\n\n"
        f"{evidence}"
    )
    return message, evidence


def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to load (e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'results' / 'evidence_extraction',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, choices=['GuardEval', 'RAWFC'], default='RAWFC',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_verify',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    if args.dataset == 'GuardEval':
        data_dir = args.data_dir / 'GuardEval'
    elif args.dataset == 'RAWFC':
        data_dir = args.data_dir / 'RAWFC'

    data = load_dataset(data_dir, args.task)

    evidence_verifier, user_proxy = setup_agents(args.model_name,args.dataset)
    output_dir = args.output_dir / args.dataset / args.task

    i = 0

    while i < len(data):  # len(data)
        item = data[i]
        results_data = dict()
        results_data['event_id'] = item['event_id']
        results_data['claim'] = item['claim']
        results_data['label'] = item['label']
        meta_message, meta_evidence = create_meta_message(item, args.dataset)

        if args.dataset == 'RAWFC':
            message = (f"{meta_message}\n"
                       f"Let's analyze this step by step.")
        else:
            message = (f"{meta_message}\n"
                       f"让我们一步一步地分析这个问题。")

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
        # results_data_list.append(results_data)
        json_name = results_data['event_id'].replace('.json', '')
        output_file = output_dir / f'{json_name}.json'
        save_data_to_json(results_data, output_file)

        i += 1


if __name__ == "__main__":
    main()
