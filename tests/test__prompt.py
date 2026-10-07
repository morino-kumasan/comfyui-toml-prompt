from typing import Any

import unittest
from toml_prompt.inner.util import Random
from toml_prompt.inner.prompt import (
    Context,
    get_keys_all,
    get_keys_all_recursive,
    get_keys_random,
    get_keys_random_recursive,
    build_search_keys,
    collect_prompt,
    remove_comment_out,
    select_dynamic_prompt,
)


class TestPrompt(unittest.TestCase):
    def setUp(self):
        self.random = Random(seed=None)

    def test__comment_out(self):
        r = remove_comment_out("a//b")
        assert r == "a"
        r = remove_comment_out("a//b //c")
        assert r == "a"
        r = remove_comment_out("a#b")
        assert r == "a"
        r = remove_comment_out("a/*b*/")
        assert r == "a"
        r = remove_comment_out(
            """a
b// bb
/*
c
d
*/"""
        )
        assert r.strip() == "a\nb"

    def test__dynamic_prompt(self):
        r = select_dynamic_prompt(self.random, "{a | a | a}")
        assert r.strip() == "a"
        r = select_dynamic_prompt(self.random, "{|}")
        assert r == ""
        # 改行
        r = select_dynamic_prompt(
            self.random,
            """{
a |
a |
a
}""",
        )
        assert r.strip() == "a"
        # 1択
        r = select_dynamic_prompt(self.random, "{abc}")
        assert r == "abc"
        # ネスト
        r = select_dynamic_prompt(self.random, "{a|{a|a}}")
        assert r == "a"
        # 変数はそのまま
        r = select_dynamic_prompt(self.random, "${var}")
        assert r == "${var}"

    def test__get_keys_all(self):
        d: dict[str, Any] = {"a": {"b": {}, "c": {}}}
        r = get_keys_all(d)
        assert r == [(0, "a")]

    def test__get_keys_all_recursive_when_else(self):
        context = Context("")
        d: dict[str, Any] = {"a": {"b": {"_t": "b", "_when": "b"}}}
        r, _ = get_keys_all_recursive(d, context=context)
        assert r == []
        d: dict[str, Any] = {"a": {"b": {"_t": "b", "_when": "b", "_else": "else"}}}
        r, _ = get_keys_all_recursive(d, context=context)
        assert r == ["a.b"]

    def test__get_keys_all_recursive(self):
        d: dict[str, Any] = {
            "a": {
                "b": {"_t": ""},
                "c": "",
                "d": {},
                "_t": "",
            }
        }
        r1, r2 = get_keys_all_recursive(d)
        print(r1, r2)
        assert r1 == ["a.b", "a.c"]
        assert r2 == ["a"]

    def test__get_keys_random(self):
        d: dict[str, Any] = {"a": {"b": {}, "c": {}}}
        r = get_keys_random(self.random, d)
        assert r == "a"

    def test__get_keys_random_recursive(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "",
                "b": {
                    "c": {"_t": "", "d": {"_t": ""}},
                },
            }
        }
        r = get_keys_random_recursive(self.random, d)
        assert r == ["a", "a.b.c", "a.b.c.d"]

    def test__search_key(self):
        r = build_search_keys("a.b+d.c")
        assert r == ["a", "a.b", "a.b.c", "a.d", "a.d.c"]

    def test__search_key_random(self):
        r = build_search_keys("a.?.c")
        assert r == ["a", "a.?", "a.?.c"]
        r = build_search_keys("a.b.?")
        assert r == ["a", "a.b", "a.b.?$"]

    def test__search_key_all(self):
        r = build_search_keys("a.*.c")
        assert r == ["a", "a.*", "a.*.c"]
        r = build_search_keys("a.b.*")
        assert r == ["a", "a.b", "a.b.*$"]

    def test__search(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"), Context(""))
        assert r == ["a", "c"]

    def test__search_random(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                },
                "d": "d",
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.?.c"), Context(""))
        print(build_search_keys("a.?.c"), r)
        assert r == ["a", "c"]

    def test__search_random_recursive(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.??"), Context(""))
        assert r == ["a", "c"]

    def test__search_all(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                },
                "d": {
                    "_t": "d",
                    "c": {
                        "_t": "C",
                    },
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.*.c"), Context(""))
        assert r == ["a", "d", "c", "C"]

    def test__search_all_recursive(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                },
                "d": {
                    "_t": "d",
                    "c": "C",
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.**"), Context(""))
        assert r == ["a", "d", "c", "C"]

    def test__search_exclude(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": "c",
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a+a.?.c"), Context(""))
        assert r == ["a", "c", "c"]

    def test__search_post(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "_post": "post_a",
                "b": {
                    "c": {
                        "_t": "c",
                        "_post": "post_c",
                    },
                },
            },
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"), Context(""))
        print(build_search_keys("a.??"), r)
        assert r == ["a", "c", "post_c", "post_a"]


if __name__ == "__main__":
    unittest.main()
