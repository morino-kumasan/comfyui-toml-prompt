import unittest
from toml_prompt.toml_prompt_decode import (
    remove_comment_out,
    select_dynamic_prompt,
)

class TestBuildKey(unittest.TestCase):
    def test__comment_out(self):
        r = remove_comment_out("a//b")
        assert r == "a"
        r = remove_comment_out("a//b //c")
        assert r == "a"
        r = remove_comment_out("a#b")
        assert r == "a"
        r = remove_comment_out("a/*b*/")
        assert r == "a"
        r = remove_comment_out("""a
b// bb
/*
c
d
*/""")
        assert r == "a\nb"

    def test__dynamic_prompt(self):
        r = select_dynamic_prompt("{a | a | a}")
        assert r == "a"
        r = select_dynamic_prompt("{|}")
        assert r == ""
        r = select_dynamic_prompt("""{
a |
a |
a
}""")
        assert r == "a"

if __name__ == "__main__":
    unittest.main()
