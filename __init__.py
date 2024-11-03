import os
import toml
import hashlib

from folder_paths import get_full_path_or_raise
from nodes import LoraLoader, CLIPTextEncode

class LoraLoaderWithPrompt:
    def __init__(self):
        self.loader = LoraLoader()
        self.encoder = CLIPTextEncode()

    @classmethod
    def INPUT_TYPES(s):
        return LoraLoader.INPUT_TYPES()
    
    RETURN_TYPES = (*CLIPTextEncode.RETURN_TYPES, *LoraLoader.RETURN_TYPES)
    OUTPUT_TOOLTIPS = (*CLIPTextEncode.OUTPUT_TOOLTIPS, *LoraLoader.OUTPUT_TOOLTIPS)
    FUNCTION = "load_lora"

    CATEGORY = "loaders"
    DESCRIPTION = "LoRAs load with prompt for each lora."

    @classmethod
    def IS_CHANGED(s, model, clip, lora_name, strength_model, strength_clips):
        lora_dir = os.path.dirname(get_full_path_or_raise("loras", lora_name))
        m = hashlib.sha256()
        with open(os.path.join(lora_dir, "lora_prompt.toml"), encoding="utf-8") as f:
            m.update(f.read())
        return m.digest().hex()

    def load_lora(self, model, clip, lora_name, strength_model, strength_clip):
        # LoraLoader
        r1 = self.loader.load_lora(model, clip, lora_name, strength_model, strength_clip)

        # get prompt for each lora
        lora_dir = os.path.dirname(get_full_path_or_raise("loras", lora_name))
        with open(os.path.join(lora_dir, "lora_prompt.toml"), encoding="utf-8") as f:
            self.file = toml.loads(f.read())
        text = self.file.get(os.path.basename(lora_name), {"prompt": ""})["prompt"]

        # CLIPTextEncode
        r2 = self.encoder.encode(clip, text)

        return (*r2, *r1)

NODE_CLASS_MAPPINGS = {
    "LoraLoaderWithPrompt": LoraLoaderWithPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LoraLoaderWithPrompt": "Load Lora With Prompt For Each Lora"
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
