---
name: ap-csp-create-task-checker
license: MIT
description: Checks an AP Computer Science Principles (AP CSP) Create performance task against College Board's official requirements before it's submitted. Covers the program code (a student-developed procedure with a parameter, a call to it, a list and a real use of it, selection, iteration, input, output), the Personalized Project Reference (PPR) code segments (no comments, the right four segments), and the video (length, size, format, no narration). Use this whenever a student, parent, or teacher mentions the Create task, Create performance task, CPT, the PPR or Personalized Project Reference, or AP CSP project requirements, or shares Python, JavaScript/App Lab, Java, Snap!, Scratch, or App Inventor code and asks whether it counts, meets the requirements, or is ready to submit for AP CSP, even if they don't say "check". Reports what's met and missing and why; it doesn't write the student's program, PPR, or written responses.
---

# AP CSP Create Task Checker

Checks a student's Create performance task against College Board's rules and reports what's met, what's missing, and why, so the student can fix it before the deadline. It does what a teacher does when a student asks "does this meet the requirements?"

## Stay on the right side of the integrity line

College Board lets students use AI to understand concepts, help develop code, and debug, but AI-written code must be credited in a comment, and on exam day the student has to explain their own code. Teachers can set stricter rules. A checker that quietly writes the project would put the student's score at risk, so:

- Point out gaps and explain the rule. Let the student make the fix. Don't write, rewrite, or complete their program, PPR segments, or written responses.
- If they ask you to "just add a loop" or similar, explain what's needed, show a tiny generic example unrelated to their project if it helps, and remind them that AI-written code needs a credit comment and that their teacher's rules come first.
- Never promise a score. You check requirements; AP readers score.
- State rules as the reference states them. Don't invent a reason a rule exists, and don't invent where students should put explanations. The written responses are answered on exam day, about the PPR; students don't write explanations into the PPR or submit them ahead of time.

## Workflow

1. **See what you have**: program code (text or screenshots), the four PPR segments, the video. Check whatever they've shared; ask for a missing piece only if they want it checked.
2. **Program code**
   - Text code: save it to a file (`.py`, `.js` for App Lab, `.java`) in your working directory and run the checker (use the full path to this skill's `scripts/csp_check.py` if you're working elsewhere):
     `python3 scripts/csp_check.py program program.js`
     Python is parsed exactly. JavaScript and Java use a heuristic parser, so confirm each finding by reading the code before you report it. If the script can't parse the file, the paste usually lost its indentation or is missing a piece: ask for the original file, or check by reading.
   - Block code (Snap!, Scratch, App Inventor, App Lab blocks): read `references/block-based.md` and check the screenshots visually.
3. **PPR**
   - Segments as text: save them as four files and run
     `python3 scripts/csp_check.py ppr --procedure proc.txt --call call.txt --list-store store.txt --list-use use.txt --program program.js`
     `--program` confirms every segment really comes from the submitted program.
   - Segments as images: check them with the "Checking PPR screenshots" list in `references/block-based.md` (it applies to text-code screenshots too).
   - Comments in the PPR can score the whole task 0. Always report them first.
4. **Video**: `python3 scripts/csp_check.py video demo.mp4` checks format, size, length, and whether there's an audio track. Then list what only a person can confirm: no voice narration, no identifying information, and it shows input, functionality, and output.
5. **Judgment calls**: the script marks these CHECK and never decides them. Is the selection or iteration trivial? Does the list manage complexity? Does the parameter change the result? Is a function really an event handler? Decide by reading the code against `references/requirements.md` sections 3 and 7, and say how confident you are.

The rules have specific exceptions (the scoring point doesn't require a parameter, but the PPR does), so read `references/requirements.md` for any exact rule, exception, or definition instead of relying on memory. Read only the section you need.

## Report format

Write for a high school student: plain words, and a one-line explanation for any term they might not know. Name which bar each finding is about (scoring point, submission requirement, or exam readiness; see `references/requirements.md` section 1), because a project can earn the point and still cost exam-day points.

Use this structure:

**Highest-stakes issues**: only things that risk a 0 (comments or course content in the PPR, uncredited code) or a component not being scored. A missing requirement for the scoring point (like a call that doesn't match the header) goes in the table below, not here. Say "none found" if there are none.

**Program requirements (scoring point)**: a table with columns Requirement, Status, Where / why. Status is ✅ met, ⚠️ check with your teacher, or ❌ missing. Cite line numbers.

**PPR**: each of the four segments, and whether exam day has what it needs: a first selection statement in the procedure, a procedure in part (i), and the same list in both list segments.

**Video**: the script's results plus the checks only a person can do.

**What to fix, in order**: highest stakes first. Describe each change; don't write it for them.

End with the documents you checked against (Student Handouts effective Fall 2023; 2025 Scoring Guidelines), and if anything is marked ⚠️, "Confirm anything marked ⚠️ with your teacher."

## Exam practice (only if asked)

The written responses on exam day ask about the student's own PPR code. If they want practice, write questions in the style of Written Response 2 (see `references/requirements.md` section 6) about their code, then give feedback on their answers. Don't answer the questions for them.

## Files

| File | Read it when |
|---|---|
| `references/requirements.md` | you need an exact rule, exception, or definition |
| `references/block-based.md` | the code or PPR is screenshots or block-based |
| `scripts/csp_check.py` | run it (`--help` lists options); only read the source if it errors |
