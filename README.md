# comfyui-utils

ComfyUI custom nodes.

## Install

```
cd ComfyUI/custom_nodes
git clone git@github.com:morino-kumasan/comfyui-utils.git
cd ../../
python_embeded/python -m pip install -r ComfyUI/custom_nodes/comfyui-utils/requirements.txt
```

## How to use
See sample workflows.

## TomlPromptDecode

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
# ${color} is replaced with dark, light or dark blue

[random_weight]
_k = ["a", "b", "c"]
_w = [0.8, 0.1, 0.1]
a = "80%"
b = "10%"
c = "10%"

[_v]
color=["dark", "light", "dark blue"]

[_exports]
key = "value"
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
<raw>
  /* raw positive prompt */
  this line is raw positive prompt.
</raw>
<raw type=negative>
  /* raw negative prompt */
  this line is raw negative prompt.
</raw>
<case>
  /* key_name1 if key name is already loaded else key_name2 */
  <when key=base.girl>
    key_name1
  </when>
  <else>
    key_name2
  </else>
</case>
<random a=0.1 b=0.9>
  /* 10%: key_a, 90%: key_b */
  <when key=a>key_a</when>
  <when key=b>key_b</when>
</random>
<fix key=base route=girl />    /* fix random choise, "base.??" is always "base.girl" */
<fix key=base find=girl />     /* fix random choise, "base.??" is always tag including girl */
<fix key=base remove=girl />   /* fix random choise, "base.??" is always tag excluding girl */
<export key=key value=value /> /* export key=value */
<set key=color value=black>    /* _v.color = ["black"] */
<set key=base.girl.color value='cyan blue'> /* base.girl._v.color = ["cyan blue"] */
<grep key=color value='ark'>   /* _v.color = ["dark", "dark blue"] */
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
