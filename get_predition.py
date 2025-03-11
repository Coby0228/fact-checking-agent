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


def clean_message(message):
    message = re.sub(r'\\\\+', r'\\', message)
    message = (message.replace("\\u201c", "").replace("\\u201d", "").replace('\\"', '"').replace("\\u2013", "").replace(
        "\\u2227", "").replace("  ", " ").replace("\\u00e2", "").replace('\\u2019', ''))
    return message


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
    print(json_string)
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
    print(json_string)
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


def safe_json_loads(json_string):
    try:
        return json.loads(json_string)
    except Exception as e:
        print(e)
        return None


def remove_field_from_json_list(data_list, field_to_remove):
    """
    Remove a specific field from each dictionary in the list.
    """
    for item in data_list:
        item.pop(field_to_remove, None)
    return data_list


def create_synthesizer_message(claim, res1_summary, res2_summary, res3_summary, dataset='RAWFC'):
    res1_summary = extract_outermost_json(res1_summary)
    res2_summary = extract_outermost_json(res2_summary)
    res3_summary = extract_outermost_json(res3_summary)

    res1_prediction, res1_justification = extract_values(res1_summary)
    res2_prediction, res2_justification = extract_values(res2_summary)
    res3_prediction, res3_justification = extract_values(res3_summary)

    if dataset == 'RAWFC':
        message = (f"Please aggregate the evaluations and predictions from Fact Checkers.\n"
                   f"Claim:{claim}\n"
                   f"Result of Fact Checker 1:\n\tPrediction:{res1_prediction}\n\tJustification:{res1_justification}\n"
                   f"Result of Fact Checker 2:\n\tPrediction:{res2_prediction}\n\tJustification:{res2_justification}\n"
                   f"Result of Fact Checker 3:\n\tPrediction:{res3_prediction}\n\tJustification:{res3_justification}\n")
    else:
        message = (f"请汇总事实核查员的评估和预测。\n"
                   f"主张:{claim}\n"
                   f"事实核查员1的结果:\n\t预测:{res1_prediction}\n\t理由:{res1_justification}\n"
                   f"事实核查员2的结果:\n\t预测:{res2_prediction}\n\t理由:{res2_justification}\n"
                   f"事实核查员3的结果:\n\t预测:{res3_prediction}\n\t理由:{res3_justification}\n")
    return message


def create_meta_message(item, dataset='RAWFC'):
    if dataset == 'RAWFC':
        evidence_header = "Evidence:\n"
        no_evidence_text = "No evidence provided\n\n"
        claim_prefix = "Claim:"
    else:
        evidence_header = "证据:\n"
        no_evidence_text = "没有提供证据\n\n"
        claim_prefix = "主张:"

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


def create_reeval_message(meta_message, synthesizer_res_summary, fc_res_summary1, fc_res_summary2, fc_res_summary3, dataset='RAWFC'):
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

    if dataset == 'RAWFC':
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
    else:
        if len(unique_predictions) == 2:
            dis_msg = f"并努力在'{unique_predictions[0]}'和'{unique_predictions[1]}'之间达成共识。"
        elif len(unique_predictions) == 3:
            dis_msg = f"并努力在'{unique_predictions[0]}', '{unique_predictions[1]}', 和'{unique_predictions[2]}'之间达成共识。"
        else:
            dis_msg = ''
        message = (
            f"不同事实核查员的预测结果存在差异。"
            f"请反思这些差异{dis_msg}。\n"
            f"\n{meta_message}\n"
            f"之前的预测和理由:\n\t预测:{fc_prediction1}\n\t理由:{fc_justification1}\n\n"
            f"协调者反馈的内容中，多位事实核查员观点的关键分歧点在于：'{synthesizer_res_summary['feedback']}'.\n\n"
            f"请根据这一反馈反思你之前的预测。"
            f"如果你认为你的预测应该改变，请提供新的预测和理由。"
            f"如果你的预测保持不变，请解释原因。"
        )
    return message, synthesizer_res_summary


