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
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    def __init__(self):
        pass

    def view_str(self, text, unique_id=None, extra_pnginfo=None):
        if extra_pnginfo is not None:
            node = [node for node in extra_pnginfo["workflow"]["nodes"] if node["id"] == int(unique_id)][0]
            node["widgets_values"][1] = text
        return {"ui": { "text": [text] }}
