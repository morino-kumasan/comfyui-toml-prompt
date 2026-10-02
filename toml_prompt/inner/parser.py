from typing import Self, Any, Callable, cast, TypeVar
import os
import re
import shlex
from html.parser import HTMLParser

from .prompt import (
    PromptFile,
    PromptDict,
    build_search_keys,
    collect_prompt,
    load_prompt_var,
    get_keys_all,
    get_keys_all_recursive,
)
from .util import Random

type AttrType = dict[str, str | None]
T = TypeVar("T")


class PromptTagParser(HTMLParser):
    def __init__(
        self,
        prompt: PromptFile | None = None,
        other: Self | None = None,
        seed: int | None = None,
        simple_join: bool = False,
    ):
        HTMLParser.__init__(self)
        if prompt is not None:
            self.positive: list[str] = []
            self.negative: list[str] = []
            self.loras: list[str] = []
            self.loras_low: list[str] = []
            self.loaded_keys: list[str] = []
            self.prompt_dict = prompt.load()
            self.root_dir = os.path.dirname(prompt.path)
            self.exports: dict[str, str] = {}
            self.random = Random(seed=seed)
            self.set_value: list[str] | None = None
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
            self.set_value = other.set_value
        self.tag: list[tuple[str, dict[str, str | None]]] = []
        self.cond: list[bool] = []
        self.random_key: list[str] = []
        self.simple_join = simple_join
        self.before_simple_join = False

    def feed(self, data: str):
        # <lora>を<?lora>に変換
        data = re.sub(
            r"<(lora[_a-z]*):([^:>]+):([0-9\-.]+)(:([0-9\-.]+))?>",
            replace_lora,
            data,
            flags=re.MULTILINE,
        )

        # <>のエスケープ
        data = data.replace(r"\<", r"\lt")
        data = data.replace(r"\>", r"\rt")

        # 変数を変換
        data = re.sub(
            r"([$%])\{?([a-zA-Z0-9_.*?]+)\}",
            replace_var,
            data,
            flags=re.MULTILINE,
        )
        data = re.sub(
            r"([$%])([a-zA-Z0-9_.*?]+)",
            replace_var,
            data,
            flags=re.MULTILINE,
        )
        return HTMLParser.feed(self, data)

    def feed_new_obj(self, prompt: str, simple_join: bool):
        parser = PromptTagParser(other=self, simple_join=simple_join)
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
        elif tag in ["set", "add"]:
            assert self.set_value is None, "Cannot nest <set>, <add>"
            self.set_value = []

        self.tag += [(tag, dict_attrs)]
        return HTMLParser.handle_starttag(self, tag, attrs)

    def handle_endtag(self, tag: str):
        assert self.tag[-1][0] == tag, f"{tag} != {self.tag}[-1][0]"
        _, args = self.tag.pop(-1)
        if tag in ["case", "when", "else", "random"]:
            _cond = self.cond.pop(-1)
        if tag == "random":
            self.random_key.pop(-1)
        if tag == "set":
            key = args["key"]
            if key is not None and self.set_value:
                self.pi_set([key, ",".join(self.set_value)])
            self.set_value = None
        if tag == "add":
            key = args["key"]
            if key is not None and self.set_value:
                self.pi_add([key, ",".join(self.set_value)])
            self.set_value = None
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
                    if self.set_value is None:
                        self.positive[-1] += data
                    else:
                        self.set_value[-1] += data
                    self.before_simple_join = False
                else:
                    if self.set_value is None:
                        self.positive += [data]
                    else:
                        self.set_value += [data]
        elif tag == "neg":
            assert self.set_value is None, "Cannot nest <set>, <add>, <neg>"
            if data.strip():
                self.negative += [data]
        elif tag == "tag" or tag == "var":
            for key in re.split(r"[,\r\n\s]", data):
                key = key.strip()
                keys = build_search_keys(key)
                simple_join = tag == "var"
                self.feed_prompt(keys, simple_join)
        elif tag in ["set", "add"]:
            assert self.set_value is not None, f"<{tag}> not started."
            self.set_value += [data]
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

        if low:
            if lora_tag not in self.loras_low:
                self.loras_low += [lora_tag]
                self.loaded_keys += [lora_name]
        else:
            if lora_tag not in self.loras:
                self.loras += [lora_tag]
                self.loaded_keys += [lora_name]

        lora_dict = cast(PromptDict, self.prompt_dict.get("<lora>", {}))
        for lora_name_key in [lora_name, lora_name.split("/")[-1]]:
            if lora_name_key in lora_dict:
                keys = [["<lora>", lora_name_key]]
                self.feed_prompt(keys)

    def feed_prompt(
        self,
        keys: list[str] | list[list[str]],
        simple_join: bool = False,
    ):
        prompt = ",".join(
            [
                v
                for v in collect_prompt(
                    self.random,
                    self.prompt_dict,
                    keys,
                    exclude_keys=self.loaded_keys,
                    exports=self.exports,
                    root_dir=self.root_dir,
                )
                if v.strip()
            ]
        )
        if prompt:
            self.feed_new_obj(prompt, simple_join=simple_join)
            self.before_simple_join = simple_join

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

    def pi_add(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        d, _ = load_prompt_var(d, keys, self.root_dir)
        val = d[keys[-1]]
        if isinstance(val, list):
            if len(cast(list[str], val)) == 1:
                d[keys[-1]] = val[0] + [args[1]]
            else:
                d[keys[-1]] = [args[1]]
        elif isinstance(val, str):
            d[keys[-1]] = val + args[1]
        print("Add:", args[0], "=", args[1])

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

        if args[0] == "fix":
            fix_route(d, args[2:])
        elif args[0] == "find":
            keys = get_keys_all_recursive(d)
            all_keys = keys[0] + keys[1]
            keys = [k for k in all_keys if args[2] in k]
            fix_route(d, keys)
        elif args[0] == "remove":
            keys = get_keys_all_recursive(d)
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
        "add": pi_add,
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


def replace_lora(m: re.Match[str]) -> str:
    if m.group(5) is not None:
        return f'<?{m.group(1)} "{m.group(2)}" "{m.group(3)}" "{m.group(5)}">'
    else:
        return f'<?{m.group(1)} "{m.group(2)}" "{m.group(3)}">'


def replace_h3(m: re.Match[str]) -> str:
    return rf"\lt{m.group(0)[1:-1]}\rt"


def replace_var(m: re.Match[str]) -> str:
    var_type = m.group(1)
    var_name = m.group(2)
    if var_name[-1] == ".":
        var_name = var_name[:-1]
        dot = "."
    else:
        dot = ""

    if var_type == "$":
        return f"<var>{var_name}</var>{dot}"
    else:
        return f"<tag>{var_name}</tag>{dot}"
