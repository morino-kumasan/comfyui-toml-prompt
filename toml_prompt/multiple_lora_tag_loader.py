from typing import cast

import os
from functools import reduce

from folder_paths import get_filename_list  # type: ignore


class MultipleLoraTagLoader:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("LoRA tag list separated by line break",)
    FUNCTION = "create_tags"
    CATEGORY = "utils"
    DESCRIPTION = "Create LoRA tags."
    MAX_TAG_LORA = 10

    @classmethod
    def INPUT_TYPES(cls):
        lora_file_list = [
            f.replace(os.path.sep, "/")
            for f in cast(list[str], get_filename_list("loras"))
        ]
        lora_values: list[
            list[
                tuple[str, tuple[list[str], dict[str, str]]]
                | tuple[str, tuple[str, dict[str, float | str]]]
            ]
        ] = [
            [
                (
                    f"lora_name_{i}",
                    (["[none]"] + lora_file_list, {"tooltip": "LoRA file name."}),
                ),
                (
                    f"strength_{i}",
                    (
                        "FLOAT",
                        {
                            "default": 0.0,
                            "min": -100.0,
                            "max": 100.0,
                            "step": 0.01,
                            "tooltip": "Modify strength.",
                        },
                    ),
                ),
            ]
            for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA)
        ]
        return {"required": {k: v for k, v in reduce(lambda x, y: x + y, lora_values)}}

    def __init__(self):
        pass

    def create_tags(self, **kwargs: dict[str, str | float]):
        return (
            "\n".join(
                [
                    "<lora:{}:{:2f}>".format(
                        kwargs[f"lora_name_{i}"], kwargs[f"strength_{i}"]
                    )
                    for i in range(0, MultipleLoraTagLoader.MAX_TAG_LORA)
                    if abs(cast(float, kwargs[f"strength_{i}"])) >= 1e-10
                    and cast(str, kwargs[f"lora_name_{i}"]) != "[none]"
                ]
            ),
        )
