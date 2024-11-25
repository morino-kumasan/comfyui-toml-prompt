class LatentSelector:
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("LATENT not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "Latent Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("LATENT",),
                "secondary": ("LATENT",),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)

class StringSelector:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "STRING Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("STRING", {"forceInput": True, "multiline": True}),
                "secondary": ("STRING", {"forceInput": True, "multiline": True}),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)

class IntSelector:
    RETURN_TYPES = ("INT",)
    OUTPUT_TOOLTIPS = ("INT not disabled.",)
    FUNCTION = "select"
    CATEGORY = "utils"
    DESCRIPTION = "INT Selector."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "optional": {
                "primary": ("INT", {"forceInput": True}),
                "secondary": ("INT", {"forceInput": True}),
            },
        }

    def __init__(self):
        pass

    def select(self, primary=None, secondary=None):
        return (primary or secondary,)
