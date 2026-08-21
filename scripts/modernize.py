"""Convert a screen's classic controls to their modern (Fluent 2) equivalents.

Modern controls are not renamed classic controls - they carry a different
styling model. A Classic/Button paints itself with Fill / HoverFill /
PressedFill; a ModernButton has none of those and takes an Appearance enum
instead, letting the app theme do the painting. So a conversion has to DROP
properties, not just map them, and dropping the wrong one silently loses a
visual decision.

Every allowed-property set below is copied from describe_control against the
live environment, not from memory. That is the same rule the rest of this repo
follows: never guess a control property. Anything not in the set is dropped and
reported, so the report is the review surface - read it, do not skim it.

Usage:  python scripts/modernize.py <in.pa.yaml> <out.pa.yaml>
"""
import re, sys

# ---------------------------------------------------------------- properties
# Input properties, verbatim from describe_control. Layout properties that only
# exist inside a GroupContainer are included; they are legal wherever we use them.
LAYOUT = {"LayoutMinWidth", "LayoutMaxWidth", "LayoutMinHeight", "LayoutMaxHeight",
          "FillPortions", "AlignInContainer", "LayoutGridColumnStart",
          "LayoutGridColumnEnd", "LayoutGridRowStart", "LayoutGridRowEnd"}

COMMON = {"AccessibleLabel", "BorderColor", "BorderStyle", "BorderThickness",
          "Color", "ContentLanguage", "DisplayMode", "Font", "FontWeight",
          "Height", "Italic", "PaddingBottom", "PaddingLeft", "PaddingRight",
          "PaddingTop", "RadiusBottomLeft", "RadiusBottomRight", "RadiusTopLeft",
          "RadiusTopRight", "Size", "Strikethrough", "Underline", "Visible",
          "Width", "X", "Y"} | LAYOUT

ALLOWED = {
    "ModernText": COMMON | {"Align", "AutoHeight", "Fill", "OnSelect", "Text",
                            "VerticalAlign", "Wrap"},
    "ModernButton": COMMON | {"Align", "Appearance", "BasePaletteColor", "Icon",
                              "IconRotation", "IconStyle", "Layout", "OnSelect",
                              "Text", "Tooltip", "VerticalAlign"},
    "ModernTextInput": COMMON | {"Align", "Appearance", "BasePaletteColor",
                                 "Default", "Fill", "MaxLength", "OnChange",
                                 "Placeholder", "Required", "TriggerOutput",
                                 "Type", "ValidationState"},
}

CONTROL_MAP = {
    "Label": "ModernText",
    "Classic/Button": "ModernButton",
    "Classic/TextInput": "ModernTextInput",
}

# Renamed rather than dropped.
RENAME = {
    "ModernTextInput": {"HintText": "Placeholder", "Mode": "Type"},
}

VALUE_MAP = {
    ("ModernTextInput", "Type"): {
        "TextMode.SingleLine": "TextInputType.SingleLine",
        "TextMode.MultiLine": "TextInputType.Multiline",
    },
}

# A colour that only restates the theme default is noise once a Fluent theme is
# in play. Colours that carry meaning - muted for hierarchy, the status palette -
# are deliberately NOT in here.
THEME_DEFAULT = {
    "Color": {"AppTheme.Fg", "AppTheme.OnPrimary"},
    "Fill": {"AppTheme.Surface", "AppTheme.Bg"},
}

# Controls that must stay classic, by name, with the reason. These are painted
# surfaces: they rely on Fill/HoverFill/PressedFill, which no modern control has.
# Converting them does not degrade gracefully, it erases the card.
KEEP_CLASSIC = {
    "btnCard": "card surface - needs Fill/HoverFill/PressedFill",
    "galCustomersHit": "transparent hit target - needs Fill/HoverFill/PressedFill",
    "btnSolCard": "card surface - needs Fill/HoverFill/PressedFill",
    "btnSolHit": "transparent hit target - needs Fill/HoverFill/PressedFill",
    "btnUnitRow": "row surface - needs Fill/HoverFill/PressedFill",
    "btnUnitHit": "transparent hit target - needs Fill/HoverFill/PressedFill",
    "btnDocRow": "row surface - needs Fill/HoverFill/PressedFill",
    "btnTile": "tile surface - needs Fill/HoverFill/PressedFill",
    "btnTileHit": "transparent hit target - needs Fill/HoverFill/PressedFill",
}

