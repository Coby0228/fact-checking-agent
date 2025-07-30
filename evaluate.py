import json
import sys
import os
from collections import defaultdict

def normalize_value(value):
    """
    Converts a value to lowercase and normalizes variations like 'half-true' to 'half'.
    """
    if not isinstance(value, str):
        return ""
    
    lowered_value = value.lower()
    
    if 'half' in lowered_value:
        return 'half'
    if 'true' in lowered_value:
        return 'true'
    if 'false' in lowered_value:
        return 'false'
        
    return lowered_value

def evaluate_file(file_path):
    """
    Reads a JSON file, compares 'label' and 'prediction', and returns the result.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            original_label = data.get('label')
            prediction = data.get('prediction')

            if original_label is None or prediction is None:
                print(f"Skipping {os.path.basename(file_path)}: 'label' or 'prediction' not found.")
                return None

            normalized_label = normalize_value(original_label)
            normalized_prediction = normalize_value(prediction)

            result = 'correct' if normalized_label == normalized_prediction else 'incorrect'
            
            return {
                "event_id": data.get("event_id"),
                "label": original_label,
                "prediction": prediction,
                "evaluation_result": result,
                "claim": data.get("claim"),
                "justification": data.get("justification")
            }

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred with {file_path}: {e}")
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python evaluate.py <path_to_directory>")
        sys.exit(1)

    target_path = sys.argv[1]
    
    if not os.path.isdir(target_path):
        print(f"Error: Provided path is not a directory: {target_path}")
        sys.exit(1)

    print(f"Starting evaluation for directory: {target_path}")
    
    all_results = []
    for filename in os.listdir(target_path):
        if filename.endswith(".json"):
            file_path = os.path.join(target_path, filename)
            result = evaluate_file(file_path)
            if result:
                all_results.append(result)

    correct_count = sum(1 for r in all_results if r['evaluation_result'] == 'correct')
    total_count = len(all_results)
    accuracy = correct_count / total_count if total_count > 0 else 0

    # --- New code for Recall, Precision, F1-Score calculation ---
    # Calculate metrics for each class
    def calculate_metrics(class_name):
        tp = sum(1 for r in all_results if r['evaluation_result'] == 'correct' and normalize_value(r['label']) == class_name)
        fp = sum(1 for r in all_results if r['evaluation_result'] == 'incorrect' and normalize_value(r['prediction']) == class_name)
        fn = sum(1 for r in all_results if r['evaluation_result'] == 'incorrect' and normalize_value(r['label']) == class_name)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

        return {
            "precision": f"{precision:.2%}",
            "recall": f"{recall:.2%}",
            "f1_score": f"{f1_score:.2f}"
        }
    
    class_metrics = {
        "true": calculate_metrics("true"),
        "false": calculate_metrics("false"),
        "half": calculate_metrics("half")
    }
    # --- End of new code ---

    # Filter for incorrect results and select desired fields for details
    error_details = []
    for r in all_results:
        if r['evaluation_result'] == 'incorrect':
            error_details.append({
                "event_id": r.get("event_id"),
                "claim": r.get("claim"),
                "justification": r.get("justification"),
                "label": r.get("label"),
                "prediction": r.get("prediction")
            })

    summary = {
        "summary": {
            "total_files_evaluated": total_count,
            "correct_predictions": correct_count,
            "incorrect_predictions": total_count - correct_count,
            "accuracy": f"{accuracy:.2%}"
        },
        "class_metrics": class_metrics,
        "details": error_details # Use the filtered list of errors
    }

    output_filename = "results/main_result/evaluation_summary.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print("-" * 20)
    print("Evaluation complete.")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Results saved to {output_filename}")