import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

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
            const widget = (name) => this.widgets?.find((w) => w.name === name);

            const saveButton = this.addWidget("button", "💾  Save to wildcard file", null, async () => {
                const text = widget("prompt_text")?.value ?? "";
                const filename = widget("filename")?.value ?? "my_wildcard.txt";
                const folder = widget("folder")?.value ?? "";
                const mode = widget("mode")?.value ?? "append";

                if (!text || !text.trim()) {
                    notify("warn", "Wildcard Saver", "Prompt text is empty - nothing to save.");
                    return;
                }

                const restoreLabel = saveButton.label ?? saveButton.name;
                saveButton.disabled = true;
                saveButton.label = "Saving…";
                this.setDirtyCanvas(true, true);

                try {
                    const resp = await api.fetchApi("/wildcard_saver/save", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ text, filename, folder, mode }),
                    });
                    const result = await resp.json();

                    if (resp.ok && result.status === "ok") {
                        const n = result.lines;
                        const lineWord = `${n} line${n === 1 ? "" : "s"}`;
                        if (result.added === false) {
                            notify("info", "Already saved", `Already in ${result.path} (${lineWord})`);
                        } else {
                            const verb = result.mode === "overwrite" ? "Overwrote" : "Saved to";
                            notify("success", "Wildcard Saved", `${verb} ${result.path} (${lineWord})`);
                        }
                    } else {
                        notify("error", "Wildcard Saver", result.message || `HTTP ${resp.status}`);
                    }
                } catch (e) {
                    notify("error", "Wildcard Saver", String(e));
                } finally {
                    saveButton.disabled = false;
                    saveButton.label = restoreLabel;
                    this.setDirtyCanvas(true, true);
                }
            });
            saveButton.serialize = false;

            const openButton = this.addWidget("button", "📂  Open folder", null, async () => {
                const filename = widget("filename")?.value ?? "my_wildcard.txt";
                const folder = widget("folder")?.value ?? "";
                try {
                    const resp = await api.fetchApi("/wildcard_saver/open_folder", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ filename, folder }),
                    });
                    const result = await resp.json();
                    if (resp.ok && result.status === "ok") {
                        notify("success", "Wildcard Saver", `Opened ${result.path}`);
                    } else {
                        notify("error", "Wildcard Saver", result.message || `HTTP ${resp.status}`);
                    }
                } catch (e) {
                    notify("error", "Wildcard Saver", String(e));
                }
            });
            openButton.serialize = false;

            const computed = this.computeSize();
            if (this.size[1] < computed[1]) this.size[1] = computed[1];

            return ret;
        };
    },
});
