import re

class StringSub:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A text.", )
    FUNCTION = "sub"
    CATEGORY = "utils"
    DESCRIPTION = "Concat string."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"defaultInput": True, "multiline": True, "tooltip": "Text."}),
                "pattern": ("STRING", {"tooltip": "Matching regex pattern."}),
                "to": ("STRING", {"tooltip": "Matching text to."}),
            }
        }

    def sub(self, text, pattern, to):
        return (re.sub(pattern, to, text, flags=re.MULTILINE), )
