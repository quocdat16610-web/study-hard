"""Stage 1: reject hostile or malformed submissions before anything touches a compiler.

The blacklist is defence in depth (macros can dodge a regex); the sandbox is the real boundary.
"""
from __future__ import annotations

import re

from .diag import Diag, Stage

NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\.(?:cpp|cc|cxx|hpp|hh|h|c|S)")
EXTS = {"user": "cpp cc cxx hpp hh h", "module": "c cpp h hpp", "toy": "cpp c h hpp S"}
BIDI = re.compile("[‪-‮⁦-⁩​-‏﻿]")
CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TOKEN = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', re.S)

# Checked on raw text (they live inside comments, strings or directives).
RAW = {
    "abs-include": r'#\s*(?:include|include_next|embed|import)\s*[<"](?:/|[^>"\n]*\.\./)',
    "incbin": r"\.incbin\b",
    "suppress": r"NOLINT|cppcheck-suppress|#\s*pragma\s+(?:clang|GCC)\s+(?:diagnostic|system_header)"
                r"|no_sanitize|disable_sanitizer_instrumentation",
    "grader-marker": r"@@GRADER|@@READY",
    "host-path": r'"/(?:proc|sys|dev|etc|root|home|var)/',
}
# Checked on code with comments and literals blanked out.
CODE = {
    "user": {
        "exec": r"\b(?:system|popen|exec[lv]p?e?|execvpe|fexecve|posix_spawnp?)\s*\(",
        "fork": r"\b(?:fork|vfork|clone3?)\s*\(",
        "net": r"\bsocket(?:pair)?\s*\(",
        "ptrace": r"\b(?:ptrace|process_vm_(?:read|write)v)\s*\(",
        "raw-syscall": r"\bsyscall\s*\(|\b(?:asm|__asm__|__asm)\b",
        "dynamic-code": r"\b(?:dlopen|dlsym|mmap|mprotect)\s*\(",
        "limits": r"\b(?:setrlimit|prlimit|setuid|setgid|chroot|unshare|setns|mount)\s*\(",
    },
    "module": {
        "usermodehelper": r"\bcall_usermodehelper\w*",
        "kernel-file-io": r"\b(?:filp_open|kernel_read|kernel_write|vfs_read|vfs_write|kernel_read_file\w*)\b",
        "fw-cfg": r"fw_cfg",
        "kallsyms": r"\bkallsyms_\w+|\bkprobe\w*|\bregister_kprobe\b",
        "cpu-control": r"\b(?:native_)?write_cr\d\b|\bwrmsrl?\b|\b(?:asm|__asm__|__asm)\b",
        "power": r"\b(?:kernel_restart|emergency_restart|machine_restart|kernel_power_off|kernel_halt)\b",
    },
    "toy": {},
}


def blank(src: str) -> str:
    """Replace comments and string/char literals with spaces, keeping line/column positions."""
    return _TOKEN.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), src)


def _scan(name: str, text: str, rules: dict[str, str], allow: set[str]) -> list[Diag]:
    out = []
    for rule, pat in rules.items():
        if rule in allow:
            continue
        for m in re.finditer(pat, text):
            line = text.count("\n", 0, m.start()) + 1
            col = m.start() - (text.rfind("\n", 0, m.start()) + 1) + 1
            out.append(Diag(name, line, col, "error", m.group().strip(), f"forbidden:{rule}"))
    return out


def check(lab: dict, files: dict[str, str]) -> Stage:
    spec, mode, diags = lab.get("files", {}), lab["mode"], []
    allow, exts = set(lab.get("allow", [])), set(EXTS[mode].split())

    def bad(rule: str, msg: str, name: str = "", line: int = 0) -> None:
        diags.append(Diag(name, line, 0, "error", msg, rule))

    if not files or len(files) > spec.get("max_files", 8):
        bad("file-count", str(len(files)))
    if sum(len(c.encode("utf-8", "replace")) for c in files.values()) > spec.get("max_bytes", 128 << 10):
        bad("too-large", str(spec.get("max_bytes", 128 << 10)))
    for name in set(spec.get("required", [])) - set(files):
        bad("missing-file", name, name)
    for name, text in files.items():
        if not NAME.fullmatch(name) or name.rsplit(".", 1)[1] not in exts:
            bad("file-name", name)
            continue
        if "only" in spec and name not in spec["only"]:
            bad("unexpected-file", name, name)
        for rule, pat in (("encoding", CTRL), ("hidden-unicode", BIDI)):
            if m := pat.search(text):
                bad(rule, f"U+{ord(m.group()):04X}", name, text.count("\n", 0, m.start()) + 1)
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            bad("encoding", "utf-8", name)
        lines = text.split("\n")
        if len(lines) > 5000 or max(map(len, lines)) > 1000:
            bad("line-limits", "5000x1000", name)
        diags += _scan(name, text, RAW, allow) + _scan(name, blank(text), CODE[mode], allow)
    return Stage(not diags, diags[:50])
