"""Stage 3: clang-tidy + cppcheck (sandboxed) + custom regex rules. Only student files are analysed."""
from __future__ import annotations

import re
from pathlib import Path

from .diag import Diag, Stage, parse
from .precheck import blank
from .sandbox import user
from .sandbox.container import Limits

LIM = Limits(timeout=90, mem_mb=1536, cpus=2, pids=128, out_cap=256 << 10)
TIDY = ("-*,clang-analyzer-*,bugprone-*,concurrency-*,cppcoreguidelines-owning-memory,cppcoreguidelines-no-malloc,"
        "cppcoreguidelines-pro-bounds-array-to-pointer-decay,modernize-use-nullptr,modernize-make-unique,"
        "modernize-make-shared,performance-unnecessary-copy-initialization,performance-for-range-copy,"
        "-bugprone-easily-swappable-parameters,-bugprone-narrowing-conversions,-bugprone-exception-escape,"
        "-bugprone-reserved-identifier,-clang-analyzer-optin.performance*")
CPPCHECK = "{file}:{line}:{column}: {severity}: {message} [cppcheck-{id}]"
SOURCE = (".cpp", ".cc", ".cxx", ".c")

# id -> (pattern on comment/literal-free code, modes where it is on by default)
RULES: dict[str, tuple[str, tuple[str, ...]]] = {
    "unsafe-cstr": (r"\b(?:strcpy|strcat|sprintf|vsprintf|gets|stpcpy)\s*\(", ("user", "module", "toy")),
    "no-raw-new": (r"(?<!operator )(?<!operator)\bnew\b|(?<!= )(?<!=)(?<!operator )(?<!operator)\bdelete\b", ()),
    "no-malloc": (r"\b(?:malloc|calloc|realloc|free)\s*\(", ()),
    "no-c-array": (r"\b(?:int|char|long|short|double|float|unsigned)\s+\w+\s*\[\s*\w*\s*\]", ()),
    "no-goto": (r"\bgoto\b", ()),
    "kernel-float": (r"\b(?:float|double)\b", ("module", "toy")),
    "kernel-libc": (r"#\s*include\s*<(?:stdio\.h|stdlib\.h|iostream|string|vector|cstdio|cstdlib|memory)>", ("module", "toy")),
    "kernel-unchecked-alloc": (r"=\s*k[mzv]alloc\s*\([^;]*;(?![^}]{0,160}(?:\bif\b|\bIS_ERR|\bunlikely|\?))", ("module",)),
    "kernel-sleep-in-atomic": (r"spin_lock\w*\s*\([^}]{0,400}?\b(?:msleep|mutex_lock|kmalloc\s*\([^;]*GFP_KERNEL|copy_(?:to|from)_user|schedule)\b", ("module",)),
    "user-ptr-deref": (r"\b(?:memcpy|strcpy|strlen)\s*\([^;]*\b(?:ubuf|user_buf|__user)\b", ("module",)),
}


def custom(lab: dict, files: dict[str, str]) -> list[Diag]:
    on = {r for r, (_, modes) in RULES.items() if lab["mode"] in modes} | set(lab.get("rules", []))
    on -= set(lab.get("rules_off", []))
    out = []
    for name, text in files.items():
        code = blank(text)
        for rule in sorted(on):
            src = text if rule == "kernel-libc" else code
            for m in re.finditer(RULES[rule][0], src):
                line = src.count("\n", 0, m.start()) + 1
                col = m.start() - src.rfind("\n", 0, m.start())
                out.append(Diag(name, line, col, "error", m.group().split("\n")[0].strip()[:80], f"rule:{rule}"))
    return out


def analyze(lab: dict, work: Path, files: dict[str, str]) -> Stage:
    mode, diags, logs = lab["mode"], custom(lab, files), []
    srcs = sorted(f for f in files if f.endswith(SOURCE))
    std = lab.get("std", "c++20")
    tools = [["cppcheck", "--quiet", "--enable=warning,performance,portability", f"--template={CPPCHECK}",
              "--suppress=missingIncludeSystem", f"--std={std}", *srcs]]
    cxx = [f for f in srcs if not f.endswith(".c")]
    if mode != "module" and cxx:  # kernel headers are not something clang-tidy can digest standalone
        flags = [f"-std={std}", "-Wall", "-Wextra"] + (["-m32", "-ffreestanding", "-fno-exceptions"] if mode == "toy" else [])
        tools.append(["clang-tidy", "--quiet", f"--checks={lab.get('tidy', TIDY)}", *cxx, "--", *flags])
    for cmd in tools if srcs else []:
        r = user.run(work, cmd, lim=LIM)
        log = (r.stdout + r.stderr).decode("utf-8", "replace")
        logs.append(log[-4000:])
        diags += [d for d in parse(log) if d.file in files and not d.rule.startswith(("clang-diagnostic", "-W"))
                  and d.rule != "link-undefined"]
    uniq = list({(d.file, d.line, d.rule): d for d in diags}.values())
    uniq.sort(key=lambda d: (d.file, d.line))
    return Stage(not any(d.severity == "error" for d in uniq), uniq[:50], {}, "\n".join(logs))
