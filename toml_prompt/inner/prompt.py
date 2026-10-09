from typing import Any, cast

import os
import re
import functools
import tomllib
import yaml
import json

from .util import Random

type PromptDict = dict[str, Any | list[Any] | PromptDict]


class PromptFile:
    def __init__(
        self,
        path: str | None,
        json_data: dict[Any, Any] | None = None,
    ):
        if path is None:
            self.text = json.dumps(json_data) or "{}"
            self.path = ""
            self.file_type = ".json"
        else:
            with open(path, "r", encoding="utf-8") as f:
                self.text = f.read()
            self.path = path
            self.file_type = os.path.splitext(path)[1]

    def load(self) -> PromptDict:
        if self.file_type in [".toml", ".txt"]:
            return cast(PromptDict, tomllib.loads(self.text))
        elif self.file_type in [".yaml", ".yml"]:
            return yaml.safe_load(self.text)
        elif self.file_type in [".json"]:
            return json.loads(self.text)
        else:
            raise Exception(f"Unknown file type: {self.file_type}")


class Context:
    def __init__(
        self,
        root_dir: str,
    ):
        self.loaded_keys: list[str] = []
        self.exports: dict[str, str] = {}
        self.root_dir = root_dir


def remove_comment_out(s: str) -> str:
    return re.sub(r"((//|#).+$|/\*[\s\S]*?\*/)", "", s, flags=re.MULTILINE)


def select_dynamic_prompt(rand: Random, s: str) -> str:
    pat = r"(^|[^$]){([^{}|]*(\|([^{}|])*)*)}"
    r = s

    def conv(m: re.Match[str]):
        return m.group(1) + rand.choices(m.group(2).split("|"), weights=None)[0]

    while re.search(pat, r, flags=re.MULTILINE):
        r = re.sub(
            pat,
            conv,
            r,
            flags=re.MULTILINE,
        )
    return r


def load_prompt_var(
    d: PromptDict, keys: list[str], context: Context
) -> tuple[PromptDict, list[str] | str]:
    for key in keys[:-1]:
        d = cast(PromptDict, d[key])
    var_name = keys[-1]

    assert var_name in d, f"Variable not found: {".".join(keys)}"

    if isinstance(d[var_name], dict) and "!include" in d[var_name]:
        path = cast(dict[str, Any], d[var_name])["!include"]
        ext = path.split(".")[-1]
        with open(
            os.path.join(context.root_dir, path),
            "r",
            encoding="utf-8",
        ) as f:
            if ext == "txt":
                r: list[str] = []
                for line in f.readlines():
                    line = line.strip()
                    if not line.startswith("#") and not line.startswith("//"):
                        r += [line]
                d[var_name] = r
            elif ext == "json":
                d[var_name] = json.loads(f.read())
            elif ext == "yaml":
                d[var_name] = yaml.safe_load(f.read())
            elif ext == "toml":
                d[var_name] = tomllib.loads(f.read())
        return (d, cast(list[str], d[var_name]))

    if isinstance(d[var_name], list):
        return (d, [str(v) for v in cast(list[Any], d[var_name])])
    elif isinstance(d[var_name], dict):
        return (d, str(cast(PromptDict, d[var_name]).get("_t", "")))
    else:
        return (d, str(d[var_name]))


def check_when(target: PromptDict, context: Context):
    return (
        ("_when" not in target or target["_when"] in context.loaded_keys)
        and (
            "_when_not" not in target or target["_when_not"] not in context.loaded_keys
        )
        and (
            "_when_any" not in target
            or any([(key in context.loaded_keys) for key in target["_when_any"]])
        )
        and (
            "_when_not_any" not in target
            or any(
                [(key not in context.loaded_keys) for key in target["_when_not_any"]]
            )
        )
    )


def get_keys_all(
    d: PromptDict,
    rand: Random | None = None,
    context: Context = Context(""),
) -> list[tuple[int, str]]:
    def when(key: str):
        if not isinstance(d[key], dict):
            return True
        target = cast(PromptDict, d[key])
        # _elseがある場合は条件を満たさなくてもキーが選択される
        if "_else" in target:
            return True
        # キー読み込み条件
        return check_when(target, context)

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
        if len(weights) < len(indices):
            weights += [1.0 for _ in range(len(indices) - len(weights))]
        return [
            (i, key)
            for i, key in keys
            if rand.choices(
                [True, False],
                [
                    weights[i],
                    1.0 - weights[i],
                ],
            )[0]
        ]
    else:
        return keys


def get_keys_term(
    d: PromptDict,
    term: bool,
    rand: Random | None = None,
    context: Context = Context(""),
):
    return [
        (i, k)
        for i, k in get_keys_all(d, rand=rand, context=context)
        if (isinstance(d[k], str) or len(get_keys_all(cast(PromptDict, d[k]))) == 0)
        == term
    ]


def get_keys_all_recursive(
    d: PromptDict,
    prefix: list[str] | None = None,
    rand: Random | None = None,
    context: Context = Context(""),
) -> tuple[list[str], list[str]]:
    if prefix is None:
        prefix = []
    r_long: list[str] = []
    r_short: list[str] = []
    for _, k in get_keys_all(d, rand=rand, context=context):
        v = d[k]
        if isinstance(v, str):
            r_long += [".".join(prefix + [k])]
        elif len(get_keys_all(cast(PromptDict, v))) == 0:
            if "_t" in v:
                r_long += [".".join(prefix + [k])]
        elif "_else" in v or check_when(cast(PromptDict, v), context=context):
            if "_t" in v:
                r_short += [".".join(prefix + [k])]
            l, s = get_keys_all_recursive(
                cast(PromptDict, v),
                prefix + [k],
                rand=rand,
                context=context,
            )
            r_long += l
            r_short += s
    return (r_long, r_short)


