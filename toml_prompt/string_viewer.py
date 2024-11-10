class StringViewer:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A text.", )
    FUNCTION = "view_str"
    OUTPUT_NODE = True
    CATEGORY = "utils"
    DESCRIPTION = "String Viewer."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True, "multiline": True, "tooltip": "file name."}),
            }
        }

    def __init__(self):
        pass

    def view_str(self, text):
        return {"ui": { "text": [text] }, "result": (text,)}
