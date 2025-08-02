import os
import hashlib
import tomllib

base_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "prompts"))

class TomlPrompt:
    def __init__(self, path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        self.prompt_dict = tomllib.loads(text)
        self.path = path

class PromptLoader:
    RETURN_TYPES = ("TOML_PROMPT", )
    OUTPUT_TOOLTIPS = ("A Prompt.", )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    @classmethod
    def INPUT_TYPES(s):
        files = []
        for (_, _, fs) in os.walk(base_path):
            files += [f for f in fs if f.endswith((".txt", ".toml"))]
        return {
            "required": {
                "file": (files, {"tooltip": "file name."}),
            }
        }

    @classmethod
    def IS_CHANGED(s, file):
        path = os.path.join(base_path, file)
        m = hashlib.sha256()
        with open(path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    def __init__(self):
        pass

    def load_prompt(self, file):
        path = os.path.join(base_path, file)
        toml = TomlPrompt(path)
        return (toml, )
