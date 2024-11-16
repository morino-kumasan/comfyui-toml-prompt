import os
from functools import reduce

from folder_paths import get_filename_list

class MultipleLoraTagLoader:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("LoRA tag list separated by line break", )
    FUNCTION = "create_tags"
    CATEGORY = "utils"
    DESCRIPTION = "Create LoRA tags."
    MAX_TAG_LORA = 10

    @classmethod
    def INPUT_TYPES(s):
        lora_file_list = [f.replace(os.path.sep, "/") for f in get_filename_list("loras")]
        return {
            "required": { k: v for k, v in reduce(lambda x, y: x + y, [[
                (f"lora_name_{i}", (["[none]"] + lora_file_list, {"tooltip": "LoRA file name."})),
                (f"strength_{i}", ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01, "tooltip": "Modify strength."})),
            ] for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA)]) }
        }

    def __init__(self):
        pass

    def create_tags(self, **kwargs):
        return ('\n'.join([
            "<lora:{}:{:2f}>".format(kwargs[f"lora_name_{i}"], kwargs[f"strength_{i}"])
            for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA)
            if abs(kwargs[f"strength_{i}"]) >= 1e-10 and kwargs[f"lora_name_{i}"] != "[none]"
        ]), )
