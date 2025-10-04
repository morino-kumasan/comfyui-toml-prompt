from typing import Any

import os
import hashlib
import tomllib

base_path: str = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "prompts")
)


class TomlPrompt:
    def __init__(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.text = f.read()
        self.path = path

    def load(self) -> dict[str, Any]:
        return tomllib.loads(self.text)


class PromptLoader:
    RETURN_TYPES = ("TOML_PROMPT",)
    OUTPUT_TOOLTIPS = ("A Prompt.",)
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    @classmethod
    def INPUT_TYPES(cls):
        files: list[str] = []
        for _, _, fs in os.walk(base_path):
            files += [f for f in fs if f.endswith((".txt", ".toml"))]
        return {
            "required": {
                "file": (files, {"tooltip": "file name."}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, file: str):
        path = os.path.join(base_path, file)
        m = hashlib.sha256()
        with open(path, "rb") as f:
            m.update(f.read())
        return m.digest().hex()

    def __init__(self):
        pass

    def load_prompt(self, file: str):
        path = os.path.join(base_path, file)
        toml = TomlPrompt(path)
        return (toml,)
