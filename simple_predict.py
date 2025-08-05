import os
import json
from pathlib import Path
from openai import OpenAI
from sklearn.metrics import accuracy_score, classification_report

from modules.utils import load_data, save_data_to_json, create_argument_parser
from modules.paths import ROOT

def evaluate(results):
    """
    Evaluates the prediction results against the ground truth labels.

    Args:
        results (list): A list of dictionaries, each containing 'prediction' and 'label'.
    """
    # Map CFEVER labels to prediction labels for comparison
    label_map = {
        "SUPPORTS": "true",
        "REFUTES": "false",
    }

    predictions = [r['prediction'] for r in results]
    # Map ground truth labels to the same format as predictions
    ground_truth = [label_map.get(r['label'], 'unknown') for r in results]
    
    # Filter out items where the label couldn't be mapped
    valid_indices = [i for i, label in enumerate(ground_truth) if label != 'unknown']
    if len(valid_indices) < len(ground_truth):
        print(f"Warning: {len(ground_truth) - len(valid_indices)} items had unknown labels and were excluded from evaluation.")
    
    predictions = [predictions[i] for i in valid_indices]
    ground_truth = [ground_truth[i] for i in valid_indices]

    if not predictions:
        print("No valid predictions to evaluate.")
        return

    print("\n--- Evaluation Report ---")
    
    # Calculate and print accuracy
    accuracy = accuracy_score(ground_truth, predictions)
    print(f"Accuracy: {accuracy:.4f}")
    
    # Print detailed classification report
    # Get all unique labels present in either ground_truth or predictions
    labels = sorted(list(set(ground_truth) | set(predictions)))
    print(classification_report(ground_truth, predictions, labels=labels, zero_division=0))
    print("-------------------------\n")


def main():
    """
    Main function to load data, process claims with an LLM, save results, and evaluate.
    """
    parser = create_argument_parser()
    parser.set_defaults(
        data_dir=ROOT / 'dataset',
        output_dir=ROOT / 'results' / 'simple_prediction',
        dataset='CFEVER',
        task=''
    )
    args = parser.parse_args()

    # 1. Setup environment
    output_dir = Path(args.output_dir) / args.dataset / args.task
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE")
    )

    # 2. Load data
    data = load_data(args.data_dir, args.dataset, args.task, agent_name='Evidence_Extractor')
    if not data:
        print("No data loaded. Exiting.")
        return

    # 3. Define System Prompt
    system_message = (
        "You are a fact-checker. Your task is to evaluate the authenticity of a given claim. "
        "You must respond with a JSON object containing your 'prediction' and 'justification'. "
        "The prediction must be one of 'true' or 'false'. "
        "The justification should briefly explain your reasoning."
    )

    all_results_for_eval = []

    # 4. Process each item
    for i, item in enumerate(data, 1):
        claim = item.get('claim')
        if not claim:
            continue

        print(f"Processing item {i}/{len(data)}: {item.get('event_id', 'N/A')}")

        try:
            # Initiate chat to get prediction
            response = client.chat.completions.create(
                model=args.model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Claim: {claim}"}
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            
            # Parse the result
            result_json = json.loads(response.choices[0].message.content)
            prediction = result_json.get('prediction', 'error')
            justification = result_json.get('justification', 'error')

        except Exception as e:
            print(f"An error occurred while processing item {item.get('event_id', i)}: {e}")
            prediction = "error"
            justification = str(e)

        # Prepare data for saving
        result_data = {
            'event_id': item.get('event_id'),
            'claim': claim,
            'label': str(item.get('label')),
            'prediction': prediction,
            'justification': justification
        }
        all_results_for_eval.append(result_data)

        # Save the result
        output_file = output_dir / f"{item.get('event_id', i)}.json"
        save_data_to_json(result_data, output_file)
        print(f"✅ Result saved to {output_file}")

    # 5. Evaluate the results
    if all_results_for_eval:
        evaluate(all_results_for_eval)

if __name__ == "__main__":
    main()