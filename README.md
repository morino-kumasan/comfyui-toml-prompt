# comfyui-utils

ComfyUI custom nodes.

Install

```
cd ComfyUI/custom_nodes
git clone git@github.com:morino-kumasan/comfyui-utils.git
cd ../../
python_embeded/python -m pip install -r ComfyUI/custom_nodes/comfyui-utils/requirements.txt
```

## TomlPromptEncoder

Encode Prompt in toml.

- Input
  - model
  - clip
  - key_name_list
    - Key name list separated by line break.
  - text
    - toml prompt triggered by key_name
  - lora_info
    - toml prompt triggered by lora_name
  - seed
- Output
  - MODEL
  - CLIP
  - CONDITION
  - STRING
    - Loaded lora tags
  - STRING
    - Prompt

### text

_t is prompt.
_v is variables for random choice.
_k is available keys for random choice.
_w is weight for random choice with _k.

```
# key _t is prompt
[base]
_t="score_9, score_8_up, score_7_up, source_anime"

# direct string prompt
quality="best quality"

[base.girl]
_t="""1girl, perfect anatomy, 
beautiful face, (detailed skin), (detailed face), (beautiful detailed eyes),  
shiny hair, ${color} hair"""
# ${color} is replaced with red, blue or blonde.

twintails = "twintails, <lora:twintails.safetensors:1>"
ponytails = "ponytails"

[base.girl._v]
color=["red", "blue", "blonde"]

[base.boy]
1boy, muscular, ${g.color} hair, formal suit,
# ${color} is replaced with dark or light

[random_weight]
_k = ["a", "b", "c"]
_w = [0.8, 0.1, 0.1]
a = "80%"
b = "10%"
c = "10%"

[_v]
color=["dark", "light"]
```

### lora_info

```<lora:lora_name:strength>``` is replaced with prompt.

```
["lora.safetensors"]
_t="lora prompt"
```

### key_name_list

```
// this is commont
# this is comment
/* this is comment */
quality          /* encode as "best quality" */
base, quality    /* encode as "score_9, score_8_up, score_7_up, source_anime, best quality" */
{base | quality} /* encode as "score_9, score_8_up, score_7_up, source_anime" or "best quality" */
base.girl        /* equals "base, base.girl", but not duplicate prompt. */
base.girl+boy    /* equals "base, base.girl, base.boy" */
base.?           /* equals "{base.girl | base.boy}" */
base.??          /* equals "{base.girl.twintails | base.girl.ponytails | base.boy}" */
<lora:lora.safetensors:1> /* load LoRA and encode as "lora prompt" */
<raw:this line is raw positive prompt.> /* raw positive prompt */
<!:this line is raw negative prompt.>   /* raw negative prompt */
<if:base.girl:key_name1:key_name2>     /* key_name1 if key name is already loaded else key_name2 */
```

## MultipleLoraTagLoader

Output multiple LoRA tags. (max 10)

- Input
  - lora_name_0
    - LoRA filename.
  - strength_0
    - LoRA modify strengh.
  - lora_name_1
  - strength_1
  - ...
  - lora_name_9
  - strength_9
- Output
  - STRING
    - LoRA tag list separated by line break.

## PromptLoader

Load String from file.

## StringConcat

Join strings.

## StringSub

Replace text by regex.

## StringViewer

View input string.
