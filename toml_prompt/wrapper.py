from typing import Any
from collections import OrderedDict
from . import InputTypesFuncResult

import re, json

try:
    from nodes import LoraLoader, LoraLoaderModelOnly, CLIPTextEncode, ConditioningConcat, CheckpointLoaderSimple, VAELoader, CLIPLoader, CLIPSetLastLayer, KSampler  # type: ignore
    import comfy.sd, folder_paths  # type: ignore
except ImportError:
    pass


def encode(encoder: Any, concat: Any, clip: Any, text: str):
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
    OUTPUT_TOOLTIPS = (
        "The diffusion model.",
        "The CLIP model.",
        "A Conditioning for positive.",
        "A Conditioning for negative.",
    )
    FUNCTION = "load_prompt"
    CATEGORY = "conditioning"
    DESCRIPTION = "Encode prompt."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "clip": ("CLIP", {"tooltip": "The CLIP model."}),
                "lora_tag_list": (
                    "STRING",
                    {"multiline": True, "tooltip": "LoRA tag list."},
                ),
                "positive": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "defaultInput": True,
                        "tooltip": "Positive prompt.",
                    },
                ),
                "negative": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "defaultInput": True,
                        "tooltip": "Negative prompt.",
                    },
                ),
                "enable_break": (
                    "BOOLEAN",
                    {"tooltip": "prompt splited by BREAK tag."},
                ),
            },
            "optional": {
                "model": ("MODEL", {"tooltip": "The diffusion model."}),
            },
        }

    def __init__(self):
        self.encoder: Any = CLIPTextEncode()  # type: ignore
        self.concat: Any = ConditioningConcat()  # type: ignore
        self.loader: dict[str, Any] = {}

    def load_prompt(
        self,
        clip: Any,
        positive: str,
        negative: str,
        lora_tag_list: str,
        model: Any | None = None,
        enable_break: bool | None = None,
    ):
        self.loader = {}

        # Load LoRAs
        r_model = model
        r_clip = clip
        for lora_tag in lora_tag_list.splitlines():
            # HIGHとLOWを両方読み込むことはない
            if lora_tag == "--":
                break
            m = re.match(r"<lora:([^:]+):([-0-9.]+)(:([-0-9.]+))?>", lora_tag)
            if m:
                lora_name = m.group(1)
                strength_model = float(m.group(2))
                strength_clip = float(m.group(4)) if m.group(4) else strength_model
                if lora_name not in self.loader:
                    if r_model is not None:
                        self.loader[lora_name] = LoraLoader()  # type: ignore
                        r_model, r_clip = self.loader[lora_name].load_lora(
                            r_model, r_clip, lora_name, strength_model, strength_clip
                        )
                    print(f"Lora Loaded: {lora_name}: {strength_model}")

        # Encode prompts
        if enable_break is None or enable_break:
            r_positive = encode(self.encoder, self.concat, r_clip, positive)
            r_negative = encode(self.encoder, self.concat, r_clip, negative)
        else:
            r_positive = self.encoder.encode(
                r_clip, re.sub(r"[\s,]+BREAK[\s,]+", ", ", positive.strip())
            )[0]
            r_negative = self.encoder.encode(
                r_clip, re.sub(r"[\s,]+BREAK[\s,]+", ", ", negative.strip())
            )[0]

        return (r_model, r_clip, r_positive, r_negative)


class LoadLoraFromLoraList:
    RETURN_TYPES = ("MODEL",)
    OUTPUT_TOOLTIPS = ("The diffusion model.",)
    FUNCTION = "load_loras"
    CATEGORY = "loaders"
    DESCRIPTION = "Load loras."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "The diffusion model."}),
                "lora_tag_list": (
                    "STRING",
                    {"multiline": True, "tooltip": "LoRA tag list."},
                ),
            },
        }

    def __init__(self):
        self.loader: dict[str, Any] = {}

    def load_loras(self, model: Any, lora_tag_list: str):
        self.loader = {}

        # Load LoRAs
        r_model = model
        for lora_tag in lora_tag_list.splitlines():
            m = re.match(r"<lora:([^:]+):([-0-9.]+)(:([-0-9.]+))?>", lora_tag)
            if m:
                lora_name = m.group(1)
                strength_model = float(m.group(2))
                if lora_name not in self.loader:
                    self.loader[lora_name] = LoraLoaderModelOnly()  # type: ignore
                    r_model = self.loader[lora_name].load_lora_model_only(
                        r_model, lora_name, strength_model
                    )[0]
                    print(f"Lora Loaded: {lora_name}: {strength_model}")

        return (r_model,)


class CheckPointLoaderSimpleFromString:
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    OUTPUT_TOOLTIPS = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "loaders"
    DESCRIPTION = "Load checkpoint from string."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ckpt_name": ("STRING",),
            }
        }

    def __init__(self):
        self.loader: Any = CheckpointLoaderSimple()  # type: ignore

    def load(self, ckpt_name: str):
        return self.loader.load_checkpoint(ckpt_name)


