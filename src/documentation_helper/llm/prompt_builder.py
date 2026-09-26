class PromptBuilder:
    system_prompt = """Enter default prompt"""

    def __init__(self, user_prompt: str):
        self.user_prompt = user_prompt

    def build(self):
        return str(self.system_prompt + self.user_prompt)
