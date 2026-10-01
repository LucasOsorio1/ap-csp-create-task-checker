#!/usr/bin/env python3
"""
csp_check.py - deterministic checks for the AP CSP Create performance task.

Subcommands
  program FILE [--lang auto|python|javascript|java] [--json]
      Finds student-developed procedures, calls, lists and list uses, selection,
      iteration, and input/output hints; reports each program requirement.
  ppr --procedure F --call F --list-store F --list-use F [--program FILE] [--lang ...] [--json]
      Checks the four Personalized Project Reference code segments (saved as text):
      comments (a score-0 risk), the right content in each segment, and - if the
      full program is given - that every segment really appears in the program.
  video FILE [--json]
      Checks format, file size, length, and whether an audio track exists.

Accuracy
  Python is parsed with the ast module, so its structure is exact.
  JavaScript (incl. Code.org App Lab) and Java use a lightweight heuristic parser:
  treat those findings as leads and confirm them by reading the code.
  Judgment calls (is the selection trivial? does the list manage complexity?)
  are never decided here - the report marks them CHECK.

Standard library only (ffprobe is used for video duration when available).
"""
import argparse
import ast
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import textwrap
import tokenize

MET, CHECK, MISSING = "MET", "CHECK", "MISSING"
INF = float("inf")

# --------------------------------------------------------------------------- #
# Shared data model
# --------------------------------------------------------------------------- #


def new_proc(name, line):
    return {
        "name": name, "line": line, "end_line": line, "params": [],
        "min_args": 0, "max_args": 0, "params_used": {},
        "selection": [], "iteration": [], "trivial": [],
        "external_calls": [], "recursive_calls": [], "callback_refs": [],
        "flags": [], "kind": "procedure",
    }


def new_list(name, line, kind, literal_len=None):
    return {"name": name, "line": line, "kind": kind, "literal_len": literal_len,
            "grows": False, "uses": []}


STRONG_USES = {"loop over list", "variable index", "passed to procedure",
               "aggregate/search function", "comprehension over list",
               "higher-order iteration", "membership test"}


# --------------------------------------------------------------------------- #
# Python analyzer (exact, via ast)
# --------------------------------------------------------------------------- #

PY_INPUT = {"input", "open", "get", "urlopen", "reader", "load", "loads",
            "onclick", "onkey", "onkeypress", "onscreenclick", "listen", "bind",
            "askstring", "askinteger", "numinput", "textinput"}
PY_OUTPUT = {"print", "write", "forward", "goto", "circle", "dot", "stamp",
             "showinfo", "config", "configure", "insert", "show", "savefig",
             "blit", "flip", "update", "set_text", "setText", "writerow", "dump"}
AGG_FUNCS = {"len", "sum", "max", "min", "sorted", "choice", "sample", "shuffle",
             "enumerate", "zip", "reversed", "any", "all", "set", "list", "tuple",
             "mean", "median", "join"}


def _walk_no_nested(node):
    """Walk a function body without descending into nested defs/classes."""
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        yield n
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(n))


def _is_const(node):
    return isinstance(node, ast.Constant)


def _range_len_one_or_zero(call):
    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) \
            and call.func.id == "range" and len(call.args) == 1 \
            and isinstance(call.args[0], ast.Constant) \
            and isinstance(call.args[0].value, int) and call.args[0].value <= 1:
        return True
    return False


