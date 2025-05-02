import json


class Prompts:
    def __init__(self, path: str):
        with open(path) as file:
            self.prompts: dict[str, str] = json.load(file)

    def get_prompt(self, prompt_name: str) -> str:
        return self.prompts[prompt_name]
