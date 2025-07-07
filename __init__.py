from .toml_prompt.toml_prompt_decode import TomlPromptDecode, SummaryReader
from .toml_prompt.multiple_lora_tag_loader import MultipleLoraTagLoader
from .toml_prompt.prompt_loader import PromptLoader
from .toml_prompt.string_viewer import StringViewer
from .toml_prompt.util import StringPicker, JsonExtractString, JsonExtractInt, JsonExtractFloat, LatentSelector, StringSelector, IntSelector, StringSub, StringConcat
from .toml_prompt.wrapper import MultipartCLIPTextEncode, CheckPointLoaderSimpleFromString, KSamplerFromJsonInfo

NODE_CLASS_MAPPINGS = {
    "TomlPromptDecode": TomlPromptDecode,
    "MultipartCLIPTextEncode": MultipartCLIPTextEncode,
    "MultipleLoraTagLoader": MultipleLoraTagLoader,
    "PromptLoader": PromptLoader,
    "StringConcat": StringConcat,
    "StringSub": StringSub,
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
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TomlPromptDecode": "TomlPromptDecode",
    "MultipartCLIPTextEncode": "MultipartCLIPTextEncode",
    "MultipleLoraTagLoader": "MultipleLoraTagLoader",
    "PromptLoader": "PromptLoader",
    "StringConcat": "StringConcat",
    "StringSub": "StringSub",
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
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