def create_finalizer_message(claim, res1_summary, res2_summary, res3_summary, dataset='RAWFC'):
    res1_summary = extract_outermost_json(res1_summary)
    res2_summary = extract_outermost_json(res2_summary)
    res3_summary = extract_outermost_json(res3_summary)

    res1_prediction, res1_justification = extract_values(res1_summary)
    res2_prediction, res2_justification = extract_values(res2_summary)
    res3_prediction, res3_justification = extract_values(res3_summary)

    if dataset == 'RAWFC':
        message = (f"Please make the final decision on the authenticity of the claim\n\n"
                   f"Claim:{claim}\n"
                   f"Result of Fact Checker 1:\n\tPrediction:{res1_prediction}\n\tJustification:{res1_justification}\n"
                   f"Result of Fact Checker 2:\n\tPrediction:{res2_prediction}\n\tJustification:{res2_justification}\n"
                   f"Result of Fact Checker 3:\n\tPrediction:{res3_prediction}\n\tJustification:{res3_justification}\n\n")
    else:
        message = (f"请就该主张的真实性做出最终决定。\n\n"
                   f"主张:{claim}\n"
                   f"事实核查员1的结果:\n\t预测:{res1_prediction}\n\t理由:{res1_justification}\n"
                   f"事实核查员2的结果:\n\t预测:{res2_prediction}\n\t理由:{res2_justification}\n"
                   f"事实核查员3的结果:\n\t预测:{res3_prediction}\n\t理由:{res3_justification}\n\n")
    return message

