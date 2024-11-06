# comfyui-utils

ComfyUI custom nodes.

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
    - example
    ```
    key_name
    key_group_1.key_group2.key_name
    ```
    - Random key. ex ```key_group_1.?``` choose key starting with ```key_group_1.```
  - text
    - Key and prompts.
    - example
    ``` 
    #[key_name]
    Simple key,
    #[key_group_1.*]
    Add prompts to a key starting with key_group_1,
    #[*]
    Add prompts to any key,
    #[key_group_1.key_group2.key_name]
    best quality,
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
