import re
import random
import toml

from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat

def remove_comment_out(s):
    return re.sub(r"((//|#).+$|/\*.*?\*/)", "", s).strip()

def select_dynamic_prompt(s):
    return re.sub(r"{([^}]+)}", lambda m: random.choice(m.group(1).split('|')).strip(), s)

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
                rand_keys = []

            if key not in d:
                print(f"Key Not Found: [{'.'.join(prefix)}.{key}]: {rand_keys}")
                return r

            prefix += [key]
            prefix_str = '.'.join(prefix)
            d = d[key]

            if prefix_str not in self.loaded_keys and "_t" in d:
                self.loaded_keys += [prefix_str]
                if '$' in d["_t"] and "_v" not in d:
                    print(f"_v Not Set: {d}")
                t = re.sub(r"\${([a-zA-Z0-9_-]+)}", lambda m: random.choice(d["_v"][m.group(1)]), d["_t"])
                t = select_dynamic_prompt(remove_comment_out(t))
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
            key_str = select_dynamic_prompt(remove_comment_out(key_str))
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
