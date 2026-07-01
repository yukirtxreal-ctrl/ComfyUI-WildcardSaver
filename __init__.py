"""
ComfyUI-WildcardSaver
---------------------
A custom node with a "Save" button that writes the prompt text into a
wildcard .txt file (one entry per line).

- Save button: writes the prompt to the file on click.
- Auto-save toggle: also saves automatically each time you run the workflow.
- Open folder button: opens the wildcards folder in your file manager.

Duplicate lines are skipped in append mode, so nothing gets spammed.
Default save location: <ComfyUI>/wildcards/<filename>.txt
"""

import os
import sys
import subprocess
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
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _wildcards_dir(folder=""):
    """Return (and create) the wildcards root to save into."""
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
    """Resolve a filename to a safe path inside the wildcards root."""
    root = os.path.normpath(_wildcards_dir(folder))
    filename = (filename or "").strip()
    if not filename:
        filename = "my_wildcard.txt"
    filename = filename.replace("\\", "/").lstrip("/")
    if not filename.lower().endswith(".txt"):
        filename += ".txt"

    full = os.path.normpath(os.path.join(root, filename))
    if os.path.commonpath([full, root]) != root:
        raise ValueError("Filename escapes the wildcards folder")
    return root, full


def _collapse(text):
    """Whole text box becomes one wildcard line (internal newlines -> spaces)."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(part.strip() for part in text.split("\n") if part.strip())


def _count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for ln in f.read().split("\n") if ln.strip())


def _save(text, filename, mode, folder=""):
    """Write text to the wildcard file. Returns (path, line_count, added)."""
    _root, path = _resolve_path(filename, folder)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = _collapse(text)
    if not text:
        return path, _count_lines(path), False

    added = True
    if mode == "overwrite":
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    else:  # append, but skip if the exact line already exists
        existing = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = [ln.rstrip("\n") for ln in f.read().split("\n")]
        if text in existing:
            added = False
        else:
            prefix = ""
            if os.path.exists(path) and os.path.getsize(path) > 0:
                with open(path, "rb") as f:
                    f.seek(-1, os.SEEK_END)
                    if f.read(1) != b"\n":
                        prefix = "\n"
            with open(path, "a", encoding="utf-8", newline="\n") as f:
                f.write(prefix + text + "\n")

    return path, _count_lines(path), added


def _open_folder_of(filename, folder=""):
    """Open the folder that holds the wildcard file in the OS file manager."""
    _root, path = _resolve_path(filename, folder)
    target = os.path.dirname(path)
    os.makedirs(target, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(target)  # noqa: S606 - local convenience
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
    return target


# --- Backend API routes -----------------------------------------------------
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
            path, lines, added = _save(text, filename, mode, folder)
            return web.json_response(
                {"status": "ok", "path": path, "lines": lines,
                 "mode": mode, "added": added}
            )
        except Exception as e:  # noqa: BLE001
            return web.json_response(
                {"status": "error", "message": str(e)}, status=500
            )

    @PromptServer.instance.routes.post("/wildcard_saver/open_folder")
    async def _wildcard_saver_open_folder(request):
        try:
            data = await request.json()
            filename = data.get("filename", "my_wildcard.txt")
            folder = data.get("folder", "")
            target = _open_folder_of(filename, folder)
            return web.json_response({"status": "ok", "path": target})
        except Exception as e:  # noqa: BLE001
            return web.json_response(
                {"status": "error", "message": str(e)}, status=500
            )


# --- The node ----------------------------------------------------------------
class SavePromptToWildcard:
    """Save prompts to a wildcard file - by button, or automatically each run."""

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
                "auto_save": ("BOOLEAN", {
                    "default": False,
                    "label_on": "on",
                    "label_off": "off",
                    "tooltip": "Save the prompt automatically each run (duplicates skipped).",
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt_text",)
    FUNCTION = "run"
    CATEGORY = "utils/wildcards"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Save prompts to a wildcard .txt file. Click the Save button, or turn on "
        "auto_save to store the prompt every time you run. The Open folder button "
        "reveals the file in your file manager. Duplicate lines are skipped."
    )

    def run(self, prompt_text, filename, mode, folder="", auto_save=False):
        if auto_save and (prompt_text or "").strip():
            try:
                _save(prompt_text, filename, mode, folder)
            except Exception as e:  # noqa: BLE001 - never break a render over this
                print(f"[WildcardSaver] auto-save failed: {e}")
        return (prompt_text,)


NODE_CLASS_MAPPINGS = {"SavePromptToWildcard": SavePromptToWildcard}
NODE_DISPLAY_NAME_MAPPINGS = {"SavePromptToWildcard": "Save Prompt to Wildcard \U0001F4BE"}
WEB_DIRECTORY = "./web/js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
