import os, sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Any

import unittest
from toml_prompt.toml_prompt_decode import (
    Random,
    get_keys_all,
    get_keys_all_recursive,
    get_keys_random_recursive,
    build_search_keys,
    collect_prompt,
)


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.random = Random(seed=None)

    def test__get_keys_all(self):
        d: dict[str, Any] = {"a": {"b": {}, "c": {}}}
        r = get_keys_all(d)
        assert r == [(0, "a")]

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
        assert r == [(0, "a")]

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
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"))
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
        r = collect_prompt(self.random, d, build_search_keys("a.?.c"))
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
        r = collect_prompt(self.random, d, build_search_keys("a.??"))
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
        r = collect_prompt(self.random, d, build_search_keys("a.*.c"))
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
        r = collect_prompt(self.random, d, build_search_keys("a.**"))
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
        r = collect_prompt(self.random, d, build_search_keys("a+a.?.c"))
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
            }
        }
        post_keys: list[str] = []
        r = collect_prompt(
            self.random, d, build_search_keys("a.??"), post_keys=post_keys
        )
        r += collect_prompt(self.random, d, post_keys)
        print(build_search_keys("a.??"), r)
        assert r == ["a", "c", "post_a", "post_c"]

    def test__search_variable(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "$d c",
                        "d": "d",
                    },
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"))
        assert r == ["a", "<var>a.b.c.d</var> c"]

    def test__search_variable_global(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "$::a.d c",
                    },
                },
                "d": "d",
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"))
        assert r == ["a", "<var>a.d</var> c"]

    def test__search_tag(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "%d c",
                        "d": "d",
                    },
                },
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"))
        assert r == ["a", "<tag>a.b.c.d</tag> c"]

    def test__search_tag_global(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "%::a.d c",
                    },
                },
                "d": "d",
            }
        }
        r = collect_prompt(self.random, d, build_search_keys("a.b.c"))
        assert r == ["a", "<tag>a.d</tag> c"]

    def test__search_post_str(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "_post": "post",
            }
        }
        post_keys: list[str] = []
        r = collect_prompt(self.random, d, build_search_keys("a"), post_keys=post_keys)
        r += collect_prompt(self.random, d, post_keys)
        assert r == ["a", "post"]

    def test__search_post_when(self):
        d: dict[str, Any] = {
            "a": {
                "_t": "a",
                "_post": {
                    "d": {
                        "e": {
                            "_when": "a.b",
                            "_w": [1.0],
                            "e": "one1",
                        },
                        "f": {
                            "_post": "post_post",
                            "_when": "a.c",
                            "_w": [1.0],
                            "f": "one2",
                        },
                    },
                    "g": {"_t": "g"},
                    "h": "h",
                },
                "b": "b",
                "c": "c",
            }
        }
        post_keys: list[str] = []
        exclude_keys: list[str] = []
        r = collect_prompt(
            self.random,
            d,
            build_search_keys("a.b"),
            post_keys=post_keys,
            exclude_keys=exclude_keys,
        )
        r += collect_prompt(self.random, d, post_keys, exclude_keys=exclude_keys)
        assert r == ["a", "b", "one1", "g", "h"]

        post_keys: list[str] = []
        exclude_keys: list[str] = []
        r = collect_prompt(
            self.random,
            d,
            build_search_keys("a.c"),
            post_keys=post_keys,
            exclude_keys=exclude_keys,
        )
        post_keys2: list[str] = []
        r += collect_prompt(
            self.random, d, post_keys, exclude_keys=exclude_keys, post_keys=post_keys2
        )
        r += collect_prompt(self.random, d, post_keys2, exclude_keys=exclude_keys)
        assert r == ["a", "c", "one2", "g", "h", "post_post"]


if __name__ == "__main__":
    unittest.main()
