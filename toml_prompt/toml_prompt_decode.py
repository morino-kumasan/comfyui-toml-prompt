import re
import json

from . import InputTypesFuncResult
from .inner.prompt import (
    PromptFile,
    export_values,
    select_dynamic_prompt,
    remove_comment_out,
)
from .inner.parser import PromptTagParser
from .util import load_image


def load_summary_header(s: str):
    r: dict[str, str] = {}
    for k, v in re.findall(r"^([^:]+): (.+)$", s, flags=re.MULTILINE):
        r[k] = v
    return r


def parse_prompt(toml: PromptFile, key_name_list: str, prompt_seed: int):
    parser = PromptTagParser(prompt=toml, seed=prompt_seed)
    parser.context.exports = {"prompt_seed": f"{prompt_seed}"}
    export_values(parser.prompt_dict, ".", parser.context)

    key_name_list = select_dynamic_prompt(
        parser.random, remove_comment_out(key_name_list)
    )

    # Decode
    parser.feed(key_name_list)
    return parser


class PromptDecode:
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
    DESCRIPTION = "Load prompt."

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
        parser = parse_prompt(toml, key_name_list, seed)
        positive, negative = parser.get_prompt()
        lora_list = parser.get_lora_list()
        exports = parser.get_exports()
        summary = f"{exports}\n\n---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}"
        exports = json.dumps(load_summary_header(exports))
        return (positive, negative, lora_list, seed, summary, exports)


class PromptDecodeV2:
    RETURN_TYPES = (
        "STRING",
        "STRING",
        "STRING",
        "INT",
        "STRING",
        "STRING",
        "IMAGE",
        "IMAGE",
        "IMAGE",
    )
    OUTPUT_TOOLTIPS = (
        "Positive prompt",
        "Negative prompt",
        "Loaded LoRA name list",
        "Random seed",
        "Summary",
        "Exports",
        "Output Image1",
        "Output Image2",
        "Output Image3",
    )
    FUNCTION = "load_prompt"
    CATEGORY = "utils"
    DESCRIPTION = "Load prompt."

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
        parser = parse_prompt(toml, key_name_list, seed)
        positive, negative = parser.get_prompt()
        lora_list = parser.get_lora_list()
        exports = parser.get_exports()
        summary = f"{exports}\n\n---- Positive ----\n{positive}\n\n---- Negative ----\n{negative}\n\n---- LoRA ----\n{lora_list}"
        exports = json.dumps(load_summary_header(exports))
        images = [None, None, None]
        for i, path in enumerate(parser.images):
            if path is not None:
                images[i] = load_image(path)
        return (
            positive,
            negative,
            lora_list,
            seed,
            summary,
            exports,
            images[0],
            images[1],
            images[2],
        )


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
    DESCRIPTION = "Read summary from PromptDecode."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "summary": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "tooltip": "PromptDecode summary.",
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
