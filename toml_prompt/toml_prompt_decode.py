import os
import re
import json
import random
import tomllib
import functools
from html.parser import HTMLParser

class TomlKeyListParser(HTMLParser):
    def __init__(self, prompt_dict=None, other=None):
        HTMLParser.__init__(self)
        if prompt_dict is not None:
            self.positive = []
            self.negative = []
            self.loras = []
            self.loaded_keys = []
            self.prompt_dict = prompt_dict
            self.exports = {}
        elif other is not None:
            self.positive = other.positive
            self.negative = other.negative
            self.loras = other.loras
            self.loaded_keys = other.loaded_keys
            self.prompt_dict = other.prompt_dict
            self.exports = other.exports
        self.tag = []
        self.cond = []
        self.random_key = []

    def feed(self, data):
        def replace(m):
            if m.group(4) is not None:
                return f'<lora path="{m.group(1)}" strength_model="{m.group(2)}" strength_clip="{m.group(4)}" />'
            else:
                return f'<lora path="{m.group(1)}" strength_model="{m.group(2)}" />'
        data = re.sub(r"<lora:([^:>]+):([0-9\-.]+)(:([0-9\-.]+))?>", replace, data, flags=re.MULTILINE)
        return HTMLParser.feed(self, data)

    def load_lora_tag(self, lora_name, strength_model, strength_clip=None):
        lora_name = lora_name.replace(os.path.sep, "/")
        if strength_clip is None:
            lora_tag = "<lora:{}:{}>".format(lora_name, strength_model)
        else:
            lora_tag = "<lora:{}:{}:{}>".format(lora_name, strength_model, strength_clip)

        if lora_tag not in self.loras:
            self.loras += [lora_tag]
            self.loaded_keys += [lora_name]

        lora_dict = self.prompt_dict.get("<lora>", {})
        if lora_name in lora_dict:
            prompt = ','.join([v.strip() for v in collect_prompt(lora_dict, [lora_name], ignore_split=True, exports=self.exports) if v.strip()])
            if prompt:
                self.positive += [prompt]

    def tag_lora(self, attrs):
        self.load_lora_tag(attrs["path"], attrs["strength_model"], attrs.get("strength_clip", None))

    def tag_set(self, attrs):
        d = self.prompt_dict
        for key in attrs["key"].strip().split("."):
            d = d[key]
        if isinstance(d, list):
            d[:] = [attrs["value"]]
            print("Set:", attrs["key"], "=", d)

    def tag_grep(self, attrs):
        d = self.prompt_dict
        for key in attrs["key"].strip().split("."):
            d = d[key]
        if isinstance(d, list):
            d[:] = [k for k in d if attrs["value"] in k]
            print("Grep:", d)

    def tag_fix(self, attrs):
        d = self.prompt_dict
        for key in attrs["key"].strip().split("."):
            d = d[key]
        keys = get_keys_all_recursive(d)
        all_keys = keys[0] + keys[1]
        if attrs.get("find", None) is not None:
            # Find: *{args[1]}*
            keys = [k for k in all_keys if attrs["find"] in k]
            fix_route(d, keys)
            print("Find:", keys)
        if attrs.get("remove", None) is not None:
            # Find Not: *{args[1]}*
            keys = [k for k in all_keys if attrs["remove"] in k]
            remove_route(d, keys)
            print("FindNot:", keys)
        if attrs.get("route", None) is not None:
            fix_route(d, [attrs["route"]])
            print("Fix:", keys)

    def tag_export(self, attrs):
        self.exports[attrs["key"]] = attrs["value"]
        print("Export:", attrs["key"], "=", attrs["value"])

    def tag_case(self, attrs):
        self.cond += [False]

    def tag_random(self, attrs):
        self.cond += [False]
        choices = [k for k in attrs.keys()]
        weights = [float(v) for v in attrs.values()]
        key = random.choices(choices, weights)[0]
        print(f"Random: {key} in {choices}")
        self.random_key += [key]

    def tag_empty(self, attrs):
        pass

    TAG_FUNCS = {
        "case": tag_case,
        "export": tag_export,
        "fix": tag_fix,
        "grep": tag_grep,
        "lora": tag_lora,
        "random": tag_random,
        "raw": tag_empty,
        "set": tag_set,
        "tag": tag_empty,
    }

    def branch_cond(self, tag, attrs):
        parent_tag = self.tag[-1][0] if len(self.tag) > 0 else "tag"
        if tag == "when":
            if parent_tag == "case":
                if self.cond[-1] == False:
                    if attrs["key"] in self.loaded_keys:
                        self.cond[-1] = None
                        self.cond += [True]
                        print("Case:", attrs["key"])
                    else:
                        self.cond += [False]
                else:
                    self.cond += [False]
            elif parent_tag == "random":
                if self.cond[-1] == False:
                    if attrs["key"] == self.random_key[-1]:
                        self.cond[-1] = None
                        self.cond += [True]
                        print("Random:", attrs["key"])
                    else:
                        self.cond += [False]
                else:
                    self.cond += [False]
            else:
                self.cond += [attrs["key"] in self.loaded_keys]
                if self.cond[-1]:
                    print("When:", attrs["key"])
            self.tag += [(tag, attrs)]
            return False
        elif tag == "else":
            self.cond += [self.cond[-1] == False]
            self.tag += [(tag, attrs)]
            return False

        if len(self.cond) > 0 and not self.cond[-1]:
            self.tag += [(tag, attrs)]
            return False

        return True

    def handle_starttag(self, tag, attrs):
        dict_attrs = dict(attrs)
        if not self.branch_cond(tag, dict_attrs):
            return HTMLParser.handle_starttag(self, tag, dict_attrs)

        self.TAG_FUNCS[tag](self, dict_attrs)
        self.tag += [(tag, dict_attrs)]
        return HTMLParser.handle_starttag(self, tag, attrs)

    def handle_endtag(self, tag):
        assert self.tag[-1][0] == tag
        self.tag.pop(-1)
        if tag == "case" or tag == "when" or tag == "else" or tag == "random":
            self.cond.pop(-1)
        return HTMLParser.handle_endtag(self, tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        # Condition is not True
        if len(self.cond) > 0 and not self.cond[-1]:
            return

        tag = self.tag[-1][0] if len(self.tag) > 0 else "tag"
        attrs = self.tag[-1][1] if len(self.tag) > 0 else {}
        if tag == "raw":
            data = data.strip()
            if data:
                if attrs.get("type", "positive") == "negative":
                    self.negative += [data]
                else:
                    self.positive += [data]
        elif tag == "tag" or tag == "when" or tag == "else":
            for key in re.split(r"[,\r\n]", data):
                key = key.strip()
                prompt = ','.join([v.strip() for v in collect_prompt(self.prompt_dict, build_search_keys(key), exclude_keys=self.loaded_keys, exports=self.exports) if v.strip()])
                if prompt:
                    parser = TomlKeyListParser(other=self)
                    parser.feed(f'<raw>{prompt}</raw>')
        else:
            assert data.strip() == "" or data.strip() == ",", f"Unknown Data: {data} in {tag}"
        return HTMLParser.handle_data(self, data)

def fix_route(d, keys):
    start = d
    for key in keys:
        d = start
        for elem in key.split("."):
            if not d.get("_fix", False):
                d["_k"] = []
                d["_w"] = []
                d["_fix"] = True
            d = d[elem]
    for key in keys:
        d = start
        for elem in key.split("."):
            if elem not in d["_k"]:
                d["_k"] += [elem]
                d["_w"] += [1.0]
            d = d[elem]

def remove_route(d, keys):
    start = d
    for key in keys:
        d = start
        l = key.split(".")
        for elem in l[:-1]:
            d = d[elem]
        elem = l[-1]

        if "_k" not in d:
            d["_k"] = get_keys_all(d)

        if elem in d["_k"]:
            i = d["_k"].index(elem)
            d["_k"].remove(elem)
            if "_w" in d:
                d["_w"].pop(i)

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

def collect_prompt(prompt_dict, keys, exclude_keys=None, init_prefix=None, global_vars=None, ignore_split=False, exports={}):
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
                r += collect_prompt(d, keys, exclude_keys, prefix, global_vars, exports=exports)
                break
            elif key in ["*", "*$"]:
                keys = [".".join([key] + key_parts) for _, key in get_keys_term(d, key.endswith("$"))]
                r += collect_prompt(d, keys, exclude_keys, prefix, global_vars, exports=exports)
                break
            elif key == "**":
                assert len(key_parts) == 0
                keys = get_keys_all_recursive(d)
                r += collect_prompt(d, keys[1] + keys[0], exclude_keys, prefix, global_vars, exports=exports)
                break

            if key not in d:
                break

            d = d[key]
            prefix += [key]

            if "_exports" in d:
                for k, v in d["_exports"].items():
                    if exports.get(k, None) != v:
                        print("Export:", k, "=", v)
                        exports[k] = v
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

class TomlPromptDecode:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING", "STRING")
    OUTPUT_TOOLTIPS = ("Positive prompt", "Negative prompt", "Loaded LoRA name list", "Random seed", "Summary", "Exports")
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
        pass

    def load_prompt(self, seed, text, key_name_list):
        random.seed(seed)

        prompt_dict = tomllib.loads(text)
        key_name_list = select_dynamic_prompt(remove_comment_out(key_name_list))
        parser = TomlKeyListParser(prompt_dict=prompt_dict)
        parser.exports = { "seed": seed }
        parser.feed(key_name_list)
        positive = ','.join([v.strip() for v in parser.positive if v.strip()])
        negative = ','.join([v.strip() for v in parser.negative if v.strip()])

        lora_list = "\n".join(parser.loras)
        exports = "\n".join(["{}: {}".format(k, v) for k, v in parser.exports.items()])
        summary = f"{exports}\n\n---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}"
        exports = json.dumps(load_summary_header(exports))
        return (positive, negative, lora_list, seed, summary, exports)

def load_summary_header(s):
    r = {}
    for k, v in re.findall(r"^([^:]+): (.+)$", s, flags=re.MULTILINE):
        r[k] = v
    return r

class SummaryReader:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING")
    OUTPUT_TOOLTIPS = ("Positive prompt", "Negative prompt", "Loaded LoRA name list", "Random seed", "Json Formatted Exports")
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
        exports = {}

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
            if beg == 0:
                exports = load_summary_header(summary[:s])
            beg = e
            type_ = m.group(1).lower()
        set(type_, beg, len(summary))

        assert positive is not None and negative is not None and lora_list is not None

        if "Seed" in exports:
            seed = int(exports["Seed"])
        elif seed is not None:
            exports["Seded"] = seed
        else:
            assert True, "Seed Not Found"
            
        return (positive, negative, lora_list, seed, json.dumps(exports))
