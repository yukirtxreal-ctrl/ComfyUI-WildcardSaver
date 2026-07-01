"""
ComfyUI-WildcardSaver
---------------------
A custom node with a "Save" button that writes the prompt text into a
wildcard .txt file (one entry per line). Saving is triggered by the button on
the node -- NOT by running the workflow -- so queued generations never spam the
file.

Default save location: <ComfyUI>/wildcards/<filename>.txt
Set the optional "folder" field to save straight into a specific wildcards
folder (e.g. your Dynamic Prompts or Impact Pack folder).
"""

import os
from aiohttp import web

try:
    from server import PromptServer
except Exception:  # pragma: no cover - only happens outside a running ComfyUI
    PromptServer = None


def _comfy_base():
    """Return the ComfyUI root path (or a sensible fallback)."""
    try:
        import folder_paths
        return folder_paths.base_path
    except Exception:
        # Fallback: .../ComfyUI/custom_nodes/<this_pack> -> go up two levels
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _wildcards_dir(folder=""):
    """Return (and create) the wildcards root to save into.

    - folder blank            -> <ComfyUI>/wildcards
    - folder is absolute      -> that folder
    - folder is relative      -> <ComfyUI>/<folder>
    """
    folder = (folder or "").strip().replace("\\", "/")
    if not folder:
        root = os.path.join(_comfy_base(), "wildcards")
    elif os.path.isabs(folder):
        root = folder
    else:
        root = os.path.join(_comfy_base(), folder)
    root = os.path.normpath(root)
    os.makedirs(root, exist_ok=True)
    return root


def _resolve_path(filename, folder=""):
    """Resolve a user-supplied filename to a safe path inside the wildcards root.

    Supports sub-folders (e.g. "characters/hair") and protects against path
    traversal (".." escaping the chosen wildcards root).
    """
    root = os.path.normpath(_wildcards_dir(folder))
    filename = (filename or "").strip()
    if not filename:
        filename = "my_wildcard.txt"
    filename = filename.replace("\\", "/").lstrip("/")
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    full = os.path.normpath(os.path.join(root, filename))
    # Ensure the resolved path is still inside the wildcards root.
    if os.path.commonpath([full, root]) != root:
        raise ValueError("Filename escapes the wildcards folder")
    return root, full


def _save(text, filename, mode, folder=""):
    """Write text to the wildcard file. Returns (path, non_empty_line_count)."""
    _root, path = _resolve_path(filename, folder)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Treat the whole text box as ONE wildcard entry (one line/option):
    # collapse any internal line breaks into single spaces.
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(part.strip() for part in text.split("\n") if part.strip())

    if mode == "overwrite":
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    else:  # append
        prefix = ""
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "rb") as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b"\n":
                    prefix = "\n"  # make sure we start on a fresh line
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(prefix + text + "\n")

    with open(path, "r", encoding="utf-8") as f:
        line_count = sum(1 for ln in f.read().split("\n") if ln.strip())
    return path, line_count


# --- Backend API route the button calls -------------------------------------
if PromptServer is not None:

    @PromptServer.instance.routes.post("/wildcard_saver/save")
    async def _wildcard_saver_save(request):
        try:
            data = await request.json()
            text = data.get("text", "")
            filename = data.get("filename", "my_wildcard.txt")
            mode = data.get("mode", "append")
            folder = data.get("folder", "")

            if not (text or "").strip():
                return web.json_response(
                    {"status": "error", "message": "Prompt text is empty."},
                    status=400,
                )

            path, lines = _save(text, filename, mode, folder)
            return web.json_response(
                {"status": "ok", "path": path, "lines": lines, "mode": mode}
            )
        except Exception as e:  # noqa: BLE001 - surface any error to the UI
            return web.json_response(
                {"status": "error", "message": str(e)}, status=500
            )


# --- The node ----------------------------------------------------------------
class SavePromptToWildcard:
    """Type a prompt, click the button, and it's appended to a wildcard file."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_text": ("STRING", {"multiline": True, "default": ""}),
                "filename": ("STRING", {
                    "default": "my_wildcard.txt",
                    "tooltip": "File name (.txt added automatically). Sub-folders work: characters/hair",
                }),
                "folder": ("STRING", {
                    "default": "",
                    "tooltip": "Blank = ComfyUI/wildcards. Or set your extension's wildcards folder.",
                }),
                "mode": (["append", "overwrite"],),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_text",)
    FUNCTION = "run"
    CATEGORY = "utils/wildcards"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Type a prompt and press the Save button to append it as a new line in a "
        "wildcard .txt file. Saves to ComfyUI/wildcards by default, or set the "
        "'folder' field to save straight into your wildcard extension's folder. "
        "The text is also passed through the output. Saving happens on button "
        "click, not when the workflow runs."
    )

    def run(self, prompt_text, filename, mode, folder=""):
        # Intentionally a no-op passthrough: saving is done by the button so that
        # queueing a workflow does not repeatedly write to the file.
        return (prompt_text,)


NODE_CLASS_MAPPINGS = {"SavePromptToWildcard": SavePromptToWildcard}
NODE_DISPLAY_NAME_MAPPINGS = {"SavePromptToWildcard": "Save Prompt to Wildcard \U0001F4BE"}
WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
