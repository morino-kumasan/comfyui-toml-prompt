import os, sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from toml_prompt.toml_prompt_decode import (
    Random,
    remove_comment_out,
    select_dynamic_prompt,
)


class TestBuildKey(unittest.TestCase):
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
        r = select_dynamic_prompt(
            self.random,
            """{
a |
a |
a
}""",
        )
        assert r.strip() == "a"


if __name__ == "__main__":
    unittest.main()