def main():
    parser = argparse.ArgumentParser(description="Load different model configurations and set up agents.")
    parser.add_argument('--model_name', type=str, default='gpt-4o-mini',
                        help='base model(e.g., gpt-4o-mini, llama)')
    parser.add_argument('--data_dir', type=str, default=ROOT / 'results' / 'evidence_verify',
                        help='Directory containing the datasets')
    parser.add_argument('--task', type=str, choices=['train', 'val', 'test'], default='test',
                        help='Task type to load (train/val/test)')
    parser.add_argument('--dataset', type=str, required=True, choices=['GuardEval', 'RAWFC'],
                        help='Name of the dataset to load')
    parser.add_argument('--output_dir', type=str, default=ROOT / 'results' / 'prediction',
                        help='Output JSON file to save the data')
    args = parser.parse_args()

    if args.dataset == 'GuardEval':
        data_dir = args.data_dir / 'GuardEval'
    elif args.dataset == 'RAWFC':
        data_dir = args.data_dir / 'RAWFC'

    data = load_dataset(data_dir, args.task)
    output_dir = args.output_dir / args.dataset / args.task

    handler = PromptHandler()
    model_config = ModelConfig()
    llm_config = model_config.get_config(args.model_name)
    if args.dataset == 'RAWFC':
        fact_checker_p_sys_message = handler.handle_prompt('Fact_Checker_P_en')
        fact_checker_m_sys_message = handler.handle_prompt('Fact_Checker_M_en')
        fact_checker_n_sys_message = handler.handle_prompt('Fact_Checker_N_en')
        synthesizer_sys_message = handler.handle_prompt('Synthesizer_en')
        finalizer_sys_message = handler.handle_prompt('Finalizer_en')
        fact_checker_names = ["Fact Checker 1", "Fact Checker 2", "Fact Checker 3"]
        synthesizer_name = "Synthesizer"
        finalizer_name = "Finalizer"
        fact_check_prompt = (
            f'Please carefully analyze the provided evidence in relation to the claim and then determine the overall authenticity as true, half-true, or false.\n'
        )
        summary_prompt = "Return review into a JSON object only:\n {'claim': '<claim>', 'prediction': '<prediction>', 'justification': '<justification>'}."
        synthesizer_summary_prompt = "Return the review as a JSON object:\n {'feedback': '<feedback>', 'suggestion': '<suggestion>', 'terminate': <true/false>}."
        max_turns = 3
    else:
        fact_checker_p_sys_message = handler.handle_prompt('Fact_Checker_P_ch')
        fact_checker_m_sys_message = handler.handle_prompt('Fact_Checker_M_ch')
        fact_checker_n_sys_message = handler.handle_prompt('Fact_Checker_N_ch')
        synthesizer_sys_message = handler.handle_prompt('Synthesizer_ch')
        finalizer_sys_message = handler.handle_prompt('Finalizer_ch')
        fact_checker_names = ["事实核查员1", "事实核查员2", "事实核查员3"]
        synthesizer_name = "协调者"
        finalizer_name = "最终决策者"
        fact_check_prompt = f'请仔细分析所提供的与主张相关的证据，然后确定整体真实性为True、Half-true或False。\n'
        summary_prompt = "请仅以JSON对象的形式返回结果：\n {'claim': '<claim>', 'prediction': '<prediction>', 'justification': '<justification>'}。"
        synthesizer_summary_prompt = "请仅以JSON对象的形式返回结果:\n {'feedback': '<feedback>', 'suggestion': '<suggestion>', 'terminate': <true/false>}."
        max_turns = 3

    user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

    fact_checker_p = AssistantAgent(
        name=fact_checker_names[0],
        system_message=fact_checker_p_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content")
    )

    fact_checker_m = AssistantAgent(
        name=fact_checker_names[1],
        system_message=fact_checker_m_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content")
    )

    fact_checker_n = AssistantAgent(
        name=fact_checker_names[2],
        system_message=fact_checker_n_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content")
    )

    synthesizer = AssistantAgent(
        name=synthesizer_name,
        system_message=synthesizer_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content")
    )

    finalizer = AssistantAgent(
        name=finalizer_name,
        system_message=finalizer_sys_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "TERMINATE" in msg.get("content")
    )

    i = 0

    while i < len(data):
        item = data[i]
        results_data = dict()
        results_data['event_id'] = item['event_id']
        results_data['claim'] = item['claim']
        results_data['label'] = item['label']

        meta_message = create_meta_message(item)

        fact_check_p_message = f"{fact_check_prompt}\n{meta_message}\n"
        fact_check_m_message = fact_check_p_message
        fact_check_n_message = fact_check_p_message

        turn = 1
        is_terminate = False
        while turn <= max_turns and not is_terminate:
            fch_p_res = user_proxy.initiate_chat(
                recipient=fact_checker_p,
                clear_history=True,
                message=fact_check_p_message,
                cache=None,
                summary_method="reflection_with_llm",
                summary_args={"summary_prompt": summary_prompt},
                max_turns=1
            )

            fch_m_res = user_proxy.initiate_chat(
                recipient=fact_checker_m,
                clear_history=True,
                message=fact_check_m_message,
                cache=None,
                summary_method="reflection_with_llm",
                summary_args={"summary_prompt": summary_prompt},
                max_turns=1
            )

            fch_n_res = user_proxy.initiate_chat(
                recipient=fact_checker_n,
                clear_history=True,
                message=fact_check_n_message,
                cache=None,
                summary_method="reflection_with_llm",
                summary_args={"summary_prompt": summary_prompt},
                max_turns=1
            )

            synthesizer_message = create_synthesizer_message(item['claim'], fch_p_res.summary, fch_m_res.summary,
                                                             fch_n_res.summary)
            synthesizer_res = user_proxy.initiate_chat(
                recipient=synthesizer,
                clear_history=True,
                message=synthesizer_message,
                cache=None,
                summary_method="reflection_with_llm",
                summary_args={"summary_prompt": synthesizer_summary_prompt},
                max_turns=1
            )

            fact_check_p_message, _ = create_reeval_message(meta_message, synthesizer_res.summary, fch_p_res.summary,
                                                            fch_m_res.summary, fch_n_res.summary)
            fact_check_m_message, _ = create_reeval_message(meta_message, synthesizer_res.summary, fch_m_res.summary,
                                                            fch_p_res.summary, fch_n_res.summary)
            fact_check_n_message, synthesizer_res_summary = create_reeval_message(meta_message, synthesizer_res.summary,
                                                                                  fch_n_res.summary, fch_p_res.summary,
                                                                                  fch_m_res.summary)
            is_terminate = synthesizer_res_summary['terminate']

            turn += 1

        finalizer_message = create_finalizer_message(item['claim'], fch_p_res.summary, fch_m_res.summary,
                                                     fch_n_res.summary)
        res = user_proxy.initiate_chat(
            recipient=finalizer,
            clear_history=True,
            message=finalizer_message,
            cache=None,
            summary_method="reflection_with_llm",
            summary_args={"summary_prompt": summary_prompt},
            max_turns=1
        )
        summary = res.summary
        summary = extract_outermost_json(summary)
        prediction, justification = extract_values(summary)
        results_data['prediction'] = prediction
        results_data['justification'] = justification
        json_name = results_data['event_id']
        output_file = output_dir / f'{json_name}.json'
        save_data_to_json(results_data, output_file)
        i += 1
        print(f"{i}'s claim is evaluated")


if __name__ == "__main__":
    main()
