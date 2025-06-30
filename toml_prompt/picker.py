import os, json
import folder_paths
from PIL import Image

class StringPicker:
    RETURN_TYPES = ("STRING",)
    OUTPUT_TOOLTIPS = ("STRING not disabled.",)
    FUNCTION = "pick"
    CATEGORY = "utils"
    DESCRIPTION = "STRING Picker."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", {"forceInput": True, "tooltip": "from LoadImage."}),
                "target_title": ("STRING", {"defaultInput": True, "multiline": False}),
                "image_index": ("INT", {"default": 0, "tooltip": "filename index of widgets_values."}),
                "string_index": ("INT", {"default": 0, "tooltip": "string index of widgets_values."}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
        }

    def __init__(self):
        pass

    def pick(self, image, target_title, image_index, string_index, unique_id=None, extra_pnginfo=None):
        if extra_pnginfo:
            # 自ノードからIMAGEのリンク先取得
            node = [node for node in extra_pnginfo["workflow"]["nodes"] if node["id"] == int(unique_id)][0]
            link_id = [input["link"] for input in node["inputs"] if input["type"] == "IMAGE"][0]
            node_id = [link[1] for link in extra_pnginfo["workflow"]["links"] if link[0] == link_id][0]
            node = [node for node in extra_pnginfo["workflow"]["nodes"] if node["id"] == node_id][0]

            # LoadImageノードからfilenameを取得
            dirname = folder_paths.get_input_directory()
            filename = node["widgets_values"][image_index]

            # workflow読み込み
            img = Image.open(os.path.join(dirname, filename))
            img_workflow = json.loads(img.info["workflow"])
            img.close()

            # workflowからtitleが一致するSTRINGを取り出し
            node = [node for node in img_workflow["nodes"] if node.get("title", "") == target_title][0]
            return (node["widgets_values"][string_index],)
        return ("",)
