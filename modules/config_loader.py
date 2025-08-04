import os
import yaml
from modules.paths import ROOT

def load_and_process_config(model_name: str = None):
    """
    從 config.yaml 載入並處理指定模型的設定。
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

    return model_config_raw