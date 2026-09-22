from typing import Any

from .toml_prompt.toml_prompt_decode import (
    PromptDecode,
    SummaryReader,
    SplitLoraList,
)
from .toml_prompt.multiple_lora_tag_loader import MultipleLoraTagLoader
from .toml_prompt.prompt_loader import PromptLoader
from .toml_prompt.string_viewer import StringViewer
from .toml_prompt.util import (
    StringPicker,
    StringToInt,
    StringToFloat,
    StringToBoolean,
    LatentSelector,
    StringSelector,
    IntSelector,
    StringConcat,
    StringConcatInt,
    DropFirstImage,
    FlipImage,
    SeedGenerator,
)
from .toml_prompt.wrapper import (
    MultipartCLIPTextEncode,
    CheckPointLoaderSimpleFromString,
    CheckPointLoaderFromString,
    KSamplerFromJsonInfo,
    KSamplerFromString,
    LoadLoraFromLoraList,
    UNETLoaderFromString,
)

NODE_CLASS_MAPPINGS: dict[str, Any] = {
    "PromptDecode": PromptDecode,
    "TomlPromptDecode": PromptDecode,
    "MultipartCLIPTextEncode": MultipartCLIPTextEncode,
    "MultipleLoraTagLoader": MultipleLoraTagLoader,
    "PromptLoader": PromptLoader,
    "StringConcat": StringConcat,
    "StringConcatInt": StringConcatInt,
    "StringViewer": StringViewer,
    "LatentSelector": LatentSelector,
    "StringSelector": StringSelector,
    "IntSelector": IntSelector,
    "SummaryReader": SummaryReader,
    "StringPicker": StringPicker,
    "StringToInt": StringToInt,
    "StringToFloat": StringToFloat,
    "StringToBoolean": StringToBoolean,
    "CheckPointLoaderSimpleFromString": CheckPointLoaderSimpleFromString,
    "CheckPointLoaderFromString": CheckPointLoaderFromString,
    "KSamplerFromJsonInfo": KSamplerFromJsonInfo,
    "KSamplerFromString": KSamplerFromString,
    "LoadLoraFromLoraList": LoadLoraFromLoraList,
    "SplitLoraList": SplitLoraList,
    "UNETLoaderFromString": UNETLoaderFromString,
    "DropFirstImage": DropFirstImage,
    "FlipImage": FlipImage,
    "SeedGenerator": SeedGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptDecode": "PromptDecode",
    "TomlPromptDecode": "PromptDecode",
    "MultipartCLIPTextEncode": "MultipartCLIPTextEncode",
    "MultipleLoraTagLoader": "MultipleLoraTagLoader",
    "PromptLoader": "PromptLoader",
    "StringConcat": "StringConcat",
    "StringConcatInt": "StringConcatInt",
    "StringViewer": "StringViewer",
    "LatentSelector": "LatentSelector",
    "StringSelector": "StringSelector",
    "IntSelector": "IntSelector",
    "SummaryReader": "SummaryReader",
    "StringPicker": "StringPicker",
    "StringToInt": "StringToInt",
    "StringToFloat": "StringToFloat",
    "StringToBoolean": "StringToBoolean",
    "CheckPointLoaderSimpleFromString": "CheckPointLoaderSimpleFromString",
    "CheckPointLoaderFromString": "CheckPointLoaderFromString",
    "KSamplerFromJsonInfo": "KSamplerFromJsonInfo",
    "KSamplerFromString": "KSamplerFromString",
    "LoadLoraFromLoraList": "LoadLoraFromLoraList",
    "SplitLoraList": "SplitLoraList",
    "UNETLoaderFromString": "UNETLoaderFromString",
    "DropFirstImage": "DropFirstImage",
    "FlipImage": "FlipImage",
    "SeedGenerator": "SeedGenerator",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
