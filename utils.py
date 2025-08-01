import os
from autogen import AssistantAgent, UserProxyAgent, register_function
import json
import yaml
from pathlib import Path
import sys
import re
from dotenv import load_dotenv

from tools import search_web, fetch_url
from prompt.PromptH import PromptHandler


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

def load_data(data_dir, dataset, task=None, agent_name=None):
    base_path = Path(data_dir) / dataset
    data_list = []

    # 判斷條件：當資料集為 TFC 或 CFEVER 且 agent 為 Evidence_Extractor 時，走單一檔案邏輯
    if (dataset == 'CFEVER' or dataset == 'TFC') and agent_name == 'Evidence_Extractor':
        # --- 邏輯二：處理單一彙總檔案 ---
        file_path = base_path / f"{dataset}_data_with_labels.json"
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return []

        print(f"Loading data from single file: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                full_data_list = json.load(file)
                # 篩選出有 'label' 欄位的資料
                data_list = [item for item in full_data_list if 'label' in item]
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_path}")
    else:
        # --- 邏輯一：處理多檔案目錄 ---
        task_dir = base_path / task
        if not task_dir.is_dir():
            print(f"Error: Directory not found: {task_dir}")
            return []
        
        print(f"Loading data from directory: {task_dir}")
        for file_name in os.listdir(task_dir):
            if file_name.endswith('.json'):
                file_path = task_dir / file_name
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        data_list.append(data)
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON from {file_path}")


    return data_list

def save_data_to_json(data, output_file):
    # Create directory if it doesn't exist
    os.makedirs(output_file.parent, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print('Save completed\n')

def load_and_process_config(model_name=None):
    """
    從 config.yaml 載入並處理指定模型的設定。
    
    Args:
        model_name (str, optional): 要載入的模型名稱。如果為 None，則使用預設模型。

    Returns:
        dict: 處理過的模型設定字典，可直接用於 llm_config。
    """
    config_path = ROOT / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if model_name not in config['models']:
        raise ValueError(f"模型 '{model_name}' 在 config.yaml 中找不到。")

    model_config_raw = config['models'][model_name].copy()

    config_list = model_config_raw.get("config_list", [])
    for cfg in config_list:
        for key, value in cfg.items():
            if isinstance(value, str) and value.isupper():
                env_value = os.getenv(value)
                if env_value is None:
                    print(f"Warning: Environment variable '{value}' for key '{key}' not set.")
                cfg[key] = env_value

    # 否則直接回傳處理過的 OpenAI 設定
    return model_config_raw

def setup_agents(agent_name, model_name=None):
    handler = PromptHandler()
    model_config = load_and_process_config(model_name)
    if "qwen3" in model_name:
        system_prompt = handler.handle_prompt(agent_name + '_System_zh')
    else:
        system_prompt = handler.handle_prompt(agent_name + '_System')
    
    evidence_extractor = AssistantAgent(
        name=agent_name,
        system_message=system_prompt,
        llm_config=model_config,
    )

    user_proxy = UserProxyAgent(
        name="user_proxy", 
        code_execution_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: (msg.get("content") or "").strip().strip("'\"").endswith("TERMINATE")
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
