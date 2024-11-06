import re
import os
import random
from functools import reduce

from folder_paths import get_filename_list
from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat

MAX_LOAD_LORA = 5

class MultipleLoraLoader:
    def __init__(self):
        self.loader = [LoraLoader() for i in range(0, MAX_LOAD_LORA)]

    @classmethod
    def INPUT_TYPES(s):
        lora_file_list = get_filename_list("loras")
        return {
            "required": { k: v for k, v in [
                ("model", ("MODEL", {"tooltip": "The diffusion model."})),
                ("clip", ("CLIP", {"tooltip": "The CLIP model."})),
            ] + reduce(lambda x, y: x + y, [[
                (f"lora_name_{i}", (lora_file_list, {"tooltip": "LoRA file name."})),
                (f"strength_{i}", ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01, "tooltip": "Modify strength."})),
            ] for i in range(0, MAX_LOAD_LORA)]) }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", "Loaded LoRA name list")
    FUNCTION = "load_lora"

    CATEGORY = "loaders"
    DESCRIPTION = "LoRAs load."

    def load_lora(self, model, clip, **kwargs):
        r_model = model
        r_clip = clip
        for i in range(0, MAX_LOAD_LORA):
            lora_name = kwargs[f"lora_name_{i}"]
            strength = kwargs[f"strength_{i}"]
            if abs(strength) >= 1e-10:
                r_model, r_clip = self.loader[i].load_lora(r_model, r_clip, lora_name, strength, strength)

        return (r_model, r_clip, '\n'.join([
            (os.path.basename(kwargs[f"lora_name_{i}"]) if abs(kwargs[f"strength_{i}"]) >= 1e-10 else "")
            for i in range(0, MAX_LOAD_LORA)
        ]))

class PromptPicker:
    def __init__(self):
        self.encoder = CLIPTextEncode()
        self.concat = ConditioningConcat()

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "clip": ("CLIP", {"tooltip": "The CLIP model."}),
                "key_name_list": ("STRING", {"multiline": True, "tooltip": "Select Key Name"}),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "Prompt Separated by Key Name Comment (#[keyname])"}),
            }
        }

    RETURN_TYPES = ("CONDITIONING", )
    OUTPUT_TOOLTIPS = ("A Conditioning containing a text by key_name.", )
    FUNCTION = "load_prompt"

    CATEGORY = "conditioning"
    DESCRIPTION = "LoRA prompt load."

    def load_prompt(self, clip, text, key_name_list):
        key = ""
        before_end = 0
        r_text = {}

        # Find key_name
        for m in re.finditer(r'^#\[(.+)\]$', text, flags=re.MULTILINE):
            beg, end = (m.start(), m.end())
            if beg != before_end and key != "":
                r_text[key] = text[before_end:beg]
            key = m.group(1)
            before_end = end

        if before_end != len(text):
            r_text[key] = text[before_end:]

        # Pick key_name and Encode Prompt
        r = None
        keys = r_text.keys()
        sep = '.'
        for key in key_name_list.splitlines():
            key = key.strip()
            if key == "":
                continue

            key_parts = key.split(sep)
            if key_parts[-1] == '?':
                prefix = sep.join(key_parts[:-1] + [''])
                random_keys = [key for key in keys if key if keys and key.startswith(prefix) and not key.endswith("*")]
                available_keys = sorted([sep.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))]) + [random.choice(random_keys)]
                prompts = [','.join([r_text[key] for key in available_keys if key in keys])]
            else:
                available_keys = sorted([sep.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))]) + [key]
                prompts = [','.join([r_text[key] for key in available_keys if key in keys])]

            for prompt in prompts:
                prompt = prompt.strip()
                if prompt == "":
                    continue
                cond = self.encoder.encode(clip, prompt)[0]
                if r is None:
                    r = cond
                else:
                    r = self.concat.concat(cond, r)[0]

        if r is None:
            r = self.encoder.encode(clip, "")[0]

        return (r, )

class PromptHolder:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "Prompt Holder."}),
            }
        }

    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A Prompt.", )
    FUNCTION = "load_prompt"

    CATEGORY = "utils"
    DESCRIPTION = "Prompt holder."

    def load_prompt(self, text):
        return (text, )

NODE_CLASS_MAPPINGS = {
    "MultipleLoraLoader": MultipleLoraLoader,
    "PromptPicker": PromptPicker,
    "PromptHolder": PromptHolder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultipleLoraLoader": "Load Multiple Loras With Output Lora Name",
    "PromptPicker": "Load Prompt by Key",
    "PromptHolder": "Hold Prompt",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
