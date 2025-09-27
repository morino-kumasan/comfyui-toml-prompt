from .toml_prompt.toml_prompt_decode import TomlPromptDecode, SummaryReader, SplitLoraList
from .toml_prompt.multiple_lora_tag_loader import MultipleLoraTagLoader
from .toml_prompt.prompt_loader import PromptLoader
from .toml_prompt.string_viewer import StringViewer
from .toml_prompt.util import StringPicker, JsonExtractString, JsonExtractInt, JsonExtractFloat, LatentSelector, StringSelector, IntSelector, StringConcat, StringConcatInt, SeedGenerator
from .toml_prompt.wrapper import MultipartCLIPTextEncode, CheckPointLoaderSimpleFromString, KSamplerFromJsonInfo, LoadLoraFromLoraList

NODE_CLASS_MAPPINGS = {
    "TomlPromptDecode": TomlPromptDecode,
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
    "JsonExtractString": JsonExtractString,
    "JsonExtractInt": JsonExtractInt,
    "JsonExtractFloat": JsonExtractFloat,
    "CheckPointLoaderSimpleFromString": CheckPointLoaderSimpleFromString,
    "KSamplerFromJsonInfo": KSamplerFromJsonInfo,
    "SeedGenerator": SeedGenerator,
    "LoadLoraFromLoraList": LoadLoraFromLoraList,
    "SplitLoraList": SplitLoraList,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TomlPromptDecode": "TomlPromptDecode",
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
    "JsonExtractString": "JsonExtractString",
    "JsonExtractInt": "JsonExtractInt",
    "JsonExtractFloat": "JsonExtractFloat",
    "CheckPointLoaderSimpleFromString": "CheckPointLoaderSimpleFromString",
    "KSamplerFromJsonInfo": "KSamplerFromJsonInfo",
    "SeedGenerator": "SeedGenerator",
    "LoadLoraFromLoraList": "LoadLoraFromLoraList",
    "SplitLoraList": "SplitLoraList",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
