import subprocess
import sys
import os
import time

def run_script(script_name):
    """
    Executes a Python script using the same interpreter and handles the output.
    """
    # Check if the script file exists before trying to run it.
    if not os.path.exists(script_name):
        print(f"Error: Script '{script_name}' not found.")
        sys.exit(1)
        
    print(f"--- Running {script_name} ---")
    start_time = time.time()
    try:
        # Use sys.executable to ensure the script is run with the same Python interpreter.
        process = subprocess.run(
            [sys.executable, script_name],
            check=True,          # Raise CalledProcessError if the script returns a non-zero exit code.
            text=True            # Decode stdout and stderr as text.
        )
        end_time = time.time()
        print(f"--- Successfully finished {script_name} in {end_time - start_time:.2f} seconds ---")
        if process.stdout:
            print("Output:")
            print(process.stdout)
        if process.stderr:
            print("Error Output (stderr):")
            print(process.stderr)

    except subprocess.CalledProcessError as e:
        print(f"--- An error occurred while running {script_name} ---")
        print(f"Return Code: {e.returncode}")
        if e.stdout:
            print("Output (stdout):")
            print(e.stdout)
        if e.stderr:
            print("Error Output (stderr):")
            print(e.stderr)
        # Exit the main script if a sub-script fails.
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: The script '{script_name}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    """
    Main function to define and run the sequence of scripts.
    """
    pipeline_start_time = time.time()
    # The order of scripts to be executed, as per the user's request.
    scripts_to_run = [
        "evidence_extraction.py",
        "evidence_verifier.py",
        "get_prediction.py",
    ]

    for script in scripts_to_run:
        run_script(script)

    pipeline_end_time = time.time()
    total_time = pipeline_end_time - pipeline_start_time
    print(f"\n--- All scripts executed successfully. Total execution time: {total_time:.2f} seconds ---")

if __name__ == "__main__":
    main()