class CheckPointLoaderFromString:
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    OUTPUT_TOOLTIPS = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "loaders"
    DESCRIPTION = "Load checkpoint from string."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "ckpt_name": ("STRING",),
                "clip_name": ("STRING",),
                "vae_name": ("STRING",),
                "stop_at_clip_layer": (
                    "INT",
                    {"default": 0, "min": -24, "max": 0, "step": 1},
                ),
            }
        }

    def __init__(self):
        self.ckpt_loader: Any = CheckpointLoaderSimple()  # type: ignore
        self.clip_loader: Any = CLIPLoader()  # type: ignore
        self.vae_loader: Any = VAELoader()  # type: ignore
        self.clip_set: Any = CLIPSetLastLayer()  # type: ignore

    def load(
        self,
        ckpt_name: str,
        clip_name: str | None = None,
        vae_name: str | None = None,
        stop_at_clip_layer: int | None = None,
    ):
        ckpt = self.ckpt_loader.load_checkpoint(ckpt_name)
        clip = self.clip_loader.load_clip(clip_name)[0] if clip_name else ckpt[1]
        vae = self.vae_loader.load_vae(vae_name)[0] if vae_name else ckpt[2]
        if stop_at_clip_layer is not None and stop_at_clip_layer < 0:
            clip = self.clip_set.set_last_layer(clip, stop_at_clip_layer)[0]
        return (ckpt[0], clip, vae)


# WAN 2.2用に使いたいだけなので取り敢えず2個キャッシュしておく
_UNET_CACHE: OrderedDict[str, Any] = OrderedDict()
MAX_UNET_CACHE = 2


class UNETLoaderFromString:
    RETURN_TYPES = ("MODEL",)
    OUTPUT_TOOLTIPS = ("The diffusion model.",)
    FUNCTION = "load"
    CATEGORY = "loaders"
    DESCRIPTION = "Load checkpoint from string."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "unet_name": ("STRING",),
            }
        }

    def __init__(self):
        pass

    def load(self, unet_name: str):  # type: ignore
        if unet_name in _UNET_CACHE:
            _UNET_CACHE.move_to_end(unet_name, True)
            return (_UNET_CACHE[unet_name],)
        else:
            model_options = {}
            unet_path = folder_paths.get_full_path_or_raise(  # type: ignore
                "diffusion_models", unet_name
            )
            model = comfy.sd.load_diffusion_model(  # type: ignore
                unet_path, model_options=model_options
            )
            if len(_UNET_CACHE) >= MAX_UNET_CACHE:
                _UNET_CACHE.popitem(False)
            _UNET_CACHE[unet_name] = model
            return (model,)  # type: ignore


class KSamplerFromJsonInfo:
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling"
    DESCRIPTION = "KSampler from json info."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING", {"tooltip": "Positive."}),
                "negative": ("CONDITIONING", {"tooltip": "Negative."}),
                "latent_image": ("LATENT",),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "json_text": (
                    "STRING",
                    {
                        "tooltip": "JSON text including seed, steps, cfg, sampler and scheduler"
                    },
                ),
            },
            "optional": {
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "forceInput": True,
                    },
                ),
            },
        }

    def __init__(self):
        self.sampler: Any = KSampler()  # type: ignore

    def sample(
        self,
        model: Any,
        positive: str,
        negative: str,
        latent_image: Any,
        denoise: float,
        json_text: str,
        seed: int | None = None,
    ):
        info = json.loads(json_text)
        seed = seed if seed is not None else int(info["seed"])
        return self.sampler.sample(
            model,
            seed,
            int(info["steps"]),
            float(info["cfg"]),
            info["sampler"],
            info["scheduler"],
            positive,
            negative,
            latent_image,
            denoise=denoise,
        )


class KSamplerFromString:
    RETURN_TYPES = ("LATENT",)
    OUTPUT_TOOLTIPS = ("LATENT",)
    FUNCTION = "sample"
    CATEGORY = "sampling"
    DESCRIPTION = "KSampler from string."

    @classmethod
    def INPUT_TYPES(cls) -> InputTypesFuncResult:
        return {
            "required": {
                "model": ("MODEL",),
                "positive": ("CONDITIONING", {"tooltip": "Positive."}),
                "negative": ("CONDITIONING", {"tooltip": "Negative."}),
                "latent_image": ("LATENT",),
                "denoise": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "steps": (
                    "INT",
                    {"default": 20, "min": 1, "max": 10000},
                ),
                "cfg": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1},
                ),
                "sampler": (
                    "STRING",
                    {"tooltip": "sampler name."},
                ),
                "scheduler": (
                    "STRING",
                    {"tooltip": "scheduler name."},
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                    },
                ),
            },
        }

    def __init__(self):
        self.sampler: Any = KSampler()  # type: ignore

    def sample(
        self,
        model: Any,
        positive: str,
        negative: str,
        latent_image: Any,
        denoise: float,
        steps: int,
        cfg: float,
        sampler: str,
        scheduler: str,
        seed: int,
    ):
        return self.sampler.sample(
            model,
            seed,
            steps,
            cfg,
            sampler,
            scheduler,
            positive,
            negative,
            latent_image,
            denoise=denoise,
        )
