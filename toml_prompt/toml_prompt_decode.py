from typing import Self, Any, Callable, cast
import os
import re
import json
import random
import shlex
import functools
from html.parser import HTMLParser

from . import InputTypesFuncResult
from .prompt_loader import TomlPrompt

AttrType = dict[str, str | None]
PromptDict = dict[str, Any]
PromptVariables = dict[str, str | float | int]


class TomlKeyListParser(HTMLParser):
    def __init__(self, toml: TomlPrompt | None = None, other: Self | None = None):
        HTMLParser.__init__(self)
        if toml is not None:
            self.positive: list[str] = []
            self.negative: list[str] = []
            self.loras: list[str] = []
            self.loras_low: list[str] = []
            self.loaded_keys: list[str] = []
            self.prompt_dict = toml.load()
            self.root_dir = os.path.dirname(toml.path)
            self.exports: dict[str, str] = {}
        elif other is not None:
            self.positive = other.positive
            self.negative = other.negative
            self.loras = other.loras
            self.loras_low = other.loras_low
            self.loaded_keys = other.loaded_keys
            self.prompt_dict = other.prompt_dict
            self.root_dir = other.root_dir
            self.exports = other.exports
        self.tag: list[tuple[str, dict[str, str | None]]] = []
        self.cond: list[bool] = []
        self.random_key: list[str] = []

    def feed(self, data: str):
        def replace(m: re.Match[str]) -> str:
            if m.group(5) is not None:
                return f'<?{m.group(1)} "{m.group(2)}" "{m.group(3)}" "{m.group(5)}">'
            else:
                return f'<?{m.group(1)} "{m.group(2)}" "{m.group(3)}">'

        data = re.sub(
            r"<(lora[_a-z]*):([^:>]+):([0-9\-.]+)(:([0-9\-.]+))?>",
            replace,
            data,
            flags=re.MULTILINE,
        )
        return HTMLParser.feed(self, data)

    def feed_new_obj(self, prompt: str):
        parser = TomlKeyListParser(other=self)
        parser.feed(f"<raw>{prompt}</raw>")
        assert (
            len(parser.tag) == 0
            and len(parser.cond) == 0
            and len(parser.random_key) == 0
        ), f"Tag not closed. {prompt}"

    def tag_case(self, attrs: AttrType):
        self.cond += [len(self.cond) == 0 or self.cond[-1] == True]

    def tag_random(self, attrs: AttrType):
        if len(self.cond) == 0 or self.cond[-1] == True:
            self.cond += [True]
            choices = [k for k in attrs.keys()]
            weights = [float(v) for v in attrs.values() if v is not None]
            key = random.choices(choices, weights)[0]
            print(f"Random: {key} in {choices}")
            self.random_key += [key]
        else:
            self.cond += [False]
            self.random_key += [""]

    def tag_when(self, attrs: AttrType):
        self.cond += [
            (len(self.cond) == 0 or self.cond[-1] == True)
            and attrs["key"] in self.loaded_keys
        ]
        if self.cond[-1]:
            print("When:", attrs["key"])

    def tag_case_when(self, attrs: AttrType):
        if self.cond[-1] == True:
            if attrs["key"] in self.loaded_keys:
                self.cond[-1] = False
                self.cond += [True]
                print("Case:", attrs["key"])
            else:
                self.cond += [False]
        else:
            self.cond += [False]

    def tag_random_when(self, attrs: AttrType):
        if self.cond[-1] == True:
            if attrs["key"] == self.random_key[-1]:
                self.cond[-1] = False
                self.cond += [True]
                print("Random:", attrs["key"])
            else:
                self.cond += [False]
        else:
            self.cond += [False]

    def tag_else(self, attrs: AttrType):
        self.cond += [self.cond[-1] == True]
        if self.cond[-1]:
            print("Else")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        dict_attrs = dict(attrs)
        parent_tag = self.tag[-1][0] if len(self.tag) > 0 else "tag"
        if tag == "when":
            if parent_tag == "case":
                self.tag_case_when(dict_attrs)
            elif parent_tag == "random":
                self.tag_random_when(dict_attrs)
            else:
                self.tag_when(dict_attrs)
        elif tag == "else":
            self.tag_else(dict_attrs)
        elif tag == "case":
            self.tag_case(dict_attrs)
        elif tag == "random":
            self.tag_random(dict_attrs)

        self.tag += [(tag, dict_attrs)]
        return HTMLParser.handle_starttag(self, tag, attrs)

    def handle_endtag(self, tag: str):
        assert self.tag[-1][0] == tag, f"{tag} != {self.tag}[-1][0]"
        self.tag.pop(-1)
        if tag in ["case", "when", "else", "random"]:
            _cond = self.cond.pop(-1)
        if tag == "random":
            self.random_key.pop(-1)
        return HTMLParser.handle_endtag(self, tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str):
        # Condition is not True
        if len(self.cond) > 0 and not self.cond[-1]:
            return HTMLParser.handle_data(self, data)

        tag = self.tag[-1][0] if len(self.tag) > 0 else "tag"
        attrs = self.tag[-1][1] if len(self.tag) > 0 else {}
        if tag == "raw":
            data = data.strip()
            if data:
                if attrs.get("type", "positive") == "negative":
                    self.negative += [data]
                else:
                    self.positive += [data]
        elif tag == "neg":
            data = data.strip()
            if data:
                self.negative += [data]
        elif tag == "tag" or tag == "when" or tag == "else":
            for key in re.split(r"[,\r\n]", data):
                key = key.strip()
                prompt = ",".join(
                    [
                        v.strip()
                        for v in collect_prompt(
                            self.prompt_dict,
                            build_search_keys(key),
                            exclude_keys=self.loaded_keys,
                            exports=self.exports,
                            root_dir=self.root_dir,
                        )
                        if v.strip()
                    ]
                )
                if prompt:
                    self.feed_new_obj(prompt)
        else:
            assert (
                data.strip() == "" or data.strip() == ","
            ), f"Unknown Data: {data} in {tag}"
        return HTMLParser.handle_data(self, data)

    def load_lora_tag(
        self, lora_name: str, strength_model: str, strength_clip: str | None, low: bool
    ):
        lora_name = lora_name.replace(os.path.sep, "/")
        if strength_clip is None:
            lora_tag = "<lora:{}:{}>".format(lora_name, strength_model)
        else:
            lora_tag = "<lora:{}:{}:{}>".format(
                lora_name, strength_model, strength_clip
            )

        if lora_tag not in self.loras:
            if low:
                self.loras_low += [lora_tag]
            else:
                self.loras += [lora_tag]
            self.loaded_keys += [lora_name]

        lora_dict = self.prompt_dict.get("<lora>", {})
        for lora_name_key in [lora_name, lora_name.split("/")[-1]]:
            if lora_name_key in lora_dict:
                prompt = ",".join(
                    [
                        v.strip()
                        for v in collect_prompt(
                            lora_dict,
                            [lora_name_key],
                            ignore_split=True,
                            exports=self.exports,
                            root_dir=self.root_dir,
                        )
                        if v.strip()
                    ]
                )
                if prompt:
                    self.feed_new_obj(prompt)

    def pi_lora(self, args: list[str]):
        self.load_lora_tag(
            args[0],
            args[1] if len(args) >= 2 else "1.0",
            args[2] if len(args) >= 3 else None,
            False,
        )

    def pi_lora_low(self, args: list[str]):
        self.load_lora_tag(
            args[0],
            args[1] if len(args) >= 2 else "1.0",
            args[2] if len(args) >= 3 else None,
            True,
        )

    def pi_set(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        for key in keys[:-1]:
            d = d[key]
        load_prompt_var(d["_v"], keys[-1], self.root_dir)
        d = d["_v"][keys[-1]]
        if isinstance(d, list):
            d[:] = [args[1]]
            print("Set:", args[0], "=", cast(list[Any], d))

    def pi_grep(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        for key in keys[:-1]:
            d = d[key]
        load_prompt_var(d["_v"], keys[-1], self.root_dir)
        d = d["_v"][keys[-1]]
        if isinstance(d, list):
            d[:] = [k for k in cast(list[Any], d) if args[1] in k]
            print("Grep:", cast(list[Any], d))

    def pi_route(self, args: list[str]):
        d = self.prompt_dict
        for key in args[1].strip().split("."):
            d = d[key]
        keys = get_keys_all_recursive(d)

        if args[0] == "fix":
            fix_route(d, [args[2]])
        elif args[0] == "find":
            all_keys = keys[0] + keys[1]
            keys = [k for k in all_keys if args[2] in k]
            fix_route(d, keys)
        elif args[0] == "remove":
            all_keys = keys[0] + keys[1]
            keys = [k for k in all_keys if args[2] in k]
            remove_route(d, keys)

    def pi_export(self, args: list[str]):
        self.exports[args[0]] = args[1]
        print("Export:", args[0], "=", args[1])

    PI_FUNCS: dict[str, Callable[[Self, list[str]], None]] = {
        "export": pi_export,
        "route": pi_route,
        "grep": pi_grep,
        "lora": pi_lora,
        "lora_high": pi_lora,
        "lora_h": pi_lora,
        "lora_low": pi_lora_low,
        "lora_l": pi_lora_low,
        "set": pi_set,
    }

    def handle_pi(self, data: str):
        # Condition is not True
        if len(self.cond) > 0 and not self.cond[-1]:
            return HTMLParser.handle_pi(self, data)

        args = shlex.split(data)
        self.PI_FUNCS[args[0]](self, args[1:])
        return HTMLParser.handle_pi(self, data)


def fix_route(d: PromptDict, keys: list[str]):
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


def remove_route(d: PromptDict, keys: list[str]):
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


def remove_comment_out(s: str) -> str:
    return re.sub(r"((//|#).+$|/\*[\s\S]*?\*/)", "", s, flags=re.MULTILINE).strip()


def select_dynamic_prompt(s: str) -> str:
    return re.sub(
        r"{([^}]+)}",
        lambda m: random.choice(m.group(1).split("|")).strip(),
        s,
        flags=re.MULTILINE,
    )


def expand_prompt_var(
    d: PromptDict, global_vars: PromptVariables, root_dir: str
) -> str:
    def random_var(m: re.Match[str]):
        var_name = m.group(1)
        if var_name.startswith("."):
            var_name = var_name[1:]
            vars = global_vars
        else:
            vars = d.get("_v", None)
            if vars is None:
                print(f"_v Not Set: {d}")
                return ""
        load_prompt_var(vars, var_name, root_dir)
        return random.choice(cast(list[Any], vars[var_name]))

    return re.sub(
        r"\${([a-zA-Z0-9_.]+)}",
        random_var,
        d if isinstance(d, str) else d["_t"],
        flags=re.MULTILINE,
    )


def load_prompt_var(vars: PromptDict, var_name: str, root_dir: str):
    if isinstance(vars[var_name], list):
        pass
    elif isinstance(vars[var_name], str):
        vars[var_name] = [vars[var_name]]
    else:
        assert "_load_from_file" in vars[var_name]
        with open(
            os.path.join(root_dir, vars[var_name]["_load_from_file"]),
            "r",
            encoding="utf-8",
        ) as f:
            vars[var_name] = []
            for line in f.readlines():
                line = line.strip()
                if not line.startswith("#") and not line.startswith("//"):
                    vars[var_name] += [line]


def get_keys_all(d: PromptDict):
    if "_k" in d:
        return [cast(str, k) for k in d["_k"] if k in d]
    return [k for k in d.keys() if not k.startswith("_")]


def get_keys_term(d: PromptDict, term: bool):
    return [
        (i, k)
        for i, k in enumerate(get_keys_all(d))
        if (isinstance(d[k], str) or len(get_keys_all(d[k])) == 0) == term
    ]


def get_keys_all_recursive(
    d: PromptDict, prefix: list[str] | None = None
) -> tuple[list[str], list[str]]:
    if prefix is None:
        prefix = []
    r_long: list[str] = []
    r_short: list[str] = []
    for k in get_keys_all(d):
        v = d[k]
        if isinstance(v, str):
            r_long += [".".join(prefix + [k])]
        elif len(get_keys_all(v)) == 0:
            if "_t" in v:
                r_long += [".".join(prefix + [k])]
        else:
            if "_t" in v:
                r_short += [".".join(prefix + [k])]
            l, s = get_keys_all_recursive(v, prefix + [k])
            r_long += l
            r_short += s
    return (r_long, r_short)


def get_keys_random(d: PromptDict, branch_term: bool = False):
    ikeys = get_keys_term(d, branch_term)
    indices = [i for i, _ in ikeys]
    if "_w" in d:
        try:
            i = random.choices(
                indices, [v for i, v in enumerate(d["_w"]) if i in indices]
            )[0]
        except:
            raise Exception(f"Invalid weights: keys={ikeys}, weights={d["_w"]}")
    else:
        i = random.choice(indices)
    return ikeys[i][1]


def get_keys_random_recursive(input_dict: PromptDict):
    r: list[str] = []
    prefix: list[str] = []
    d = input_dict
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
            r += [".".join(prefix + [key])]
        prefix += [key]
    return r


def build_search_keys(
    keys: str | list[list[str]], prefix: list[str] | None = None
) -> list[str]:
    if prefix is None:
        prefix = []
    if isinstance(keys, str):
        keys = [(key.split("+")) for key in keys.split(".")]
    key_len = len(keys)
    if key_len == 1:
        # 終端の*, ?を区別できるように変換
        return [
            ".".join(prefix + [key + "$" if key in ["?", "*"] else key])
            for key in keys[0]
        ]
    elif key_len == 0:
        return []
    return functools.reduce(
        lambda x, y: x + y,
        [
            [".".join(prefix + [key])] + build_search_keys(keys[1:], prefix + [key])
            for key in keys[0]
        ],
    )


def export_values(
    d: PromptDict, exports: dict[str, str], prefix: str, exclude_keys: list[str]
):
    if "_exports" in d:
        for k, v in d["_exports"].items():
            if exports.get(k, None) != v and prefix not in exclude_keys:
                print("Export:", k, "=", v)
                exports[k] = v


def collect_prompt(
    prompt_dict: dict[str, Any],
    keys: str | list[str],
    exclude_keys: list[str] | None = None,
    init_prefix: list[str] | None = None,
    global_vars: PromptVariables | None = None,
    ignore_split: bool = False,
    exports: dict[str, str] = {},
    root_dir: str | None = None,
) -> list[str]:
    if isinstance(keys, str):
        keys = build_search_keys(keys)
    if exclude_keys is None:
        exclude_keys = []
    if global_vars is None:
        global_vars = cast(PromptVariables, prompt_dict.get("_v", {}))
    if root_dir is None:
        root_dir = ""

    r: list[str] = []
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
                pick_keys = get_keys_random_recursive(d)
                r += collect_prompt(
                    d,
                    pick_keys,
                    exclude_keys,
                    prefix,
                    global_vars,
                    exports=exports,
                    root_dir=root_dir,
                )
                break
            elif key in ["*", "*$"]:
                pick_keys = get_keys_term(d, key.endswith("$"))
                if "_r" in d:
                    all_keys = pick_keys
                    pick_keys = [
                        key
                        for i, key in enumerate(pick_keys)
                        if random.choices(
                            [True, False], [d["_r"][i], 1.0 - d["_r"][i]]
                        )[0]
                    ]
                    print(
                        "RandomAll:",
                        [key for _, key in all_keys],
                        "->",
                        [key for _, key in pick_keys],
                    )
                pick_keys = [".".join([key] + key_parts) for _, key in pick_keys]
                r += collect_prompt(
                    d,
                    pick_keys,
                    exclude_keys,
                    prefix,
                    global_vars,
                    exports=exports,
                    root_dir=root_dir,
                )
                break
            elif key == "**":
                assert len(key_parts) == 0
                pick_keys = get_keys_all_recursive(d)
                r += collect_prompt(
                    d,
                    pick_keys[1] + pick_keys[0],
                    exclude_keys,
                    prefix,
                    global_vars,
                    exports=exports,
                    root_dir=root_dir,
                )
                break
            elif key.endswith("()"):
                key_parts = ["_f"] + key_parts
                key = key[:-2]

            if key not in d:
                break

            d = d[key]
            prefix += [key]

            export_values(d, exports, ".".join(prefix), exclude_keys)
        else:
            prefix_str = ".".join(prefix)
            d_is_str = isinstance(d, str)
            if d_is_str or "_t" in d:
                if prefix_str not in exclude_keys:
                    r += [
                        select_dynamic_prompt(
                            remove_comment_out(
                                expand_prompt_var(d, global_vars, root_dir)
                            )
                        )
                    ]
                    exclude_keys += [prefix_str]
                    print(f"Load Prompt: {prefix_str}")
                elif d_is_str or len(get_keys_all(d)) == 0:
                    r += [
                        select_dynamic_prompt(
                            remove_comment_out(
                                expand_prompt_var(d, global_vars, root_dir)
                            )
                        )
                    ]
                    print(f"Load Prompt (Duplicated): {prefix_str}")
    return r


def load_summary_header(s: str):
    r: dict[str, str] = {}
    for k, v in re.findall(r"^([^:]+): (.+)$", s, flags=re.MULTILINE):
        r[k] = v
    return r


def normalize_prompt(s: str):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r", ", ",", s)
    s = re.sub(r",+", ",", s)
    return s[1:] if s.startswith(",") else s


class TomlPromptDecode:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING", "STRING")
    OUTPUT_TOOLTIPS = (
        "Positive prompt",
        "Negative prompt",
        "Loaded LoRA name list",
        "Random seed",
        "Summary",
        "Exports",
    )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Load toml prompt."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "key_name_list": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "tooltip": "Select Key Name",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Random seed.",
                    },
                ),
                "toml": (
                    "TOML_PROMPT",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "defaultInput": True,
                        "tooltip": "TOML format prompt.",
                    },
                ),
            }
        }

    def __init__(self):
        pass

    def load_prompt(self, seed: int, toml: TomlPrompt, key_name_list: str):
        random.seed(seed)

        key_name_list = select_dynamic_prompt(remove_comment_out(key_name_list))
        parser = TomlKeyListParser(toml=toml)
        parser.exports = {"prompt_seed": f"{seed}"}
        export_values(parser.prompt_dict, parser.exports, ".", [])

        # Decode
        parser.feed(key_name_list)
        positive = normalize_prompt(
            ",".join([v.strip() for v in parser.positive if v.strip()])
        )
        negative = normalize_prompt(
            ",".join([v.strip() for v in parser.negative if v.strip()])
        )

        lora_list = "\n".join(parser.loras)
        if parser.loras_low:
            lora_list += "\n--\n"
            lora_list += "\n".join(parser.loras_low)
        exports = "\n".join(["{}: {}".format(k, v) for k, v in parser.exports.items()])
        summary = f"{exports}\n\n---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}"
        exports = json.dumps(load_summary_header(exports))
        return (positive, negative, lora_list, seed, summary, exports)


