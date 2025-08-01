import os
from autogen import AssistantAgent, UserProxyAgent
import argparse
import shutil

from modules.utils import (
    ROOT, 
    load_data, 
    save_data_to_json, 
    extract_outermost_json, 
    extract_from_string
)
from modules.message_generator import MessageGenerator
from prompt.PromptH import PromptHandler


def _create_agent(name, system_message, llm_config):
    """輔助函式，用於建立 AssistantAgent"""
    return AssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", "")
    )

def _run_chat(user_proxy, recipient, message, summary_prompt):
    """輔助函式，用於執行 user_proxy.initiate_chat"""
    return user_proxy.initiate_chat(
        recipient=recipient,
        clear_history=True,
        message=message,
        cache=None,
        summary_method="reflection_with_llm",
        summary_args={"summary_prompt": summary_prompt},
        max_turns=1
    )

def setup_environment_and_agents(args):
    """根據命令列參數設定環境、載入資料並建立所有 Agent。"""
    data = load_data(args.data_dir, args.dataset, args.task)
    output_dir = args.output_dir / args.dataset / args.task
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    handler = PromptHandler()
    llm_config = {
        "model": args.model_name,
        "api_key": os.getenv('OPENAI_API_KEY', ''),
        "base_url": 'https://api.openai.com/v1',
        "cache_seed": 42
    }

    # 載入所有 Agent 的系統提示
    fact_checker_p_sys_message = handler.handle_prompt('Fact_Checker_P_en')
    fact_checker_m_sys_message = handler.handle_prompt('Fact_Checker_M_en')
    fact_checker_n_sys_message = handler.handle_prompt('Fact_Checker_N_en')
    synthesizer_sys_message = handler.handle_prompt('Synthesizer_en')
    finalizer_sys_message = handler.handle_prompt('Finalizer_en')
    
    fact_checker_names = ["Fact_Checker_1", "Fact_Checker_2", "Fact_Checker_3"]
    fact_checker_sys_messages = [fact_checker_p_sys_message, fact_checker_m_sys_message, fact_checker_n_sys_message]

    # 建立所有 Agent
    user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)
    fact_checkers = [_create_agent(name, msg, llm_config) for name, msg in zip(fact_checker_names, fact_checker_sys_messages)]
    synthesizer = _create_agent("Synthesizer", synthesizer_sys_message, llm_config)
    finalizer = _create_agent("Finalizer", finalizer_sys_message, llm_config)

    return data, output_dir, user_proxy, fact_checkers, synthesizer, finalizer

def process_item_with_agents(item, user_proxy, fact_checkers, synthesizer, finalizer):
    """
    使用一組 Agent 處理單一資料項目，以生成預測。
    """
    fact_check_prompt = (
        f'Please carefully analyze the provided evidence in relation to the claim and then determine the overall authenticity as true, half-true, or false.\n'
    )
    summary_prompt = "Return review into a JSON object only:\n {'claim': '<claim>', 'prediction': '<prediction>', 'justification': '<justification>'}."
    synthesizer_summary_prompt = "Return the review as a JSON object:\n {'feedback': '<feedback>', 'suggestion': '<suggestion>', 'terminate': <true/false>}."
    max_turns = 3

    msg_generator = MessageGenerator()
    meta_message = msg_generator.create_meta_message(item)
    
    # 初始化每個 fact_checker 的訊息
    fact_check_messages = [f"{fact_check_prompt}\n{meta_message}\n"] * len(fact_checkers)

    turn = 1
    is_terminate = False
    fch_results_summaries = []
    synthesizer_res_summary = {}

    while turn <= max_turns and not is_terminate:
        fch_results_summaries = []
        # 使用迴圈處理所有 fact-checkers
        for i, checker in enumerate(fact_checkers):
            res = _run_chat(user_proxy, checker, fact_check_messages[i], summary_prompt)
            fch_results_summaries.append(res.summary)

        synthesizer_message = msg_generator.create_synthesizer_message(item['claim'], *fch_results_summaries)
        synthesizer_res = _run_chat(user_proxy, synthesizer, synthesizer_message, synthesizer_summary_prompt)

        # 為了下一輪更新訊息，使用迴圈動態產生
        new_fact_check_messages = []
        for i in range(len(fact_checkers)):
            own_res = fch_results_summaries[i]
            other_res = [res for j, res in enumerate(fch_results_summaries) if i != j]
            
            message, synthesizer_res_summary = msg_generator.create_reeval_message(
                meta_message, 
                synthesizer_res.summary, 
                own_res, 
                other_res
            )
            new_fact_check_messages.append(message)
        
        fact_check_messages = new_fact_check_messages
        is_terminate = synthesizer_res_summary.get('terminate', False)
        turn += 1

    finalizer_message = msg_generator.create_finalizer_message(item['claim'], *fch_results_summaries)
    res = _run_chat(user_proxy, finalizer, finalizer_message, summary_prompt)
    
    summary = extract_outermost_json(res.summary)
    prediction, justification = extract_from_string(summary, 'prediction', 'justification')
    
    return {
        'event_id': item['event_id'],
        'claim': item['claim'],
        'label': item['label'],
        'prediction': prediction,
        'justification': justification
    }


def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='base model(e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'results' / 'evidence_verify',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test', ''], default='',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, choices=['CFEVER', 'RAWFC', 'TFC'], default='CFEVER',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'prediction',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    data, output_dir, user_proxy, fact_checkers, synthesizer, finalizer = setup_environment_and_agents(args)

    for i, item in enumerate(data, 1):
        results_data = process_item_with_agents(
            item, user_proxy, fact_checkers, synthesizer, finalizer
        )
        
        json_name = results_data['event_id'].replace('.json', '')
        output_file = output_dir / f'{json_name}.json'
        save_data_to_json(results_data, output_file)
        print(f"✅ Claim {i} ({json_name}) is evaluated. Results saved to {output_file}")


if __name__ == "__main__":
    main()
