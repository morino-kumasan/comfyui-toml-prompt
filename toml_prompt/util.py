import sys, os, json, re
import folder_paths
from PIL import Image

class StringPicker:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "pick"
    CATEGORY = "utils"
    DESCRIPTION = "Get STRING from workflow in Image to be loaded from LoadImage."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {"forceInput": True, "tooltip": "from LoadImage."}),
                "target_title": ("STRING", {"defaultInput": True, "multiline": False}),
                "image_index": ("INT", {"default": 0, "tooltip": "filename index of widgets_values."}),
                "string_index": ("INT", {"default": 0, "tooltip": "string index of widgets_values."}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    def __init__(self):
        pass

    def pick(self, image, target_title, image_index, string_index, unique_id=None, extra_pnginfo=None):
        if extra_pnginfo:
            # 自ノードからIMAGEのリンク先取得
            node = [node for node in extra_pnginfo["workflow"]["nodes"] if node["id"] == int(unique_id)][0]
            link_id = [input["link"] for input in node["inputs"] if input["type"] == "IMAGE"][0]
            node_id = [link[1] for link in extra_pnginfo["workflow"]["links"] if link[0] == link_id][0]
            node = [node for node in extra_pnginfo["workflow"]["nodes"] if node["id"] == node_id][0]

            # LoadImageノードからfilenameを取得
            dirname = folder_paths.get_input_directory()
            filename = node["widgets_values"][image_index]

            # workflow読み込み
            img = Image.open(os.path.join(dirname, filename))
            img_workflow = json.loads(img.info["workflow"])
            img.close()

            # workflowからtitleが一致するSTRINGを取り出し
            node = [node for node in img_workflow["nodes"] if node.get("title", "") == target_title][0]
            return (node["widgets_values"][string_index],)
        return ("",)

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

class LatentSelector:
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("LATENT not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "Latent Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("LATENT",),
                "secondary": ("LATENT",),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)

class StringSelector:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "STRING Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("STRING", {"forceInput": True, "multiline": True}),
                "secondary": ("STRING", {"forceInput": True, "multiline": True}),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)

class IntSelector:
    RETURN_TYPES = ("INT",)
    OUTPUT_TOOLTIPS = ("INT not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "INT Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("INT", {"forceInput": True, "min": 0, "max": 0xffffffffffffffff}),
                "secondary": ("INT", {"forceInput": True, "min": 0, "max": 0xffffffffffffffff}),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)

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

# Primitiveだとうまくいかない場合用
class SeedGenerator:
    RETURN_TYPES = ("INT",)
    OUTPUT_TOOLTIPS = ("INT.",)
    FUNCTION = "generate"
    CATEGORY = "utils"
    DESCRIPTION = "INT Primitive for optional force input."

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
            }
        }

    def generate(self, seed):
        return (seed,)
