class StringConcat:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A text.", )
    FUNCTION = "concat"
    CATEGORY = "utils"
    DESCRIPTION = "Concat string."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_from": ("STRING", {"defaultInput": True, "multiline": True, "tooltip": "Text from."}),
                "text_to": ("STRING", {"defaultInput": True, "multiline": True, "tooltip": "Text to."}),
                "sep": ("STRING", {"multiline": True, "tooltip": "Join separator."}),
            }
        }

    def __init__(self):
        pass

    def concat(self, text_from, text_to, sep):
        return (text_to + sep + text_from, )
