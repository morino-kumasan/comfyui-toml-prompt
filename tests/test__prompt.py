import os, sys
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from toml_prompt.toml_prompt_decode import (
    remove_comment_out,
    select_dynamic_prompt,
    split_toml_prompt,
    split_toml_prompt_in_tag,
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

    def test__split_toml_prompt(self):
        r = split_toml_prompt("""a, b
c <lora:a:1>
d (d)
<if:1:(a:1)
:
<if:1:b:c>
>
e""")
        print(r)
        assert r == ["a", "b", "c", "<lora:a:1>", "d", "(d)", "<if:1:(a:1)\n:\n<if:1:b:c>\n>", "e"]

        r = split_toml_prompt("a, b, (c, d)")
        assert r == ["a", "b", "(c, d)"]

        r = split_toml_prompt(r"(a:1.2), b_(c), b \(c\), a (b) c")
        print(r)
        assert r == ["(a:1.2)", "b_(c)", r"b \(c\)", "a", "(b)", "c"]

    def test__split_toml_prompt_in_tag(self):
        r = split_toml_prompt_in_tag("""a, b
c <lora:a:1>:
d (d:1.2)
(e)
<if:1:(a:1)
:
<if:1:b:c>
>
:
e""")
        print(r)
        assert r == ["a, b\nc <lora:a:1>", "\nd (d:1.2)\n(e)\n<if:1:(a:1)\n:\n<if:1:b:c>\n>\n", "\ne"]

        r = split_toml_prompt_in_tag("lora (pony) v1.safetensors:1")
        print(r)
        assert r == ["lora (pony) v1.safetensors", "1"]

        r = split_toml_prompt_in_tag("(a), (a, b):1")
        print(r)
        assert r == ["(a), (a, b)", "1"]

if __name__ == "__main__":
    unittest.main()
