import os
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent, register_function
from PromptH import PromptHandler
import json
from pathlib import Path
import sys
import re
from dotenv import load_dotenv

from tools import search_web, fetch_url


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

def setup_agents(agent_name):
    handler = PromptHandler()
    
    llm_config = {
        "config_list": [
            {
                "model": "gpt-4o-mini",
                "api_key": os.getenv('OPENAI_API_KEY', ''),
                "base_url": 'https://api.openai.com/v1',
            }
        ],
        "cache_seed": 42,
    }

    evidence_extractor = AssistantAgent(
        name=agent_name,
        system_message=handler.handle_prompt(agent_name + '_System'),
        llm_config=llm_config,
    )

    user_proxy = UserProxyAgent(
        name="user_proxy", 
        code_execution_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: (msg.get("content") or "").strip().endswith("TERMINATE")
    )

    if agent_name == 'Evidence_Extractor':
        register_function(
            search_web,
            caller=evidence_extractor,  # AssistantAgent 可以調用
            executor=user_proxy,        # UserProxyAgent 可以執行
            name="search_web",
            description="Search for information related to a claim and store results"
        )
        
        register_function(
            fetch_url,
            caller=evidence_extractor,
            executor=user_proxy,
            name="fetch_url", 
            description="Fetch content from a URL for evidence extraction"
        )

    return evidence_extractor, user_proxy

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

def create_meta_message(item):
    
    evidence_header = "Evidence:\n"
    no_evidence_text = "No evidence provided\n\n"
    prompt = "Please analyze and verify the accuracy and completeness of the provided evidence in relation to the given claim.\n\n"
    claim_prefix = "Claim:"

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
