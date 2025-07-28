import os
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
from PromptH import PromptHandler
import argparse
import json
import re

from utils import *


def extract_values(json_string):
    json_string = json_string.replace('Prediction', 'prediction').replace('Justification', 'justification')
    cleaned_string = clean_json_string(json_string)

    try:
        data = json.loads(cleaned_string)
    except json.JSONDecodeError:
        prediction = extract_prediction(cleaned_string)
        justification = extract_justification(cleaned_string)
        if prediction is None:
            prediction = extract_prediction(json_string)
        if justification is None:
            justification = extract_justification(json_string)

        return prediction, justification

    if isinstance(data, str):
        prediction = extract_prediction(cleaned_string)
        justification = extract_justification(cleaned_string)
    else:
        prediction = data.get('prediction')
        justification = data.get('justification')

    if prediction is None:
        prediction = extract_prediction(json_string)
    if justification is None:
        justification = extract_justification(json_string)

    return prediction, justification


def extract_prediction(json_string):
    try:
        # Define the regular expression pattern to handle different cases of quotation marks or missing quotation marks
        prediction_pattern = r'["\']?prediction["\']?\s*:\s*["\']?([^"\',]+)["\']?\s*,\s*["\']?justification["\']?'

        # Perform the regular expression matching
        prediction_match = re.search(prediction_pattern, json_string)

        # Extract the matched value, handling cases where the match might be missing
        prediction = prediction_match.group(1) if prediction_match else None

    except (re.error, ValueError, TypeError) as e:
        print(f"Error occurred: {e}")
        prediction = None

    return prediction


def extract_justification(json_string):
    try:
        # Define the regular expression pattern to handle different cases of quotation marks or missing quotation marks
        justification_pattern = r'["\']?justification["\']?\s*:\s*["\']([^"\'}]+)["\']\s*}'

        # Perform the regular expression matching
        justification_match = re.search(justification_pattern, json_string)

        # Extract the matched value, handling cases where the match might be missing
        justification = justification_match.group(1) if justification_match else None

    except (re.error, ValueError, TypeError) as e:
        print(f"Error occurred: {e}")
        justification = None

    return justification


def create_synthesizer_message(claim, res1_summary, res2_summary, res3_summary):
    res1_summary = extract_outermost_json(res1_summary)
    res2_summary = extract_outermost_json(res2_summary)
    res3_summary = extract_outermost_json(res3_summary)

    res1_prediction, res1_justification = extract_values(res1_summary)
    res2_prediction, res2_justification = extract_values(res2_summary)
    res3_prediction, res3_justification = extract_values(res3_summary)

    message = (f"Please aggregate the evaluations and predictions from Fact Checkers.\n"
                f"Claim:{claim}\n"
                f"Result of Fact Checker 1:\n\tPrediction:{res1_prediction}\n\tJustification:{res1_justification}\n"
                f"Result of Fact Checker 2:\n\tPrediction:{res2_prediction}\n\tJustification:{res2_justification}\n"
                f"Result of Fact Checker 3:\n\tPrediction:{res3_prediction}\n\tJustification:{res3_justification}\n")
    
    return message


def create_meta_message(item):
    evidence_header = "Evidence:\n"
    no_evidence_text = "No evidence provided\n\n"
    claim_prefix = "Claim:"

    evidence = evidence_header
    
    if isinstance(item.get('verified_evidence'), list):
        for evidence_item in item['verified_evidence']:
            evidence += f"{evidence_item}\n"
    elif isinstance(item.get('verified_evidence'), str):
        evidence += f"{item['verified_evidence']}\n"

    if evidence == evidence_header:
        evidence = evidence_header + no_evidence_text

    message = (
        f"{claim_prefix}{item['claim']}\n\n"
        f"{evidence}")
    return message


def create_reeval_message(meta_message, synthesizer_res_summary, fc_res_summary1, fc_res_summary2, fc_res_summary3):
    synthesizer_res_summary = extract_outermost_json(synthesizer_res_summary)
    synthesizer_res_summary = json.loads(synthesizer_res_summary)

    fc_res_summary1 = extract_outermost_json(fc_res_summary1)
    fc_prediction1, fc_justification1 = extract_values(fc_res_summary1)
    fc_res_summary2 = extract_outermost_json(fc_res_summary2)
    fc_prediction2, fc_justification2 = extract_values(fc_res_summary2)
    fc_res_summary3 = extract_outermost_json(fc_res_summary3)
    fc_prediction3, fc_justification = extract_values(fc_res_summary3)

    prediction_list = [fc_prediction1.lower(), fc_prediction2.lower(), fc_prediction3.lower()]
    prediction_list = ['half-true' if item == 'half true' else item for item in prediction_list]
    prediction_list = ['mostly-true' if item == 'mostly true' else item for item in prediction_list]
    prediction_list = ['barely-true' if item == 'barely true' else item for item in prediction_list]
    unique_predictions = list(set(prediction_list))

    if len(unique_predictions) == 2:
        dis_msg = f"and work towards reaching a consensus between '{unique_predictions[0]}' and '{unique_predictions[1]}'."
    elif len(unique_predictions) == 3:
        dis_msg = f"and work towards reaching a consensus among '{unique_predictions[0]}', '{unique_predictions[1]}', and '{unique_predictions[2]}'."
    else:
        dis_msg = ''
    message = (
        f"There are discrepancies in the prediction results from different Fact Checkers. "
        f"Please reflect on these differences {dis_msg}.\n"
        f"\n{meta_message}\n"
        f"Previous Prediction and Justification:\n\tPrediction:{fc_prediction1}\n\tJustification:{fc_justification1}\n\n"
        f"The Synthesizer has identified key areas where perspectives differ: '{synthesizer_res_summary['feedback']}'.\n\n"
        f"Reflect on your previous prediction in light of this feedback. "
        f"If you believe your prediction should change, provide the new prediction and justification. "
        f"If your prediction remains the same, explain why."
    )

    return message, synthesizer_res_summary