def analyze_python(src):
    tree = ast.parse(src)
    procs, lists = {}, {}
    parents = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parents[c] = p

    # ---- procedures ----
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        pr = new_proc(node.name, node.lineno)
        pr["end_line"] = getattr(node, "end_lineno", node.lineno)
        in_class = isinstance(parents.get(node), ast.ClassDef)
        a = node.args
        names = [x.arg for x in a.posonlyargs + a.args]
        if in_class and names and names[0] in ("self", "cls"):
            names = names[1:]
            pr["kind"] = "method"
        kwonly = [x.arg for x in a.kwonlyargs]
        pr["params"] = names + kwonly
        n_defaults = len(a.defaults)
        pr["min_args"] = max(0, len(names) - n_defaults) + sum(
            1 for d in a.kw_defaults if d is None)
        pr["max_args"] = INF if a.vararg or a.kwarg else len(names) + len(kwonly)
        if a.vararg:
            pr["params"].append("*" + a.vararg.arg)
        if a.kwarg:
            pr["params"].append("**" + a.kwarg.arg)

        # parameter use (any load of the name inside the function, nested included)
        loads = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)
                 and isinstance(n.ctx, ast.Load)}
        for p in pr["params"]:
            pr["params_used"][p] = p.lstrip("*") in loads

        for n in _walk_no_nested(node):
            ln = getattr(n, "lineno", None)
            if isinstance(n, ast.If):
                pr["selection"].append(("if", ln))
                if _is_const(n.test):
                    pr["trivial"].append(f"line {ln}: if-test is a constant")
            elif isinstance(n, ast.IfExp):
                pr["selection"].append(("conditional expression", ln))
            elif isinstance(n, ast.Try) and n.handlers:
                pr["selection"].append(("try/except", ln))
            elif hasattr(ast, "Match") and isinstance(n, ast.Match):
                pr["selection"].append(("match", ln))
            elif isinstance(n, (ast.For, ast.AsyncFor)):
                pr["iteration"].append(("for loop", ln))
                if _range_len_one_or_zero(n.iter):
                    pr["trivial"].append(f"line {ln}: loop runs at most once")
            elif isinstance(n, ast.While):
                pr["iteration"].append(("while loop", ln))
                if _is_const(n.test) and not n.test.value:
                    pr["trivial"].append(f"line {ln}: while-test is always false")
            elif isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp,
                                ast.GeneratorExp)):
                pr["iteration"].append(("comprehension", ln))
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                    and n.func.id == node.name:
                pr["iteration"].append(("recursion", ln))

        decos = [ast.unparse(d) for d in node.decorator_list]
        decos = [d for d in decos if d not in ("staticmethod", "classmethod",
                                               "property")]
        if decos:
            pr["flags"].append(
                "decorated with @" + ", @".join(decos) +
                " - if a framework calls this for you, it may count as an "
                "event handler (not student-developed)")
        if node.name == "main":
            pr["flags"].append("named main - main methods are not considered "
                               "student-developed")
        if node.name == "__init__" and in_class:
            pr["kind"] = "constructor"
            pr["class_name"] = parents[node].name
        elif pr["kind"] == "method" and node.name.startswith("__"):
            pr["flags"].append("special method - usually called implicitly, "
                               "which is not a visible call for the PPR")
        # dedupe by name: keep first definition, note duplicates
        if node.name in procs:
            procs[node.name]["flags"].append(
                f"defined more than once (again at line {node.lineno})")
        else:
            procs[node.name] = pr

    # ---- calls and callback references ----
    func_nodes = {id(n): n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def enclosing_func(n):
        cur = parents.get(n)
        while cur is not None:
            if id(cur) in func_nodes:
                return cur.name
            cur = parents.get(cur)
        return None

    call_func_ids = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        fname = None
        if isinstance(n.func, ast.Name):
            fname = n.func.id
        elif isinstance(n.func, ast.Attribute):
            fname = n.func.attr
        call_func_ids.add(id(n.func))
        if isinstance(n.func, ast.Name) and fname not in procs:
            ctor = [p for p in procs.values() if p.get("class_name") == fname]
            if ctor:
                fname = "__init__"
        if fname not in procs:
            continue
        pr = procs[fname]
        starred = any(isinstance(x, ast.Starred) for x in n.args) or any(
            k.arg is None for k in n.keywords)
        nargs = len(n.args) + len(n.keywords)
        ok = True if starred else (pr["min_args"] <= nargs <= pr["max_args"])
        kw_bad = [k.arg for k in n.keywords if k.arg and k.arg not in
                  [p.lstrip("*") for p in pr["params"]] and pr["max_args"] != INF]
        if kw_bad:
            ok = False
        rec = {"line": n.lineno, "args": nargs, "consistent": ok}
        if enclosing_func(n) == fname:
            pr["recursive_calls"].append(rec)
        else:
            pr["external_calls"].append(rec)
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) \
                and n.id in procs and id(n) not in call_func_ids:
            procs[n.id]["callback_refs"].append(n.lineno)
        elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load) \
                and n.attr in procs and id(n) not in call_func_ids \
                and not isinstance(parents.get(n), ast.Call):
            procs[n.attr]["callback_refs"].append(n.lineno)

    # ---- lists / collections ----
    def lname(t):
        if isinstance(t, (ast.Name, ast.Attribute)):
            return ast.unparse(t)
        return None

    for n in ast.walk(tree):
        targets, value = [], None
        if isinstance(n, ast.Assign):
            targets, value = n.targets, n.value
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            targets, value = [n.target], n.value
        for t in targets:
            name = lname(t)
            if not name or value is None:
                continue
            kind, llen = None, None
            if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                kind, llen = type(value).__name__.lower() + " literal", len(value.elts)
            elif isinstance(value, ast.Dict):
                kind, llen = "dict literal", len(value.keys)
            elif isinstance(value, (ast.ListComp, ast.SetComp, ast.DictComp)):
                kind = "comprehension"
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                    and value.func.id in ("list", "dict", "set", "tuple", "sorted"):
                kind = value.func.id + "()"
            elif isinstance(value, ast.BinOp) and isinstance(value.op, ast.Mult) \
                    and isinstance(value.left, ast.List):
                kind = "repeated list"
            elif isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) \
                    and value.func.attr in ("split", "readlines", "splitlines",
                                            "findall", "keys", "values", "items"):
                kind = f".{value.func.attr}() result"
            if kind and name not in lists:
                lists[name] = new_list(name, n.lineno, kind, llen)

    grow_methods = {"append", "extend", "insert", "add", "update", "setdefault"}
    for n in ast.walk(tree):
        ln = getattr(n, "lineno", None)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = lname(n.func.value)
            if base in lists:
                if n.func.attr in grow_methods:
                    lists[base]["grows"] = True
                elif n.func.attr in ("index", "count", "pop", "remove", "copy",
                                     "sort", "reverse", "keys", "values", "items",
                                     "get"):
                    lists[base]["uses"].append(("list method ." + n.func.attr, ln))
            for arg in n.args:
                an = lname(arg)
                if an in lists:
                    fid = n.func.attr if isinstance(n.func, ast.Attribute) else None
                    if fid == "join":
                        lists[an]["uses"].append(("aggregate/search function", ln))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            for arg in n.args:
                an = lname(arg)
                if an in lists:
                    if n.func.id in procs:
                        lists[an]["uses"].append(("passed to procedure", ln))
                    elif n.func.id in AGG_FUNCS or n.func.id in ("range",):
                        lists[an]["uses"].append(("aggregate/search function", ln))
                    else:
                        lists[an]["uses"].append(("passed to function", ln))
                # range(len(lst))
                if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) \
                        and arg.func.id == "len" and arg.args \
                        and lname(arg.args[0]) in lists:
                    lists[lname(arg.args[0])]["uses"].append(
                        ("aggregate/search function", ln))
        if isinstance(n, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(n.iter):
                sn = lname(sub) if isinstance(sub, (ast.Name, ast.Attribute)) else None
                if sn in lists:
                    lists[sn]["uses"].append(("loop over list", ln))
        if isinstance(n, ast.comprehension):
            sn = lname(n.iter)
            if sn in lists:
                lists[sn]["uses"].append(("comprehension over list", ln))
        if isinstance(n, ast.Subscript):
            base = lname(n.value)
            if base in lists:
                if isinstance(n.ctx, ast.Store):
                    lists[base]["grows"] = True
                elif isinstance(n.slice, ast.Constant):
                    lists[base]["uses"].append(("fixed index", ln))
                else:
                    lists[base]["uses"].append(("variable index", ln))
        if isinstance(n, ast.Compare):
            for op, comp in zip(n.ops, n.comparators):
                if isinstance(op, (ast.In, ast.NotIn)) and lname(comp) in lists:
                    lists[lname(comp)]["uses"].append(("membership test", ln))
        if isinstance(n, ast.AugAssign) and lname(n.target) in lists:
            lists[lname(n.target)]["grows"] = True
    # later re-assignments that build the list count as growth
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                nm = lname(t)
                if nm in lists and n.lineno != lists[nm]["line"]:
                    lists[nm]["grows"] = True

    # ---- program-wide selection/iteration, input/output hints ----
    sel_any, it_any, trivial_any = [], [], []
    io_in, io_out = set(), set()
    for n in ast.walk(tree):
        ln = getattr(n, "lineno", None)
        if isinstance(n, ast.If):
            sel_any.append(ln)
            if _is_const(n.test):
                trivial_any.append(f"line {ln}: if-test is a constant")
        elif isinstance(n, ast.Try) and n.handlers:
            sel_any.append(ln)
        elif isinstance(n, ast.IfExp) or (hasattr(ast, "Match")
                                          and isinstance(n, ast.Match)):
            sel_any.append(ln)
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.While)):
            it_any.append(ln)
        elif isinstance(n, ast.Call):
            fn = n.func.id if isinstance(n.func, ast.Name) else (
                n.func.attr if isinstance(n.func, ast.Attribute) else "")
            if fn in PY_INPUT:
                io_in.add(f"{fn}() line {ln}")
            if fn in PY_OUTPUT:
                io_out.add(f"{fn}() line {ln}")
        elif isinstance(n, ast.Attribute) and ast.unparse(n) == "sys.argv":
            io_in.add(f"sys.argv line {ln}")
    for pr in procs.values():
        if any(k == "recursion" for k, _ in pr["iteration"]):
            it_any.append(pr["line"])
    return {"language": "python", "exact": True, "procedures": procs,
            "lists": lists, "selection_lines": sorted(set(sel_any)),
            "iteration_lines": sorted(set(it_any)), "trivial": trivial_any,
            "input_hints": sorted(io_in), "output_hints": sorted(io_out)}


