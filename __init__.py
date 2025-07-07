from .toml_prompt.toml_prompt_decode import TomlPromptDecode, SummaryReader
from .toml_prompt.multipart_clip_text_encode import MultipartCLIPTextEncode
from .toml_prompt.multiple_lora_tag_loader import MultipleLoraTagLoader
from .toml_prompt.prompt_loader import PromptLoader
from .toml_prompt.string_concat import StringConcat
from .toml_prompt.string_sub import StringSub
from .toml_prompt.string_viewer import StringViewer
from .toml_prompt.selector import LatentSelector, StringSelector, IntSelector
from .toml_prompt.picker import StringPicker
from .toml_prompt.json_extract import JsonExtractString, JsonExtractInt, JsonExtractFloat
from .toml_prompt.checkpoint_loader_from_string import CheckPointLoaderSimpleFromString

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
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
