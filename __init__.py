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
    SEPARATOR = "."

    def build_prompt_dict(self, text):
        r = {}
        before_end = 0
        before_key = ""
        for m in re.finditer(r'^#\[(.+)\]$', text, flags=re.MULTILINE):
            beg, end = (m.start(), m.end())
            if beg != before_end and before_key != "":
                r[before_key] = text[before_end:beg]
            before_key = m.group(1)
            before_end = end

        if before_end != len(text):
            r[before_key] = text[before_end:]
        
        return r

    def collect_prompts(self, prompt_dict, key):
        keys = prompt_dict.keys()
        key_parts = key.split(PromptPicker.SEPARATOR)
        if key_parts[-1] == '?':
            prefix = PromptPicker.SEPARATOR.join(key_parts[:-1] + [''])
            random_keys = [key for key in keys if key if keys and key.startswith(prefix) and not key.endswith("*")]
            available_keys = sorted([PromptPicker.SEPARATOR.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))])
            if len(random_keys) == 0:
                print("Random Keys Not Found:", prefix, random_keys, keys)
            else:
                available_keys += [random.choice(random_keys)]
            prompts = [','.join([prompt_dict[key] for key in available_keys if key in keys])]
        else:
            available_keys = sorted([PromptPicker.SEPARATOR.join(key_parts[:l] + ["*"]) for l in range(0, len(key_parts))]) + [key]
            prompts = [','.join([prompt_dict[key] for key in available_keys if key in keys])]
        return prompts

    def load_lora_from_prompt(self, prompt, model, clip, lora_i):
        r_model = model
        r_clip = clip
        loras = []
        for lora_name, strength in re.findall(r'<lora:([^:]+):([0-9.]+)>', prompt):
            i = len(loras) + lora_i
            r_model, r_clip = self.loader[i].load_lora(r_model, r_clip, lora_name, float(strength), float(strength))
            loras += [lora_name]
            print(f"lora loaded[{i}]: {lora_name}: {strength}")
        prompt = re.sub(r'<lora:([^:]+):([0-9.]+)>', '', prompt)
        return (r_model, r_clip, loras)

    def encode_prompts(self, prompts, model, clip, cond, loras, lora_i):
        r_model = model
        r_clip = clip
        r_cond = cond
        for prompt in prompts:
            prompt = prompt.strip()
            if prompt == "":
                continue

            r_model, r_clip, loaded_loras = self.load_lora_from_prompt(prompt, r_model, r_clip, lora_i)
            lora_i += len(loaded_loras)
            loras += loaded_loras

            cond = self.encoder.encode(r_clip, prompt)[0]
            if r_cond is None:
                r_cond = cond
            else:
                r_cond = self.concat.concat(cond, r_cond)[0]
        return (r_model, r_clip, r_cond, loras, lora_i)

    def load_prompt(self, model, clip, text, key_name_list):
        r_cond = None
        r_model = model
        r_clip = clip
        r_loras = []
        lora_i = 0
        prompt_dict = self.build_prompt_dict(text)
        for key in key_name_list.splitlines():
            key = key.strip()
            if key == "":
                continue
            prompts = self.collect_prompts(prompt_dict, key)
            r_model, r_clip, r_cond, r_loras, lora_i = self.encode_prompts(prompts, r_model, r_clip, r_cond, r_loras, lora_i)

        if r_cond is None:
            r_cond = self.encoder.encode(clip, "")[0]

        return (r_model, r_clip, r_cond, '\n'.join(r_loras))

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
