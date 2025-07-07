import sys, json

class JsonExtractString:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING.",)
    FUNCTION = "extract"
    CATEGORY = "utils"
    DESCRIPTION = "Extract string from json text."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("STRING",),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text, path, default):
        r = json.loads(json_text)
        for key in path.split("."):
            if key not in r:
                return (default,)
            r = r[key]
        return (str(r),)

class JsonExtractInt:
    RETURN_TYPES = ("INT",)
    OUTPUT_TOOLTIPS = ("INT.",)
    FUNCTION = "extract"
    CATEGORY = "utils"
    DESCRIPTION = "Extract integer from json text."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("INT", {"min": -sys.maxsize, "max": sys.maxsize}),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text, path, default):
        r = json.loads(json_text)
        for key in path.split("."):
            if key not in r:
                return (default,)
            r = r[key]
        return (int(r),)

class JsonExtractFloat:
    RETURN_TYPES = ("FLOAT",)
    OUTPUT_TOOLTIPS = ("FLOAT.",)
    FUNCTION = "extract"
    CATEGORY = "utils"
    DESCRIPTION = "Extract float from json text."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("FLOAT", {"min": -sys.maxsize, "max": sys.maxsize}),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text, path, default):
        r = json.loads(json_text)
        for key in path.split("."):
            if key not in r:
                return (default,)
            r = r[key]
        return (float(r),)
