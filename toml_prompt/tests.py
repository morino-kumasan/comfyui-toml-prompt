import unittest
from toml_prompt.toml_prompt_encoder import (
    get_keys_all,
    get_keys_all_recursive,
    build_search_keys,
    collect_prompt,
)

class TestBuildSearchKey(unittest.TestCase):
    def test__get_keys_all(self):
        d = {"a": {"b": {}, "c": {}}}
        r = get_keys_all(d)
        assert r == ["a"]

    def test__get_keys_all_recursive(self):
        d = {
            "a": {
                "b": { "_t": "" },
                "c": { "_t": "" },
                "d": {},
                "_t": "",
            }
        }
        r = get_keys_all_recursive(d)
        assert r == ["a", "a.b", "a.c"]

    def test__get_keys_random(self):
        d = {"a": {"b": {}, "c": {}}}
        r = get_keys_all(d)
        assert r == ["a"]

    def test__get_keys_random_recursive(self):
        d = {
            "a": {
                "b": {
                    "c": {
                        "d": {},
                        "_t": "",
                    },
                }
            }
        }
        r = get_keys_all_recursive(d)
        assert r == ["a.b.c"]

    def test__search_key(self):
        r = build_search_keys("a.b+d.c")
        assert r == ["a", "a.b", "a.b.c", "a.d", "a.d.c"]

    def test__search(self):
        d = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                }
            }
        }
        r = collect_prompt(d, build_search_keys("a.b.c"))
        assert r == ["a", "c"]

    def test__search_random(self):
        d = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                }
            }
        }
        r = collect_prompt(d, build_search_keys("a.?.c"))
        assert r == ["a", "c"]

    def test__search_random_recursive(self):
        d = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                }
            }
        }
        r = collect_prompt(d, build_search_keys("a.??"))
        assert r == ["a", "c"]

    def test__search_all(self):
        d = {
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
        d = {
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
        r = collect_prompt(d, build_search_keys("a.**"))
        assert r == ["a", "c", "d", "C"]

    def test__search_exclude(self):
        d = {
            "a": {
                "_t": "a",
                "b": {
                    "c": {
                        "_t": "c",
                    },
                }
            }
        }
        r = collect_prompt(d, build_search_keys("a+a.?.c"))
        assert r == ["a", "c"]
