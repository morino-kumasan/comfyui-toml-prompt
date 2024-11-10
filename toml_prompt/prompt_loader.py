import os
import hashlib

from folder_paths import get_user_directory

class PromptLoader:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A Prompt.", )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "file": ("STRING", {"tooltip": "file name."}),
            }
        }

    @classmethod
    def IS_CHANGED(s, file):
        path = os.path.join(get_user_directory(), file)
        m = hashlib.sha256()
        with open(path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    def __init__(self):
        pass

    def load_prompt(self, file):
        path = os.path.expanduser(file)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return (text, )
