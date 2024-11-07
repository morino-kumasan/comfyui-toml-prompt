import os
import re
import hashlib
import random
import time
import toml
from functools import reduce

from folder_paths import get_filename_list, recursive_search, get_user_directory
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
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Random seed."}),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "Prompt Separated by Key Name Comment (#[keyname])"}),
            }
        }

    @classmethod
    def IS_CHANGED(s, *args, **kwargs):
        return time.time()

    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "STRING", "INT")
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", "A Conditioning containing a text by key_name.", "Loaded LoRA name list", "Random seed")
    FUNCTION = "load_prompt"

    CATEGORY = "conditioning"
    DESCRIPTION = "LoRA prompt load."

    def collect_prompts(self, prompt_dict, key_str):
        l = [(0, 0)] + [(m.start() + 1, m.end()) for m in re.finditer(r"[^\\]\.", key_str)] + [(len(key_str), len(key_str))]
        keys = [re.sub(r"\\\.", ".", key_str[l[i][1]:l[i + 1][0]]) for i in range(0, len(l) - 1)]

        r = []
        d = prompt_dict
        for i, key in enumerate(keys):
            if key == "?" or key == "??":
                assert(key == "?" or i == (len(keys) - 1))
                recur = key == "??"
                rand_keys = [k for k in d.keys() if k != "_t"]
                if len(rand_keys) == 0:
                    return r
                key = random.choice(rand_keys)
            else:
                recur = False

            if key not in d:
                print(f"Key Not Found: {key}")
                return r

            d = d[key]
            if "_t" in d:
                r += [d["_t"]]

            if recur:
                r += self.collect_prompts(d, "??")
        return r

    def load_lora_from_prompt(self, prompt, model, clip, lora_i):
        r_model = model
        r_clip = clip
        loras = []
        for lora_name, strength in re.findall(r'<lora:([^:]+):([0-9.]+)>', prompt):
            i = len(loras) + lora_i
            r_model, r_clip = self.loader[i].load_lora(r_model, r_clip, lora_name, float(strength), float(strength))
            loras += [lora_name]
            print(f"Lora Loaded[{i}]: {lora_name}: {strength}")
        prompt = re.sub(r'<lora:([^:]+):([0-9.]+)>', '', prompt)
        return (r_model, r_clip, loras)

    def encode_prompt(self, prompt, model, clip, cond, loras, lora_i):
        r_model = model
        r_clip = clip
        r_cond = cond
        prompt = prompt.strip()
        if prompt == "":
            return (r_model, r_clip, r_cond, loras, lora_i)

        r_model, r_clip, loaded_loras = self.load_lora_from_prompt(prompt, r_model, r_clip, lora_i)
        lora_i += len(loaded_loras)
        loras += loaded_loras

        cond = self.encoder.encode(r_clip, prompt)[0]
        if r_cond is None:
            r_cond = cond
        else:
            r_cond = self.concat.concat(cond, r_cond)[0]
        return (r_model, r_clip, r_cond, loras, lora_i)

    def load_prompt(self, model, clip, seed, text, key_name_list):
        random.seed(seed)
        r_cond = None
        r_model = model
        r_clip = clip
        r_loras = []
        lora_i = 0
        prompt_dict = toml.loads(text)
        for key in key_name_list.splitlines():
            key = key.strip()
            if key == "":
                continue
            prompt = ','.join(self.collect_prompts(prompt_dict, key))
            r_model, r_clip, r_cond, r_loras, lora_i = self.encode_prompt(prompt, r_model, r_clip, r_cond, r_loras, lora_i)

        if r_cond is None:
            r_cond = self.encoder.encode(clip, "")[0]

        return (r_model, r_clip, r_cond, '\n'.join(r_loras), seed)

class PromptLoader:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        files, _ = recursive_search(get_user_directory(), excluded_dir_names=[".git"])
        return {
            "required": {
                "file": (files, {"tooltip": "file name."}),
            }
        }

    @classmethod
    def IS_CHANGED(s, file):
        path = os.path.join(get_user_directory(), file)
        m = hashlib.sha256()
        with open(path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A Prompt.", )
    FUNCTION = "load_prompt"

    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    def load_prompt(self, file):
        path = os.path.join(get_user_directory(), file)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
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
    "PromptLoader": PromptLoader,
    "MultilineStringConcat": MultilineStringConcat,
    "StringSub": StringSub,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MultipleLoraLoader": "MultipleLoraLoader",
    "PromptPicker": "PromptPicker",
    "PromptLoader": "PromptLoader",
    "MultilineStringConcat": "MultilineStringConcat",
    "StringSub": "StringSub",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
