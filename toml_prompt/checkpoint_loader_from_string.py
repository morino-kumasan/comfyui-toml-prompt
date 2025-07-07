from nodes import CheckpointLoaderSimple

class CheckPointLoaderSimpleFromString:
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    OUTPUT_TOOLTIPS = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "loaders"
    DESCRIPTION = "Load checkpoint from string."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "ckpt_name": ("STRING",),
            }
        }

    def __init__(self):
        self.loader = CheckpointLoaderSimple()

    def concat(self, ckpt_name):
        return self.loader.load_checkpoint(ckpt_name)
