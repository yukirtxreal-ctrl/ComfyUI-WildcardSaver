import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Small helper: use ComfyUI's toast if present, otherwise fall back gracefully.
function notify(severity, summary, detail) {
    try {
        if (app.extensionManager?.toast?.add) {
            app.extensionManager.toast.add({ severity, summary, detail, life: 4000 });
            return;
        }
    } catch (e) {
        /* ignore and fall through */
    }
    if (severity === "error" || severity === "warn") {
        alert(`${summary}: ${detail}`);
    } else {
        console.log(`[WildcardSaver] ${summary}: ${detail}`);
    }
}

app.registerExtension({
    name: "comfy.wildcardSaver",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SavePromptToWildcard") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

            const button = this.addWidget(
                "button",
                "💾  Save to wildcard file",
                null,
                async () => {
                    const widget = (name) => this.widgets?.find((w) => w.name === name);
                    const text = widget("prompt_text")?.value ?? "";
                    const filename = widget("filename")?.value ?? "my_wildcard.txt";
                    const folder = widget("folder")?.value ?? "";
                    const mode = widget("mode")?.value ?? "append";

                    if (!text || !text.trim()) {
                        notify("warn", "Wildcard Saver", "Prompt text is empty - nothing to save.");
                        return;
                    }

                    const restoreLabel = button.label ?? button.name;
                    button.disabled = true;
                    button.label = "Saving…";
                    this.setDirtyCanvas(true, true);

                    try {
                        const resp = await api.fetchApi("/wildcard_saver/save", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ text, filename, folder, mode }),
                        });
                        const result = await resp.json();

                        if (resp.ok && result.status === "ok") {
                            const verb = result.mode === "overwrite" ? "Overwrote" : "Appended to";
                            const n = result.lines;
                            notify(
                                "success",
                                "Wildcard Saved",
                                `${verb} ${result.path} (${n} line${n === 1 ? "" : "s"})`
                            );
                        } else {
                            notify("error", "Wildcard Saver", result.message || `HTTP ${resp.status}`);
                        }
                    } catch (e) {
                        notify("error", "Wildcard Saver", String(e));
                    } finally {
                        button.disabled = false;
                        button.label = restoreLabel;
                        this.setDirtyCanvas(true, true);
                    }
                }
            );

            // The button's transient state shouldn't be serialized into the workflow.
            button.serialize = false;

            // Make sure the node opens tall enough to show the text box + button.
            const computed = this.computeSize();
            if (this.size[1] < computed[1]) this.size[1] = computed[1];

            return ret;
        };
    },
});
