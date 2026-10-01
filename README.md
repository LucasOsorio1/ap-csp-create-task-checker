# AP CSP Create Task Checker

A [Claude skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that checks an **AP Computer Science Principles Create performance task** against College Board's published requirements *before* you submit it, and tells you what's met, what's missing, and why.

It works like asking a teacher "does this meet the requirements?" It points out gaps and explains the rule. **It never writes or fixes your code.**

## What it checks

| Part | What it looks at |
|---|---|
| **Program code** | A student-developed procedure with a parameter, a call that matches its header, a list (not a one-element list) and a real use of it, selection, iteration, input, and output |
| **Personalized Project Reference (PPR)** | Comments (which can score the whole task 0), the four required code segments, the same list in both list segments, and that each segment really comes from your program |
| **Video** | File type, size (30 MB or less), length (1 minute or less), and whether there is an audio track (voice narration isn't allowed) |

It also keeps three different bars apart, because students mix them up: what earns the **scoring point**, what the **submission requirements** say, and what you'll need on **exam day** (for example, the first `if` statement in your PPR procedure is what written-response question 2(a) asks about).

**Languages:** Python is parsed exactly. JavaScript (including Code.org App Lab) and Java use a lightweight parser, so Claude confirms each finding by reading the code. Block-based projects (Snap!, Scratch, App Inventor, App Lab blocks) are checked from screenshots with a visual checklist.

## What it won't do

- Write, rewrite, or complete your program, PPR segments, or written responses.
- Predict your score. It checks requirements; AP readers score.

## Install

**Claude.ai (web or desktop):** turn on *Code execution and file creation* under **Settings → Capabilities**, then go to **Settings → Capabilities → Skills**, choose **Upload skill**, and pick `ap-csp-create-task-checker.skill` from the [latest release](../../releases/latest). If the upload dialog doesn't accept `.skill`, rename the file to `.zip`.

**Claude Code:** clone this repo into your skills folder.

```bash
git clone https://github.com/LucasOsorio1/ap-csp-create-task-checker ~/.claude/skills/ap-csp-create-task-checker
```

On Windows the folder is `%USERPROFILE%\.claude\skills\`.

## Try it

Start a new chat and paste something like:

> can you check if my AP CSP create task code meets the requirements? its python
> *(then paste your code)*

> i left two # comments in my PPR screenshot so the grader knows what my procedure does. thats fine right?

> is my create task video ok to upload? *(attach the file)*

## How it works

| File | Purpose |
|---|---|
| `SKILL.md` | Short router: integrity rules, workflow, report format |
| `references/requirements.md` | The official rules, exceptions, and definitions, paraphrased with sources |
| `references/block-based.md` | How to check block-based code and PPR screenshots |
| `scripts/csp_check.py` | Deterministic checks for program code, PPR segments, and video |

You can also run the script yourself (Python 3.9+, standard library only; `ffprobe` is optional and adds audio-track detection):

```bash
python3 scripts/csp_check.py program my_program.py
python3 scripts/csp_check.py ppr --procedure proc.txt --call call.txt \
    --list-store store.txt --list-use use.txt --program my_program.py
python3 scripts/csp_check.py video demo.mp4
```

On Windows use `python` or `py` instead of `python3`.

## Accuracy and sources

Rules come from College Board's *AP Computer Science Principles Student Handouts* (effective Fall 2023) and the *2025 AP Computer Science Principles Scoring Guidelines*. Requirements can change from year to year, so check [AP Central](https://apcentral.collegeboard.org) for the current handout, and confirm anything uncertain with your teacher. Your teacher's rules, including any stricter AI policy, come first.

## Responsible use

College Board lets students use generative AI to understand concepts and debug, but AI-written code must be credited in a comment, and on exam day you have to explain your own code. This skill is built to stay on the checking side of that line.

## Disclaimer

This is an independent project. *AP* and *Advanced Placement* are trademarks registered by College Board, which is not affiliated with and does not endorse this project. The skill gives guidance, not an official determination.

## Tests

```bash
python3 evals/test_checker.py
```

16 regression tests run the checker against the sample projects in `evals/files/`. The two video tests generate their clips with `ffmpeg` and are skipped if it isn't installed. `evals/evals.json` holds four end-to-end prompts with the results each should produce.

## License

[MIT](LICENSE.txt)
