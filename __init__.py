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

    RETURN_TYPES = ("MODEL", "CLIP", *["STRING" for i in range(0, MAX_LOAD_LORA)])
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", *["Loaded LoRA names" for i in range(0, MAX_LOAD_LORA)])
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

        return (r_model, r_clip, *[
            (os.path.basename(kwargs[f"lora_name_{i}"]) if abs(kwargs[f"strength_{i}"]) >= 1e-10 else "")
            for i in range(0, MAX_LOAD_LORA)
        ])

class PromptPicker:
    def __init__(self):
        self.encoder = [CLIPTextEncode() for i in range(0, MAX_LOAD_LORA)]
        self.concat = [ConditioningConcat() for i in range(0, MAX_LOAD_LORA - 1)]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": { k: v for k, v in [
                ("clip", ("CLIP", {"tooltip": "The CLIP model."})),
                ("select_type", (["key_name", "random"], {"tooltip": "Select by Key Name or Random"})),
            ] + [
                (f"key_name_{i}", ("STRING", {"tooltip": "Select Key Name"})) for i in range(0, MAX_LOAD_LORA)
            ] + [
                ("text", ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "Prompt Separated by Key Name Comment (#[keyname])"})),
            ]}
        }

    RETURN_TYPES = ("CONDITIONING", )
    OUTPUT_TOOLTIPS = ("A Conditioning containing a text by key_name.", )
    FUNCTION = "load_prompt"

    CATEGORY = "conditioning"
    DESCRIPTION = "LoRA prompt load."

    def load_prompt(self, clip, select_type, text, **kwargs):
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

        # Pick Random and Encode Prompt
        if select_type == "random":
            prompt = random.choice([v for v in r_text.values()])
            cond = self.encoder[0].encode(clip, prompt)[0]
            return (cond, )

        # Pick key_name and Encode Prompt
        r = None
        for i in range(0, MAX_LOAD_LORA):
            prompt = r_text.get(kwargs[f"key_name_{i}"], "")
            if prompt == "":
                continue
            cond = self.encoder[i].encode(clip, prompt)[0]
            if r is None:
                r = cond
            else:
                r = self.concat[i].concat(cond, r)[0]

        if r is None:
            r = self.encoder[0].encode(clip, "")[0]

        return (r, )

NODE_CLASS_MAPPINGS = {
    "MultipleLoraLoader": MultipleLoraLoader,
    "PromptPicker": PromptPicker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultipleLoraLoader": "Load Multiple Loras With Output Lora Name",
    "PromptPicker": "Load Prompt by Key",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