# --------------------------------------------------------------------------- #
# C-like heuristic analyzer (JavaScript / App Lab, Java)
# --------------------------------------------------------------------------- #

KEYWORDS = {"if", "for", "while", "switch", "catch", "function", "return", "else",
            "do", "with", "new", "typeof", "try", "finally", "throw", "case",
            "synchronized", "super", "this"}


REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%<>~^")


def _regex_context(out):
    """True if a '/' at this point starts a JS regex literal, not division."""
    prev = "".join(out).rstrip()
    if not prev:
        return True
    if prev[-1] in REGEX_PRECEDERS:
        return True
    return bool(re.search(r"\b(return|typeof|case|in|of|delete|void|throw)$", prev))


def strip_c_like(src, lang="javascript"):
    """Blank out comments, string contents, and (JS) regex literals, keeping
    newlines/positions. Returns (clean_text, comments) with [(line, text)]."""
    out, comments = [], []
    i, n, line = 0, len(src), 1
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if lang == "javascript" and c == "/" and nxt not in "/*" \
                and _regex_context(out[-200:]):
            j, in_class = i + 1, False
            while j < n and src[j] != "\n":
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "[":
                    in_class = True
                elif src[j] == "]":
                    in_class = False
                elif src[j] == "/" and not in_class:
                    break
                j += 1
            if j < n and src[j] == "/":
                j += 1
                while j < n and src[j].isalpha():
                    j += 1
                out.append("/" + " " * (j - i - 2) + "/")
                i = j
                continue
            out.append(c)
            i += 1
        elif c == "/" and nxt == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            comments.append((line, src[i:j].strip()))
            out.append(" " * (j - i))
            i = j
        elif c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            chunk = src[i:j]
            comments.append((line, chunk.strip().splitlines()[0][:80] if chunk.strip() else "/* */"))
            out.append("".join("\n" if ch == "\n" else " " for ch in chunk))
            line += chunk.count("\n")
            i = j
        elif c in "\"'`":
            q, j = c, i + 1
            while j < n and src[j] != q:
                if src[j] == "\\":
                    j += 1
                j += 1
            j = min(j + 1, n)
            chunk = src[i:j]
            out.append(q + "".join("\n" if ch == "\n" else " " for ch in chunk[1:-1])
                       + (q if len(chunk) > 1 else ""))
            line += chunk.count("\n")
            i = j
        else:
            out.append(c)
            if c == "\n":
                line += 1
            i += 1
    return "".join(out), comments


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def match_bracket(text, start, open_ch, close_ch):
    depth = 0
    for k in range(start, len(text)):
        if text[k] == open_ch:
            depth += 1
        elif text[k] == close_ch:
            depth -= 1
            if depth == 0:
                return k
    return len(text) - 1


def split_top(s):
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def parse_params(raw, lang):
    names, min_args, variadic = [], 0, False
    for p in split_top(raw):
        has_default = "=" in p
        p = p.split("=")[0].strip()
        if p.startswith("...") or "..." in p:
            variadic = True
        ids = re.findall(r"[A-Za-z_$][\w$]*", p)
        ids = [x for x in ids if x not in ("final", "const", "let", "var")]
        if not ids:
            continue
        name = ids[-1]
        names.append(name)
        if not has_default and not variadic:
            min_args += 1
    return names, min_args, (INF if variadic else len(names))


def find_defs(clean, lang):
    defs = []  # (name, params_raw, header_start, brace_idx)
    if lang == "javascript":
        pats = [
            r"\bfunction\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(",
            r"\b([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\*?\s*[\w$]*\s*\(",
            r"\b([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",   # arrow w/ parens
            r"\b([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*=>\s*\{",
            r"(?m)^[ \t]*(?:static\s+|async\s+)*([A-Za-z_$][\w$]*)\s*\(",  # class method
        ]
        for pi, pat in enumerate(pats):
            for m in re.finditer(pat, clean):
                name = m.group(1)
                if name in KEYWORDS:
                    continue
                if pi == 3:
                    params_raw, after = m.group(2), m.end() - 1
                    defs.append((name, params_raw, m.start(), after))
                    continue
                p_open = m.end() - 1
                p_close = match_bracket(clean, p_open, "(", ")")
                params_raw = clean[p_open + 1:p_close]
                rest = clean[p_close + 1:p_close + 40]
                if pi == 2:
                    mm = re.match(r"\s*=>\s*\{", rest)
                    if not mm:
                        continue
                    brace = p_close + 1 + mm.end() - 1
                elif pi == 4:
                    mm = re.match(r"\s*\{", rest)
                    # a bare "name(...) {" is a method only inside a class body
                    if not mm or not re.search(r"\bclass\b", clean[:m.start()]):
                        continue
                    brace = p_close + 1 + mm.end() - 1
                else:
                    mm = re.match(r"\s*\{", rest)
                    if not mm:
                        continue
                    brace = p_close + 1 + mm.end() - 1
                defs.append((name, params_raw, m.start(), brace))
    else:  # java
        pat = (r"(?m)^[ \t]*((?:(?:public|private|protected|static|final|abstract|"
               r"synchronized)\s+)*)([\w<>\[\],.?\s]*?\s+)?([A-Za-z_]\w*)\s*\(")
        for m in re.finditer(pat, clean):
            name, rtype = m.group(3), (m.group(2) or "").strip()
            if name in KEYWORDS or rtype in KEYWORDS or rtype.split()[-1:] == ["new"]:
                continue
            if not rtype and not m.group(1):
                continue  # a call statement, not a definition
            p_open = m.end() - 1
            p_close = match_bracket(clean, p_open, "(", ")")
            rest = clean[p_close + 1:p_close + 80]
            mm = re.match(r"\s*(?:throws\s+[\w.,\s]+)?\{", rest)
            if not mm:
                continue
            defs.append((name, clean[p_open + 1:p_close], m.start(),
                         p_close + 1 + mm.end() - 1))
    # dedupe by header position
    seen, out = set(), []
    for d in sorted(defs, key=lambda d: d[2]):
        if d[3] in seen:
            continue
        seen.add(d[3])
        out.append(d)
    return out


