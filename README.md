# comfyui-utils

ComfyUI custom nodes.

Install

```
cd ComfyUI/custom_nodes
git clone git@github.com:morino-kumasan/comfyui-utils.git
cd ../../
python_embeded/python -m pip install -r ComfyUI/custom_nodes/comfyui-utils/requirements.txt
```

## MultipleLoraLoader

Load multiple LoRAs. (max 10)

- Input
  - model
  - clip
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
  - MODEL
  - CLIP
  - STRING
    - LoRA name list separated by line break.

## PromptPicker

Pick prompt by key name.
Enable LoRA tag (max 10). ex ```<lora:lora_name:1.0>```.

- Input
  - model
  - clip
  - key_name_list
    - Key name list separated by line break.
    - Example (each line): ```key_group_1.key_group2.key_name```
    - Random key
      - key_group_1.?
        - Include example: key_group_1.key_name
        - Exclude example: key_group_1.key_group_2.key_name
      - key_group_1.??
        - Include example: key_group_1.key_name
        - Include example: key_group_1.key_group_2.key_name
  - text
    - Key and prompts.
    - toml format
    - Prompt: 
    ```
    [key_group_1.key_name]
    _t = "this is prompt"
    ```
- Output
  - MODEL
  - CLIP
  - CONDITION
  - STRING
    - Loaded lora name

## PromptHolder

Hold prompt.

- Input
  - text
- Output
  - STRING
    - Input text.

## MultilineStringConcat

Join texts by line break.

- Input
  - text_from
  - text_to
- Output
  - STRING
    - Input text.

## StringSub

Replace text by regex.

- Input
  - text
  - pattern
    - Regex pattern.
  - to
    - eplace string matching pattern with "to"
- Output
  - STRING
    - Input text.
