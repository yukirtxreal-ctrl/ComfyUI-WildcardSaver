# ComfyUI-WildcardSaver

A tiny ComfyUI custom node: type a prompt, **click the Save button**, and it gets
written into a wildcard `.txt` file (one entry per line). Great for building up
wildcard files as you discover prompts you like.

Saving happens **on the button click**, not when the workflow runs — so queueing
generations never spams your file.

## Node

**Save Prompt to Wildcard** (category: `utils/wildcards`)

| Widget | What it does |
| --- | --- |
| `prompt_text` | The text to save. The whole box is saved as **one line** (one wildcard option). |
| `filename` | Target file. `.txt` is added automatically. Sub-folders work, e.g. `characters/hair`. |
| `folder` | Where to save. **Blank = `ComfyUI/wildcards`.** Set it to your wildcard extension's folder (see the table below) so saves land where they're actually read. An absolute path like `D:/wildcards` works too. |
| `mode` | `append` adds the prompt as a new line (duplicates skipped); `overwrite` replaces the file; `numbered` writes a **new file every save** (`name_00001.txt`, `name_00002.txt`, …) so every generation is kept, even identical prompts. |
| `auto_save` | When **on**, the prompt is saved automatically every time you run. Pair with `mode = numbered` to keep **every** generation as its own numbered file; with `append` it adds new lines (duplicates skipped). |
| Save button | Writes the current prompt to the file and shows a confirmation. |
| Open folder button | Opens the wildcards folder in your file manager. |

The node also passes `prompt_text` straight through its output, so you can wire it
into a CLIP Text Encode and save it from the same node.

## How to use (saving a prompt)

1. Add the node: double-click the canvas and search **Save Prompt to Wildcard**.
2. Type or paste a prompt into `prompt_text`.
3. Set `filename`, e.g. `hair`.
4. Set `folder` to your wildcard extension's folder (see table below), or leave it blank for `ComfyUI/wildcards`.
5. Choose `mode`: `append` to keep adding lines, `overwrite` to replace the file.
6. Click **Save**. The prompt is written and a small confirmation appears.

Repeat with more prompts to grow the file — each save is one new line, i.e. one
wildcard option.

## Using your wildcards

A wildcard file is just a text file with **one option per line**. A wildcard-aware
extension then swaps `__filename__` in your prompt for one random line. You need one
of these extensions installed (from ComfyUI-Manager): **ComfyUI Dynamic Prompts** or
**ComfyUI Impact Pack**.

### Point the node at the right folder

Each extension reads wildcards from its **own** folder — not `ComfyUI/wildcards`. So
set this node's `folder` field to match, and your saves land where they'll be found:

| Extension | Put this in the `folder` field | Reference in prompt as |
| --- | --- | --- |
| Dynamic Prompts | `custom_nodes/comfyui-dynamicprompts/wildcards` | `__name__` |
| Impact Pack | `custom_nodes/ComfyUI-Impact-Pack/custom_wildcards` | `__name__` |
| (blank) | `ComfyUI/wildcards` | `__name__` |

After adding a **new** file, restart ComfyUI or use your extension's wildcard
"refresh" so it notices the new file. (New lines added to an existing file are picked
up without a restart in most versions.)

### The basics

Save a few prompts to `hair.txt` (in `append` mode, each click adds a line):

```
blue hair, smiling
red hair, serious
long black hair
```

Now in any prompt, `__hair__` becomes one of those lines at random each run.

### Every situation

These all work in both Dynamic Prompts and Impact Pack:

- **One wildcard** — `1girl, __hair__` picks one line from `hair.txt`.
- **Several at once** — `1girl, __hair__, __outfit__, __background__` — each is chosen independently.
- **Sub-folders** — save with `filename` = `characters/hair`, then use `__characters/hair__`.
- **Inline choice, no file needed** — `{blue|red|green} hair` picks one.
- **Weighted choice** — `{5::blue|2::red|1::green} hair` — blue is most likely (numbers are relative weights; note the double colon `::`).
- **Pick several** — `{2$$__hair__|__outfit__|__pose__}` picks 2, comma-joined. Range: `{1-3$$...}` picks 1–3. Custom separator: `{2$$ and $$a|b|c}`.
- **Nesting** — a wildcard file may itself contain `{a|b}` choices or other `__wildcards__`; they get resolved too.
- **Comment out a line** — start a line in the file with `#` and it's skipped.

### Random, fixed, or every combination

- **Dynamic Prompts** provides two nodes: *Random Prompts* (a fresh random pick each run) and *Combinatorial Prompts* (steps through every possible combination one at a time). Wire its string output into your CLIP Text Encode.
- **Impact Pack** uses *ImpactWildcardProcessor* / *ImpactWildcardEncode* with a **Populate / Fixed** switch: *Populate* rolls a new prompt each time you queue; *Fixed* locks the current text so you can reproduce or hand-edit it.

### Tips

- One option per line. A line with commas (`masterpiece, best quality`) counts as a **single** option — which is exactly what this node saves per click.
- Wildcard names are case-insensitive in Impact Pack (`__Hair__` = `__hair__`).
- `.txt` is the simplest format; both extensions also support `.yaml` collections if you like nested categories.

## Example workflow

The `example_workflows/` folder has **`gummy_autosave_workflow.json`** — a Qwen-Image
graph where a Dynamic Prompts *Random Prompts* node feeds both the image and this node
(set to `auto_save` + `numbered`), so every generation writes a new `gummy_00001.txt`,
`gummy_00002.txt`, … Drag it onto the ComfyUI canvas and swap in your own model names.

> Restart ComfyUI after installing/updating the node so the new modes load, **then**
> load the workflow.

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

- `__init__.py` registers the node plus a backend route `POST /wildcard_saver/save`. It saves to `ComfyUI/wildcards` by default, or to the `folder` you set.
- `web/js/savePromptToWildcard.js` adds the button to the node; clicking it sends the current widget values to that route, which appends/overwrites the file safely — path-traversal is blocked, so `filename` can't escape the chosen folder.
