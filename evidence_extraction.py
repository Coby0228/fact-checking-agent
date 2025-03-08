import os
import ast
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
import autogen
from autogen import initiate_chats
import pprint
import random
from PromptH import PromptHandler
import argparse
from config import ModelConfig
import json
from pathlib import Path
import sys
import re

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


def load_data(data_dir, dataset, task):
    data_dir = data_dir / dataset / task
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
    model_config = ModelConfig()
    llm_config = model_config.get_config(model_name)
    # Load system messages
    if dataset == "RAWFC":
        evi_ext_sys_message = handler.handle_prompt('Evidence_Extraction_en')
        name = "Evidence Extractor"
    else:
        evi_ext_sys_message = handler.handle_prompt('Evidence_Extraction_ch')
        name = "证据提取器"
    # Initialize the agents
    evidence_extractor = AssistantAgent(
        name=name,
        system_message=evi_ext_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content"))

    user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

    return evidence_extractor, user_proxy


def clean_message(message):
    """
    Clean the input message by replacing consecutive backslashes with a single backslash
    and removing specific Unicode characters and escaped quotes.

    Args:
        message (str): The input message to be cleaned.

    Returns:
        str: The cleaned message.
    """
    # Replace consecutive backslashes with a single backslash
    message = re.sub(r'\\\\+', r'\\', message)
    # Remove specific Unicode characters and replace escaped quotes
    message = message.replace("\u201c", "").replace("\u201d", "").replace('\\"', '"').replace("\u2013", "").replace(
        "\u2227", "")
    return message


def clean_json_string(json_string):
    """
    Clean the JSON string by replacing single quotes with double quotes when outside of strings.

    Args:
        json_string (str): The input JSON string to be cleaned.

    Returns:
        str: The cleaned JSON string.
    """
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


def extract_values(json_string):
    """
    Extract 'have_evidence' and 'evidence' values from the JSON string.
    Try to parse the cleaned string first, and if it fails, use regular expressions to extract the values.

    Args:
        json_string (str): The input JSON string.

    Returns:
        tuple: A tuple containing the 'have_evidence' and 'evidence' values.
    """
    # Replace 'Evidence' with 'evidence' to make the key case - consistent
    json_string = json_string.replace('Evidence', 'evidence')
    # Clean the JSON string
    cleaned_string = clean_json_string(json_string)

    try:
        # Try to parse the cleaned JSON string
        data = json.loads(cleaned_string)
    except json.JSONDecodeError:
        # If parsing fails, use regular expressions to extract the fields
        have_evidence = extract_have_evidence(cleaned_string)
        evidence = extract_evidence(cleaned_string)
        if have_evidence is None:
            have_evidence = extract_have_evidence(json_string)
        if evidence is None:
            evidence = extract_evidence(json_string)

        return have_evidence, evidence

    if isinstance(data, str):
        have_evidence = extract_have_evidence(cleaned_string)
        evidence = extract_evidence(cleaned_string)
    else:
        # Extract the fields from the parsed JSON
        have_evidence = data.get('have_evidence')
        evidence = data.get('evidence')

    if have_evidence is None:
        have_evidence = extract_have_evidence(json_string)
    if evidence is None:
        evidence = extract_evidence(json_string)

    return have_evidence, evidence


def extract_have_evidence(json_string):
    """
    Extract the 'have_evidence' value from the JSON string using a regular expression.

    Args:
        json_string (str): The input JSON string.

    Returns:
        str: The extracted 'have_evidence' value, or None if not found.
    """
    print(json_string)
    try:
        # Define the regular expression pattern to handle different cases of quotation marks or missing quotation marks
        have_evidence_pattern = r'["\']?have_evidence["\']?\s*:\s*["\']?([^"\',]+)["\']?\s*,\s*["\']?evidence["\']?'
        # Perform the regular expression matching
        have_evidence_match = re.search(have_evidence_pattern, json_string)
        # Extract the matched value, handling cases where the match might be missing
        have_evidence = have_evidence_match.group(1) if have_evidence_match else None
    except (re.error, ValueError, TypeError) as e:
        print(f"Error occurred: {e}")
        have_evidence = None

    return have_evidence


def extract_evidence(json_string):
    """
    Extract the 'evidence' value from the JSON string using a regular expression.

    Args:
        json_string (str): The input JSON string.

    Returns:
        str: The extracted 'evidence' value, or None if not found.
    """
    print(json_string)
    try:
        # Define the regular expression pattern to handle different cases of quotation marks or missing quotation marks
        evidence_pattern = r'["\']?evidence["\']?\s*:\s*["\']([^"\'}]+)["\']\s*}'
        # Perform the regular expression matching
        evidence_match = re.search(evidence_pattern, json_string)
        # Extract the matched value, handling cases where the match might be missing
        evidence = evidence_match.group(1) if evidence_match else None
    except (re.error, ValueError, TypeError) as e:
        print(f"Error occurred: {e}")
        evidence = None

    return evidence


def safe_json_loads(json_string):
    try:
        return json.loads(json_string)
    except Exception as e:
        print(e)
        return None


def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to load (e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'dataset',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, required=True, choices=['GuardEval', 'RAWFC'],
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'evidence_extraction',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    data = load_data(args.data_dir, args.dataset, args.task)
    evidence_extractor, user_proxy = setup_agents(args.model_name, args.dataset)
    output_dir = args.output_dir / args.dataset / args.task

    i = 0

    while i < len(data):  # len(data)
        item = data[i]
        results_data = dict()
        results_data['event_id'] = item['event_id']
        results_data['claim'] = item['claim']
        results_data['label'] = item['label']
        results_data['reports'] = []
        report_list = item["reports"]
        j = 0
        while j < len(report_list):
            report = report_list[j]
            report_result = dict()
            report_result['report'] = report['content']
            if args.dataset == 'GuardEval':
                message = (
                    "请识别并提取新闻报道中与主张相关的证据。\n\n"
                    "主张:\n"
                    f"{item['claim']}\n\n"
                    "新闻报道:\n"
                    f"{report['content']}\n\n"
                    "让我们一步一步地分析这个问题。"
                )
            else:
                message = (
                    "Please identify and extract evidence from the report that is relevant to the claim.\n\n"
                    "Claim:\n"
                    f"{item['claim']}\n\n"
                    "News Report:\n"
                    f"{report['content']}\n\n"
                    "Let's analyze this step by step."
                )

            res = user_proxy.initiate_chat(
                recipient=evidence_extractor,
                clear_history=True,
                message=message,
                cache=None,
                summary_method="last_msg",
                max_turns=1
            )
            summary = res.summary

            summary = extract_outermost_json(summary)
            have_evidence, evidence = extract_values(summary)

            report_result['have_evidence'] = have_evidence
            report_result['evidence'] = evidence
            results_data['reports'].append(report_result)
            j = j + 1
        # results_data_list.append(results_data)
        json_name = results_data['event_id'].replace('.json', '')
        output_file = output_dir / f'{json_name}.json'
        save_data_to_json(results_data, output_file)
        i += 1


if __name__ == "__main__":
    main()