def analyze_c_like(src, lang):
    clean, comments = strip_c_like(src, lang)
    procs, lists = {}, {}
    spans = []
    for name, praw, hstart, brace in find_defs(clean, lang):
        end = match_bracket(clean, brace, "{", "}")
        body = clean[brace:end + 1]
        pr = new_proc(name, line_of(clean, hstart))
        pr["end_line"] = line_of(clean, end)
        names, mn, mx = parse_params(praw, lang)
        pr["params"], pr["min_args"], pr["max_args"] = names, mn, mx
        for p in names:
            pr["params_used"][p] = bool(re.search(r"(?<![\w$.])" + re.escape(p)
                                                  + r"(?![\w$])", body[1:]))
        base = brace
        for kind, pat in (("if", r"\bif\s*\("), ("switch", r"\bswitch\s*\("),
                          ("try/catch", r"\btry\s*\{"),
                          ("conditional expression", r"(?<![<?])\?(?![.?:])")):
            for m in re.finditer(pat, body):
                pr["selection"].append((kind, line_of(clean, base + m.start())))
        for kind, pat in (("for loop", r"\bfor\s*\("), ("while loop", r"\bwhile\s*\("),
                          ("do-while loop", r"\bdo\s*\{"),
                          ("higher-order iteration",
                           r"\.(?:forEach|map|filter|reduce|some|every)\s*\(")):
            for m in re.finditer(pat, body):
                pr["iteration"].append((kind, line_of(clean, base + m.start())))
        for m in re.finditer(r"\bif\s*\(\s*(true|false)\s*\)", body):
            pr["trivial"].append(f"line {line_of(clean, base + m.start())}: "
                                 f"if-test is always {m.group(1)}")
        for m in re.finditer(r"\bwhile\s*\(\s*false\s*\)", body):
            pr["trivial"].append(f"line {line_of(clean, base + m.start())}: "
                                 "while-test is always false")
        if re.search(r"(?<![\w$.])" + re.escape(name) + r"\s*\(", body):
            pr["iteration"].append(("recursion", pr["line"]))
        if name == "main" and lang == "java":
            pr["flags"].append("main method - not considered student-developed")
        if name in procs:
            procs[name]["flags"].append(
                f"defined more than once (again at line {pr['line']})")
        else:
            procs[name] = pr
        spans.append((name, hstart, brace, end))

    def inside(idx):
        for nm, hs, br, en in spans:
            if br <= idx <= en:
                return nm
        return None

    header_spans = [(hs, br) for _, hs, br, _ in spans]
    if lang == "javascript" and "constructor" in procs:
        cls = None
        for nm, hs, br, en in spans:
            if nm == "constructor":
                found = re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", clean[:hs])
                cls = found[-1] if found else None
        if cls:
            pr = procs["constructor"]
            pr["kind"] = "constructor"
            for m in re.finditer(r"\bnew\s+" + re.escape(cls) + r"\s*\(", clean):
                p_open = m.end() - 1
                p_close = match_bracket(clean, p_open, "(", ")")
                nargs = len(split_top(clean[p_open + 1:p_close]))
                pr["external_calls"].append({
                    "line": line_of(clean, m.start()), "args": nargs,
                    "consistent": pr["min_args"] <= nargs <= pr["max_args"]})

    for name, pr in procs.items():
        if name == "constructor" and lang == "javascript":
            continue
        for m in re.finditer(r"(?<![\w$])" + re.escape(name) + r"(?![\w$])", clean):
            idx = m.start()
            if any(hs <= idx < br for hs, br in header_spans):
                continue
            after = clean[m.end():m.end() + 1]
            rest = clean[m.end():]
            if re.match(r"\s*\(", rest):
                p_open = m.end() + rest.index("(")
                p_close = match_bracket(clean, p_open, "(", ")")
                nargs = len(split_top(clean[p_open + 1:p_close]))
                ok = pr["min_args"] <= nargs <= pr["max_args"]
                rec = {"line": line_of(clean, idx), "args": nargs, "consistent": ok}
                if inside(idx) == name:
                    pr["recursive_calls"].append(rec)
                else:
                    pr["external_calls"].append(rec)
            elif after != ".":
                pr["callback_refs"].append(line_of(clean, idx))

    # ---- lists ----
    ident = r"[A-Za-z_$][\w$]*"
    if lang == "javascript":
        for m in re.finditer(r"(?:\b(?:var|let|const)\s+)?(" + ident + r")\s*=\s*\[",
                             clean):
            b_open = m.end() - 1
            b_close = match_bracket(clean, b_open, "[", "]")
            n_el = len(split_top(clean[b_open + 1:b_close]))
            nm = m.group(1)
            if nm not in lists:
                lists[nm] = new_list(nm, line_of(clean, m.start()), "array literal", n_el)
            elif m.group(0).count("var") + m.group(0).count("let") == 0:
                lists[nm]["grows"] = True
        for m in re.finditer(r"(?:\b(?:var|let|const)\s+)?(" + ident +
                             r")\s*=\s*(new\s+Array|new\s+Set|new\s+Map|Array\.from|"
                             r"getColumn|readRecords)\s*\(", clean):
            nm = m.group(1)
            if nm not in lists:
                kind = re.sub(r"\s+", " ", m.group(2))
                lists[nm] = new_list(nm, line_of(clean, m.start()),
                                     kind + "()" + (" (App Lab data)" if kind ==
                                                    "getColumn" else ""))
        for m in re.finditer(r"(?:\b(?:var|let|const)\s+)?(" + ident +
                             r")\s*=\s*[^;\n=]*?\.split\s*\(", clean):
            nm = m.group(1)
            if nm not in lists:
                lists[nm] = new_list(nm, line_of(clean, m.start()), ".split() result")
        for m in re.finditer(r"(?:\b(?:var|let|const)\s+)?(" + ident + r")\s*=\s*\{\s*\}",
                             clean):
            nm = m.group(1)
            # an empty object filled with computed keys is a dictionary
            if nm not in lists and re.search(r"\b" + re.escape(nm) +
                                             r"\s*\[\s*(?![\d\"'])[^\]]+\]", clean):
                lists[nm] = new_list(nm, line_of(clean, m.start()),
                                     "object used as a dictionary")
        grow_pats = [r"\b({n})\.(?:push|unshift|splice|add|set)\s*\(",
                     r"\b(?:appendItem|insertItem)\s*\(\s*({n})\b",
                     r"\b({n})\s*\[[^\]]+\]\s*=(?!=)"]
        use_pats = [
            ("variable index", r"\b({n})\s*\[\s*(?!\d+\s*\])[^\]]+\]"),
            ("fixed index", r"\b({n})\s*\[\s*\d+\s*\]"),
            ("aggregate/search function", r"\b({n})\.(?:length|indexOf|includes|join|"
                                          r"slice|concat|find|sort)\b"),
            ("higher-order iteration", r"\b({n})\.(?:forEach|map|filter|reduce|"
                                       r"some|every)\s*\("),
            ("loop over list", r"\bfor\s*\([^)]*\b(?:of|in)\s+({n})\b"),
        ]
    else:
        decl = (r"\b(?:int|double|float|long|short|byte|char|boolean|String|[A-Z]\w*)"
                r"\s*\[\s*\]\s*(" + ident + r")\s*=")
        for m in re.finditer(decl, clean):
            nm = m.group(1)
            rest = clean[m.end():m.end() + 200]
            n_el = None
            mm = re.match(r"\s*\{", rest)
            if mm:
                b_open = m.end() + mm.end() - 1
                n_el = len(split_top(clean[b_open + 1:match_bracket(clean, b_open,
                                                                    "{", "}")]))
            lists.setdefault(nm, new_list(nm, line_of(clean, m.start()), "array", n_el))
        for m in re.finditer(r"\b(?:ArrayList|List|LinkedList|HashMap|Map|HashSet|Set|"
                             r"TreeMap|TreeSet)\s*<[^;=]*>\s*(" + ident + r")\s*=",
                             clean):
            nm = m.group(1)
            lists.setdefault(nm, new_list(nm, line_of(clean, m.start()), "collection"))
        grow_pats = [r"\b({n})\.(?:add|put|addAll|set)\s*\(",
                     r"\b({n})\s*\[[^\]]+\]\s*=(?!=)"]
        use_pats = [
            ("variable index", r"\b({n})\s*\[\s*(?!\d+\s*\])[^\]]+\]"),
            ("fixed index", r"\b({n})\s*\[\s*\d+\s*\]"),
            ("aggregate/search function", r"\b({n})\.(?:length|size|get|contains|"
                                          r"indexOf|keySet|values)\b"),
            ("loop over list", r"\bfor\s*\([^)]*:\s*({n})\b"),
        ]
    for nm, L in lists.items():
        esc = re.escape(nm)
        for gp in grow_pats:
            if re.search(gp.format(n=esc), clean):
                L["grows"] = True
        for kind, up in use_pats:
            for m in re.finditer(up.format(n=esc), clean):
                L["uses"].append((kind, line_of(clean, m.start())))
        # passed as an argument to a call
        for m in re.finditer(r"(" + ident + r")\s*\(([^()]*\b" + esc + r"\b[^()]*)\)",
                             clean):
            fn = m.group(1)
            if fn in ("appendItem", "insertItem", "removeItem") or fn in KEYWORDS:
                continue
            if re.search(r"(?<![\w$.])" + esc + r"(?![\w$\[.])", m.group(2)):
                kind = "passed to procedure" if fn in procs else "passed to function"
                L["uses"].append((kind, line_of(clean, m.start())))

    sel_any = [line_of(clean, m.start()) for m in re.finditer(
        r"\bif\s*\(|\bswitch\s*\(|\btry\s*\{", clean)]
    it_any = [line_of(clean, m.start()) for m in re.finditer(
        r"\bfor\s*\(|\bwhile\s*\(|\bdo\s*\{|\.(?:forEach|map|filter|reduce)\s*\(",
        clean)]
    trivial_any = [f"line {line_of(clean, m.start())}: constant test"
                   for m in re.finditer(r"\bif\s*\(\s*(?:true|false)\s*\)|"
                                        r"\bwhile\s*\(\s*false\s*\)", clean)]
    if lang == "javascript":
        in_pat = (r"\b(onEvent|getText|getNumber|getValue|getChecked|prompt|promptNum|"
                  r"readRecords|getColumn|addEventListener|getKeyValue)\s*\(")
        out_pat = (r"\b(setText|setProperty|setImageURL|setNumber|console\.log|write|"
                   r"playSound|showElement|hideElement|setScreen|drawImage|"
                   r"updateRecord|createRecord|alert)\s*\(")
    else:
        in_pat = r"\b(Scanner|System\.in|readLine|nextInt|nextLine|nextDouble)\b"
        out_pat = r"\b(System\.out\.print(?:ln)?|JOptionPane|printf)\b"
    io_in = sorted({f"{m.group(1)} line {line_of(clean, m.start())}"
                    for m in re.finditer(in_pat, clean)})
    io_out = sorted({f"{m.group(1)} line {line_of(clean, m.start())}"
                     for m in re.finditer(out_pat, clean)})
    for pr in procs.values():
        if any(k == "recursion" for k, _ in pr["iteration"]):
            it_any.append(pr["line"])
    return {"language": lang, "exact": False, "procedures": procs, "lists": lists,
            "selection_lines": sorted(set(sel_any)),
            "iteration_lines": sorted(set(it_any)), "trivial": trivial_any,
            "input_hints": io_in, "output_hints": io_out, "comments": comments}


