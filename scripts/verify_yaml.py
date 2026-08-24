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
                         "Installed Version", "Status", "Config Notes",
                         "Last Verified"},
    "TB_References": {"Title", "Product", "Customer", "Section",
                      "Reference Type", "URL", "Version", "Featured",
                      "Last Checked"},
    "TB_SoftwareVersions": {"Title", "Customer", "Product", "Software Version",
                            "Last Verified"},
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
    # "As" was banned by the previous generation of this app (see 73ef065,
    # "Resolve references with one lookup shape and no local names"), citing a
    # tasks/lessons.md that no longer exists on this branch. Re-tested against
    # the live environment on 2026-08-21: scrEditForm's ddParentInst uses
    #     Filter(Choices(TB_Installations.'Parent') As Opt, ...)
    # which compiles clean AND scopes the dropdown correctly at runtime.
    # Removed rather than left firing on every build.
    # AddColumns and With remain banned - neither has been re-tested.
]


# Inline SVG markup, used for the chamfered panels and custom glyphs on scrHome.
# SVG attributes are single-quoted (width='30', fill='none'), which is exactly the shape
# check 4 treats as a quoted SharePoint column name - one card background produced eleven
# false findings. Real findings then hide in the noise, which is worse than no check.
#
# Matching the markup itself rather than the data: prefix, because the formula spans
# several lines and only the first carries the prefix.
SVG_MARKUP_RE = re.compile(
    r"<svg|</svg>|<path|<rect|<polygon|<circle|<line|<g |viewBox|xmlns|preserveAspectRatio"
    # Continuation lines too: a Power Fx conditional inside an SVG splits the markup
    # across lines, so an attribute can appear with no tag beside it.
    r"|fill='|stroke='|stroke-width='|/>\" &"
)


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


# Studio rejects two controls with the same name in one screen:
#   PA1001 : DuplicateNameInSequence
# Worth checking here because the failure names a line number, not the name, and because a
# shared fragment (the brand band) can collide with a control the screen already had.
NAME_RE = re.compile(r"^\s*- (\w+):\s*$", re.M)


def duplicate_names(text):
    seen, dupes = set(), []
    for n in NAME_RE.findall(text):
        if n in seen and n not in dupes:
            dupes.append(n)
        seen.add(n)
    return dupes


PROP_RE = re.compile(r"^(\s+)([A-Za-z]\w*):")


