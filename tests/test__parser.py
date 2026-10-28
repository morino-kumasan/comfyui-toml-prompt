from typing import Any

import unittest
import pathlib
from toml_prompt.inner.util import Random
from toml_prompt.inner.prompt import PromptFile
from toml_prompt.inner.parser import PromptTagParser, LINE_CONTINUATION


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

    # loaded_keysのテスト
    def test__loaded_keys(self):
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {"_t": "b"},
            }
        }
        _, t, _ = parse_prompt(d, ["a.b", "a.b"])
        assert t == "a, b, b"
        _, t, _ = parse_prompt(d, ["a.?", "a.?"])
        assert t == "a, b, b"
        _, t, _ = parse_prompt(d, ["a.??", "a.??"])
        assert t == "a, b, b"
        _, t, _ = parse_prompt(d, ["a.*", "a.*"])
        assert t == "a, b, b"
        _, t, _ = parse_prompt(d, ["a.**", "a.**"])
        assert t == "a, b, b"

    # key.?のテスト
    def test__random_pick(self):
        _, t, _ = parse_prompt(
            {"a": {"_w": [0.0, 1.0, 0.0], "b": "b", "c": "c", "d": "d"}},
            ["a.?"],
        )
        assert t == "c"
        # _kによるキー一覧の指定あり
        _, t, _ = parse_prompt(
            {"a": {"_k": ["c", "d"], "_w": [0.0, 1.0], "b": "b", "c": "c", "d": "d"}},
            ["a.?"],
        )
        assert t == "d"
        # 途中をランダム
        _, t, _ = parse_prompt(
            {
                "a": {
                    "b": {"_t": "b", "e": "e"},
                    "c": {"_t": "c", "e": "e"},
                    "d": {"_t": "d", "e": "e"},
                }
            },
            ["a.?.e"],
        )
        assert t.endswith(", e") and len(t) == 4
        # recursive
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "a\n%{a.??}",
                    "b": {
                        "_t": "b",
                    },
                }
            },
            ["a.??"],
        )
        assert t == "a, b, b"
        # listも含める
        _, t, _ = parse_prompt(
            {"a": {"b": ["b1", "b2"]}},
            ["a.??"],
        )
        assert t in ["b1", "b2"]

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
        # depthに違いのあるdictの**の動作
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "a",
                    "b": "b",
                    "c": {
                        "_t": "c",
                    },
                    "d": {
                        "_t": "d",
                        "e": {"_t": "e"},
                        "f": {"_t": "f", "_when": "a"},
                    },
                    "g": "g",
                },
            },
            ["a.**"],
        )
        assert t == "a, b, c, d, e, f, g"
        # recursive
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "a\n%{a.**}",
                    "b": {
                        "_t": "b",
                    },
                }
            },
            ["a.**"],
        )
        assert t == "a, b, b"
        # listも含める
        _, t, _ = parse_prompt(
            {"a": {"b": ["b1", "b2"]}},
            ["a.**"],
        )
        assert t in ["b1", "b2"]

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
        assert t == "c" and parser.context.exports.get("key", "") == "value2"
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
        assert t == "c, d" and parser.context.exports.get("key", "") == "value3"
        # whenが一致してないので無視
        parser, t, _ = parse_prompt(
            {
                "a": {
                    "b": {"_t": "b", "_when": "zzz", "_exports": {"key": "value1"}},
                }
            },
            ["a.*"],
        )
        assert t == "" and parser.context.exports.get("key", "") == ""

    def test__post(self):
        _, t, _ = parse_prompt(
            {"a": {"_t": "a", "_post": "post"}},
            ["a"],
        )
        assert t == "a, post"
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "a",
                    "_post": "post",
                    "b": {
                        "_t": "b",
                        "_post": "post2",
                    },
                }
            },
            ["a.??"],
        )
        assert t == "a, b, post2, post"

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
        # recursive
        _, t, _ = parse_prompt(
            {
                "a": {
                    "_t": "a\n%{a.??}",
                    "b": {
                        "_when": "a",
                        "_t": "b",
                    },
                }
            },
            ["a.??"],
        )
        assert t == "a, b, b"

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
        # _when_not
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not": "c", "_else": "else"}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, b"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b"
        d: dict[Any, Any] = {
            "a": {"_t": "a", "b": {"_t": "b", "_when_not": "c", "_else": "else"}},
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, else"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, else"
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
        # _when, _else, _post
        d: dict[Any, Any] = {
            "a": {
                "_t": "a",
                "b": {"_t": "b", "_when": "c", "_else": "else", "_post": "post"},
            },
            "c": "c",
        }
        _, t, _ = parse_prompt(d, ["c", "a.??"])
        assert t == "c, a, b, post"
        _, t, _ = parse_prompt(d, ["a.??"])
        assert t == "a, else, post"
        _, t, _ = parse_prompt(d, ["c", "a.**"])
        assert t == "c, a, b, post"
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, else, post"
        # ネストした_when, _else, _post
        d: dict[Any, Any] = {
            "a": {
                "_when": "d",
                "b": {
                    "_when": "e",
                    "c": {
                        "_when": "f",
                        "_t": "c",
                        "_else": "else",
                        "_post": "post",
                    },
                },
            },
            "d": "d",
            "e": "e",
            "f": "f",
        }
        _, t, _ = parse_prompt(d, ["a.**"])
        assert t == ""
        _, t, _ = parse_prompt(d, ["d", "a.**"])
        assert t == "d"
        _, t, _ = parse_prompt(d, ["d", "e", "a.**"])
        assert t == "d, e, else, post"
        _, t, _ = parse_prompt(d, ["d", "e", "f", "a.**"])
        assert t == "d, e, f, c, post"

    def test__when_nest(self):
        d: dict[Any, Any] = {
            "f1": "",
            "f2": "",
            "a": {
                "b": {
                    "_when": "f1",
                    "c": {
                        "_when": "f2",
                        "_t": "c",
                    },
                },
            },
        }
        _, t, _ = parse_prompt(d, ["f1", "f2", "a.**"])
        assert t == "c"

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
        assert t == "a, b, c" and parser.context.exports.get("key", "") == "value2"
        parser, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, b, c" and parser.context.exports.get("key", "") == "value2"
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
        assert t == "a, else" and parser.context.exports.get("key", "") == "value2"
        parser, t, _ = parse_prompt(d, ["a.**"])
        assert t == "a, else" and parser.context.exports.get("key", "") == "value2"

    def test__variable(self):
        _, t, _ = parse_prompt(
            {
                "a": "$var",
                "var": "pen",
            },
            ["a"],
        )
        assert t == "pen"
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
                "a": "this is a ${var}.",
                "var": "pen",
            },
            ["a"],
        )
        assert t == "this is a pen."
        _, t, _ = parse_prompt(
            {
                "a": "this is $var pen.",
                "var": "a",
            },
            ["a"],
        )
        assert t == "this is a pen."
        # カッコ
        _, t, _ = parse_prompt(
            {
                "a": "this is ($var) pen.",
                "var": "a",
            },
            ["a"],
        )
        assert t == "this is (a) pen."
        _, t, _ = parse_prompt(
            {
                "a": "this is [$var] pen.",
                "var": "a",
            },
            ["a"],
        )
        assert t == "this is [a] pen."
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
        # 途中も無視しない
        _, t, _ = parse_prompt(
            {
                "a": "this is a $var.v1.",
                "var": {
                    "_t": "gold",
                    "v1": "pen",
                },
            },
            ["a"],
        )
        assert t == "this is a gold, pen."
        # 変数に追加
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
        # +で連結
        _, t, _ = parse_prompt(
            {
                "a": "this is ${var+col} pen.",
                "var": "a",
                "col": "gold",
            },
            ["a"],
        )
        assert t == "this is a, gold pen."

    def test__tag(self):
        _, t, _ = parse_prompt(
            {
                "a": "this is a %var.",
                "var": "pen",
            },
            ["a"],
        )
        assert t == "this is a, pen."
        # 途中も無視しない
        _, t, _ = parse_prompt(
            {
                "a": "this is a %var.v1.",
                "var": {
                    "_t": "hoge",
                    "v1": "pen",
                },
            },
            ["a"],
        )
        assert t == "this is a, hoge, pen."

    def test__newline(self):
        _, t, _ = parse_prompt(
            {"a": r"this is \na pen."},
            ["a"],
        )
        print(t)
        assert t == "this is \na pen."

    def test__when_tag(self):
        # key
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key=a>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key=zzz>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen."
        # key_not
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not=zzz>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not=a>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen."
        # key_any
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_any=a key_any=zzz>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_any=zzz>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen."
        # key_not_any
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not_any=zzz key_not_any=a>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not_any=a>, it is gold</when>."
            },
            ["a"],
        )
        assert t == "this is a pen."
        # key_empty
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_empty=b>, it is gold</when>.",
                "b": "",
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_empty=b>, it is gold</when>.",
                "b": "b",
            },
            ["a"],
        )
        assert t == "this is a pen."
        # key_not_empty
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not_empty=b>, it is gold</when>.",
                "b": "",
            },
            ["a"],
        )
        assert t == "this is a pen."
        _, t, _ = parse_prompt(
            {
                "a": rf"this is a pen {LINE_CONTINUATION} <when key_not_empty=b>, it is gold</when>.",
                "b": "b",
            },
            ["a"],
        )
        assert t == "this is a pen, it is gold."

    def test__variable_in_set_tag(self):
        _, t, _ = parse_prompt(
            {
                "a": "<set key=var2>this is a ${var} pen.</set>",
                "b": "${var2}",
                "var": "gold",
                "var2": "",
            },
            ["a", "b"],
        )
        assert t == "this is a gold pen."
        # **で実行
        _, t, _ = parse_prompt(
            {
                "p": {
                    "a": "<set key=var2>this is a ${var} pen.</set>",
                    "b": "${var2}",
                },
                "a": "%{p.**}",
                "var": "gold",
                "var2": "",
            },
            ["a"],
        )
        assert t == "this is a gold pen."
        # 更にwhenタグ内
        _, t, _ = parse_prompt(
            {
                "p": {
                    "a": "<when key=a><set key=var2>this is a ${var} pen.</set></when>",
                    "b": "${var2}",
                },
                "p2": {
                    "a": "${var2}",
                },
                "a": "%{p.**}, %{p2.**}",
                "var": "gold",
                "var2": "",
            },
            ["a"],
        )
        print(t)
        assert t == "this is a gold pen. this is a gold pen."

    def test__lora_tag(self):
        parser, t, _ = parse_prompt(
            {
                "a": "<lora:test.safetensors:1.0>",
                "b": "<lora:d/test2.safetensors:2.0>",
                "c": "<lora:d/test3.safetensors:3.0>",
                "<lora>": {
                    "test.safetensors": "test",
                    "test2.safetensors": "test2",
                    "d/test3.safetensors": "test3",
                },
            },
            ["a", "b", "c"],
        )
        assert len(parser.loras) == 3
        assert parser.loras[0] == "<lora:test.safetensors:1.0>"
        assert parser.loras[1] == "<lora:d/test2.safetensors:2.0>"
        assert parser.loras[2] == "<lora:d/test3.safetensors:3.0>"
        assert t == "test, test2, test3"

    def test__lora_tag_overwrite(self):
        parser, t, _ = parse_prompt(
            {
                "a": "<lora:d/test.safetensors:1.0>",
                "b": "<lora:d/test.safetensors:2.0>",
                "c": "<lora:test2.safetensors:3.0>",
                "<lora>": {
                    "d/test.safetensors": "test",
                    "test2.safetensors": "test2",
                },
            },
            ["a", "b", "c"],
        )
        assert len(parser.loras) == 2
        assert parser.loras[0] == "<lora:d/test.safetensors:2.0>"
        assert parser.loras[1] == "<lora:test2.safetensors:3.0>"
        assert t == "test, test2"

    def test__h3_tag(self):
        _, t, _ = parse_prompt(
            {
                "a": "<Subject man1>: The man shown in <Picture man1>.",
                "b": "<Subject man2>: The man shown in <Picture 2>.",
                "c": "<Subject man1> and <Subject man2>'s child is fighting.",
            },
            ["a", "b", "c"],
        )
        assert (
            t
            == "<Subject 1>: The man shown in <Picture 1>. <Subject 2>: The man shown in <Picture 2>. <Subject 1> and <Subject 2>'s child is fighting."
        )
        # setで指定
        _, t, _ = parse_prompt(
            {
                "a": "<?set v '<Subject man1\\> is fighting.'>",
                "b": "[Shot 1] ${v}",
                "v": "",
            },
            ["a", "b"],
        )
        print(t)
        assert t == "[Shot 1] <Subject 1> is fighting."
        # set tagで指定
        _, t, _ = parse_prompt(
            {
                "a": "<set key=v><Picture man1></set>",
                "b": "The man is shown in ${v}.",
                "v": "",
            },
            ["a", "b"],
        )
        print(t)
        assert t == "The man is shown in <Picture 1>."

    def test__h3_tag_set_image(self):
        d: dict[str, Any] = {
            "a": "The man shown in <Picture man1>.",
            "b": "The man shown in <Picture man2>.",
            "c": "<load type=picture key=man2>${dir}/a.jpg</load>",
            "d": "dir is ${dir}.",
            "dir": "path/to",
        }
        parser, t, _ = parse_prompt(d, ["d"])
        assert t == "dir is path/to."
        parser, t, _ = parse_prompt(d, ["a", "b", "c"])
        references = parser.references.get_summary()
        assert len(references) == 1
        assert "<Picture 2>" in references
        assert references["<Picture 2>"] == "path/to/a.jpg"
        assert t == "The man shown in <Picture 1>. The man shown in <Picture 2>."
        parser, t, _ = parse_prompt(d, ["c", "a", "b"])
        references = parser.references.get_summary()
        assert len(references) == 1
        assert "<Picture 1>" in references
        assert references["<Picture 1>"] == "path/to/a.jpg"
        assert t == "The man shown in <Picture 2>. The man shown in <Picture 1>."

    def test__include(self):
        d: dict[str, Any] = {
            "a": {"!include": f"{pathlib.Path(__file__).parent}/a.yaml"},
            "b": {
                "p1": {
                    "_t": "${b.p1.list}",
                    "list": ["<?set a._key v1>", "<?set a._key v2>"],
                },
                "p2": {
                    "_t": "${b.p2.list}",
                    "list": ["<?set a._key v1>", "<?set a._key v2>"],
                },
            },
            "c": {"a": {"!include": f"{pathlib.Path(__file__).parent}/c.yaml"}},
        }
        _, t, _ = parse_prompt(d, ["b.??", "a._key"])  # ファイル読み込み部分への<?set>
        assert t in ["v1", "v2"]
        # c.??でc.a._tの読み込みを確認
        _, t, _ = parse_prompt(d, ["a.??", "a._key"])
        assert t in ["v1", "v2"]
        _, t, _ = parse_prompt(
            {
                "c": {"a": {"!include": f"{pathlib.Path(__file__).parent}/c.yaml"}},
            },
            ["c.??"],
        )
        assert t == "c, hoge"

    def test__include_route(self):
        _, t, _ = parse_prompt(
            {
                "a": {"!include": f"{pathlib.Path(__file__).parent}/a.yaml"},
            },
            ["<?route fix a p1>", "a.??", "a._key"],
        )
        assert t in ["v1", "v2"]
        d: dict[str, Any] = {
            "a": {"b": {"!include": f"{pathlib.Path(__file__).parent}/a_b.yaml"}},
        }
        _, t, _ = parse_prompt(d, ["<?route fix a b.p1>", "a.??", "a.b._key"])
        assert t in ["v1", "v2"]
        _, t, _ = parse_prompt(d, ["<?route fix a.b p1>", "a.??", "a.b._key"])
        assert t in ["v1", "v2"]

    def test__include_grep(self):
        _, t, _ = parse_prompt(
            {
                "a": {"!include": f"{pathlib.Path(__file__).parent}/a.txt"},
            },
            ["<?grep a.value 2>", "a.value"],
        )
        assert t == "line2"
        _, t, _ = parse_prompt(
            {
                "a": {"b": {"!include": f"{pathlib.Path(__file__).parent}/a.txt"}},
            },
            ["<?grep a.b.value 2>", "a.b.value"],
        )
        assert t == "line2"

    def test__include_lora(self):
        parser, t, _ = parse_prompt(
            {
                "a": "<lora:a.safetensors:1.0>",
                "b": "<lora:b.safetensors:1.0>",
                "<lora>": {"!include": f"{pathlib.Path(__file__).parent}/lora.yaml"},
            },
            ["a", "b"],
        )
        assert len(parser.loras) == 2
        assert parser.loras[0] == "<lora:a.safetensors:1.0>"
        assert parser.loras[1] == "<lora:b.safetensors:1.0>"
        assert t == "a, b"

    def test__rendom_count(self):
        parser, t, _ = parse_prompt(
            {
                "a": {"_t": "a", "b": "b, %{var}, ${var}"},
                "var": "",
            },
            ["a.b"],
        )
        assert t == "a, b," and parser.random.count == 0
        parser, t, _ = parse_prompt(
            {
                "a": {"_t": "a", "b": "b"},
            },
            ["a.?"],
        )
        assert t == "a, b" and parser.random.count == 1


def parse_prompt(data: dict[Any, Any], keys: list[str]):
    parser = PromptTagParser(prompt=PromptFile(path=None, json_data=data))
    parser.feed("\n".join(keys))
    p, n = parser.get_prompt()
    return (parser, p, n)


if __name__ == "__main__":
    unittest.main()
