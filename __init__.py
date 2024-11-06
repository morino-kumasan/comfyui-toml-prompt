import re
import random
from functools import reduce

from folder_paths import get_filename_list
from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat

MAX_LOAD_LORA = 10

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
            (kwargs[f"lora_name_{i}"] if abs(kwargs[f"strength_{i}"]) >= 1e-10 else "")
            for i in range(0, MAX_LOAD_LORA)
        ]))

class PromptPicker:
    def __init__(self):
        self.encoder = CLIPTextEncode()
        self.concat = ConditioningConcat()
        self.loader = [LoraLoader() for i in range(0, MAX_LOAD_LORA)]

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "The diffusion model."}),
                "clip": ("CLIP", {"tooltip": "The CLIP model."}),
                "key_name_list": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "Select Key Name"}),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "Prompt Separated by Key Name Comment (#[keyname])"}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "STRING")
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", "A Conditioning containing a text by key_name.", "Loaded LoRA name list")
    FUNCTION = "load_prompt"

    CATEGORY = "conditioning"
    DESCRIPTION = "LoRA prompt load."

    def load_prompt(self, model, clip, text, key_name_list):
        sep = '.'
        key = ""
        before_end = 0
        prompt_dict = {}

        # Find key_name
        for m in re.finditer(r'^#\[(.+)\]$', text, flags=re.MULTILINE):
            beg, end = (m.start(), m.end())
            if beg != before_end and key != "":
                prompt_dict[key] = text[before_end:beg]
            key = m.group(1)
            before_end = end

        if before_end != len(text):
            prompt_dict[key] = text[before_end:]

        r_cond = None
        r_model = model
        r_clip = clip
        r_loras = ""
        keys = prompt_dict.keys()
        lora_i = 0

        # Pick key_name and Encode Prompt
        for key in key_name_list.splitlines():
            key = key.strip()
            if key == "":
                continue

            # Collect Prompts
            key_parts = key.split(sep)
            if key_parts[-1] == '?':
                prefix = sep.join(key_parts[:-1] + [''])
                random_keys = [key for key in keys if key if keys and key.startswith(prefix) and not key.endswith("*")]
                available_keys = sorted([sep.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))]) + [random.choice(random_keys)]
                prompts = [','.join([prompt_dict[key] for key in available_keys if key in keys])]
            else:
                available_keys = sorted([sep.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))]) + [key]
                prompts = [','.join([prompt_dict[key] for key in available_keys if key in keys])]

            # Encode Prompts
            for prompt in prompts:
                prompt = prompt.strip()
                if prompt == "":
                    continue

                loras = re.findall(r'<lora:([^:]+):([0-9.]+)>', prompt)
                for lora_name, strength in loras:
                    r_model, r_clip = self.loader[lora_i].load_lora(r_model, r_clip, lora_name, float(strength), float(strength))
                    lora_i += 1
                    r_loras += lora_name + '\n'
                    print(f"lora loaded: {lora_name}: {strength}")
                prompt = re.sub(r'<lora:([^:]+):([0-9.]+)>', '', prompt)

                cond = self.encoder.encode(clip, prompt)[0]
                if r_cond is None:
                    r_cond = cond
                else:
                    r_cond = self.concat.concat(cond, r_cond)[0]

        if r_cond is None:
            r_cond = self.encoder.encode(clip, "")[0]

        return (r_model, r_clip, r_cond, r_loras)

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

class MultilineStringConcat:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_from": ("STRING", {"defaultInput": True, "multiline": True, "tooltip": "Text from."}),
                "text_to": ("STRING", {"defaultInput": True, "multiline": True, "tooltip": "Text to."}),
            }
        }

    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A text.", )
    FUNCTION = "concat"

    CATEGORY = "utils"
    DESCRIPTION = "Concat string."

    def concat(self, text_from, text_to):
        return (text_to + '\n' + text_from, )

class StringSub:
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

    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A text.", )
    FUNCTION = "sub"

    CATEGORY = "utils"
    DESCRIPTION = "Concat string."

    def sub(self, text, pattern, to):
        return (re.sub(pattern, to, text, flags=re.MULTILINE), )

NODE_CLASS_MAPPINGS = {
    "MultipleLoraLoader": MultipleLoraLoader,
    "PromptPicker": PromptPicker,
    "PromptHolder": PromptHolder,
    "MultilineStringConcat": MultilineStringConcat,
    "StringSub": StringSub,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultipleLoraLoader": "MultipleLoraLoader",
    "PromptPicker": "PromptPicker",
    "PromptHolder": "PromptHolder",
    "MultilineStringConcat": "MultilineStringConcat",
    "StringSub": "StringSub",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
