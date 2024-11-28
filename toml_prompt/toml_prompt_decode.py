import os
import re
import random
import tomllib
import functools

def remove_comment_out(s):
    return re.sub(r"((//|#).+$|/\*[\s\S]*?\*/)", "", s, flags=re.MULTILINE).strip()

def select_dynamic_prompt(s):
    return re.sub(r"{([^}]+)}", lambda m: random.choice(m.group(1).split('|')).strip(), s, flags=re.MULTILINE)

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
    return re.sub(r"\${([a-zA-Z0-9_.]+)}", random_var, d if isinstance(d, str) else d["_t"], flags=re.MULTILINE)

def get_keys_all(d):
    if "_k" in d:
        return [k for k in d["_k"] if k in d]
    return [k for k in d.keys() if not k.startswith("_")]

def get_keys_term(d, term):
    return [(i, k) for i, k in enumerate(get_keys_all(d)) if (isinstance(d[k], str) or len(get_keys_all(d[k])) == 0) == term ]

def get_keys_all_recursive(d, prefix=[]):
    r_long = []
    r_short = []
    for k in get_keys_all(d):
        v = d[k]
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

def get_keys_random(d, branch_term = False):
    ikeys = get_keys_term(d, branch_term)
    indices = [i for i, _ in ikeys]
    if "_w" in d:
        i = random.choices(indices, [v for i, v in enumerate(d["_w"]) if i in indices])[0]
    else:
        i = random.choice(indices)
    return ikeys[i][1]

def get_keys_random_recursive(d):
    r = []
    prefix = []
    while isinstance(d, dict):
        keys = get_keys_all(d)
        if len(keys) == 0:
            break

        if "_w" in d:
            key = random.choices(keys, d["_w"])[0]
        else:
            key = random.choice(keys)

        d = d[key]
        if isinstance(d, str) or "_t" in d:
            r += ['.'.join(prefix + [key])]
        prefix += [key]
    return r

def build_search_keys(keys, prefix=[]):
    if isinstance(keys, str):
        keys = [(key.split("+")) for key in keys.split(".")]
    key_len = len(keys)
    if key_len == 1:
        # 終端の*, ?を区別できるように変換
        return [".".join(prefix + [key + "$" if key in ["?", "*"] else key]) for key in keys[0]]
    elif key_len == 0:
        return []
    return functools.reduce(lambda x, y: x + y, [
        [".".join(prefix + [key])] + build_search_keys(keys[1:], prefix + [key])
    for key in keys[0]])

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
        prefix = init_prefix[:] if init_prefix is not None else []
        while len(key_parts) > 0:
            key = key_parts.pop(0)
            if key in ["?", "?$"]:
                key = get_keys_random(d, key.endswith("$"))
            elif key == "??":
                assert len(key_parts) == 0
                keys = get_keys_random_recursive(d)
                r += collect_prompt(d, keys, exclude_keys, prefix, global_vars)
                break
            elif key in ["*", "*$"]:
                keys = [".".join([key] + key_parts) for _, key in get_keys_term(d, key.endswith("$"))]
                r += collect_prompt(d, keys, exclude_keys, prefix, global_vars)
                break
            elif key == "**":
                assert len(key_parts) == 0
                keys = get_keys_all_recursive(d)
                r += collect_prompt(d, keys[1] + keys[0], exclude_keys, prefix, global_vars)
                break

            if key not in d:
                break
            d = d[key]
            prefix += [key]
        else:
            prefix_str = ".".join(prefix)
            d_is_str = isinstance(d, str)
            if d_is_str or "_t" in d:
                if prefix_str not in exclude_keys:
                    r += [select_dynamic_prompt(remove_comment_out(expand_prompt_var(d, global_vars)))]
                    exclude_keys += [prefix_str]
                    print(f"Load Prompt: {prefix_str}")
                elif d_is_str or len(get_keys_all(d)) == 0:
                    r += [select_dynamic_prompt(remove_comment_out(expand_prompt_var(d, global_vars)))]
                    print(f"Load Prompt (Duplicated): {prefix_str}")
    return r

def expand_prompt_tag(prompt, prompt_dict, loaded_keys, loras):
    positive = []
    negative = []
    for key in split_toml_prompt(prompt):
        if not key.startswith("<"):
            positive += [key]
            continue

        tag, args = key.split(":", 1)
        tag = tag[1:].strip()
        args = split_toml_prompt_in_tag(args[:-1])
        if tag == "lora":
            lora_name = args[0]
            lora_name = lora_name.replace(os.path.sep, "/")

            lora_tag = "<lora:{}>".format(":".join(args))
            if lora_tag not in loras:
                loras += [lora_tag]
                loaded_keys += [lora_name]

            lora_dict = prompt_dict.get("<lora>", {})
            if lora_name in lora_dict:
                positive += [','.join(collect_prompt(lora_dict, [lora_name], ignore_split=True))]
        elif tag == "raw":
            positive += [args[0]]
        elif tag == "!":
            negative += [args[0]]
        elif tag == "if":
            conds = [args[i] for i in range(0, len(args), 2)]
            branches = [args[i] for i in range(1, len(args), 2)]
            for i, branch in enumerate(branches):
                keys = [v.strip() for v in conds[i].split(",")]
                if len([v for v in keys if v not in loaded_keys]) == 0:
                    print(f"If {keys}: True")
                    r = load_prompt(branch, prompt_dict, loaded_keys, loras)
                    positive += [r[0]]
                    negative += [r[1]]
                    break
            else:
                if len(conds) > len(branches):
                    print(f"If {keys}: Else")
                    r = load_prompt(conds[-1], prompt_dict, loaded_keys, loras)
                    positive += [r[0]]
                    negative += [r[1]]
        elif tag == "random":
            choices = [i for i in range(1, len(args), 2)]
            weights = [float(args[i]) for i in range(0, len(args), 2)]
            i = random.choices(choices, weights)[0]
            print(f"Random: {int((i - 1) / 2)}")
            r = load_prompt(args[i], prompt_dict, loaded_keys, loras)
            positive += [r[0]]
            negative += [r[1]]
        else:
            print(f"Unknown Tag: {tag}")

    return (",".join(positive), ",".join(negative))