# --------------------------------------------------------------------------- #
# Language detection, comment scanning
# --------------------------------------------------------------------------- #


def detect_lang(path, src):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "python"
    if ext in (".js", ".mjs", ".jsx", ".ts"):
        return "javascript"
    if ext == ".java":
        return "java"
    if re.search(r"^\s*def\s+\w+\s*\(.*\)\s*(->.*)?:\s*$", src, re.M):
        return "python"
    if re.search(r"\bfunction\b|\b(var|let|const)\s+\w+|onEvent\s*\(|=>", src):
        return "javascript"
    if re.search(r"\b(public|private|protected|static)\b|System\.out|"
                 r"\b(int|double|String|boolean)\s+\w+\s*[=;(]", src):
        return "java"
    try:
        ast.parse(textwrap.dedent(src))
        return "python"
    except SyntaxError:
        pass
    if re.search(r":\s*$", src, re.M) and "{" not in src:
        return "python"
    return "javascript"


def python_comments(src):
    found = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                found.append((tok.start[0], tok.string.strip()))
    except (tokenize.TokenError, IndentationError):
        for i, line in enumerate(src.splitlines(), 1):
            if "#" in line:
                found.append((i, line[line.index("#"):].strip()))
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Module)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                        and isinstance(first.value.value, str):
                    found.append((first.lineno, "docstring (reads as a comment)"))
    except SyntaxError:
        pass
    return sorted(found)


