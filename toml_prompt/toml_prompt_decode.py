import re
import json

from . import InputTypesFuncResult
from .inner.prompt import (
    PromptFile,
    export_values,
    select_dynamic_prompt,
    remove_comment_out,
)
from .inner.parser import TomlKeyListParser


def load_summary_header(s: str):
    r: dict[str, str] = {}
    for k, v in re.findall(r"^([^:]+): (.+)$", s, flags=re.MULTILINE):
        r[k] = v
    return r


def normalize_prompt(s: str):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r", ", ",", s)
    s = re.sub(r",+", ",", s)
    s = re.sub(r"\.,", ".", s)
    return s[1:] if s.startswith(",") else s


class TomlPromptDecode:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING", "STRING")
    OUTPUT_TOOLTIPS = (
        "Positive prompt",
        "Negative prompt",
        "Loaded LoRA name list",
        "Random seed",
        "Summary",
        "Exports",
    )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Load toml prompt."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "key_name_list": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "tooltip": "Select Key Name",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Random seed.",
                    },
                ),
                "toml": (
                    "PROMPT_FILE",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "defaultInput": True,
                        "tooltip": "TOML format prompt.",
                    },
                ),
            }
        }

    def __init__(self):
        pass

    def load_prompt(self, seed: int, toml: PromptFile, key_name_list: str):
        parser = TomlKeyListParser(toml=toml, seed=seed)
        parser.exports = {"prompt_seed": f"{seed}"}
        export_values(parser.prompt_dict, parser.exports, ".", [])

        key_name_list = select_dynamic_prompt(
            parser.random, remove_comment_out(key_name_list)
        )

        # Decode
        parser.feed(key_name_list)
        positive = normalize_prompt(
            ",".join([v.strip() for v in parser.positive if v.strip()])
        )
        negative = normalize_prompt(
            ",".join([v.strip() for v in parser.negative if v.strip()])
        )

        lora_list = "\n".join(parser.loras)
        if parser.loras_low:
            lora_list += "\n--\n"
            lora_list += "\n".join(parser.loras_low)
        exports = "\n".join(["{}: {}".format(k, v) for k, v in parser.exports.items()])
        summary = f"{exports}\n\n---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}"
        exports = json.dumps(load_summary_header(exports))
        return (positive, negative, lora_list, seed, summary, exports)


class SummaryReader:
    RETURN_TYPES = ("STRING", "STRING", "STRING", "INT", "STRING")
    OUTPUT_TOOLTIPS = (
        "Positive prompt",
        "Negative prompt",
        "Loaded LoRA name list",
        "Random seed",
        "Json Formatted Exports",
    )
    FUNCTION = "read"
    CATEGORY = "utils"
    DESCRIPTION = "Read summary from TomlPromptDecode."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "summary": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "tooltip": "TomlPromptDecode summary.",
                    },
                ),
            }
        }

    def __init__(self):
        pass

    def read(self, summary: str):
        positive = None
        negative = None
        lora_list = None
        seed = None
        exports = {}

        def set(t: str | None, b: int, e: int):
            nonlocal positive, negative, lora_list, seed
            if t == "positive":
                positive = summary[b:e].strip()
            elif t == "negative":
                negative = summary[b:e].strip()
            elif t == "lora":
                lora_list = summary[b:e].strip()
            elif t == "seed":
                seed = float(summary[b:e].strip())

        beg = 0
        type_ = None
        for m in re.finditer(
            r"\n*---- ([a-zA-Z0-9]+) ----\n", summary, flags=re.MULTILINE
        ):
            s, e = m.span()
            set(type_, beg, s)
            if beg == 0:
                exports = load_summary_header(summary[:s])
            beg = e
            type_ = m.group(1).lower()
        set(type_, beg, len(summary))

        assert positive is not None and negative is not None and lora_list is not None

        if "seed" in exports:
            seed = int(exports["seed"])
        elif seed is not None:
            exports["seed"] = seed
        else:
            assert True, "Seed Not Found"

        return (positive, negative, lora_list, seed, json.dumps(exports))


class SplitLoraList:
    RETURN_TYPES = ("STRING", "STRING")
    OUTPUT_TOOLTIPS = ("High noise lora list.", "Low noise lora list.")
    FUNCTION = "split"
    CATEGORY = "utils"
    DESCRIPTION = "Split lora list."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "lora_list": (
                    "STRING",
                    {"defaultInput": True, "multiline": True, "tooltip": "Lora list."},
                ),
            }
        }

    def __init__(self):
        pass

    def split(self, lora_list: str):
        r = lora_list.split("\n--\n", 1)
        return (r[0], r[1] if len(r) == 2 else "")
