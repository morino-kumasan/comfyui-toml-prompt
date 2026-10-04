from typing import Any

import unittest
from toml_prompt.inner.util import Random
from toml_prompt.inner.prompt import PromptFile
from toml_prompt.inner.parser import PromptTagParser


class TestParser(unittest.TestCase):
    def setUp(self):
        self.random = Random(seed=None)

    def test__simple(self):
        _, t, _ = parse_prompt({"a": {"b": "a.b"}}, ["a.b"])
        assert t == "a.b"

    # _tのテスト
    def test__dict_text(self):
        _, t, _ = parse_prompt({"a": {"b": {"_t": "a.b"}}}, ["a.b"])
        assert t == "a.b"

    # ネガティブタグのテスト
    def test__negative(self):
        _, t, n = parse_prompt(
            {"a": {"_t": "a <neg>negative</neg>"}},
            ["a"],
        )
        assert t == "a" and n == "negative"

    # key.?のテスト
    def test__random_pick(self):
        _, t, _ = parse_prompt(
            {"a": {"_w": [0.0, 1.0, 0.0], "b": "b", "c": "c", "d": "d"}}, ["a.?"]
        )
        assert t == "c"
        # _kによるキー一覧の指定あり
        _, t, _ = parse_prompt(
            {"a": {"_k": ["c", "d"], "_w": [0.0, 1.0], "b": "b", "c": "c", "d": "d"}},
            ["a.?"],
        )
        assert t == "d"

    # key.*のテスト
    def test__random_each(self):
        _, t, _ = parse_prompt(
            {"a": {"_r": [0.0, 1.0, 0.0], "b": "b", "c": "c", "d": "d"}}, ["a.*"]
        )
        assert t == "c"
        # _kによるキー一覧の指定あり
        _, t, _ = parse_prompt(
            {"a": {"_k": ["c", "d"], "_r": [0.0, 1.0], "b": "b", "c": "c", "d": "d"}},
            ["a.*"],
        )
        assert t == "d"

    # _exportsのテスト
    def test__export(self):
        parser, t, _ = parse_prompt(
            {
                "a": {
                    "_w": [0.0, 1.0, 0.0],
                    "b": {"_t": "b", "_exports": {"key": "value1"}},
                    "c": {"_t": "c", "_exports": {"key": "value2"}},
                    "d": {"_t": "d", "_exports": {"key": "value3"}},
                }
            },
            ["a.?"],
        )
        assert t == "c" and parser.exports.get("key", "") == "value2"
        # 上書き確認
        parser, t, _ = parse_prompt(
            {
                "a": {
                    "_r": [0.0, 1.0, 1.0],
                    "b": {"_t": "b", "_exports": {"key": "value1"}},
                    "c": {"_t": "c", "_exports": {"key": "value2"}},
                    "d": {"_t": "d", "_exports": {"key": "value3"}},
                }
            },
            ["a.*"],
        )
        assert t == "c, d" and parser.exports.get("key", "") == "value3"

    def test__post(self):
        _, t, _ = parse_prompt(
            {"a": {"_t": "a", "_post": "post"}},
            ["a"],
        )
        assert t == "a, post"

    def test__when(self):
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when": "a"}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when": "zzz"}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when": "c"}}, "c": "c"}
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, b"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, b"
        # _whenの子要素
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when": "zzz", "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when": "a", "c": "c"}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c"

    def test__when_not(self):
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when_not": "a"}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when_not": "zzz"}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not": "c"}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a"
        # _whenの子要素
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not": "a", "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not": "zzz", "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c"

    def test__when_any(self):
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_any": ["a", "c"]}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_any": ["c", "d"]}},
            "c": "c",
            "d": "d",
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_any": ["c", "d"]}},
            "c": "c",
            "d": "d",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, b"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, b"
        # _whenの子要素
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_any": ["zzz"], "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_any": ["a"], "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c"

    def test__when_not_any(self):
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["a", "c"]}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {"a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["a"]}}}
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["c", "d"]}},
            "c": "c",
            "d": "d",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, b"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, b"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["c", "d"]}},
            "c": "c",
            "d": "d",
        }
        _, t, _ = parse_prompt(d, ["c", "d", "a.??"])
        assert t == "c, d, a"
        _, t, _ = parse_prompt(d, ["c", "d", "a.**"])
        assert t == "c, d, a"
        # _whenの子要素
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["a"], "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not_any": ["zzz"], "c": "c"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c"

    def test__when_else(self):
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when": "a", "_else": "else"}}
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when": "c", "_else": "else"}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, else"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, else"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when": "c", "_else": "else"}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, b"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, b"
        # _whenの子要素
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {"_t": "b", "_when": "a", "_else": "else", "c": "c"},
            },
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c"
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {"_t": "b", "_when": "zzz", "_else": "else", "c": "c"},
            },
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, else"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, else"

    def test__when_else_exports(self):
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "_t": "b",
                    "_when": "a",
                    "_else": "else",
                    "_exports": {"key": "value1"},
                    "c": {"_t": "c", "_exports": {"key": "value2"}},
                },
            }
        }
        parser, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b, c" and parser.exports.get("key", "") == "value2"
        parser, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c" and parser.exports.get("key", "") == "value2"
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "_t": "b",
                    "_when": "zzz",
                    "_else": "else",
                    "_exports": {"key": "value1"},
                    "c": {"_t": "c", "_exports": {"key": "value2"}},
                },
            }
        }
        parser, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, else" and parser.exports.get("key", "") == ""
        parser, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, else" and parser.exports.get("key", "") == ""

    def test__variable(self):
        _, t, _ = parse_prompt(
            {
                "a": "this is a $var.",
                "var": "pen",
            },
            ["a"],
        )
        assert t == "this is a pen."
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "<set key=var>this is</set>",
                    "b": {"_t": "<add key=var> a pen.</add>", "c": {"_t": "$var"}},
                },
                "var": "pen",
            },
            ["a.b.c"],
        )
        assert t == "this is a pen."
        # 改行してもOK
        _, t, _ = parse_prompt(
            {
                "a": "<?set var 'this\nis\na\npen.'>",
                "b": "$var",
                "var": "",
            },
            ["a", "b"],
        )
        assert t == "this is a pen."
        # <?set>が展開される前に参照
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "<?set var 'this\nis\na\npen.'>",
                    "b": "$var",
                },
                "var": "",
            },
            ["a"],
        )
        assert t == ""

    def test__tag(self):
        _, t, _ = parse_prompt(
            {
                "a": "this is a %var.",
                "var": "pen",
            },
            ["a"],
        )
        assert t == "this is a, pen."


def parse_prompt(data: dict[Any, Any], keys: list[str]):
    parser = PromptTagParser(prompt=PromptFile(path=None, json_data=data))
    parser.feed("\n".join(keys))
    p, n = parser.get_prompt()
    return (parser, p, n)


if __name__ == "__main__":
    unittest.main()
