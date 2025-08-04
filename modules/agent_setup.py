from autogen import AssistantAgent, UserProxyAgent, register_function

from modules.config_loader import load_and_process_config
from prompt.PromptH import PromptHandler
from tools.search import search_web
from tools.fetch import fetch_url

def setup_agents(agent_name: str, model_name: str = None):
    """
    根據 agent 名稱和模型名稱，設定並回傳一個 AssistantAgent 和一個 UserProxyAgent。
    """
    handler = PromptHandler()
    model_config = load_and_process_config(model_name)
    
    if "qwen" in model_name:
        system_prompt = handler.handle_prompt(agent_name + '_System_zh')
    else:
        system_prompt = handler.handle_prompt(agent_name + '_System')
    
    assistant = AssistantAgent(
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
            caller=assistant,
            executor=user_proxy,
            name="search_web",
            description="Search for information related to a claim and store results"
        )
        register_function(
            fetch_url,
            caller=assistant,
            executor=user_proxy,
            name="fetch_url", 
            description="Fetch content from a URL for evidence extraction"
        )

    return assistant, user_proxy