# Per-control extras keyed by control name: properties to add after conversion.
# Appearance replaces the Fill that gets dropped, so a converted button is not
# left with no styling at all. Appearance and Layout are typed enums, so a typo
# is a compile error; Icon is a plain string, so a wrong name renders nothing -
# but the button keeps its text, which is why the "<" is dropped from the label
# only where an icon actually replaces it.
EXTRA = {
    "btnBackCus": {"Appearance": "ButtonAppearance.Subtle",
                   "Icon": '"ChevronLeft"',
                   "Layout": "ButtonLayout.IconBefore"},
    "txtSearchCus": {"Type": "TextInputType.Search"},
}

# Values replaced outright, where the modern control changes what the text
# should say.
OVERRIDE = {
    "btnBackCus": {"Text": '"Home"'},
}


def indent_of(line):
    return len(line) - len(line.lstrip())


def convert(src, extra=None, keep_classic=None):
    extra = extra or EXTRA
    keep_classic = keep_classic if keep_classic is not None else KEEP_CLASSIC
    lines = src.split("\n")
    out, report = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)- ([A-Za-z_]\w*):\s*$", line)
        if not m:
            out.append(line); i += 1; continue

        ind, name = m.group(1), m.group(2)
        # Look ahead for this control's type without consuming anything yet.
        j, ctype, tline = i + 1, None, None
        while j < len(lines):
            s = lines[j].strip()
            if s.startswith("#") or not s:
                j += 1; continue
            cm = re.match(r"^Control:\s*(.+)$", s)
            if cm:
                ctype, tline = cm.group(1).strip(), j
            break

        target = CONTROL_MAP.get(ctype)
        if target is None or name in keep_classic:
            if name in keep_classic and target:
                report.append(f"  KEPT CLASSIC  {name} ({ctype}) - {keep_classic[name]}")
            out.append(line); i += 1; continue

        # Emit through the Control: line, rewritten.
        out.extend(lines[i:tline])
        out.append(re.sub(r"Control:\s*.+$", f"Control: {target}", lines[tline]))
        i = tline + 1

        # Pass through to Properties:, then transform the block beneath it.
        while i < len(lines) and lines[i].strip() != "Properties:":
            out.append(lines[i]); i += 1
        if i >= len(lines):
            continue
        pind = indent_of(lines[i])
        out.append(lines[i]); i += 1

        seen, added_at = set(), len(out)
        while i < len(lines):
            if not lines[i].strip():
                out.append(lines[i]); i += 1; continue
            if indent_of(lines[i]) <= pind and lines[i].strip():
                break
            if lines[i].strip().startswith("#"):
                out.append(lines[i]); i += 1; continue

            kind = indent_of(lines[i])
            pm = re.match(r"^(\s*)([A-Za-z_]\w*):\s?(.*)$", lines[i])
            if not pm:
                out.append(lines[i]); i += 1; continue

            key, rest = pm.group(2), pm.group(3)
            block = [lines[i]]
            i += 1
            while i < len(lines) and (not lines[i].strip() or indent_of(lines[i]) > kind):
                block.append(lines[i]); i += 1

            newkey = RENAME.get(target, {}).get(key, key)
            value = rest.lstrip("=").strip() if rest.startswith("=") else None

            if newkey not in ALLOWED[target]:
                report.append(f"  dropped       {name}.{key}"
                              + (f" = {value}" if value else " (block)"))
                continue
            if value is not None and value in THEME_DEFAULT.get(newkey, ()):
                report.append(f"  theme default {name}.{newkey} = {value}")
                continue

            ov = OVERRIDE.get(name, {}).get(newkey)
            if ov is not None:
                report.append(f"  overrode      {name}.{newkey} = {ov}")
                seen.add(newkey)
                out.append(f"{pm.group(1)}{newkey}: ={ov}")
                continue

            vmap = VALUE_MAP.get((target, newkey), {})
            if value in vmap:
                block = [f"{pm.group(1)}{newkey}: ={vmap[value]}"]
                report.append(f"  remapped      {name}.{key} -> {newkey} = {vmap[value]}")
            elif newkey != key:
                block[0] = f"{pm.group(1)}{newkey}: {rest}"
                report.append(f"  renamed       {name}.{key} -> {newkey}")

            seen.add(newkey)
            out.extend(block)

        for k, v in extra.get(name, {}).items():
            if k in seen:
                continue
            out.insert(added_at, f"{' ' * (pind + 2)}{k}: ={v}")
            added_at += 1
            report.append(f"  ADDED         {name}.{k} = {v}")

    return "\n".join(out), report


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8").read()
    dst, rep = convert(src)
    open(sys.argv[2], "w", encoding="utf-8", newline="").write(dst)
    print("\n".join(rep) if rep else "  (no changes)")
    print(f"\n{len(rep)} change(s)")
