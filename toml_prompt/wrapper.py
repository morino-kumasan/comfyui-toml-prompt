import re, json

from nodes import LoraLoader, CLIPTextEncode, ConditioningConcat, CheckpointLoaderSimple, KSampler


def encode(encoder, concat, clip, text):
    r_cond = None
    for prompt in re.split(r"[\s,]+BREAK[\s,]+", text):
        prompt = prompt.strip()
        if prompt == "":
            continue

        cond = encoder.encode(clip, prompt)[0]
        if r_cond is None:
            r_cond = cond
        else:
            r_cond = concat.concat(cond, r_cond)[0]

    if r_cond is None:
        r_cond = encoder.encode(clip, "")[0]
    return r_cond

class MultipartCLIPTextEncode:
    RETURN_TYPES = ("MODEL", "CLIP", "CONDITIONING", "CONDITIONING")
    OUTPUT_TOOLTIPS = ("The diffusion model.", "The CLIP model.", "A Conditioning for positive.", "A Conditioning for negative.")
    FUNCTION = "load_prompt"
    CATEGORY = "conditioning"
    DESCRIPTION = "Encode prompt."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "The diffusion model."}),
                "clip": ("CLIP", {"tooltip": "The CLIP model."}),
                "lora_tag_list": ("STRING", {"multiline": True, "tooltip": "LoRA tag list."}),
                "positive": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "Positive prompt."}),
                "negative": ("STRING", {"multiline": True, "dynamicPrompts": True, "defaultInput": True, "tooltip": "Negative prompt."}),
            }
        }

    def __init__(self):
        self.encoder = CLIPTextEncode()
        self.concat = ConditioningConcat()
        self.loader = {}

    def load_prompt(self, model, clip, positive, negative, lora_tag_list):
        self.loader = {}

        # Load LoRAs
        r_model = model
        r_clip = clip
        for lora_tag in lora_tag_list.splitlines():
            m = re.match(r"<lora:([^:]+):([-0-9.]+)(:([-0-9.]+))?>", lora_tag)
            if m:
                lora_name = m.group(1)
                strength_model = float(m.group(2))
                strength_clip = float(m.group(4)) if m.group(4) else strength_model
                if lora_name not in self.loader:
                    self.loader[lora_name] = LoraLoader()
                    r_model, r_clip = self.loader[lora_name].load_lora(r_model, r_clip, lora_name, strength_model, strength_clip)
                    print(f"Lora Loaded: {lora_name}: {strength_model}")

        # Encode prompts
        r_positive = encode(self.encoder, self.concat, r_clip, positive)
        r_negative = encode(self.encoder, self.concat, r_clip, negative)

        return (r_model, r_clip, r_positive, r_negative)

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

class KSamplerFromJsonInfo:
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling"
    DESCRIPTION = "KSampler from json info."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING", {"tooltip": "Positive."}),
                "negative": ("CONDITIONING", {"tooltip": "Negative."}),
                "latent_image": ("LATENT",),
                "denoise": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "json_text": ("STRING", {"tooltip": "JSON text including seed, steps, cfg, sampler and scheduler"}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "forceInput": True}),
            }
        }

    def __init__(self):
        self.sampler = KSampler()

    def sample(self, positive, negative, latent_image, denoise, json_text, seed=None):
        info = json.loads(json_text)
        seed = seed if seed is not None else info["seed"]
        return self.sampler.sample(info["model"], seed, info["steps"], info["cfg"], info["sampler"], info["scheduler"], positive, negative, latent_image, denoise=denoise)