def duplicate_properties(text):
    """A property key set twice inside one control.

    YAML keeps the last occurrence and drops the rest without complaint, so a control can
    look configured twice and behave once. Found after gen_form set Color and Fill on a
    ModernDatePicker and fix_dark_defaults added its own pair: the strip that clears the
    generator's values only matched =AppDark.<token>, so literal colours survived alongside
    the replacements.

    Keyed on indent as well as name so a nested control's property cannot collide with its
    parent's. Block scalars are skipped whole - their contents are Power Fx, and a formula
    line can look exactly like a key.
    """
    out = []
    ctrl_name, seen, skip_indent = None, {}, None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if skip_indent is not None:
            if indent > skip_indent:
                continue
            skip_indent = None
        m = re.match(r"^\s*- (\w+):\s*$", line)
        if m:
            ctrl_name, seen = m.group(1), {}
            continue
        if ctrl_name is None:
            continue
        pm = PROP_RE.match(line)
        if not pm:
            continue
        key = pm.group(2)
        if line.rstrip().endswith(("|", "|-", ">", ">-")):
            skip_indent = indent
        if key in ("Properties", "Children"):
            continue
        prev = seen.get((indent, key))
        if prev:
            out.append((n, f"'{key}' is set twice on {ctrl_name} (first at line {prev}) - "
                           "YAML keeps only the last, so one of them silently does nothing"))
        else:
            seen[(indent, key)] = n
    return out


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

        # 1d. a nested LookUp reaching the outer row by bare column name. LookUp opens
        #     its own record scope, so an unqualified outer column fails with
        #     "Name isn't valid". Reach outward with Table[@Field].
        #     An "As" alias is NOT a bare outer column: Filter(T As U, ...) explicitly
        #     names that scope, and U.Field resolves inside a nested LookUp. This app
        #     depends on that (As R, As I, As U), so aliases declared on the same line are
        #     exempt - without this the check fires on every correct use of As.
        code = _code_only(line)
        aliases = set(re.findall(r"\bAs\s+([A-Z]\w*)", code))
        for m in re.finditer(r"LookUp\([A-Za-z_]\w*,\s*ID\s*=\s*(?!ThisItem\.)(?!var)(?!\w+\[@)([A-Z]\w*)\.", code):
            if m.group(1) in aliases:
                continue
            findings.append((n, f"nested LookUp reaches the outer row by bare name - use Table[@Field]: {stripped[:50]}"))

        # 1e. ButtonAppearance.Secondary is unreadable on this app's dark ground. It
        #     paints an opaque neutral fill from the modern theme, which is a light theme
        #     with no dark-mode switch, so it renders near-white on any background - and
        #     these buttons carry near-white text. Outline is the transparent-with-border
        #     variant; Subtle is transparent with none.
        if "ButtonAppearance.Secondary" in code:
            findings.append((n, "ButtonAppearance.Secondary renders near-white on any "
                                "background - use Outline or Subtle"))

        # 1f. LookUp takes ONE condition, unlike Filter:
        #         LookUp(Table, Condition [, ReductionFormula])
        #     A second condition passed as another argument is either rejected outright
        #     ("Invalid number of arguments: received 4, expected 2-3") or, worse, silently
        #     accepted as the reduction formula - which returns the wrong column rather
        #     than filtering, and reports the failure somewhere else entirely.
        for m in re.finditer(r"LookUp\(", code):
            depth, args, cur = 0, [], ""
            for ch in code[m.end():]:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    if depth == 0:
                        args.append(cur)
                        break
                    depth -= 1
                elif ch == "," and depth == 0:
                    args.append(cur)
                    cur = ""
                    continue
                cur += ch
            if len(args) > 3:
                findings.append((n, f"LookUp given {len(args)} arguments - it takes one "
                                    "condition; join them with &&"))
            elif len(args) == 3 and re.search(r"[<>=]", args[2]):
                findings.append((n, "LookUp's third argument looks like a condition, but "
                                    "that slot is the reduction formula - join with &&"))

        # 1g. A column filtered on a list that does not have it. The generators build
        #     these expressions by string substitution, and a rename that reaches one copy
        #     and not another leaves a filter pointed at the wrong list - which reports as
        #     "Name isn't valid" against a column that exists elsewhere.
        for m in re.finditer(r"LookUp\((TB_\w+)([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
            table, body = m.group(1), m.group(2)
            if table not in SCHEMA:
                continue
            for col in re.findall(r"(?<![\w.'])([A-Z]\w+)\.(?:Value|Id)\b", body):
                if col not in SCHEMA[table]:
                    findings.append((n, f"{table} has no column '{col}' - "
                                        f"filter refers to a column of another list"))

        # 1h. an unresolved templating placeholder. The generators build these files by
        #     f-string, so a brace that was escaped but never substituted ships as text.
        #     Studio says "unexpected characters" and the control falls back to zero,
        #     which reads as a layout bug rather than a build one.
        for ph in re.findall(r"\{([A-Za-z_]\w*)\}", code):
            findings.append((n, f"unresolved template placeholder '{{{ph}}}' - the "
                                "generator emitted it literally"))

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
            code = _code_only(line)
            if re.search(pattern, code):
                # Choices() is the exception: it takes the choice column itself
                # and returns its option set. Choices(X.'Product Type').Value
                # would be wrong. Anything else touching a choice column as a
                # scalar still needs .Value.
                if re.search(r"Choices\(\s*\w+" + re.escape("." + choice), code):
                    continue
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
        if SVG_MARKUP_RE.search(line):
            continue
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

    findings.extend(duplicate_properties(text))

    for n in duplicate_names(text):
        findings.append((0, f"duplicate control name '{n}' - Studio rejects this as "
                            "DuplicateNameInSequence"))

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
