"""Regression tests for scripts/csp_check.py. Run: python3 evals/test_checker.py"""
import subprocess, sys, os, shutil, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "scripts", "csp_check.py")
F = os.path.join(ROOT, "evals", "files")

# Demo videos are generated on the fly (needs ffmpeg); video tests are skipped without it.
VID = tempfile.mkdtemp()
HAS_FFMPEG = shutil.which("ffmpeg") is not None
if HAS_FFMPEG:
    for name, secs, audio in (("demo_long.mp4", 75, True), ("demo_ok.mp4", 20, False)):
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
               f"testsrc=duration={secs}:size=320x240:rate=10"]
        if audio:
            cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}", "-shortest"]
        subprocess.run(cmd + [os.path.join(VID, name)], check=True)

def run(*a):
    return subprocess.run([sys.executable, S, *a], capture_output=True, text=True).stdout

cases = [
  ("python passing project", run("program", f"{F}/quiz_game.py"),
   ["[MET    ] call to the procedure", "READY   grade_quiz", "[MET    ] selection"]),
  ("app lab: call/header mismatch + one-element list", run("program", f"{F}/weather_app.js"),
   ["[MISSING] call to the procedure", "ONE-ELEMENT LIST", "(ARG COUNT MISMATCH)"]),
  ("java: selection only in main", run("program", f"{F}/GradeBook.java"),
   ["[MET    ] selection", "NOT YET average: no selection inside it", "main method"]),
  ("python failing: callback-only procedure, 1-element list", run("program", f"{F}/turtle_game.py"),
   ["[CHECK  ] call to the procedure", "[MISSING] list", "[MISSING] selection", "[MISSING] iteration"]),
  ("js arrows/classes/constructor", run("program", f"{F}/arrows.js"),
   ["READY   curve", "READY   roster", "passed as callback"]),
  ("python constructor call", run("program", f"{F}/pets.py"),
   ["calls:      line 5"]),
  ("python PPR: comment is score-0 risk", run("ppr", "--procedure", f"{F}/ppr_py_procedure.txt",
     "--call", f"{F}/ppr_py_call.txt", "--list-store", f"{F}/ppr_py_list_store.txt",
     "--list-use", f"{F}/ppr_py_list_use.txt", "--program", f"{F}/quiz_game.py"),
   ["SCORE-0 RISK", "# loop through every answer", "[MET    ] ii. same list used: questions",
    "all lines found in program"]),
  ("js PPR: comment, different list, edited call", run("ppr", "--procedure", f"{F}/ppr_js_procedure.txt",
     "--call", f"{F}/ppr_js_call.txt", "--list-store", f"{F}/ppr_js_list_store.txt",
     "--list-use", f"{F}/ppr_js_list_use.txt", "--program", f"{F}/weather_app.js"),
   ["SCORE-0 RISK", "[MISSING] ii. the list-use segment", "call: 1 line(s) not found"]),
  ("video too long, has audio", run("video", os.path.join(VID, "demo_long.mp4")),
   ["[MISSING] length 75.0 s", "has an audio track"]),
  ("video ok", run("video", os.path.join(VID, "demo_ok.mp4")),
   ["[MET    ] length 20.0 s", "no audio track"]),
  ("js regex literal is not a comment (no false score-0 alarm)",
   run("ppr", "--procedure", f"{F}/regex_edge.js", "--call", f"{F}/regex_edge.js",
       "--list-store", f"{F}/regex_edge.js", "--list-use", f"{F}/regex_edge.js"),
   ["no comments found in the four segments"]),
  ("js division kept, real comment caught",
   run("ppr", "--procedure", f"{F}/division.js", "--call", f"{F}/division.js",
       "--list-store", f"{F}/division.js", "--list-use", f"{F}/division.js"),
   ["// done", "SCORE-0 RISK"]),
  ("python list from split() counts", run("program", f"{F}/split_list.py"),
   ["[MET    ] list (or other collection): names", "READY   longest"]),
  ("js dictionary object and split() list count", run("program", f"{F}/dict_obj.js"),
   ["object used as a dictionary", ".split() result"]),
  ("empty file reports everything missing", run("program", f"{F}/empty.py"),
   ["[MISSING] student-developed procedure", "[MISSING] iteration"]),
]
err = subprocess.run([sys.executable, S, "program", f"{F}/syntax_error.py"], capture_output=True, text=True)
cases.append(("syntax error exits 2 with a hint", err.stderr + f"exit={err.returncode}",
              ["Could not parse as Python", "exit=2"]))
HAS_FFPROBE = shutil.which("ffprobe") is not None  # audio detection needs ffprobe
skipped = 0
if not HAS_FFPROBE:
    print("note: ffprobe not found; skipping audio-track expectations\n")
fails = 0
for name, out, expects in cases:
    if "video" in name and not HAS_FFMPEG:
        print("SKIP " + name + " (needs ffmpeg)")
        skipped += 1
        continue
    if not HAS_FFPROBE:
        expects = [e for e in expects if "audio track" not in e]
    missing = [e for e in expects if e not in out]
    print(("PASS " if not missing else "FAIL ") + name + ("" if not missing else f"  missing: {missing}"))
    fails += bool(missing)
print(f"\n{len(cases) - fails - skipped}/{len(cases) - skipped} passed" + (f" ({skipped} skipped)" if skipped else ""))
sys.exit(1 if fails else 0)
