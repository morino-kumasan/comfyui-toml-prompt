import os, sys
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from toml_prompt.toml_prompt_decode import (
    remove_comment_out,
    select_dynamic_prompt,
    expand_prompt_tag_negative,
    expand_prompt_tag_lora,
)

class TestBuildKey(unittest.TestCase):
    def test__comment_out(self):
        r = remove_comment_out("a//b")
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
        print(r)
        assert r == "a\nb\n"

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

    def test__expand_prompt_tag_lora(self):
        r = expand_prompt_tag_lora("<lora:a:1>", {"a": "A"})
        assert r == "A"

    def test__expand_prompt_tag_negative(self):
        r = expand_prompt_tag_negative("<!:this is negative prompt.>")
        print(r)
        assert r == ""
        r = expand_prompt_tag_negative("""<!:this is 
negative prompt.>""")
        assert r == ""

if __name__ == "__main__":
    unittest.main()
