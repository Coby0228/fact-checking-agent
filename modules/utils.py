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
# 將 ROOT 直接定義為當前工作目錄，以確保路徑解析的穩定性
ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH


def extract_outermost_json(text):
    """
    從字串中提取最外層的 JSON 物件。
    """
    if not isinstance(text, str):
        return None
        
    # 找到第一個 '{' 和最後一個 '}'
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1 or end_index < start_index:
        return None

    # 截取可能的 JSON 字串
    potential_json = text[start_index : end_index + 1]

    # 嘗試解析，如果成功，表示我們找到了有效的 JSON
    try:
        json.loads(potential_json)
        return potential_json
    except json.JSONDecodeError:
        # 如果解析失敗，表示這不是一個有效的 JSON 物件
        return None

def load_data(data_dir, dataset, task=None, agent_name=None):
    base_path = Path(data_dir) / dataset
    data_list = []

    # 判斷條件：當資料集為 TFC 或 CFEVER 且 agent 為 Evidence_Extractor 時，走單一檔案邏輯
    if (dataset == 'CFEVER' or dataset == 'TFC') and agent_name == 'Evidence_Extractor':
        # --- 邏輯二：處理單一彙總檔案 ---
        # 動態尋找目錄中的第一個 JSON 檔案
        try:
            file_path = next(base_path.glob('*.json'))
        except StopIteration:
            print(f"Error: No JSON file found in directory: {base_path}")
            return []

        print(f"Found file: {file_path}")
        confirm = input("Load this file? (y/n): ")

        if confirm.lower() == 'y':
            print(f"Loading data from single file: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    full_data_list = json.load(file)
                    data_list = [item for item in full_data_list if 'label' in item]
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {file_path}")
        else:
            print("File loading cancelled by user.")
            return []
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

def extract_from_string(text, *keys):
    """
    從字串中提取指定鍵的值。
    優先嘗試將字串解析為 JSON，如果失敗或找不到鍵，則使用正規表示式作為備案。

    Args:
        text (str): 要從中提取資料的輸入字串。
        *keys (str): 一個或多個要提取的鍵。

    Returns:
        - 如果只提供一個鍵，則回傳該鍵的值 (str 或 None)。
        - 如果提供多個鍵，則回傳一個包含所有鍵值的元組。
    """
    if not text or not keys:
        return None if len(keys) == 1 else (None,) * len(keys)

    # 1. 嘗試 JSON 解析
    try:
        # 統一鍵的大小寫並清理字串
        normalized_text = text
        for key in keys:
            normalized_text = normalized_text.replace(f'"{key.capitalize()}"', f'"{key.lower()}"')
        
        cleaned_text = clean_json_string(normalized_text)
        data = json.loads(cleaned_text)
        
        if isinstance(data, dict):
            values = [data.get(key.lower()) for key in keys]
            # 如果所有值都成功找到，就回傳
            if all(v is not None for v in values):
                return values[0] if len(values) == 1 else tuple(values)
    except (json.JSONDecodeError, AttributeError):
        pass  # JSON 解析失敗，繼續執行正規表示式備案

    # 2. 正規表示式備案
    results = []
    for key in keys:
        # 針對不同 key 使用不同的 pattern
        if key == 'evidence':
            # 匹配 "evidence": [...]
            pattern = r'["\']?evidence["\']?\s*:\s*(\[[^\]]*\])'
        else:
            # 通用模式，匹配 "key": "value"
            pattern = rf'["\']?{key}["\']?\s*:\s*["\']([^"\']+)["\']'
        
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            results.append(match.group(1).strip() if match else None)
        except (re.error, IndexError):
            results.append(None)

    return results[0] if len(results) == 1 else tuple(results)

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
