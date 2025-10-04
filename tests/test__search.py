from typing import Any

import unittest
from toml_prompt.toml_prompt_decode import (
    get_keys_all,
    get_keys_all_recursive,
    get_keys_random_recursive,
    build_search_keys,
    collect_prompt,
)


class TestSearch(unittest.TestCase):
    def test__get_keys_all(self):
        d: dict[str, Any] = {"a": {"b": {}, "c": {}}}
        r = get_keys_all(d)
        assert r == ["a"]

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
        r = get_keys_all(d)
        assert r == ["a"]

    def test__get_keys_random_recursive(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "",
                "b": {
                    "c": {"_t": "", "d": {"_t": ""}},
                },
            }
        }
        r = get_keys_random_recursive(d)
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
        r = collect_prompt(d, build_search_keys("a.b.c"))
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
        r = collect_prompt(d, build_search_keys("a.?.c"))
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
        r = collect_prompt(d, build_search_keys("a.??"))
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
        r = collect_prompt(d, build_search_keys("a.*.c"))
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
        r = collect_prompt(d, build_search_keys("a.**"))
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
        r = collect_prompt(d, build_search_keys("a+a.?.c"))
        assert r == ["a", "c", "c"]


if __name__ == "__main__":
    unittest.main()