def comments_in(src, lang):
    if lang == "python":
        return python_comments(textwrap.dedent(src))
    return strip_c_like(src, lang)[1]


# --------------------------------------------------------------------------- #
# Requirement verdicts
# --------------------------------------------------------------------------- #


def strong_list_uses(L):
    return [u for u in L["uses"] if u[0] in STRONG_USES]


def evaluate_program(res):
    procs, lists = res["procedures"], res["lists"]
    req = {}

    student_procs = [p for p in procs.values()
                     if not any("main" in f for f in p["flags"])]
    called = [p for p in student_procs if p["external_calls"]]
    consistent = [p for p in called if any(c["consistent"] for c in p["external_calls"])]
    if not student_procs:
        req["student-developed procedure"] = (MISSING, "no procedure/function "
                                              "definitions found (event handlers and "
                                              "main don't count)")
    else:
        names = ", ".join(p["name"] for p in student_procs)
        flagged = [p["name"] for p in student_procs if p["flags"]]
        st = CHECK if flagged and len(flagged) == len(student_procs) else MET
        req["student-developed procedure"] = (st, f"found: {names}" + (
            f" (review flags on: {', '.join(flagged)})" if flagged else ""))
    if consistent:
        req["call to the procedure"] = (MET, "; ".join(
            f"{p['name']} called at line(s) " + ", ".join(
                str(c["line"]) for c in p["external_calls"]) for p in consistent))
    elif called:
        bad = [f"{p['name']} line {c['line']} passes {c['args']} argument(s), header "
               f"expects {p['min_args']}" + ("" if p['max_args'] == p['min_args'] else
                                             f"-{p['max_args']}")
               for p in called for c in p["external_calls"]]
        req["call to the procedure"] = (MISSING, "call doesn't match the procedure "
                                        "header (a 'do not award' rule): " +
                                        "; ".join(bad))
    elif any(p["callback_refs"] for p in student_procs):
        req["call to the procedure"] = (CHECK, "procedure only passed as a callback "
                                        "(e.g. to an event handler) - graders may not "
                                        "see a call; add a direct call")
    else:
        req["call to the procedure"] = (MISSING, "no call found")

    real_lists = []
    for L in lists.values():
        one_elem = L["literal_len"] == 1 and not L["grows"]
        L["one_element"] = one_elem
        if not one_elem:
            real_lists.append(L)
    if real_lists:
        req["list (or other collection)"] = (MET, ", ".join(
            f"{L['name']} (line {L['line']}, {L['kind']})" for L in real_lists))
    elif lists:
        req["list (or other collection)"] = (MISSING, "only one-element lists found "
                                             "(a 'do not award' rule)")
    else:
        req["list (or other collection)"] = (MISSING, "no list/array/collection found")

    used = [L for L in real_lists if strong_list_uses(L)]
    weak = [L for L in real_lists if L["uses"] and not strong_list_uses(L)]
    if used:
        req["use of the list"] = (CHECK, "; ".join(
            f"{L['name']}: " + ", ".join(sorted({u[0] for u in strong_list_uses(L)}))
            for L in used) + " - confirm the use is connected to the program's "
                             "functionality (irrelevant use doesn't count)")
    elif weak:
        req["use of the list"] = (CHECK, "only fixed-index access found (e.g. lst[0]); "
                                  "'using' a list means creating new data from it or "
                                  "accessing multiple elements")
    else:
        req["use of the list"] = (MISSING, "no use of a list found")

    triv = res["trivial"] + [t for p in procs.values() for t in p["trivial"]]
    for key, lines in (("selection", res["selection_lines"]),
                       ("iteration", res["iteration_lines"])):
        if lines:
            note = f"at line(s) {', '.join(map(str, lines[:8]))}"
            if triv:
                note += f"; possible trivial use: {'; '.join(sorted(set(triv)))}"
            req[key] = (CHECK if triv else MET, note)
        else:
            req[key] = (MISSING, f"no {key} found")

    req["input (submission requirement)"] = (
        MET if res["input_hints"] else CHECK,
        ", ".join(res["input_hints"][:6]) or "no recognizable input call - confirm "
        "input from the user, a device, an online data stream, or a file")
    req["output (submission requirement)"] = (
        MET if res["output_hints"] else CHECK,
        ", ".join(res["output_hints"][:6]) or "no recognizable output call - confirm "
        "the program produces output")

    # PPR candidates: procedure w/ used parameter, selection, iteration, direct call
    cands = []
    for p in student_procs:
        reasons = []
        used_params = [k for k, v in p["params_used"].items() if v]
        if not p["params"]:
            reasons.append("no parameter")
        elif not used_params:
            reasons.append("parameter(s) never used in the body")
        if not p["selection"]:
            reasons.append("no selection inside it")
        if not p["iteration"]:
            reasons.append("no iteration inside it")
        if not any(c["consistent"] for c in p["external_calls"]):
            reasons.append("no matching direct call")
        if p["flags"]:
            reasons.append("flag: " + "; ".join(p["flags"]))
        cands.append((p["name"], reasons))
    return req, cands


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #


