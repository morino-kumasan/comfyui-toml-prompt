from typing import Any


class StringViewer:
    RETURN_TYPES = ()
    OUTPUT_TOOLTIPS = ()
    FUNCTION = "view_str"
    OUTPUT_NODE = True
    CATEGORY = "utils"
    DESCRIPTION = "String Viewer."

    @classmethod
    def INPUT_TYPES(
        cls,
    ) -> dict[str, dict[str, tuple[str, dict[str, bool | str]]] | dict[str, str]]:
        return {
            "required": {
                "text": (
                    "STRING",
                    {"forceInput": True, "multiline": True, "tooltip": "file name."},
                ),
            },
            "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    def __init__(self):
        pass

    def view_str(
        self,
        text: str,
        unique_id: str | None = None,
        extra_pnginfo: dict[str, Any] | None = None,
    ):
        if extra_pnginfo is not None and unique_id is not None:
            node = [
                node
                for node in extra_pnginfo["workflow"]["nodes"]
                if node["id"] == int(unique_id)
            ][0]
            node["widgets_values"][0] = text
        return {"ui": {"text": [text]}}
