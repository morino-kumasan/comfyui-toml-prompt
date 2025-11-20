from typing import Any, cast

import os
import re
import functools
import tomllib
import yaml

from .util import Random

type PromptDict = dict[str, Any | list[Any] | PromptDict]


class PromptFile:
    def __init__(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            self.text = f.read()
        self.path = path
        self.file_type = os.path.splitext(path)[1]

    def load(self) -> PromptDict:
        if self.file_type in [".toml", ".txt"]:
            return cast(PromptDict, tomllib.loads(self.text))
        elif self.file_type in [".yaml", ".yml"]:
            return yaml.safe_load(self.text)
        else:
            raise Exception(f"Unknown file type: {self.file_type}")


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
        if len(weights) < len(indices):
            weights += [1.0 for _ in range(len(indices) - len(weights))]
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
    keys: str | list[str] | list[list[str]],
    exclude_keys: list[str] | None = None,
    init_prefix: list[str] | None = None,
    root_dict: PromptDict | None = None,
    parent_dict: PromptDict | None = None,
    exports: dict[str, str] = {},
    root_dir: str | None = None,
    post_keys: list[str] | None = None,
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
        key_parts = key.split(".") if isinstance(key, str) else key
        prefix = init_prefix[:]
        while len(key_parts) > 0:
            key = key_parts.pop(0)
            if key in ["?", "?$"]:
                key = get_keys_random(
                    rand,
                    cast(PromptDict, d),
                    key.endswith("$"),
                    loaded_keys=exclude_keys,
                )
            elif key == "??":
                assert len(key_parts) == 0
                if not isinstance(d, str) and len(get_keys_all(cast(Any, d))) > 0:
                    pick_keys = get_keys_random_recursive(
                        rand, cast(PromptDict, d), loaded_keys=exclude_keys
                    )
                    r += collect_prompt(
                        rand,
                        cast(PromptDict, d),
                        pick_keys,
                        exclude_keys,
                        prefix,
                        root_dict=root_dict,
                        parent_dict=parent_dict,
                        exports=exports,
                        root_dir=root_dir,
                        post_keys=post_keys,
                    )
                    break
                if ".".join(prefix) in exclude_keys:
                    break
            elif key in ["*", "*$", "*!"]:
                pick_keys = (
                    get_keys_term(
                        cast(PromptDict, d),
                        key.endswith("$"),
                        rand=rand,
                        loaded_keys=exclude_keys,
                    )
                    if not key.endswith("!")
                    else get_keys_all(
                        cast(PromptDict, d), rand=rand, loaded_keys=exclude_keys
                    )
                )
                pick_keys = [".".join([key] + key_parts) for _, key in pick_keys]
                r += collect_prompt(
                    rand,
                    cast(PromptDict, d),
                    pick_keys,
                    exclude_keys,
                    prefix,
                    root_dict=root_dict,
                    parent_dict=parent_dict,
                    exports=exports,
                    root_dir=root_dir,
                    post_keys=post_keys,
                )
                break
            elif key == "**":
                assert len(key_parts) == 0
                pick_keys = get_keys_all_recursive(
                    cast(PromptDict, d), rand=rand, loaded_keys=exclude_keys
                )
                r += collect_prompt(
                    rand,
                    cast(PromptDict, d),
                    pick_keys[1] + pick_keys[0],
                    exclude_keys,
                    prefix,
                    root_dict=root_dict,
                    parent_dict=parent_dict,
                    exports=exports,
                    root_dir=root_dir,
                    post_keys=post_keys,
                )
                break
            elif key.endswith("()"):
                key_parts = ["_f"] + key_parts
                key = key[:-2]

            if key != "??":
                if not isinstance(d, dict) or key not in d:
                    break

                parent_dict = cast(PromptDict, d)
                d = cast(Any, d[key])
                prefix += [key]

                export_values(d, exports, ".".join(prefix), exclude_keys)
                if isinstance(d, dict):
                    # _postを処理
                    key = ".".join(prefix)
                    if "_post" in d and f"{key}._post" not in exclude_keys:
                        if isinstance(d["_post"], dict):
                            order = cast(PromptDict, d["_post"]).get("_order", "last")
                            if order == "last":
                                post_keys += [f"{key}._post.*!.??"]
                            else:
                                order = int(cast(str | int, order))
                                post_keys.insert(order, f"{key}._post.*!.??")
                        else:
                            post_keys += [f"{key}._post"]
                        exclude_keys += [f"{key}._post"]
                    # _random_countを処理
                    if "_random_count" in d:
                        rand.set_count(int(cast(int, d["_random_count"])))
        else:
            prefix_str = ".".join(prefix)
            is_term = isinstance(d, (str, list)) or len(get_keys_all(cast(Any, d))) == 0
            is_dict = isinstance(d, dict)
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
    return r
