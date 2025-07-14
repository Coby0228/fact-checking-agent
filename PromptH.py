import os

class PromptHandler:
    def __init__(self):
        self.prompt_directory = self.get_prompt_directory()
        self.prompts = {
            'Evidence_Extraction_ch': self.load_prompt('Evidence_Extraction_ch'),
            'Evidence_Extraction_en': self.load_prompt('Evidence_Extraction_en'),
            'Evidence_Verifier_ch': self.load_prompt('Evidence_Verifier_ch'),
            'Evidence_Verifier_en': self.load_prompt('Evidence_Verifier_en'),
            'Finalizer_ch': self.load_prompt('Finalizer_ch'),
            'Finalizer_en': self.load_prompt('Finalizer_en'),
            'Fact_Checker_M_ch': self.load_prompt('Fact_Checker_M_ch'),
            'Fact_Checker_M_en': self.load_prompt('Fact_Checker_M_en'),
            'Fact_Checker_N_ch': self.load_prompt('Fact_Checker_N_ch'),
            'Fact_Checker_N_en': self.load_prompt('Fact_Checker_N_en'),
            'Fact_Checker_P_ch': self.load_prompt('Fact_Checker_P_ch'),
            'Fact_Checker_P_en': self.load_prompt('Fact_Checker_P_en'),
            'Synthesizer_ch': self.load_prompt('Synthesizer_ch'),
            'Synthesizer_en': self.load_prompt('Synthesizer_en')
        }

    def get_prompt_directory(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_directory = os.path.join(current_dir, 'prompt')
        return prompt_directory

    def load_prompt(self, prompt_name):
        file_path = os.path.join(self.prompt_directory, prompt_name)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return f"Prompt file {prompt_name} not found."

    def handle_prompt(self, prompt_name):
        if prompt_name in self.prompts:
            prompt_content = self.prompts[prompt_name]
            return f"{prompt_content}"
        else:
            return "Invalid prompt name"

if __name__ == "__main__":
    # Example usage
    handler = PromptHandler()
    print(handler.handle_prompt('Evidence_Extraction_ch'))
