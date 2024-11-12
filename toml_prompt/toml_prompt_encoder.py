import re
import random
import tomllib
import functools

from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat

def remove_comment_out(s):
    return re.sub(r"((//|#).+$|/\*.*?\*/)", "", s).strip()

def select_dynamic_prompt(s):
    return re.sub(r"{([^}]+)}", lambda m: random.choice(m.group(1).split('|')).strip(), s)

def expand_prompt_var(d, global_vars):
    def random_var(m):
        var_name = m.group(1)
        if var_name.startswith("g."):
            var_name = var_name[2:]
            vars = global_vars
        else:
            vars = d.get("_v", None)
            if vars is None:
                print(f"_v Not Set: {d}")
                return ""
        return random.choice(vars[var_name])
    return re.sub(r"\${([a-zA-Z0-9_.]+)}", random_var, d if isinstance(d, str) else d["_t"])

def get_keys_all(d):
    return [k for k in d.keys() if not k.startswith("_")]

def get_keys_all_recursive(d, prefix=[]):
    r_long = []
    r_short = []
    for k, v in [(k, v) for k, v in d.items() if not k.startswith("_")]:
        if isinstance(v, str):
            r_long += ['.'.join(prefix + [k])]
        elif len(get_keys_all(v)) == 0:
            if "_t" in v:
                r_long += ['.'.join(prefix + [k])]
        else:
            if "_t" in v:
                r_short += ['.'.join(prefix + [k])]
            l, s = get_keys_all_recursive(v, prefix + [k])
            r_long += l
            r_short += s
    return (r_long, r_short)

def get_keys_random(d):
    rand_keys = get_keys_all(d)
    return random.choice(rand_keys)

def get_keys_random_recursive(d):
    rand_keys, keys = get_keys_all_recursive(d)
    selected_key = random.choice(rand_keys)
    return [key for key in keys if selected_key.startswith(f"{key}.")] + [selected_key]

def build_search_keys(keys, prefix=[]):
    assert len(keys) > 0
    if isinstance(keys, str):
        keys = [(key.split("+")) for key in keys.split(".")]
    if len(keys) == 1:
        return [".".join(prefix + [key]) for key in keys[0]]
    return functools.reduce(lambda x, y: x + y, [[".".join(prefix + [key])] + build_search_keys(keys[1:], prefix + [key]) for key in keys[0]])

def collect_prompt(prompt_dict, keys, exclude_keys=None, init_prefix=None, global_vars=None, ignore_split=False):
    if isinstance(keys, str):
        keys = build_search_keys(keys)

    if exclude_keys is None:
        exclude_keys = []
    if global_vars is None:
        global_vars = prompt_dict.get("_v", {})

    r = []
    for key in keys:
        d = prompt_dict
        key_parts = key.split(".") if not ignore_split else [key]
        prefix = init_prefix or []
        while len(key_parts) > 0:
            key = key_parts.pop(0)
            if key == "?":
                key = get_keys_random(d)
            elif key == "??":
                assert len(key_parts) == 0
                keys = get_keys_random_recursive(d)
                r += collect_prompt(d, keys, exclude_keys, prefix[:], global_vars)
                break
            elif key == "*":
                keys = [".".join([key] + key_parts) for key in get_keys_all(d)]
                r += collect_prompt(d, keys, exclude_keys, prefix[:], global_vars)
                break
            elif key == "**":
                assert len(key_parts) == 0
                keys = get_keys_all_recursive(d)
                r += collect_prompt(d, keys[1] + keys[0], exclude_keys, prefix[:], global_vars)
                break

            if key not in d:
                break
            d = d[key]
            prefix += [key]
        else:
            prefix_str = ".".join(prefix)
            if isinstance(d, str) or "_t" in d:
                if prefix_str not in exclude_keys:
                    r += [select_dynamic_prompt(remove_comment_out(expand_prompt_var(d, global_vars)))]
                    exclude_keys += [prefix_str]
                    print(f"Load Prompt: {prefix_str}")
    return r

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

    def load_lora_from_prompt(self, prompt, lora_dict, model, clip):
        r_model = model
        r_clip = clip
        for lora_name, strength in re.findall(r'<lora:([^:]+):([0-9.]+)>', prompt):
            if lora_name not in self.loader:
                self.loader[lora_name] = LoraLoader()
                r_model, r_clip = self.loader[lora_name].load_lora(r_model, r_clip, lora_name, float(strength), float(strength))
                print(f"Lora Loaded: {lora_name}: {strength}")
            self.loras += ["<lora:{}:{}>".format(lora_name, strength)]
        def lora_prompt(m):
            # for toml key
            lora_name = m.group(1).replace("\\", "\\\\")
            return ','.join(collect_prompt(lora_dict, [lora_name], ignore_split=True))
        prompt = re.sub(r'<lora:([^:]+):([0-9.]+)>', lora_prompt, prompt)
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
        prompt_dict = tomllib.loads(text)
        lora_dict = tomllib.loads(lora_info)
        for key_str in key_name_list.splitlines():
            key_str = select_dynamic_prompt(remove_comment_out(key_str))
            if key_str == "":
                continue

            prompts = []
            for key in [k.strip() for k in key_str.split("&")]:
                m = re.match(r'^<lora:([^:]+):([0-9.]+)>$', key)
                if m:
                    # lora tag
                    prompts += [key]
                else:
                    prompts += [','.join(collect_prompt(prompt_dict, build_search_keys(key), exclude_keys=self.loaded_keys))]
            prompt = ','.join(prompts)

            r_model, r_clip, r_cond = self.encode_prompt(prompt, lora_dict, r_model, r_clip, r_cond)

        if r_cond is None:
            r_cond = self.encoder.encode(clip, "")[0]

        return (r_model, r_clip, r_cond, '\n'.join(self.loras), '\nBREAK\n'.join([p for p in self.prompt if p]), seed)
