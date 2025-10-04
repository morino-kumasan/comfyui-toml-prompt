from typing import cast, Any
from . import InputTypesFuncResult

import sys, os, json

try:
    import folder_paths  # pyright: ignore
    from PIL import Image  # pyright: ignore
except ImportError:
    pass

class StringPicker:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "pick"
    CATEGORY = "utils"
    DESCRIPTION = "Get STRING from workflow in Image to be loaded from LoadImage."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "image": ("IMAGE", {"forceInput": True, "tooltip": "from LoadImage."}),
                "target_title": ("STRING", {"defaultInput": True, "multiline": False}),
                "image_index": (
                    "INT",
                    {"default": 0, "tooltip": "filename index of widgets_values."},
                ),
                "string_index": (
                    "INT",
                    {"default": 0, "tooltip": "string index of widgets_values."},
                ),
            },
            "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def __init__(self):
        pass

    def pick(
        self,
        image: Any,
        target_title: str,
        image_index: int,
        string_index: int,
        unique_id: str | None = None,
        extra_pnginfo: dict[str, Any] | None = None,
    ):
        if extra_pnginfo is not None and unique_id is not None:
            # 自ノードからIMAGEのリンク先取得
            node = [
                node
                for node in extra_pnginfo["workflow"]["nodes"]
                if node["id"] == int(unique_id)
            ][0]
            link_id = [
                input["link"] for input in node["inputs"] if input["type"] == "IMAGE"
            ][0]
            node_id = [
                link[1]
                for link in extra_pnginfo["workflow"]["links"]
                if link[0] == link_id
            ][0]
            node = [
                node
                for node in extra_pnginfo["workflow"]["nodes"]
                if node["id"] == node_id
            ][0]

            # LoadImageノードからfilenameを取得
            dirname = cast(str, folder_paths.get_input_directory())  # type: ignore
            filename = node["widgets_values"][image_index]

            # workflow読み込み
            img = Image.open(os.path.join(dirname, filename))  # type: ignore
            img_workflow = json.loads(img.info["workflow"])  # type: ignore
            img.close()  # type: ignore

            # workflowからtitleが一致するSTRINGを取り出し
            node = [
                node
                for node in img_workflow["nodes"]
                if node.get("title", "") == target_title
            ][0]
            return (node["widgets_values"][string_index],)
        return ("",)


class JsonExtractString:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING.",)
    FUNCTION = "extract"
    CATEGORY = "utils"
    DESCRIPTION = "Extract string from json text."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("STRING",),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text: str, path: str, default: str):
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
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("INT", {"min": -sys.maxsize, "max": sys.maxsize}),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text: str, path: str, default: int):
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
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "json_text": ("STRING",),
                "path": ("STRING", {"tooltip": "period separated path to json value"}),
                "default": ("FLOAT", {"min": -sys.maxsize, "max": sys.maxsize}),
            },
        }

    def __init__(self):
        pass

    def extract(self, json_text: str, path: str, default: float):
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
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "primary": ("LATENT",),
                "secondary": ("LATENT",),
            },
        }

    def __init__(self):
        pass

    def select(self, primary: Any = None, secondary: Any = None):
        return (primary or secondary,)


class StringSelector:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "STRING Selector."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "primary": ("STRING", {"forceInput": True, "multiline": True}),
                "secondary": ("STRING", {"forceInput": True, "multiline": True}),
            },
        }

    def __init__(self):
        pass

    def select(self, primary: str | None = None, secondary: str | None = None):
        return (primary or secondary,)


class IntSelector:
    RETURN_TYPES = ("INT",)
    OUTPUT_TOOLTIPS = ("INT not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "INT Selector."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "optional": {
                "primary": (
                    "INT",
                    {"forceInput": True, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
                "secondary": (
                    "INT",
                    {"forceInput": True, "min": 0, "max": 0xFFFFFFFFFFFFFFFF},
                ),
            },
        }

    def __init__(self):
        pass

    def select(self, primary: int | None = None, secondary: int | None = None):
        return (primary or secondary,)


class StringConcat:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("A text.",)
    FUNCTION = "concat"
    CATEGORY = "utils"
    DESCRIPTION = "Concat string."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "text_from": (
                    "STRING",
                    {"defaultInput": True, "multiline": True, "tooltip": "Text from."},
                ),
                "text_to": (
                    "STRING",
                    {"defaultInput": True, "multiline": True, "tooltip": "Text to."},
                ),
                "sep": ("STRING", {"multiline": True, "tooltip": "Join separator."}),
            }
        }

    def __init__(self):
        pass

    def concat(self, text_from: str, text_to: str, sep: str):
        return (text_to + sep + text_from,)


class StringConcatInt:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("A text.",)
    FUNCTION = "concat"
    CATEGORY = "utils"
    DESCRIPTION = "Concat string and int."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "text_from": (
                    "INT",
                    {"min": -sys.maxsize, "max": sys.maxsize, "tooltip": "Text to."},
                ),
                "text_to": (
                    "STRING",
                    {"defaultInput": True, "multiline": True, "tooltip": "Text from."},
                ),
                "sep": ("STRING", {"multiline": True, "tooltip": "Join separator."}),
            }
        }

    def __init__(self):
        pass

    def concat(self, text_from: int, text_to: str, sep: str):
        return (text_to + sep + str(text_from),)


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
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            }
        }

    def generate(self, seed: int):
        return (seed,)
