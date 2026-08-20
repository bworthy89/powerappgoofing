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

# Single-quoted, capitalised Power Fx tokens that are legitimately not column
# names (e.g. font enums like Font.'Lato'). Check 4 would otherwise flag these
# as unknown columns, since the project's global constraints require this
# quoted-enum style. Extend this list as new non-column quoted tokens show up.
NON_COLUMN_QUOTED_TOKENS = {
    "Lato",
    "Segoe UI",
    "Open Sans",
    "Arial",
    "Georgia",
    "Courier New",
}

# Names the environment rejects. See tasks/lessons.md.
BANNED = [
    (r"\bAddColumns\s*\(", "AddColumns introduces a local name this environment rejects"),
    (r"\bWith\s*\(", "With introduces a local name this environment rejects"),
    (r"\s+As\s+[A-Za-z_]", "As aliases are rejected by this environment"),
]


def check_file(path):
    findings = []
    text = path.read_text(encoding="utf-8")

    # 1. does it parse at all
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        findings.append((0, f"YAML does not parse: {exc}"))

    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # 2. inline scalar carrying ": " outside a block scalar
        m = re.match(r"^(\w+):\s*=(.*)$", stripped)
        if m and ": " in m.group(2):
            findings.append((n, f"inline value contains ': ' — use a | block scalar: {stripped[:60]}"))

        # 3. locally-introduced names
        for pattern, why in BANNED:
            if re.search(pattern, line):
                findings.append((n, f"{why}: {stripped[:60]}"))

        # 4. quoted names that look like columns but are not in the schema
        for quoted in re.findall(r"'([^']{2,40})'", line):
            if quoted in NON_COLUMN_QUOTED_TOKENS:
                continue
            looks_like_column = " " in quoted or quoted[0].isupper()
            if looks_like_column and quoted not in ALL_COLUMNS and quoted not in SCHEMA:
                if not quoted.startswith(("scr", "gal", "lbl", "btn", "con", "ico", "rect", "img")):
                    findings.append((n, f"'{quoted}' is not a column in any of the four lists"))

    return findings


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "app2/screens")
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
