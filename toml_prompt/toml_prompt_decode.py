from typing import Self, Any, Callable, cast, TypeVar
import os
import re
import json
import random
import shlex
import functools
from html.parser import HTMLParser

from . import InputTypesFuncResult
from .prompt_loader import PromptFile, PromptDict

type AttrType = dict[str, str | None]
T = TypeVar("T")


class Random(random.Random):
    def __init__(self, seed: int | None):
        super().__init__(seed)
        self.count = 0

    def set_count(self, count: int):
        print(f"RandomCount: {self.count} -> {count}")
        assert count >= self.count
        _rands = [self.random() for _i in range(self.count, count)]
        self.count = 0

    def random(self) -> float:
        self.count += 1
        return super().random()


class TomlKeyListParser(HTMLParser):
    def __init__(
        self,
        toml: PromptFile | None = None,
        other: Self | None = None,
        seed: int | None = None,
        simple_join: bool = False,
    ):
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
            self.random = Random(seed=seed)
        elif other is not None:
            self.positive = other.positive
            self.negative = other.negative
            self.loras = other.loras
            self.loras_low = other.loras_low
            self.loaded_keys = other.loaded_keys
            self.prompt_dict = other.prompt_dict
            self.root_dir = other.root_dir
            self.exports = other.exports
            self.random = other.random
        self.tag: list[tuple[str, dict[str, str | None]]] = []
        self.cond: list[bool] = []
        self.random_key: list[str] = []
        self.simple_join = simple_join
        self.before_simple_join = False

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

    def feed_new_obj(self, prompt: str, simple_join: bool):
        parser = TomlKeyListParser(other=self, simple_join=simple_join)
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
            key = self.random.choices(choices, weights)[0]
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
        if tag == "raw" or tag == "when" or tag == "else":
            if data.strip():
                if (self.simple_join or self.before_simple_join) and self.positive:
                    self.positive[-1] += data
                    self.before_simple_join = False
                else:
                    self.positive += [data]
        elif tag == "neg":
            if data.strip():
                self.negative += [data]
        elif tag == "tag" or tag == "var":
            for key in re.split(r"[,\r\n]", data):
                key = key.strip()
                prompt = ",".join(
                    [
                        v
                        for v in collect_prompt(
                            self.random,
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
                    self.feed_new_obj(prompt, simple_join=tag == "var")
                    self.before_simple_join = tag == "var"
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

        lora_dict = cast(PromptDict, self.prompt_dict.get("<lora>", {}))
        for lora_name_key in [lora_name, lora_name.split("/")[-1]]:
            if lora_name_key in lora_dict:
                prompt = ",".join(
                    [
                        v
                        for v in collect_prompt(
                            self.random,
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
                    self.feed_new_obj(prompt, simple_join=False)

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
        d, _ = load_prompt_var(d, keys, self.root_dir)
        d[keys[-1]] = [args[1]]
        print("Set:", args[0], "=", args[1])

    def pi_grep(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        d, values = load_prompt_var(d, keys, self.root_dir)
        d[keys[-1]] = [
            k
            for k in (values if isinstance(values, list) else [values])
            if args[1] in k
        ]
        print("Grep:", cast(list[Any], d[keys[-1]]))

    def pi_route(self, args: list[str]):
        d = self.prompt_dict
        for key in args[1].strip().split("."):
            d = cast(PromptDict, d[key])
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

    def pi_random_count(self, args: list[str]):
        self.random.set_count(int(args[0]))

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
        "random_count": pi_random_count,
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
            d = cast(PromptDict, d[elem])
    for key in keys:
        d = start
        for elem in key.split("."):
            if elem not in d.get("_k", []):
                if "_k" in d and isinstance(d["_k"], list):
                    d["_k"] += [elem]
                else:
                    d["_k"] = [elem]
                if "_w" in d and isinstance(d["_w"], list):
                    d["_w"] += [1.0]
                else:
                    d["_w"] = [1.0]
            d = cast(PromptDict, d[elem])


def remove_route(d: PromptDict, keys: list[str]):
    start = d
    for key in keys:
        d = start
        l = key.split(".")
        for elem in l[:-1]:
            d = cast(PromptDict, d[elem])
        elem = l[-1]

        if "_k" not in d:
            d["_k"] = [k for _, k in get_keys_all(d)]

        if elem in d["_k"]:
            i = cast(list[str], d["_k"]).index(elem)
            cast(list[str], d["_k"]).remove(elem)
            if "_w" in d:
                cast(list[float], d["_w"]).pop(i)


def remove_comment_out(s: str) -> str:
    return re.sub(r"((//|#).+$|/\*[\s\S]*?\*/)", "", s, flags=re.MULTILINE)


def select_dynamic_prompt(rand: Random, s: str) -> str:
    return re.sub(
        r"{([^}]+)}",
        lambda m: rand.choices(m.group(1).split("|"), weights=None)[0],
        s,
        flags=re.MULTILINE,
    )


def expand_prompt_var(
    rand: Random,
    d: PromptDict | list[str] | str | int | float | bool,
    prefix: list[str],
) -> str:
    if isinstance(d, dict):
        value = d.get("_t", "")
    elif isinstance(d, list):
        value = rand.choices(d)[0]
    else:
        value = str(d)

    def to_tag(m: re.Match[str]) -> str:
        var_name = m.group(1)
        var_type = "var" if var_name[0] == "$" else "tag"
        var_name = var_name[1:]
        if var_name.startswith("::"):
            r = ".".join([var_name[2:]])
        else:
            r = ".".join(prefix + [var_name])
        return f"<{var_type}>{r}</{var_type}>"

    while re.search(r"([$%]:*[a-zA-Z_.*?]+)", cast(str, value)):
        value = re.sub(
            r"([$%]:*[a-zA-Z_.*?]+)",
            to_tag,
            cast(str, value),
            flags=re.MULTILINE,
        )
    return cast(str, value)


def load_prompt_var(
    d: PromptDict, keys: list[str], root_dir: str
) -> tuple[PromptDict, list[str] | str]:
    for key in keys[:-1]:
        d = cast(PromptDict, d[key])
    var_name = keys[-1]

    if isinstance(d[var_name], dict) and "_load_from_file" in d[var_name]:
        with open(
            os.path.join(
                root_dir,
                cast(dict[str, Any], d[var_name])["_load_from_file"],
            ),
            "r",
            encoding="utf-8",
        ) as f:
            r: list[str] = []
            for line in f.readlines():
                line = line.strip()
                if not line.startswith("#") and not line.startswith("//"):
                    r += [line]
            d[var_name] = r
        return (d, cast(list[str], d[var_name]))

    if isinstance(d[var_name], list):
        return (d, [str(v) for v in cast(list[Any], d[var_name])])
    elif isinstance(d[var_name], dict):
        return (d, str(cast(PromptDict, d[var_name]).get("_t", "")))
    else:
        return (d, str(d[var_name]))


def get_keys_all(
    d: PromptDict,
    rand: Random | None = None,
    loaded_keys: list[str] | None = None,
) -> list[tuple[int, str]]:
    def when(key: str):
        if loaded_keys is None:
            return True
        if not isinstance(d[key], dict):
            return True
        target = cast(PromptDict, d[key])
        return "_when" not in target or target["_when"] in loaded_keys

    if "_k" in d:
        keys = [(i, str(k)) for i, k in enumerate(d["_k"]) if k in d and when(k)]
    else:
        keys = [
            (i, k)
            for i, k in enumerate([k for k in d.keys() if not k.startswith("_")])
            if when(k)
        ]

    if rand and "_r" in d:
        indices = [i for i, _ in keys]
        weights = cast(list[float], d["_r"])
        return [
            (i, key)
            for i, key in keys
            if rand.choices(
                [True, False],
                [
                    weights[indices.index(i)],
                    1.0 - weights[indices.index(i)],
                ],
            )[0]
        ]
    else:
        return keys


def get_keys_term(
    d: PromptDict,
    term: bool,
    rand: Random | None = None,
    loaded_keys: list[str] | None = None,
):
    return [
        (i, k)
        for i, k in get_keys_all(d, rand=rand, loaded_keys=loaded_keys)
        if (isinstance(d[k], str) or len(get_keys_all(cast(PromptDict, d[k]))) == 0)
        == term
    ]


def get_keys_all_recursive(
    d: PromptDict,
    prefix: list[str] | None = None,
    rand: Random | None = None,
    loaded_keys: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    if prefix is None:
        prefix = []
    r_long: list[str] = []
    r_short: list[str] = []
    for _, k in get_keys_all(d, rand=rand, loaded_keys=loaded_keys):
        v = d[k]
        if isinstance(v, str):
            r_long += [".".join(prefix + [k])]
        elif len(get_keys_all(cast(PromptDict, v))) == 0:
            if "_t" in v:
                r_long += [".".join(prefix + [k])]
        else:
            if "_t" in v:
                r_short += [".".join(prefix + [k])]
            l, s = get_keys_all_recursive(
                cast(PromptDict, v),
                prefix + [k],
                rand=rand,
                loaded_keys=loaded_keys,
            )
            r_long += l
            r_short += s
    return (r_long, r_short)


def get_keys_random(
    rand: Random,
    d: PromptDict,
    branch_term: bool = False,
    loaded_keys: list[str] | None = None,
):
    ikeys = get_keys_term(d, branch_term, loaded_keys=loaded_keys)
    indices = [i for i, _ in ikeys]
    if "_w" in d:
        try:
            i = rand.choices(
                indices,
                [float(v) for i, v in enumerate(d["_w"]) if i in indices],
            )[0]
        except:
            raise Exception(f"Invalid weights: keys={ikeys}, weights={d["_w"]}")
    else:
        i = rand.choices(indices, weights=None)[0]
    return ikeys[indices.index(i)][1]


def get_keys_random_recursive(
    rand: Random,
    input_dict: PromptDict,
    loaded_keys: list[str] | None = None,
):
    r: list[str] = []
    prefix: list[str] = []
    d = input_dict
    while isinstance(d, dict):
        ikeys = get_keys_all(d, loaded_keys=loaded_keys)
        indices = [i for i, _ in ikeys]
        if len(ikeys) == 0:
            break

        weights = (
            None
            if d.get("_w", None) is None
            else [float(v) for i, v in enumerate(d["_w"]) if i in indices]
        )
        i = rand.choices(indices, weights=weights)[0]
        key = ikeys[indices.index(i)][1]
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


def exists_in_prompt_dict(prompt_dict: PromptDict, key: str):
    d = prompt_dict
    for key_part in key.split("."):
        if not isinstance(d, dict) or key_part not in d:
            return False
        d = d[key_part]
    return True


def export_values(
    d: PromptDict, exports: dict[str, str], prefix: str, exclude_keys: list[str]
):
    if "_exports" in d:
        for k, v in cast(dict[str, Any], d["_exports"]).items():
            if exports.get(k, None) != v and prefix not in exclude_keys:
                print("Export:", k, "=", v)
                exports[k] = v


def collect_prompt(
    rand: Random,
    prompt_dict: PromptDict,
    keys: str | list[str],
    exclude_keys: list[str] | None = None,
    init_prefix: list[str] | None = None,
    root_dict: PromptDict | None = None,
    parent_dict: PromptDict | None = None,
    ignore_split: bool = False,
    exports: dict[str, str] = {},
    root_dir: str | None = None,
    post_keys: list[str] | None = None,
    collect_post_prompt: bool = True,
) -> list[str]:
    if exclude_keys is None:
        exclude_keys = []
    if root_dict is None:
        root_dict = prompt_dict
    if parent_dict is None:
        parent_dict = prompt_dict
    if root_dir is None:
        root_dir = ""
    if init_prefix is None:
        init_prefix = []
    if post_keys is None:
        post_keys = []

    if isinstance(keys, str):
        keys = build_search_keys(keys)

    init_parent_dict = parent_dict
    r: list[str] = []
    for key in keys:
        d = prompt_dict
        parent_dict = init_parent_dict
        key_parts = key.split(".") if not ignore_split else [key]
        prefix = init_prefix[:]
        while len(key_parts) > 0:
            key = key_parts.pop(0)
            if key in ["?", "?$"]:
                key = get_keys_random(
                    rand, d, key.endswith("$"), loaded_keys=exclude_keys
                )
            elif key == "??":
                assert len(key_parts) == 0
                pick_keys = get_keys_random_recursive(rand, d, loaded_keys=exclude_keys)
                r += collect_prompt(
                    rand,
                    d,
                    pick_keys,
                    exclude_keys,
                    prefix,
                    root_dict=root_dict,
                    parent_dict=parent_dict,
                    exports=exports,
                    root_dir=root_dir,
                    post_keys=post_keys,
                    collect_post_prompt=False,
                )
                break
            elif key in ["*", "*$"]:
                pick_keys = get_keys_term(
                    d, key.endswith("$"), rand=rand, loaded_keys=exclude_keys
                )
                pick_keys = [".".join([key] + key_parts) for _, key in pick_keys]
                r += collect_prompt(
                    rand,
                    d,
                    pick_keys,
                    exclude_keys,
                    prefix,
                    root_dict=root_dict,
                    parent_dict=parent_dict,
                    exports=exports,
                    root_dir=root_dir,
                    post_keys=post_keys,
                    collect_post_prompt=False,
                )
                break
            elif key == "**":
                assert len(key_parts) == 0
                pick_keys = get_keys_all_recursive(
                    d, rand=rand, loaded_keys=exclude_keys
                )
                r += collect_prompt(
                    rand,
                    d,
                    pick_keys[1] + pick_keys[0],
                    exclude_keys,
                    prefix,
                    root_dict=root_dict,
                    parent_dict=parent_dict,
                    exports=exports,
                    root_dir=root_dir,
                    post_keys=post_keys,
                    collect_post_prompt=False,
                )
                break
            elif key.endswith("()"):
                key_parts = ["_f"] + key_parts
                key = key[:-2]

            if not isinstance(d, dict) or key not in d:
                break

            parent_dict = cast(PromptDict, d)
            d = cast(Any, d[key])
            prefix += [key]

            export_values(d, exports, ".".join(prefix), exclude_keys)
        else:
            prefix_str = ".".join(prefix)
            is_term = isinstance(d, (str, list)) or len(get_keys_all(d)) == 0
            is_dict = isinstance(d, dict)
            if isinstance(d, dict):
                proc_order = [
                    ("_all", "_all.*.**"),
                    ("_one", "_one.*.??"),
                    ("_post", "_post"),
                ]
                for post_key, post_key_suffix in proc_order:
                    if post_key in d and f"{prefix_str}.{post_key}" not in exclude_keys:
                        if isinstance(d[post_key], dict):
                            order = cast(PromptDict, d[post_key]).get("_order", "last")
                        else:
                            order = "last"
                        if order == "last":
                            post_keys += [f"{prefix_str}.{post_key_suffix}"]
                        else:
                            order = int(cast(str | int, order))
                            post_keys.insert(order, f"{prefix_str}.{post_key_suffix}")
                        exclude_keys += [f"{prefix_str}.{post_key}"]

            _, d = load_prompt_var(prompt_dict, prefix[len(init_prefix) :], root_dir)
            if prefix_str not in exclude_keys or is_term:
                prompt = select_dynamic_prompt(
                    rand,
                    remove_comment_out(
                        expand_prompt_var(rand, d, prefix if is_dict else prefix[:-1])
                    ),
                )
                if prompt:
                    r += [prompt]
                if prefix_str in exclude_keys:
                    print(f"Load Prompt (Duplicated): {prefix_str}")
                else:
                    exclude_keys += [prefix_str]
                    print(f"Load Prompt: {prefix_str}")

    if collect_post_prompt and post_keys:
        r += collect_prompt(
            rand,
            prompt_dict,
            post_keys,
            exclude_keys,
            init_prefix,
            root_dict=root_dict,
            parent_dict=parent_dict,
            exports=exports,
            root_dir=root_dir,
            collect_post_prompt=False,
        )
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
    s = re.sub(r"\.,", ".", s)
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
                    "PROMPT_FILE",
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

    def load_prompt(self, seed: int, toml: PromptFile, key_name_list: str):
        parser = TomlKeyListParser(toml=toml, seed=seed)
        parser.exports = {"prompt_seed": f"{seed}"}
        export_values(parser.prompt_dict, parser.exports, ".", [])

        key_name_list = select_dynamic_prompt(
            parser.random, remove_comment_out(key_name_list)
        )

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
