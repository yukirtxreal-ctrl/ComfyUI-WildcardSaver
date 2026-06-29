# ComfyUI-WildcardSaver

A tiny ComfyUI custom node: type a prompt, **click the Save button**, and it gets
written into a wildcard `.txt` file (one entry per line). Great for building up
wildcard files as you discover prompts you like.

Saving happens **on the button click**, not when the workflow runs — so queueing
generations never spams your file.

## Node

**Save Prompt to Wildcard 💾** (category: `utils/wildcards`)

| Widget | What it does |
| --- | --- |
| `prompt_text` | The text to save. The whole box is saved as **one line** (one wildcard option). |
| `filename` | Target file. `.txt` is added automatically. Sub-folders work, e.g. `characters/hair`. |
| `mode` | `append` adds a new line each click (default); `overwrite` replaces the file. |
| 💾 Save button | Writes the text to the file and shows a confirmation toast. |

The node also passes `prompt_text` straight through its output, so you can wire it
into a CLIP Text Encode and save it from the same node.

## How to use

1. In ComfyUI, double-click the canvas, search **Save Prompt to Wildcard**, and add the node.
2. Type or paste a prompt into the text box.
3. Set **filename** to the wildcard you want, e.g. `hair` (the `.txt` is added for you). Sub-folders work too, like `characters/hair`.
4. Pick **mode** — `append` adds your prompt as a new line (best for building a wildcard), `overwrite` replaces the whole file.
5. Click the **💾 Save** button. The prompt is written to `ComfyUI/wildcards/<filename>.txt` and a small confirmation appears.
6. Repeat with more prompts to grow the file — one prompt per line.

To use what you saved, install the **Dynamic Prompts** extension and write `__filename__` in any prompt (for example `__hair__`). Each time you run, it swaps in one random line from that file.

## Where files go

Files are saved to:

```
<ComfyUI>/wildcards/<filename>.txt
```

This is the folder the **Dynamic Prompts** extension reads from, so anything you
save can be used immediately as `__filename__` in a prompt (e.g. a file named
`hair.txt` becomes `__hair__`). Each line in the file is one random option.

> Using **Impact Pack** instead? Point `filename` at a path it scans, or copy the
> file into its wildcards folder. The save location is `ComfyUI/wildcards` by design.

## Install

Clone this repository into your ComfyUI `custom_nodes` folder:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yukirtxreal-ctrl/ComfyUI-WildcardSaver.git
```

Then restart ComfyUI and refresh the browser tab. Add the node by double-clicking the
canvas and searching **Save Prompt to Wildcard** (category `utils/wildcards`).

No extra Python dependencies — it only uses what ComfyUI already ships with.

### Updating

To get the latest version later, pull inside the cloned folder:

```bash
cd ComfyUI/custom_nodes/ComfyUI-WildcardSaver
git pull
```

## How it works

- `__init__.py` registers the node plus a backend route `POST /wildcard_saver/save`.
- `web/js/savePromptToWildcard.js` adds the button to the node; clicking it sends the
  current widget values to that route, which appends/overwrites the file safely
  (path-traversal is blocked, so `filename` can't escape `ComfyUI/wildcards`).
