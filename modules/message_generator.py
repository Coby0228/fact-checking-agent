import json
from .parsers import extract_outermost_json, extract_from_string


class MessageGenerator:
    """一個用於生成各種代理訊息的類別。"""

    def _extract_from_summary(self, summary_str):
        """從摘要字串中提取預測和理由。"""
        summary_json_str = extract_outermost_json(summary_str)
        prediction, justification = extract_from_string(summary_json_str, 'Prediction', 'Justification')
        return prediction, justification

    def _create_fact_checker_results_message(self, claim, summaries, base_message):
        """建立包含多個 Fact Checker 結果的訊息。"""
        message_parts = [base_message, f"Claim:{claim}"]
        for i, summary in enumerate(summaries, 1):
            prediction, justification = self._extract_from_summary(summary)
            message_parts.append(
                f"Result of Fact Checker {i}:\n\tPrediction:{prediction}\n\tJustification:{justification}"
            )
        return "\n".join(message_parts) + "\n\n"

    def create_synthesizer_message(self, claim, *summaries):
        """為 Synthesizer 建立訊息。"""
        base_message = "Please aggregate the evaluations and predictions from Fact Checkers."
        return self._create_fact_checker_results_message(claim, summaries, base_message)

    def create_finalizer_message(self, claim, *summaries):
        """為 Finalizer 建立訊息。"""
        base_message = "Please make the final decision on the authenticity of the claim"
        return self._create_fact_checker_results_message(
            claim, 
            summaries, 
            base_message
        )

    def create_verifier_message(self, item):
        """為 Evidence_Verifier 建立初始訊息。"""
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
            evidence += evidence_header + no_evidence_text

        message = (
            f"{prompt}"
            f"{claim_prefix}{item['claim']}\n\n"
            f"{evidence}\n"
            f"Let's analyze this step by step."
        )
        return message

    def create_prediction_message(self, item):
        """建立包含 Claim 和 Evidence 的訊息。"""
        evidence_header = "Evidence:\n"
        no_evidence_text = "No evidence provided\n\n"
        claim_prefix = "Claim:"

        evidence = evidence_header
        
        verified_evidence = item.get('verified_evidence')
        if isinstance(verified_evidence, list):
            evidence += "".join(f"{e}\n" for e in verified_evidence)
        elif isinstance(verified_evidence, str):
            evidence += f"{verified_evidence}\n"

        if evidence == evidence_header:
            evidence = evidence_header + no_evidence_text

        message = (
            f"{claim_prefix}{item['claim']}\n\n"
            f"{evidence}")
        return message

    def create_reeval_message(self, meta_message, synthesizer_res_summary, own_fc_res_summary, other_fc_res_summaries):
        """為 Fact Checker 建立重新評估的訊息。"""
        synthesizer_res_summary_json = extract_outermost_json(synthesizer_res_summary)
        synthesizer_data = json.loads(synthesizer_res_summary_json)

        own_fc_res_summary_json = extract_outermost_json(own_fc_res_summary)
        own_prediction, own_justification = extract_from_string(own_fc_res_summary_json, 'Prediction', 'Justification')

        all_predictions = [own_prediction]
        for summary in other_fc_res_summaries:
            summary_json = extract_outermost_json(summary)
            prediction, _ = extract_from_string(summary_json, 'Prediction', 'Justification')
            all_predictions.append(prediction)

        prediction_list = [p.lower().replace(' ', '-') for p in all_predictions if p]
        unique_predictions = list(set(prediction_list))

        dis_msg = ''
        if len(unique_predictions) == 2:
            dis_msg = f"and work towards reaching a consensus between '{unique_predictions[0]}' and '{unique_predictions[1]}'."
        elif len(unique_predictions) == 3:
            dis_msg = f"and work towards reaching a consensus among '{unique_predictions[0]}', '{unique_predictions[1]}', and '{unique_predictions[2]}'."
        
        message = (
            f"There are discrepancies in the prediction results from different Fact Checkers. "
            f"Please reflect on these differences {dis_msg}.\n"
            f"\n{meta_message}\n"
            f"Previous Prediction and Justification:\n\tPrediction:{own_prediction}\n\tJustification:{own_justification}\n\n"
            f"The Synthesizer has identified key areas where perspectives differ: '{synthesizer_data['feedback']}'.\n\n"
            f"Reflect on your previous prediction in light of this feedback. "
            f"If you believe your prediction should change, provide the new prediction and justification. "
            f"If your prediction remains the same, explain why."
        )

        return message, synthesizer_data