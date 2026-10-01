# AP CSP Create Task: the rules this skill checks against

Sources (paraphrased; read the originals if anything looks off):
- **Handout**: College Board, *AP Computer Science Principles Student Handouts* (effective Fall 2023), apcentral.collegeboard.org/media/pdf/ap-csp-student-task-directions.pdf
- **SG**: College Board, *2025 AP Computer Science Principles Scoring Guidelines* (Set 1)

These documents can change between school years. If you have web access, check AP Central for a newer handout or scoring guidelines before telling a student something is final.

## Contents
1. Three bars to keep separate
2. Program code requirements (Handout)
3. The "Program Requirements" scoring point (SG)
4. Personalized Project Reference (Handout + SG)
5. Video (Handout + SG)
6. What the exam-day written responses need from the PPR (SG)
7. Definitions that settle arguments (SG terminology)
8. Integrity and AI rules (Handout)
9. Highest-stakes risks, ranked

---

## 1. Three bars to keep separate

Students confuse these constantly, so name the bar in every finding:

| Bar | What it controls | Example of the difference |
|---|---|---|
| **Scoring point** (SG "Program Requirements", 1 point) | Whether the program code earns the point | The procedure does **not** need a parameter to earn this point |
| **Submission requirement** (Handout) | What the submitted program and PPR must contain | The PPR procedure **must** have a parameter that affects its functionality |
| **Exam readiness** (SG Written Response 2) | Whether the student can earn points on exam day | Question 2(a) uses the **first selection statement in the PPR procedure**; if the procedure has none, that point is lost |

## 2. Program code requirements (Handout, Component A)

Submit one PDF with all program code, **including comments**. Code written by someone else (teacher starter code, APIs, open-source code, generative AI) must be acknowledged, ideally in a comment. The student-developed code must contain:

- **Input** from the user (including user actions that trigger events), a device, an online data stream, or a file.
- **At least one list or other collection** that stores data and is used to manage complexity and help fulfill the program's purpose. Managing complexity means the list makes the program easier to develop (the alternative would be more complex) or easier to maintain (changing the amount of data would otherwise need big code changes).
- **At least one procedure** that contributes to the program's purpose, with a defined name, a return type if the language needs one, and one or more parameters. Built-in procedures, event handlers, and main methods don't count as student-developed.
- **An algorithm with sequencing, selection, and iteration** in the body of that selected procedure.
- **Calls** to the student-developed procedure.
- **Output** (tactile, audible, visual, or textual) based on input and program functionality.

Block-based code is submitted as screenshots of only the program code, not blurry, text at least 10 pt.

## 3. The "Program Requirements" scoring point (SG, 0–1 point)

Graders look at the PPR first, and the full program code only if the requirements aren't in the PPR. The code must include all of: a student-developed procedure, a call to it, a list (or collection), a use of that list, selection, and iteration.

Relaxed for this point:
- The procedure doesn't need a parameter.
- Selection and iteration don't have to be in the same algorithm, or inside a procedure.

The point is **not** awarded if any of these is true:
- The list has only one element.
- The use of the list is irrelevant, i.e. not connected to what the program does.
- The call doesn't match the procedure header (wrong number of arguments, for example), unless the language allows it.
- The selection or the iteration is trivial, meaning it doesn't affect the program's outcome.

## 4. Personalized Project Reference (Handout Component C)

The PPR is screenshots of the student's own code, returned to them on exam day. It must be made individually; code in it may have been developed with a partner. Screenshots must not be blurry and text must be at least 10 pt.

**No comments and no course content anywhere in the PPR.** The Handout says this can make the Create task score 0, including the written responses. This is the single most expensive mistake a student can make.

Four code segments:

**Procedure section**
- (i) A student-developed procedure that defines its name (and return type if needed), contains and **uses** one or more parameters that affect its functionality, and implements an algorithm with sequencing, selection, and iteration.
- (ii) The place in the program where that procedure is called.

**List section**
- (i) Code showing data being stored in the list.
- (ii) Code showing data from **the same list** being used, e.g. creating new data from it or accessing multiple elements, as part of fulfilling the program's purpose.

If the PPR isn't submitted as final by the deadline, the student won't have it on exam day.

## 5. Video (Handout Component B, SG)

Must show the program **running**: input, at least one aspect of functionality, and output. Screenshots or storyboards are not credited. Must be .webm, .mp4, .wmv, .avi, or .mov, **1 minute or less**, **30 MB or less**. No voice narration (text captions are encouraged) and no distinguishing information about the student. Made individually.

## 6. What exam-day written responses need from the PPR (SG, Written Response 2)

- **2(a) Algorithm development**: asks about the Boolean expression in the **first selection statement** in the PPR Procedure section, and values that make it true. No selection statement in the Procedure section means no point.
- **2(b) Errors and testing**: asks for a change that would cause a logic error in the procedure in part (i). No procedure in part (i) means no point. If several procedures appear, the one referenced in the response is used, otherwise the first.
- **2(c) Data and procedural abstraction**: asks how the list-access code would change if elements were added to the end of the list. No list in the List section, or a trivial list use, means no point. If several lists appear, the referenced one is used, otherwise the first.

So a PPR that technically lists four segments can still cost exam points if the procedure has no selection, or the list use is trivial.

## 7. Definitions that settle arguments (SG terminology)

- **Code segment**: for text-based code, continuous statements within the same procedure. For block-based code, statements under the same starting ("hat") block.
- **Collection type**: lists, databases, hash tables, dictionaries, sets, anything that aggregates elements in one structure.
- **Data stored in a list**: by initialization, or computed from other variables or list elements.
- **List being used**: creating new data from existing data, or accessing multiple elements.
- **Iteration**: a repeating portion of an algorithm; **recursion counts as iteration**.
- **Selection**: executing different statements based on a condition; **if-statements and try/except (try/catch) both count**.
- **Parameter**: an input variable of a procedure. Explicit parameters are in the header. Implicit parameters are assigned before a call, e.g. through a GUI.
- **Procedure**: a named group of instructions (function, method, or constructor).
- **Student-developed**: written by the student (alone or with a partner). Calls to existing code or libraries can appear but aren't student-developed. **Event handlers are built-in abstractions and not student-developed; in some block languages they start with "when".**

## 8. Integrity and AI rules (Handout)

- Using code, media, data, or AI-generated code without acknowledgment is plagiarism and scores 0, including the written responses.
- Generative AI is allowed as a supplementary resource for understanding coding principles, helping develop code, and debugging. AI-co-written code must be acknowledged with a comment like "This code was generated using [tool]". The student must understand and be able to explain all of it.
- Once the official task starts, students can't get help writing, revising, debugging, or testing the program from anyone but their partner(s). The AI rule above is College Board's allowance, but **teachers can set stricter class rules**.
- The video and PPR must be made individually.
- Students may ask their teacher to clarify the program and submission requirements. This skill stays on that side of the line: it clarifies requirements and flags gaps; it doesn't do the work.

## 9. Highest-stakes risks, ranked (check these first)

1. Comments or course content in the PPR.
2. Unacknowledged code from others or AI.
3. PPR not submitted as final by the deadline (no reference on exam day).
4. Any of the three components not submitted as final.
