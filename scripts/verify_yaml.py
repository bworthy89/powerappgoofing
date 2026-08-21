#!/usr/bin/env python3
"""Verify Power Apps .pa.yaml screen files before pasting them into Studio.

Two checks, both earned from real failures:

  1. An inline scalar containing ": " makes the YAML parser read a nested
     mapping and the whole document fails to load. Projected SharePoint
     columns always contain ": ", so this is not hypothetical.

  2. A column name that is not in the schema produces a "Name isn't valid"
     error in Studio that points at the formula rather than at the list.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required:  pip install pyyaml")

SCHEMA = {
    "TB_Customers": {"Title", "Description", "Support Notes", "Active"},
    "TB_Products": {"Title", "Product Type", "Family",
                    "Current Standard Version", "Description", "Active"},
    "TB_Installations": {"Title", "Customer", "Parent", "Product",
                         "Installed Version", "Status", "Config Notes"},
    "TB_References": {"Title", "Product", "Customer", "Section",
                      "Reference Type", "URL", "Version", "Featured",
                      "Last Checked"},
}
ALL_COLUMNS = set().union(*SCHEMA.values())

# Choice columns are records, not scalars. Every read needs .Value.
CHOICE_COLUMNS = ["'Product Type'", "Family", "Status", "Section", "'Reference Type'"]

# Power Fx enum TYPE names whose members this project writes quoted
# (Font.'Lato', FontWeight.'Bold'). This is a closed set defined by the
# language itself, so listing the enum *types* here does not repeat the
# whack-a-mole of listing every enum *value*. It must NOT be widened to "any
# identifier before a dot": SharePoint column access uses the identical
# shape (ThisItem.'Deployment Status'), and that is exactly what check 4
# exists to catch — see tasks/lessons.md.
QUOTED_ENUM_TYPES = {
    "Font", "FontWeight", "Align", "DisplayMode", "TextMode",
    "Overflow", "VerticalAlign", "TextDecoration",
}
_ENUM_PREFIX_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in QUOTED_ENUM_TYPES) + r")\.\s*$"
)

# Fallback for single-quoted tokens the enum-prefix rule above does not reach
# (e.g. a formula split across lines so the "EnumType." prefix is not on the
# same line as the quote). Keep this list small. Must contain at least "Lato".
NON_COLUMN_QUOTED_TOKENS = {
    "Lato",
}

# Names the environment rejects. See tasks/lessons.md.
# "As" is matched case-insensitively because Power Fx keywords are.
BANNED = [
    (r"\bAddColumns\s*\(", "AddColumns introduces a local name this environment rejects"),
    (r"\bWith\s*\(", "With introduces a local name this environment rejects"),
    (r"(?i)\s+As\s+[A-Za-z_]", "As aliases are rejected by this environment"),
]


def _code_only(line):
    """Strip a YAML comment and any double-quoted string contents from a line
    so keyword checks do not fire on comment text or string literals (e.g. a
    comment reading "not With AddColumns(" or a UI string "Configured As
    default"). Single-quoted Power Fx tokens are left alone — check 4 needs
    them and they are not where these keywords legitimately appear."""
    out = []
    in_string = False
    for ch in line:
        if in_string:
            if ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out)


def check_file(path):
    findings = []
    text = path.read_text(encoding="utf-8")

    # 1. does it parse at all
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        findings.append((0, f"YAML does not parse: {exc}"))

    _props_indent = None
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # 1b. a property sitting at the same indent as its own Properties: line.
        #     Valid YAML, but Studio rejects it with
        #     "PA1001 ... Property 'X' not found on type ControlInstance" because the key
        #     lands on the control node instead of inside Properties.
        if _props_indent is not None:
            ind = len(line) - len(line.lstrip())
            if line.strip() and ind <= _props_indent:
                if re.match(r"^\s*\w+:", line) and not re.match(r"^\s*(Control|Variant|Properties|Children):", line.strip() and line):
                    if ind == _props_indent:
                        findings.append((n, f"property sits level with Properties: instead of inside it: {stripped[:55]}"))
                _props_indent = None
        if re.match(r"^\s*Properties:\s*$", line):
            _props_indent = len(line) - len(line.lstrip())

        # 1c. the reserved word Parent used as a column. In Power Fx Parent means the
        #     parent CONTROL, so a column of that name must be reached through
        #     ThisRecord inside a record scope. Unqualified, it resolves to the control,
        #     the expression errors, and the control renders blank with no error shown.
        code = _code_only(line)
        if re.search(r"(?<!ThisRecord\.)(?<!varInstallation\.)\bParent\.(Value|Id)\b", code) \
           or re.search(r"\bParent\s*=\s*Blank\(\)", code):
            findings.append((n, f"reserved word Parent used as a column - qualify with ThisRecord.Parent: {stripped[:50]}"))

        # 2. inline scalar carrying ": " outside a block scalar
        m = re.match(r"^(\w+):\s*=(.*)$", stripped)
        if m and ": " in m.group(2):
            findings.append((n, f"inline value contains ': ' — use a | block scalar: {stripped[:60]}"))

        # 2b. a Choice column as a SortByColumns key. SortByColumns takes only
        #     primitive columns; a choice raises the same "Invalid argument type".
        if "SortByColumns" in text:  # any sort key in a file that sorts
            for choice in CHOICE_COLUMNS:
                bare = choice.strip("'")
                if f'"{bare}"' in line:
                    findings.append((n, f"SortByColumns cannot sort on the choice column {choice}: {stripped[:55]}"))

        # 3. a Choice column used as a scalar. SharePoint choice columns are records;
        #    concatenating or comparing one without .Value gives Studio's
        #    "Invalid argument type. Expecting one of: Text, Number, ... ViewValue".
        for choice in CHOICE_COLUMNS:
            pattern = r"\." + re.escape(choice) + r"(?!\.Value)(?![\w'])"
            if re.search(pattern, _code_only(line)):
                findings.append((n, f"choice column {choice} used without .Value: {stripped[:60]}"))

        # 3. locally-introduced names (skip YAML comments and string literals)
        code_line = _code_only(line)
        for pattern, why in BANNED:
            if re.search(pattern, code_line):
                findings.append((n, f"{why}: {stripped[:60]}"))

        # 4. quoted names that look like columns but are not in the schema.
        # A single-quoted token immediately preceded by "EnumType." (Font,
        # FontWeight, ...) is Power Fx enum syntax, not a column reference,
        # so it is never flagged — no per-enum-value allowlist needed. Only
        # the closed set of real enum type names is exempted; column access
        # through a record/control (ThisItem.'Deployment Status') uses the
        # same dotted shape and must still be checked.
        for m in re.finditer(r"'([^']{2,40})'", line):
            quoted = m.group(1)
            prefix = line[:m.start()]
            if _ENUM_PREFIX_RE.search(prefix):
                continue
            if quoted in NON_COLUMN_QUOTED_TOKENS:
                continue
            looks_like_column = " " in quoted or quoted[0].isupper()
            if looks_like_column and quoted not in ALL_COLUMNS and quoted not in SCHEMA:
                if not quoted.startswith(("scr", "gal", "lbl", "btn", "con", "ico", "rect", "img")):
                    findings.append((n, f"'{quoted}' is not a column in any of the four lists"))

    return findings


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "app/screens")
    files = sorted(root.rglob("*.pa.yaml")) if root.is_dir() else [root]
    if not files:
        sys.exit(f"no .pa.yaml files under {root}")

    total = 0
    for f in files:
        findings = check_file(f)
        total += len(findings)
        status = "ok" if not findings else f"{len(findings)} finding(s)"
        print(f"{f}: {status}")
        for line_no, msg in findings:
            print(f"  line {line_no}: {msg}")

    print(f"\n{len(files)} file(s), {total} finding(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