def fmt_program(res, req, cands):
    out = []
    lang = res["language"]
    out.append(f"AP CSP Create task - program check ({lang}; "
               + ("exact parse" if res["exact"] else "HEURISTIC parse: confirm by "
                  "reading the code") + ")")
    out.append("=" * 72)
    out.append("PROGRAM REQUIREMENTS")
    for k, (st, note) in req.items():
        out.append(f"  [{st:<7}] {k}: {note}")
    out.append("")
    out.append("PROCEDURES FOUND")
    if not res["procedures"]:
        out.append("  (none)")
    for p in res["procedures"].values():
        params = ", ".join(f"{k}{'' if v else ' (UNUSED)'}"
                           for k, v in p["params_used"].items()) or "none"
        sel = ", ".join(f"{k}@{ln}" for k, ln in p["selection"]) or "none"
        it = ", ".join(f"{k}@{ln}" for k, ln in p["iteration"]) or "none"
        calls = ", ".join(f"line {c['line']}" + ("" if c["consistent"] else
                                                  " (ARG COUNT MISMATCH)")
                          for c in p["external_calls"]) or "none"
        out.append(f"  {p['name']} (lines {p['line']}-{p['end_line']})")
        out.append(f"      parameters: {params}")
        out.append(f"      selection:  {sel}")
        out.append(f"      iteration:  {it}")
        out.append(f"      calls:      {calls}"
                   + (f"; passed as callback at line(s) "
                      f"{', '.join(map(str, p['callback_refs']))}"
                      if p["callback_refs"] else ""))
        for f in p["flags"]:
            out.append(f"      flag:       {f}")
    out.append("")
    out.append("LISTS / COLLECTIONS FOUND")
    if not res["lists"]:
        out.append("  (none)")
    for L in res["lists"].values():
        uses = ", ".join(sorted({u[0] for u in L["uses"]})) or "no uses found"
        extra = " - ONE-ELEMENT LIST (doesn't count)" if L.get("one_element") else ""
        size = f", {L['literal_len']} element(s) at start" if L["literal_len"] \
            is not None else ""
        out.append(f"  {L['name']} (line {L['line']}, {L['kind']}{size}"
                   f"{', grows later' if L['grows'] else ''}){extra}")
        out.append(f"      uses: {uses}")
    out.append("")
    out.append("PPR PROCEDURE CANDIDATES (needs: used parameter, selection AND "
               "iteration inside, a direct call)")
    ready = [n for n, r in cands if not r]
    for n, r in cands:
        out.append(f"  {'READY  ' if not r else 'NOT YET'} {n}"
                   + ("" if not r else f": {'; '.join(r)}"))
    if not cands:
        out.append("  (no procedures)")
    elif not ready:
        out.append("  -> No procedure meets every PPR requirement yet. The scoring "
                   "point can still be earned, but the PPR and exam-day written "
                   "responses depend on one.")
    out.append("")
    out.append("Not checked by this script (judgment calls): whether the selection/"
               "iteration affects the outcome, whether the list manages complexity, "
               "whether the parameter changes what the procedure does, and whether a "
               "procedure is really an event handler.")
    return "\n".join(out)


def cmd_program(args):
    src = open(args.file, encoding="utf-8", errors="replace").read()
    lang = args.lang if args.lang != "auto" else detect_lang(args.file, src)
    try:
        res = analyze_python(src) if lang == "python" else analyze_c_like(src, lang)
    except SyntaxError as e:
        print(f"Could not parse as Python: {e}. If this is not Python, rerun with "
              f"--lang javascript or --lang java.", file=sys.stderr)
        return 2
    req, cands = evaluate_program(res)
    if args.json:
        print(json.dumps({"analysis": res, "requirements": req,
                          "ppr_candidates": cands}, default=str, indent=2))
    else:
        print(fmt_program(res, req, cands))
    return 0


def norm_lines(text):
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"\s//.*$|^//.*$|\s#.*$|^#.*$", "", ln)  # drop trailing comments
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            out.append(ln)
    return out


def cmd_ppr(args):
    seg = {}
    for key in ("procedure", "call", "list_store", "list_use"):
        path = getattr(args, key)
        seg[key] = open(path, encoding="utf-8", errors="replace").read()
    lang = args.lang
    if lang == "auto":
        lang = detect_lang(args.procedure, seg["procedure"])
    results, score0 = [], []
    out = [f"AP CSP Create task - Personalized Project Reference check ({lang})",
           "=" * 72]

    # 1. comments anywhere (score-0 risk)
    out.append("COMMENTS (any comment in the PPR can make the Create task score 0)")
    any_comment = False
    for key, text in seg.items():
        cm = comments_in(text, lang)
        if cm:
            any_comment = True
            score0.append(f"comments in {key} segment")
            for ln, t in cm:
                out.append(f"  [MISSING] {key} segment line {ln}: {t}")
    if not any_comment:
        out.append("  [MET    ] no comments found in the four segments")
    out.append("")

    def analyze(text):
        text = textwrap.dedent(text)
        try:
            return analyze_python(text) if lang == "python" else \
                analyze_c_like(text, lang)
        except SyntaxError:
            # segments can be fragments; fall back to heuristic parsing for python
            return None

    # 2. procedure segment
    out.append("PROCEDURE SECTION")
    pres = analyze(seg["procedure"])
    proc = None
    if pres and pres["procedures"]:
        proc = list(pres["procedures"].values())[0]
        used = [k for k, v in proc["params_used"].items() if v]
        rows = [
            ("i. defines a named procedure", MET, proc["name"]),
            ("i. has a parameter", MET if proc["params"] else MISSING,
             ", ".join(proc["params"]) or "none"),
            ("i. parameter is used (affects functionality)",
             CHECK if used else MISSING,
             (", ".join(used) + " used - confirm it changes what the procedure does")
             if used else "no parameter is used in the body"),
            ("i. selection inside the procedure", MET if proc["selection"] else MISSING,
             ", ".join(f"{k}@{ln}" for k, ln in proc["selection"]) or "none - exam "
             "question 2(a) asks about the FIRST selection statement here"),
            ("i. iteration inside the procedure", MET if proc["iteration"] else MISSING,
             ", ".join(f"{k}@{ln}" for k, ln in proc["iteration"]) or "none"),
        ]
        if len(pres["procedures"]) > 1:
            rows.append(("i. one procedure shown", CHECK, "segment defines "
                         f"{len(pres['procedures'])} procedures; exam questions use "
                         "the one you reference, else the first"))
        for label, st, note in rows:
            out.append(f"  [{st:<7}] {label}: {note}")
        if proc["selection"]:
            first_line = proc["selection"][0][1]
            src_line = seg["procedure"].splitlines()[first_line - 1].strip() \
                if first_line and first_line <= len(seg["procedure"].splitlines()) else ""
            out.append(f"  note: first selection statement (exam 2a) -> line "
                       f"{first_line}: {src_line}")
    else:
        out.append("  [MISSING] i. no procedure definition found in the procedure "
                   "segment (or it could not be parsed)")
    # call segment
    if proc:
        pat = r"(?<![\w$])" + re.escape(proc["name"]) + r"\s*\(([^()]*(?:\([^()]*\)"\
              r"[^()]*)*)\)"
        calls = [m for m in re.finditer(pat, seg["call"])
                 if not re.search(r"\b(def|function)\s+$",
                                  seg["call"][:m.start()].splitlines()[-1]
                                  if seg["call"][:m.start()] else "")]
        if calls:
            nargs = len(split_top(calls[0].group(1)))
            ok = proc["min_args"] <= nargs <= proc["max_args"]
            out.append(f"  [{MET if ok else MISSING:<7}] ii. call to {proc['name']}: "
                       f"{nargs} argument(s)" + ("" if ok else
                                                 f", header expects {proc['min_args']}"))
        else:
            out.append(f"  [MISSING] ii. call segment doesn't call {proc['name']}")
    out.append("")

    # 3. list section
    out.append("LIST SECTION")
    sres, ures = analyze(seg["list_store"]), analyze(seg["list_use"])
    store_names = set(sres["lists"]) if sres else set()
    if not store_names:
        # growth-only segments (e.g. appendItem(scores, x) or lst.append(x))
        store_names = set(re.findall(r"\b([A-Za-z_$][\w$]*)\s*\.\s*(?:append|push|"
                                     r"add|insert|extend)\s*\(", seg["list_store"]))
        store_names |= set(re.findall(r"\b(?:appendItem|insertItem)\s*\(\s*"
                                      r"([A-Za-z_$][\w$]*)", seg["list_store"]))
    if store_names:
        out.append(f"  [MET    ] i. data stored in list(s): {', '.join(sorted(store_names))}")
    else:
        out.append("  [MISSING] i. no list being created or filled in the list-store "
                   "segment")
    use_text = seg["list_use"]
    same = [n for n in store_names if re.search(r"(?<![\w$])" + re.escape(n)
                                                + r"(?![\w$])", use_text)]
    if same:
        strong = []
        if ures:
            for n in same:
                L = ures["lists"].get(n)
                if L:
                    strong += [u[0] for u in strong_list_uses(L)]
        multi = bool(strong) or bool(re.search(
            r"\bfor\b|\bwhile\b|forEach|\.map\(|\blen\(|\.length", use_text))
        out.append(f"  [{MET if multi else CHECK:<7}] ii. same list used: "
                   f"{', '.join(same)}" + ("" if multi else " - confirm it creates new "
                                           "data or accesses multiple elements"))
    else:
        out.append("  [MISSING] ii. the list-use segment doesn't use the list from "
                   "segment i (it must be the SAME list)")
    out.append("")

    # 4. segments really come from the program
    if args.program:
        prog = norm_lines(open(args.program, encoding="utf-8",
                               errors="replace").read())
        prog_set = set(prog)
        out.append("SEGMENTS MATCH THE SUBMITTED PROGRAM")
        for key, text in seg.items():
            code_lines = [ln for ln in norm_lines(text)]
            missing = [ln for ln in code_lines if ln not in prog_set
                       and not ln.startswith(("#", "//"))]
            st = MET if not missing else CHECK
            out.append(f"  [{st:<7}] {key}: " + ("all lines found in program" if not
                                                  missing else f"{len(missing)} line(s) "
                                                  f"not found, e.g. '{missing[0][:60]}'"))
        out.append("")
    out.append("Not checkable from text: screenshots must be readable (not blurry, "
               "text at least 10 pt) and contain no course content. Check the images.")
    if score0:
        out.insert(2, "!! SCORE-0 RISK: " + "; ".join(score0) + "\n")
    print("\n".join(out))
    return 0


