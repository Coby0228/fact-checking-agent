import os
import json
from pathlib import Path
from dotenv import load_dotenv
import argparse

load_dotenv()
FILE = Path(__file__).resolve()

def load_data(data_dir, dataset, task=None, agent_name=None):
    """
    從指定目錄載入資料。
    根據 agent_name 和 dataset 決定是讀取單一彙總檔案還是多個獨立檔案。
    """
    base_path = Path(data_dir) / dataset
    data_list = []

    if (dataset == 'CFEVER' or dataset == 'TFC') and agent_name == 'Evidence_Extractor':
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
            print(f"Warning: File not found at {file_path}")
    else:
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

def create_argument_parser():
    """
    建立並回傳一個設定好通用參數的 ArgumentParser 物件。
    """
    parser = argparse.ArgumentParser(description="Fact-Checking Agent Pipeline Script")
    
    # 通用參數
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='Name of the model to use (e.g., gpt-4o-mini, qwen2:7b)')
    parser.add_argument('--dataset', type=str, choices=['CFEVER', 'RAWFC', 'TFC'], default='CFEVER',
                        help='Name of the dataset to use')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test', ''], default='',
                        help='Task type to load (train, val, test)')
    parser.add_argument('--data_dir', type=str,
                        help='Directory containing the input datasets')
    parser.add_argument('--output_dir', type=str,
                        help='Directory to save the output files')

    return parser