class SummaryReader:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING")
    OUTPUT_TOOLTIPS = (
        "Positive prompt",
        "Negative prompt",
        "Loaded LoRA name list",
        "Random seed",
        "Json Formatted Exports",
    )
    FUNCTION = "read"
    CATEGORY = "utils"
    DESCRIPTION = "Read summary from TomlPromptDecode."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "summary": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "tooltip": "TomlPromptDecode summary.",
                    },
                ),
            }
        }

    def __init__(self):
        pass

    def read(self, summary: str):
        positive = None
        negative = None
        lora_list = None
        seed = None
        exports = {}

        def set(t: str | None, b: int, e: int):
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
        for m in re.finditer(
            r"\n*---- ([a-zA-Z0-9]+) ----\n", summary, flags=re.MULTILINE
        ):
            s, e = m.span()
            set(type_, beg, s)
            if beg == 0:
                exports = load_summary_header(summary[:s])
            beg = e
            type_ = m.group(1).lower()
        set(type_, beg, len(summary))

        assert positive is not None and negative is not None and lora_list is not None

        if "seed" in exports:
            seed = int(exports["seed"])
        elif seed is not None:
            exports["seed"] = seed
        else:
            assert True, "Seed Not Found"

        return (positive, negative, lora_list, seed, json.dumps(exports))


class SplitLoraList:
    RETURN_TYPES = ("STRING", "STRING")
    OUTPUT_TOOLTIPS = ("High noise lora list.", "Low noise lora list.")
    FUNCTION = "split"
    CATEGORY = "utils"
    DESCRIPTION = "Split lora list."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "lora_list": (
                    "STRING",
                    {"defaultInput": True, "multiline": True, "tooltip": "Lora list."},
                ),
            }
        }

    def __init__(self):
        pass

    def split(self, lora_list: str):
        r = lora_list.split("\n--\n", 1)
        return (r[0], r[1] if len(r) == 2 else "")
