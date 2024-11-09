import os
import re
import hashlib
import random
import toml
from functools import reduce

from folder_paths import get_filename_list, get_user_directory
from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat

def remove_comment_out(s):
    return re.sub(r"((//|#).+$|/\*.*?\*/)", "", s).strip()

class TomlPromptEncoder:
    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "STRING", "STRING", "INT")
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", "A Conditioning containing a text by key_name.", "Loaded LoRA name list", "A prompt", "Random seed")
    FUNCTION = "load_prompt"
    CATEGORY = "conditioning"
    DESCRIPTION = "LoRA prompt load."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "The diffusion model."}),
                "clip": ("CLIP", {"tooltip": "The CLIP model."}),
                "key_name_list": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "Select Key Name"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Random seed."}),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "TOML format prompt."}),
                "lora_info": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "TOML format lora prompt."}),
            }
        }

    def __init__(self):
        self.encoder = CLIPTextEncode()
        self.concat = ConditioningConcat()
        self.loader = {}
        self.loras = []
        self.prompt = []
        self.loaded_keys = []

    def collect_prompts(self, prompt_dict, keys, prefix):
        r = []
        d = prompt_dict
        for i, key in enumerate(keys):
            if key == "?" or key == "??":
                assert(key == "?" or i == (len(keys) - 1))
                recur = key == "??"
                rand_keys = [k for k in d.keys() if not k.startswith("_")]
                if len(rand_keys) == 0:
                    return r
                key = random.choice(rand_keys)
            else:
                recur = False

            if key not in d:
                print(f"Key Not Found: {key}")
                return r

            prefix += [key]
            prefix_str = '.'.join(prefix)
            d = d[key]

            if prefix_str not in self.loaded_keys and "_t" in d:
                self.loaded_keys += [prefix_str]
                if '$' in d["_t"] and "_v" not in d:
                    print(f"_v Not Set: {d}")
                t = re.sub(r"\${([a-zA-Z0-9_-]+)}", lambda m: random.choice(d["_v"][m.group(1)]), d["_t"])
                r += [t]

            if recur:
                r += self.collect_prompts(d, ["??"], prefix)
        return r

    def load_lora_from_prompt(self, prompt, lora_dict, model, clip):
        r_model = model
        r_clip = clip
        for lora_name, strength in re.findall(r'<lora:([^:]+):([0-9.]+)>', prompt):
            if lora_name not in self.loader:
                self.loader[lora_name] = LoraLoader()
                r_model, r_clip = self.loader[lora_name].load_lora(r_model, r_clip, lora_name, float(strength), float(strength))
                print(f"Lora Loaded: {lora_name}: {strength}")
            self.loras += ["<lora:{}:{}>".format(lora_name, strength)]
        prompt = re.sub(r'<lora:([^:]+):([0-9.]+)>', lambda m: ','.join(self.collect_prompts(lora_dict, [m.group(1).replace("\\", "\\\\")], [])), prompt)
        return (r_model, r_clip, prompt)

    def encode_prompt(self, prompt, lora_dict, model, clip, cond):
        r_model = model
        r_clip = clip
        r_cond = cond
        prompt = prompt.strip()
        if prompt == "":
            return (r_model, r_clip, r_cond)

        r_model, r_clip, prompt = self.load_lora_from_prompt(prompt, lora_dict, r_model, r_clip)
        self.prompt += [prompt]

        cond = self.encoder.encode(r_clip, prompt)[0]
        if r_cond is None:
            r_cond = cond
        else:
            r_cond = self.concat.concat(cond, r_cond)[0]
        return (r_model, r_clip, r_cond)

    def load_prompt(self, model, clip, seed, text, lora_info, key_name_list):
        random.seed(seed)
        self.loader = {}
        self.loras = []
        self.prompt = []
        self.loaded_keys = []

        r_cond = None
        r_model = model
        r_clip = clip
        prompt_dict = toml.loads(text)
        lora_dict = toml.loads(lora_info)
        for key_str in key_name_list.splitlines():
            key_str = remove_comment_out(key_str)
            if key_str == "":
                continue

            prompts = []
            for key in [k.strip() for k in key_str.split("&")]:
                m = re.match(r'^<lora:([^:]+):([0-9.]+)>$', key)
                if m:
                    r_model, r_clip, prompt = self.load_lora_from_prompt(key, lora_dict, r_model, r_clip)
                    prompts += [prompt]
                else:
                    prompts += [','.join(self.collect_prompts(prompt_dict, key.split("."), []))]
            prompt = ','.join(prompts)

            r_model, r_clip, r_cond = self.encode_prompt(prompt, lora_dict, r_model, r_clip, r_cond)

        if r_cond is None:
            r_cond = self.encoder.encode(clip, "")[0]

        return (r_model, r_clip, r_cond, '\n'.join(self.loras), '\nBREAK\n'.join([p for p in self.prompt if p]), seed)

class MultipleLoraTagLoader:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("LoRA tag list separated by line break", )
    FUNCTION = "create_tags"
    CATEGORY = "utils"
    DESCRIPTION = "Create LoRA tags."
    MAX_TAG_LORA = 10

    @classmethod
    def INPUT_TYPES(s):
        lora_file_list = get_filename_list("loras")
        return {
            "required": { k: v for k, v in reduce(lambda x, y: x + y, [[
                (f"lora_name_{i}", (lora_file_list, {"tooltip": "LoRA file name."})),
                (f"strength_{i}", ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 0.01, "tooltip": "Modify strength."})),
            ] for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA)]) }
        }

    def __init__(self):
        pass

    def create_tags(self, **kwargs):
        return ('\n'.join([
            "<lora:{}:{:2f}>".format(kwargs[f"lora_name_{i}"], kwargs[f"strength_{i}"])
            for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA) if abs(kwargs[f"strength_{i}"]) >= 1e-10
        ]), )

class PromptLoader:
    RETURN_TYPES = ("STRING", )
    OUTPUT_TOOLTIPS = ("A Prompt.", )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Prompt loader."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "file": ("STRING", {"tooltip": "file name."}),
            }
        }

    @classmethod
    def IS_CHANGED(s, file):
        path = os.path.join(get_user_directory(), file)
        m = hashlib.sha256()
        with open(path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    def __init__(self):
        pass

    def load_prompt(self, file):
        path = os.path.expanduser(file)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return (text, )

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
            }
        }

    def __init__(self):
        pass

    def view_str(self, text):
        return {"ui": { "text": [text] }, "result": (text,)}

NODE_CLASS_MAPPINGS = {
    "TomlPromptEncoder": TomlPromptEncoder,
    "MultipleLoraTagLoader": MultipleLoraTagLoader,
    "PromptLoader": PromptLoader,
    "StringConcat": StringConcat,
    "StringSub": StringSub,
    "StringViewer": StringViewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TomlPromptEncoder": "TomlPromptEncoder",
    "MultipleLoraTagLoader": "MultipleLoraTagLoader",
    "PromptLoader": "PromptLoader",
    "StringConcat": "StringConcat",
    "StringSub": "StringSub",
    "StringViewer": "StringViewer",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
