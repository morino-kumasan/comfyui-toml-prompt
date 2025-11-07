from typing import Any, cast

import os
import hashlib
import tomllib
import yaml

base_path: str = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "prompts")
)

type PromptDict = dict[str, Any | list[Any] | PromptDict]


class PromptFile:
    def __init__(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.text = f.read()
        self.path = path
        self.file_type = os.path.splitext(path)[1]

    def load(self) -> PromptDict:
        if self.file_type in [".toml", ".txt"]:
            return cast(PromptDict, tomllib.loads(self.text))
        elif self.file_type in [".yaml", ".yml"]:
            return yaml.safe_load(self.text)
        else:
            raise Exception(f"Unknown file type: {self.file_type}")


class PromptLoader:
    RETURN_TYPES = ("PROMPT_FILE",)
    OUTPUT_TOOLTIPS = ("A Prompt.",)
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    @classmethod
    def INPUT_TYPES(cls):
        files: list[str] = []
        for _, _, fs in os.walk(base_path):
            files += [f for f in fs if f.endswith((".txt", ".toml", ".yaml", ".yml"))]
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
        toml = PromptFile(path)
        return (toml,)
