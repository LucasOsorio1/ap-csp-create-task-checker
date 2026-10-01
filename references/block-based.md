# Checking block-based code (screenshots)

The script can't read block code, so you check it visually. Ask for screenshots of **all** the code, plus the four PPR screenshots, and work through this list. Report anything you can't see clearly as CHECK instead of guessing.

If they upload a project file instead of screenshots: a Scratch `.sb3` is a zip containing `project.json`, where blocks are a flat map of IDs with opcodes (for example `procedures_definition`, `control_if`, `control_repeat`, and `event_...` hat blocks). Unzip it and read the opcodes, or ask for screenshots if that's quicker. The PPR itself is always screenshots, so check those visually either way.

## What each requirement looks like in blocks

| Requirement | Snap! | Scratch | App Inventor | App Lab (block mode) |
|---|---|---|---|---|
| Student-developed procedure | a custom block made with "Make a block" | a "define" block (My Blocks) | "to *name* do" or "to *name* result" | a "function *name*" block |
| Parameter | an input slot on the custom block | an input added to the "define" block | an argument added with the mutator (blue gear) | a parameter in the function block |
| Returns a value | "report" block | (no return; custom blocks only run) | "to *name* result" | "return" block |
| Call | the custom block used elsewhere | the custom block used elsewhere | a "call *name*" block | a call to the function |
| Event handler (**not** student-developed) | hat blocks, e.g. "when green flag clicked", "when key pressed" | hat blocks starting with "when" (including "when I receive") | gold "when *Component.Event* do" blocks | "onEvent" |
| List | "list" block, variables holding lists | a list from "Make a List" | "make a list", "create empty list" | [ ] list blocks, appendItem |
| Selection | "if", "if else" | "if", "if else" | "if/then", "if/else" | "if", "if/else" |
| Iteration | "repeat", "repeat until", "for each", "forever", "for i" | "repeat", "repeat until", "forever" | "for each item", "for each number", "while" | "for", "while" |

A **code segment** in block code means blocks under the **same hat block** (SG terminology). A PPR segment that stitches together blocks from different scripts isn't one segment.

## Common block-code problems

- **The only procedure is an event handler.** A "when button clicked" script with all the logic inside doesn't satisfy "student-developed procedure". The student needs a custom block/procedure that the handler calls.
- **The procedure has an input slot it never uses.** An unused parameter doesn't "have an effect on the functionality of the procedure", which the PPR requires.
- **Broadcasts instead of calls (Scratch).** "broadcast" plus "when I receive" is an event, not a procedure call. The PPR call segment needs the custom block itself.
- **"forever" as the only loop.** It does count as iteration, but check it isn't trivial. If the loop just keeps a sprite animating and doesn't affect the program's outcome, flag it as CHECK.
- **One-element or never-used list.** A list with one item fails the scoring point outright.

## Checking PPR screenshots

- **Comments**: Scratch sticky-note comments, Snap! comment boxes, App Inventor block comments (the "?" bubble), and code comments in text mode all count. **Any visible comment is a score-0 risk.** Look at the edges of every screenshot, where comments are easy to miss.
- **Course content**: no teacher notes, rubric text, or lesson material in the images.
- **Readability**: not blurry, text roughly 10 pt or larger. If you have to squint, a reader will too; say so.
- **Right content in each of the four segments**: procedure definition with a used parameter, selection, and iteration; the call; the list being filled; the same list being used (same name in both).
- **Same code as the program**: the PPR shows code from the submitted program. If a screenshot doesn't match the full program, flag it.
