import os

class PromptHandler:
    def __init__(self):
        self.prompt_directory = self.get_prompt_directory()
        self.prompts = {
            'Evidence_Extractor_System': self.load_prompt('Evidence_Extractor_System'),
            'Evidence_Extractor_User': self.load_prompt('Evidence_Extractor_User'),
            'Evidence_Verifier_System': self.load_prompt('Evidence_Verifier_System'),
            'Evidence_Verifier_User': self.load_prompt('Evidence_Verifier_User'),
            
            'Finalizer_en': self.load_prompt('Finalizer_en'),
            'Fact_Checker_M_en': self.load_prompt('Fact_Checker_M_en'),
            'Fact_Checker_N_en': self.load_prompt('Fact_Checker_N_en'),
            'Fact_Checker_P_en': self.load_prompt('Fact_Checker_P_en'),
            'Synthesizer_en': self.load_prompt('Synthesizer_en')
        }

    def get_prompt_directory(self):
        return os.path.dirname(os.path.abspath(__file__))

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