VIDEO_EXT = {".webm", ".mp4", ".wmv", ".avi", ".mov"}


def mp4_duration(path):
    """Read the mvhd atom of an mp4/mov file (fallback when ffprobe is absent)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        i = data.find(b"mvhd")
        if i < 4:
            return None
        version = data[i + 4]
        if version == 1:
            timescale, duration = struct.unpack(">IQ", data[i + 24:i + 36])
        else:
            timescale, duration = struct.unpack(">II", data[i + 16:i + 24])
        return duration / timescale if timescale else None
    except (OSError, struct.error):
        return None


def cmd_video(args):
    path = args.file
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    duration, audio, source = None, None, None
    if shutil.which("ffprobe"):
        try:
            d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "default=nw=1:nk=1", path],
                               capture_output=True, text=True, timeout=60)
            duration = float(d.stdout.strip()) if d.stdout.strip() else None
            a = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                                "-show_entries", "stream=index", "-of", "csv=p=0",
                                path], capture_output=True, text=True, timeout=60)
            audio = bool(a.stdout.strip())
            source = "ffprobe"
        except (ValueError, subprocess.SubprocessError):
            pass
    if duration is None and ext in (".mp4", ".mov"):
        duration, source = mp4_duration(path), "mp4 header"
    out = ["AP CSP Create task - video check", "=" * 72]
    out.append(f"  [{MET if ext in VIDEO_EXT else MISSING:<7}] format {ext or '(none)'}"
               f" - allowed: .webm .mp4 .wmv .avi .mov")
    mb = size / 1_000_000
    out.append(f"  [{MET if size <= 30_000_000 else MISSING:<7}] size {mb:.1f} MB - "
               f"limit 30 MB (checked as 30,000,000 bytes, the stricter reading)")
    if duration is None:
        out.append("  [CHECK  ] length unknown (no ffprobe) - must be 1 minute or less")
    else:
        out.append(f"  [{MET if duration <= 60.0 else MISSING:<7}] length "
                   f"{duration:.1f} s ({source}) - limit 60 s")
    if audio is True:
        out.append("  [CHECK  ] has an audio track - voice narration is not allowed "
                   "(program sounds and text captions are fine)")
    elif audio is False:
        out.append("  [MET    ] no audio track (so no voice narration)")
    out.append("  [CHECK  ] watch it: shows input, at least one aspect of "
               "functionality, and output; no name, face, school, or other "
               "distinguishing information; a real recording, not screenshots")
    print("\n".join(out))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("program", help="check the full program code")
    p.add_argument("file")
    p.add_argument("--lang", default="auto",
                   choices=["auto", "python", "javascript", "java"])
    p.add_argument("--json", action="store_true")
    q = sub.add_parser("ppr", help="check the four PPR code segments (as text files)")
    q.add_argument("--procedure", required=True, help="segment i of Procedure section")
    q.add_argument("--call", required=True, help="segment ii of Procedure section")
    q.add_argument("--list-store", required=True, dest="list_store",
                   help="segment i of List section")
    q.add_argument("--list-use", required=True, dest="list_use",
                   help="segment ii of List section")
    q.add_argument("--program", help="full program file, to confirm segments are real")
    q.add_argument("--lang", default="auto",
                   choices=["auto", "python", "javascript", "java"])
    v = sub.add_parser("video", help="check the video file")
    v.add_argument("file")
    args = ap.parse_args()
    if args.cmd == "program":
        return cmd_program(args)
    if args.cmd == "ppr":
        return cmd_ppr(args)
    return cmd_video(args)


if __name__ == "__main__":
    sys.exit(main())
