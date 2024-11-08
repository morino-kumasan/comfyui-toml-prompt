import { app } from '/scripts/app.js';
import { ComfyWidgets } from '/scripts/widgets.js';

app.registerExtension({
    name: "StringViewerNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name != "StringViewer") {
            return;
        }
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated?.apply(this);
            // CreateTextBox
            const inputConfig = ["STRING", { default: "", multiline: true, placeholder: "Text" }];
            let text = ComfyWidgets.STRING(this, "output_text", inputConfig, app);
            text.widget.inputEl.readOnly = true;
            return ret;
        };
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (r) {
            onExecuted?.apply(this);
            this?.widgets?.map((w) => {
                if (w.type == "customtext") {
                    w.value = r?.text[0];
                }
            });
        };
    },
});
