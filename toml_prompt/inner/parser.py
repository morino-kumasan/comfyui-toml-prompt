from typing import Self, Any, Callable, cast, TypeVar, Final
import os
import re
import shlex
from html.parser import HTMLParser

from .prompt import (
    PromptFile,
    PromptDict,
    Context,
    build_search_keys,
    collect_prompt,
    load_prompt_var,
    get_keys_all,
    get_keys_all_recursive,
)
from .util import Random

type AttrType = dict[str, str | None]
T = TypeVar("T")

MINIMAX_TAGS: Final[list[str]] = ["picture", "audio", "video", "subject"]
MINIMAX_TAGS_REGEX: Final[str] = "(" + "|".join(MINIMAX_TAGS) + ")"


class PromptTagParser(HTMLParser):
    def __init__(
        self,
        prompt: PromptFile | None = None,
        other: Self | None = None,
        seed: int | None = None,
    ):
        HTMLParser.__init__(self)
        if prompt is not None:
            self.prompt_dict = prompt.load()
            self.context = Context(os.path.dirname(prompt.path))
            self.random = Random(seed=seed)
            self.loras: list[str] = []
            self.loras_low: list[str] = []
            self.set_value: list[str] | None = None
            self.h3_tags: dict[str, list[str]] = {}
        else:
            assert other is not None
            self.prompt_dict = other.prompt_dict
            self.context = other.context
            self.random = other.random
            self.loras = other.loras
            self.loras_low = other.loras_low
            self.set_value = other.set_value
            self.h3_tags = other.h3_tags
        # 内部状態
        self.positive: list[str] = []
        self.negative: list[str] = []
        self.tag: list[tuple[str, dict[str, str | None]]] = []
        self.cond: list[bool] = []
        self.random_key: list[str] = []

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

        # minimax h3用タグを変換
        data = re.sub(
            r"<\s*" + MINIMAX_TAGS_REGEX + r"\s+([^\s>/]+)\s*>",
            replace_h3,
            data,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        # 変数を変換
        data = re.sub(
            r"([$%])(\{([a-zA-Z0-9_+.*?]+)\}|([a-zA-Z0-9_+.*?]+))",
            replace_var,
            data,
            flags=re.MULTILINE,
        )
        return HTMLParser.feed(self, data)

    def feed_new_obj(self, prompt: str, is_var: bool):
        parser = PromptTagParser(other=self)
        parser.feed(f"<raw>{prompt}</raw>")
        assert (
            len(parser.tag) == 0
            and len(parser.cond) == 0
            and len(parser.random_key) == 0
        ), f"Tag not closed. {prompt}"

        def prepare_to_add_var(target: PromptTagParser):
            if target.positive:
                target.positive[-1] += r"\\"
            if target.negative:
                target.negative[-1] += r"\\"

        if is_var:
            prepare_to_add_var(self)
            prepare_to_add_var(parser)

        self.positive += parser.positive
        self.negative += parser.negative

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
            and self.check_when_tag(attrs)
        ]

    def tag_case_when(self, attrs: AttrType):
        if self.cond[-1] == True:
            if self.check_when_tag(attrs):
                self.cond[-1] = False
                self.cond += [True]
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
            assert "key" in args, f"<set>: key argument not found."
            key = args["key"]
            if key is not None and self.set_value:
                self.pi_set([key, ",".join(self.set_value)])
            self.set_value = None
        if tag == "add":
            assert "key" in args, f"<set>: key argument not found."
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
                if self.set_value is None:
                    self.positive += [data]
                else:
                    if self.set_value:
                        self.set_value[-1] += r"\\"
                    self.set_value += [data + r"\\"]
        elif tag == "neg":
            assert self.set_value is None, "Cannot nest <set>, <add>, <neg>"
            if data.strip():
                self.negative += [data]
        elif tag == "tag" or tag == "var":
            for key in re.split(r"[,\r\n\s]", data):
                key = key.strip()
                keys = build_search_keys(key)
                self.feed_prompt(keys, is_var=tag == "var")
        elif tag in ["set", "add"]:
            assert self.set_value is not None, f"<{tag}> not started."
            self.set_value += [data]
        elif tag in MINIMAX_TAGS:
            try:
                n = int(data)
            except:
                if data not in self.h3_tags.setdefault(tag, []):
                    self.h3_tags[tag] += [data]
                n = self.h3_tags[tag].index(data) + 1
            # ,で区切らずに挿入
            data = f"\\lt{tag[0].upper()}{tag[1:]} {n}\\rt"
            if self.set_value is None:
                if self.positive:
                    self.positive[-1] += r"\\"
                self.positive += [data + r"\\"]
            else:
                if self.set_value:
                    self.set_value[-1] += r"\\"
                self.set_value += [data + r"\\"]
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

        def add_lora(target: list[str]):
            if lora_tag in target:
                return
            i = next(
                (
                    i
                    for i, v in enumerate(target)
                    if v.startswith(f"<lora:{lora_name}:")
                ),
                None,
            )
            if i is None:
                target += [lora_tag]
                self.context.loaded_keys += [lora_name]
                return True
            else:
                target[i] = lora_tag
                return False

        if low:
            is_add = add_lora(self.loras_low)
        else:
            is_add = add_lora(self.loras)

        if is_add:
            lora_dict = cast(PromptDict, self.prompt_dict.get("<lora>", {}))
            for lora_name_key in (
                [lora_name, lora_name.split("/")[-1]]
                if "/" in lora_name
                else [lora_name]
            ):
                if lora_name_key in lora_dict:
                    keys = [["<lora>", lora_name_key]]
                    self.feed_prompt(keys)

    def feed_prompt(
        self,
        keys: list[str] | list[list[str]],
        is_var: bool = False,
    ):
        prompt = ",".join(
            [
                v
                for v in collect_prompt(
                    self.random, self.prompt_dict, keys, self.context
                )
                if v.strip()
            ]
        )
        if prompt:
            self.feed_new_obj(prompt, is_var)

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
        d, _ = load_prompt_var(d, keys, self.context)
        d[keys[-1]] = [args[1]]
        print("Set:", args[0], "=", args[1])

    def pi_add(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        d, _ = load_prompt_var(d, keys, self.context)
        val = d[keys[-1]]
        if isinstance(val, list):
            if len(cast(list[str], val)) == 1:
                d[keys[-1]] = [val[0] + args[1]]
            else:
                d[keys[-1]] = [args[1]]
        elif isinstance(val, str):
            d[keys[-1]] = val + args[1]
        print("Add:", args[0], "=", args[1])

    def pi_grep(self, args: list[str]):
        d = self.prompt_dict
        keys = args[0].strip().split(".")
        d, values = load_prompt_var(d, keys, self.context)
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
        self.context.exports[args[0]] = args[1]
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

    def check_when_tag(self, attrs: AttrType) -> bool:
        return (
            ("key" in attrs and attrs["key"] in self.context.loaded_keys)
            or ("key_not" in attrs and attrs["key_not"] not in self.context.loaded_keys)
            or (
                "key_empty" in attrs
                and get_variable(attrs["key_empty"], self.prompt_dict, self.context)
                == ""
            )
            or (
                "key_not_empty" in attrs
                and get_variable(attrs["key_not_empty"], self.prompt_dict, self.context)
                != ""
            )
        )

    def get_prompt(self):
        positive = normalize_prompt(",".join([v for v in self.positive if v.strip()]))
        negative = normalize_prompt(",".join([v for v in self.negative if v.strip()]))
        return (positive.strip(), negative.strip())


def get_variable(key: str | None, prompt_dict: PromptDict, context: Context):
    if not key:
        return ""
    keys = key.strip().split(".")
    d, _ = load_prompt_var(prompt_dict, keys, context)
    return d[keys[-1]]


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
    return rf"<{m.group(1)}>{m.group(2)}</{m.group(1)}>"


def replace_var(m: re.Match[str]) -> str:
    var_type = m.group(1)
    var_name = m.group(3) or m.group(2)
    if var_name[-1] == ".":
        var_name = var_name[:-1]
        dot = "."
    else:
        dot = ""

    if var_type == "$":
        return f"<var>{var_name}</var>{dot}"
    else:
        return f"<tag>{var_name}</tag>{dot}"


def normalize_prompt(s: str):
    # 改行 -> スペース
    s = re.sub(r"[\r\n]+", " ", s)
    # \\で後続の,を無視
    s = re.sub(r"\\\\\s*,", "", s)
    s = s.replace(r"\\", "")
    # 連続した","や"."を削除
    s = re.sub(r",[\s,]+", ", ", s)
    s = re.sub(r",[\s]*\.+", ". ", s)
    s = re.sub(r"\.[\s,]+", ". ", s)
    s = re.sub(r"\s*\.\s*,", ". ", s)
    # ","や"."の周りのスペース整理
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s*\.", ".", s)
    # 連続したスペースを削除
    s = re.sub(r"\s+", " ", s)
    # カッコの始まりと終わりのスペース削除
    s = re.sub(r"([(\[])\s+", "\\1", s)
    s = re.sub(r"\s+([)\]])", "\\1", s)
    # エスケープ変換
    s = re.sub(r"\\n[\s,.]*", "\n", s)
    s = s.replace(r"\t", "\t")
    s = s.replace(r"\lt", "<")
    s = s.replace(r"\rt", ">")
    return (s[1:] if s.startswith(",") else s).strip()