def split_toml_prompt(s, separator=r"[,\r\n]", ignore_empty=True):
    r = []
    beg = 0
    before_sep = []
    beg_tag = 0
    tag_starts = ['<', '(']
    tag_ends = ['>', ')']
    for m in re.finditer(r"[<>()]", s, flags=re.MULTILINE):
        sep = m.group(0)
        if sep in tag_starts:
            before_sep += [sep]
        else:
            bef = before_sep.pop(-1)
            assert (sep == ">" and bef == "<") or (sep == ")" and bef == "(")
        
        span = m.span()
        if sep in tag_starts and len(before_sep) == 1:
            if beg < span[0]:
                r += [v.strip() if ignore_empty else v for v in re.split(separator, s[beg:span[0]])] if separator else [s[beg:span[0]]]
            beg_tag = span[0]
        elif sep in tag_ends and len(before_sep) == 0:
            r += [s[beg_tag:span[1]]]
        beg = span[1]
    if beg < len(s):
        r += [v for v in re.split(separator, s[beg:len(s)])] if separator else [s[beg:len(s)]]
    return [v for v in r if v] if ignore_empty else r

def split_toml_prompt_in_tag(s):
    r = []
    t = []
    for key in split_toml_prompt(s, ":", False):
        if key and key[0] in ["<", "("]:
            t += [key]
            continue

        if t and r:
            r[-1] += "".join(t + [key])
        else:
            r += ["".join(t + [key])]
        t = []

    if t and r:
        r[-1] += "".join(t)
    elif t:
        r += [",".join(t)]

    return r

def load_prompt(s, prompt_dict, loaded_keys, loras):
    prompts = []
    for key in split_toml_prompt(s):
        key = key.strip()
        if key.startswith("<"):
            prompts += [key]
        else:
            prompts += [','.join(collect_prompt(prompt_dict, build_search_keys(key), exclude_keys=loaded_keys))]

    prompt = ','.join(prompts).strip()
    if prompt == "":
        return ("", "")

    positive, negative = expand_prompt_tag(prompt, prompt_dict, loaded_keys, loras)
    return (positive, negative)

class TomlPromptDecode:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING")
    OUTPUT_TOOLTIPS = ("Positive prompt", "Negative prompt", "Loaded LoRA name list", "Random seed", "Summary")
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Load toml prompt."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "key_name_list": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "Select Key Name"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": "Random seed."}),
                "text": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "TOML format prompt."}),
            }
        }

    def __init__(self):
        self.loras = []
        self.loaded_keys = []

    def load_prompt(self, seed, text, key_name_list):
        random.seed(seed)
        self.loras = []
        self.loaded_keys = []

        prompt_dict = tomllib.loads(text)
        key_name_list = select_dynamic_prompt(remove_comment_out(key_name_list))

        positive, negative = load_prompt(key_name_list, prompt_dict, self.loaded_keys, self.loras)

        lora_list = "\n".join(self.loras)
        summary = f"---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}\n\n---- Seed ----\n{seed}"
        return (positive, negative, lora_list, seed, summary)

class SummaryReader:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT")
    OUTPUT_TOOLTIPS = ("Positive prompt", "Negative prompt", "Loaded LoRA name list", "Random seed")
    FUNCTION = "read"
    CATEGORY = "utils"
    DESCRIPTION = "Read summary from TomlPromptDecode."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "summary": ("STRING", {"multiline": True, "dynamicPrompts": True, "tooltip": "TomlPromptDecode summary."}),
            }
        }

    def __init__(self):
        pass

    def read(self, summary):
        positive = None
        negative = None
        lora_list = None
        seed = None

        def set(t, b, e):
            nonlocal positive, negative, lora_list, seed
            if t == "positive":
                positive = summary[b:e].strip()
            elif t == "negative":
                negative = summary[b:e].strip()
            elif t == "lora":
                lora_list = summary[b:e].strip()
            elif t == "seed":
                seed = float(summary[b:e].strip())

        beg = 0
        type_ = None
        for m in re.finditer(r"\n*---- ([a-zA-Z0-9]+) ----\n", summary, flags=re.MULTILINE):
            s, e = m.span()
            set(type_, beg, s)
            beg = e
            type_ = m.group(1).lower()
        set(type_, beg, len(summary))

        assert positive is not None and negative is not None and lora_list is not None and seed is not None
        return (positive, negative, lora_list, seed)