def get_keys_random(
    rand: Random,
    d: PromptDict,
    branch_term: bool = False,
    context: Context = Context(""),
):
    ikeys = get_keys_term(d, branch_term, context=context)
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
    context: Context = Context(""),
):
    r: list[str] = []
    prefix: list[str] = []
    d = input_dict
    while isinstance(d, dict):
        ikeys = get_keys_all(d, context=context)
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


def export_values(d: PromptDict, prefix: str, context: Context):
    if "_exports" in d:
        for k, v in cast(dict[str, Any], d["_exports"]).items():
            if context.exports.get(k, None) != v and prefix not in context.loaded_keys:
                print("Export:", k, "=", v)
                context.exports[k] = v


def collect_prompt(
    rand: Random,
    prompt_dict: PromptDict,
    keys: str | list[str] | list[list[str]],
    context: Context,
    init_prefix: list[str] | None = None,
    parent_dict: PromptDict | None = None,
) -> list[str]:
    if parent_dict is None:
        parent_dict = prompt_dict
    if init_prefix is None:
        init_prefix = []

    if isinstance(keys, str):
        keys = build_search_keys(keys)

    init_parent_dict = parent_dict
    r: list[str] = []
    post_prompt: list[str] = []
    for key in keys:
        d = prompt_dict
        parent_dict = init_parent_dict
        key_parts = key.split(".") if isinstance(key, str) else key
        prefix = init_prefix[:]
        while len(key_parts) > 0:
            key = key_parts.pop(0)
            if key in ["?", "?$"]:
                key = get_keys_random(
                    rand,
                    cast(Any, d),
                    key.endswith("$"),
                    context=context,
                )
            elif key == "??":
                assert len(key_parts) == 0
                pick_keys = get_keys_random_recursive(
                    rand, cast(PromptDict, d), context=context
                )
                r += collect_prompt(
                    rand,
                    cast(PromptDict, d),
                    pick_keys,
                    context,
                    prefix,
                    parent_dict=parent_dict,
                )
                break
            elif key in ["*", "*$"]:
                pick_key_and_indices = get_keys_term(
                    cast(PromptDict, d),
                    key.endswith("$"),
                    rand=rand,
                    context=context,
                )
                pick_keys = [
                    ".".join([key] + key_parts) for _, key in pick_key_and_indices
                ]
                r += collect_prompt(
                    rand,
                    cast(PromptDict, d),
                    pick_keys,
                    context,
                    prefix,
                    parent_dict=parent_dict,
                )
                break
            elif key == "**":
                assert len(key_parts) == 0
                pick_keys = get_keys_all_recursive(
                    cast(PromptDict, d), rand=rand, context=context
                )
                r += collect_prompt(
                    rand,
                    cast(PromptDict, d),
                    pick_keys[1] + pick_keys[0],
                    context,
                    prefix,
                    parent_dict=parent_dict,
                )
                break

            if key != "??":
                if not isinstance(d, dict) or key not in d:
                    break

                parent_dict = cast(PromptDict, d)
                d = cast(Any, d[key])
                prefix += [key]

                if (
                    isinstance(d, dict)
                    and ("_else" in d or check_when(cast(PromptDict, d), context))
                    and ("_else" in parent_dict or check_when(parent_dict, context))
                ):
                    export_values(cast(PromptDict, d), ".".join(prefix), context)
                    # _postを処理
                    key = ".".join(prefix)
                    if (
                        "_post" in d
                        and isinstance(d["_post"], str)
                        and f"{key}._post" not in context.loaded_keys
                    ):
                        prompt = select_dynamic_prompt(
                            rand,
                            remove_comment_out(d["_post"]),
                        )
                        post_prompt = [prompt] + post_prompt
                        context.loaded_keys += [f"{key}._post"]
        else:
            # breakされてないならプロンプトを追加
            prefix_str = ".".join(prefix)
            is_term = isinstance(d, (str, list)) or len(get_keys_all(cast(Any, d))) == 0
            _ = load_prompt_var(prompt_dict, prefix[len(init_prefix) :], context)
            # ファイル読み込みの場合は上書きされてるのでparent_dictから取り直す
            d = parent_dict[prefix[-1]]
            if (prefix_str not in context.loaded_keys or is_term) and (
                check_when(parent_dict, context)
            ):
                if isinstance(d, list):
                    d = rand.choices(cast(list[Any], d), weights=None)[0]
                elif isinstance(d, dict):
                    if check_when(cast(PromptDict, d), context):
                        d = cast(str, d.get("_t", ""))
                    else:
                        d = cast(str, d.get("_else", ""))
                prompt = select_dynamic_prompt(
                    rand,
                    remove_comment_out(cast(str, d)),
                )
                if prompt:
                    r += [prompt]
                if prefix_str in context.loaded_keys:
                    print(f"Load Prompt (Duplicated): {prefix_str}")
                else:
                    context.loaded_keys += [prefix_str]
                    print(f"Load Prompt: {prefix_str}")

    return r + post_prompt