def create_finalizer_message(claim, res1_summary, res2_summary, res3_summary):
    res1_summary = extract_outermost_json(res1_summary)
    res2_summary = extract_outermost_json(res2_summary)
    res3_summary = extract_outermost_json(res3_summary)

    res1_prediction, res1_justification = extract_values(res1_summary)
    res2_prediction, res2_justification = extract_values(res2_summary)
    res3_prediction, res3_justification = extract_values(res3_summary)

    message = (f"Please make the final decision on the authenticity of the claim\n\n"
                f"Claim:{claim}\n"
                f"Result of Fact Checker 1:\n\tPrediction:{res1_prediction}\n\tJustification:{res1_justification}\n"
                f"Result of Fact Checker 2:\n\tPrediction:{res2_prediction}\n\tJustification:{res2_justification}\n"
                f"Result of Fact Checker 3:\n\tPrediction:{res3_prediction}\n\tJustification:{res3_justification}\n\n")
    
    return message

def create_agent(name, system_message, llm_config):
    """輔助函式，用於建立 AssistantAgent"""
    return AssistantAgent(
        name=name,
        system_message=system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", "")
    )

def run_chat(user_proxy, recipient, message, summary_prompt):
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

    meta_message = create_meta_message(item)
    
    # 初始化每個 fact_checker 的訊息
    fact_check_messages = [f"{fact_check_prompt}\n{meta_message}\n"] * len(fact_checkers)

    turn = 1
    is_terminate = False
    fch_results = []

    while turn <= max_turns and not is_terminate:
        fch_results = []
        # 使用迴圈處理所有 fact-checkers
        for i, checker in enumerate(fact_checkers):
            res = run_chat(user_proxy, checker, fact_check_messages[i], summary_prompt)
            fch_results.append(res)

        synthesizer_message = create_synthesizer_message(item['claim'], fch_results[0].summary, fch_results[1].summary, fch_results[2].summary)
        synthesizer_res = run_chat(user_proxy, synthesizer, synthesizer_message, synthesizer_summary_prompt)

        # 為了下一輪更新訊息
        # 這裡的邏輯比較複雜，暫時保留原樣，但未來也可以考慮優化 create_reeval_message
        fact_check_p_message, _ = create_reeval_message(meta_message, synthesizer_res.summary, fch_results[0].summary, fch_results[1].summary, fch_results[2].summary)
        fact_check_m_message, _ = create_reeval_message(meta_message, synthesizer_res.summary, fch_results[1].summary, fch_results[0].summary, fch_results[2].summary)
        fact_check_n_message, synthesizer_res_summary = create_reeval_message(meta_message, synthesizer_res.summary, fch_results[2].summary, fch_results[0].summary, fch_results[1].summary)
        
        fact_check_messages = [fact_check_p_message, fact_check_m_message, fact_check_n_message]
        is_terminate = synthesizer_res_summary.get('terminate', False)
        turn += 1

    finalizer_message = create_finalizer_message(item['claim'], fch_results[0].summary, fch_results[1].summary, fch_results[2].summary)
    res = run_chat(user_proxy, finalizer, finalizer_message, summary_prompt)
    
    summary = extract_outermost_json(res.summary)
    prediction, justification = extract_values(summary)
    
    return {
        'event_id': item['event_id'],
        'claim': item['claim'],
        'label': item['label'],
        'prediction': prediction,
        'justification': justification
    }


def setup_environment_and_agents(args):
    """根據命令列參數設定環境、載入資料並建立所有 Agent。"""
    data = load_data(args.data_dir, args.dataset, args.task)
    output_dir = args.output_dir / args.dataset / args.task
    output_dir.mkdir(parents=True, exist_ok=True)

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

    synthesizer_name = "Synthesizer"
    finalizer_name = "Finalizer"

    # 建立所有 Agent
    user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)
    fact_checkers = [create_agent(name, msg, llm_config) for name, msg in zip(fact_checker_names, fact_checker_sys_messages)]
    synthesizer = create_agent(synthesizer_name, synthesizer_sys_message, llm_config)
    finalizer = create_agent(finalizer_name, finalizer_sys_message, llm_config)

    return data, output_dir, user_proxy, fact_checkers, synthesizer, finalizer, llm_config, handler


def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='base model(e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'results' / 'evidence_verify',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, choices=['GuardEval', 'RAWFC'], default='RAWFC',
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'prediction',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    data, output_dir, user_proxy, fact_checkers, synthesizer, finalizer, llm_config, handler = setup_environment_and_agents(args)

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
