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
# Normally empty: the empty-Text rule in is_surface() identifies painted
# surfaces on its own. This is the escape hatch for anything it misjudges.
KEEP_CLASSIC = {
    # ModernTextInput has no Reset property, and Reset(control) is unverified
    # against it. These three are cleared after a write - the first two by
    # Reset() in the Add-solution button, the third by a Reset property bound to
    # varWizCompReset because it lives inside a gallery. Converting them would
    # compile clean and quietly stop the form clearing itself.
    "txtWizSolVersion": "cleared by Reset() after adding a solution",
    "txtWizSolNotes": "cleared by Reset() after adding a solution",
    "txtWizCompVersion": "Reset property binding, inside a gallery",
}

# Per-control extras keyed by control name: properties to add after conversion.
# Appearance replaces the Fill that gets dropped, so a converted button is not
# left with no styling at all. Appearance and Layout are typed enums, so a typo
# is a compile error; Icon is a plain string, so a wrong name renders nothing -
# but the button keeps its text, which is why the "<" is dropped from the label
# only where an icon actually replaces it.
# Applied to every converted control of a type, unless the source already set
# the property.
#
# ModernText carries Fluent's default vertical padding; a classic Label had
# none. On a control sized to its text - a 22px row for 14pt type - content
# plus padding overflows by a pixel or two and the control renders an overflow
# gutter down its right edge. It reads as a stray grey bar and does not scroll,
# because there is almost nothing to scroll. Zeroing the padding restores the
# Label's fit without touching any of the heights the layout depends on.
# ModernButton defaults to ButtonAppearance.Primary - a solid brand-coloured
# button. Every converted button has just had its Fill dropped, so without a
# fallback a quiet list row or a secondary action silently becomes the loudest
# thing on the screen. Secondary is the safe landing place; anything that should
# be Primary says so explicitly in EXTRA, which is applied first and wins.
DEFAULTS = {
    "ModernText": {"PaddingTop": "0", "PaddingBottom": "0"},
    "ModernButton": {"Appearance": "ButtonAppearance.Secondary"},
}

BACK = {"Appearance": "ButtonAppearance.Subtle",
        "Icon": '"ChevronLeft"',
        "Layout": "ButtonLayout.IconBefore"}
SEARCH = {"Type": "TextInputType.Search"}


# Icon is a plain string, so a wrong name renders nothing and the compiler says
# nothing - "Documents" and "AddUser" both silently produced text-only tiles.
# The two that worked, People and Settings, are both in the Segoe Fluent Icons
# list, so names are taken from there rather than invented.
def tab(key):
    """The admin list buttons carried their selected state in Fill, which
    ModernButton does not have. Appearance carries it instead - Primary for the
    active list, Secondary for the rest - so the indicator survives rather than
    being silently dropped as decoration."""
    return {"Appearance": f'If(varAdminList = "{key}", '
                          "ButtonAppearance.Primary, ButtonAppearance.Secondary)"}


def tile(icon):
    return {"Appearance": "ButtonAppearance.Secondary",
            "Icon": f'"{icon}"',
            "Layout": "ButtonLayout.IconBefore"}


EXTRA = {
    # wave 1
    "btnBackCus": BACK,
    "txtSearchCus": SEARCH,
    # wave 2
    "btnBackCat": BACK,
    "txtSearchCat": SEARCH,
    "txtSearchHome": SEARCH,
    "btnTileCatalogue": tile("Document"),
    "btnTileAdmin": tile("Settings"),
    "btnTileOnboard": tile("Add"),
    # wave 4
    "btnBackAdm": BACK,
    "btnBackEdit": {"Appearance": "ButtonAppearance.Subtle",
                    "Icon": '"Cancel"', "Layout": "ButtonLayout.IconBefore"},
    "btnSaveEdit": {"Appearance": "ButtonAppearance.Primary",
                    "Icon": '"Save"', "Layout": "ButtonLayout.IconBefore"},
    "btnAddNew": {"Appearance": "ButtonAppearance.Primary",
                  "Icon": '"Add"', "Layout": "ButtonLayout.IconBefore"},
    "txtSearchAdm": SEARCH,
    "btnGuidedSetup": {"Appearance": "ButtonAppearance.Outline",
                       "Icon": '"People"', "Layout": "ButtonLayout.IconBefore"},
    "btnListCust": tab("Cust"),
    "btnListProd": tab("Prod"),
    "btnListInst": tab("Inst"),
    "btnListRef": tab("Ref"),
    # The wizard's green "add" buttons read as a different kind of action from
    # the blue "next" ones. BasePaletteColor keeps that distinction, which a
    # bare Appearance would have flattened.
    "btnWizStep1Next": {"Appearance": "ButtonAppearance.Primary"},
    "btnWizStep2Next": {"Appearance": "ButtonAppearance.Primary"},
    "btnWizFinish": {"Appearance": "ButtonAppearance.Primary"},
    "btnWizAddSolution": {"Appearance": "ButtonAppearance.Primary",
                          "BasePaletteColor": "AppTheme.Ok",
                          "Icon": '"Add"', "Layout": "ButtonLayout.IconBefore"},
    "btnWizAddUnits": {"Appearance": "ButtonAppearance.Primary",
                       "BasePaletteColor": "AppTheme.Ok",
                       "Icon": '"Add"', "Layout": "ButtonLayout.IconBefore"},
    "btnWizCancel": BACK,
    # wave 3
    "btnBackOvw": BACK,
    "btnBackSol": BACK,
    "btnBackUnit": BACK,
}

# Values replaced outright, where the modern control changes what the text
# should say.
OVERRIDE = {
    "btnBackCus": {"Text": '"Home"'},
    "btnBackCat": {"Text": '"Home"'},
    "btnBackOvw": {"Text": '"Customers"'},
    "btnBackSol": {"Text": '"Overview"'},
    "btnBackUnit": {"Text": '"Solution"'},
    # Corrected after the first push rendered these text-only: neither
    # "Documents" nor "AddUser" is a real Fluent name.
    "btnTileCatalogue": {"Icon": '"Document"'},
    "btnTileOnboard": {"Icon": '"Add"'},
    "btnBackAdm": {"Text": '"Home"'},
    "btnBackEdit": {"Text": '"Cancel"'},
    "btnAddNew": {"Text": '"Add new"'},
    "btnWizCancel": {"Text": '"Home"'},
}


def indent_of(line):
    return len(line) - len(line.lstrip())


def is_surface(lines, tline):
    """True when the control at tline has no text of its own.

    Empty Text or no Text at all - both mean the control is a painted surface
    with labels sitting on top, not a button. The admin galleries' row
    backgrounds declare no Text whatsoever.

    Scans only this control's own Properties block, stopping at the next
    sibling, so a nested child's Text is never mistaken for the parent's.
    """
    j = tline + 1
    while j < len(lines) and lines[j].strip() != "Properties:":
        if re.match(r"^\s*- \w+:\s*$", lines[j]):
            return False
        j += 1
    if j >= len(lines):
        return False
    pind = indent_of(lines[j])
    for k in range(j + 1, len(lines)):
        if lines[k].strip() and indent_of(lines[k]) <= pind:
            break
        if re.match(rf"^\s{{{pind + 2}}}Text:", lines[k]):
            # Has a Text of its own - a surface only if that text is empty.
            # Matches the key, not "Text: =", so a block scalar ("Text: |")
            # counts as having text rather than falling through to True.
            return bool(re.match(rf"^\s{{{pind + 2}}}Text:\s*=\"\"\s*$", lines[k]))
    return True


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

        # A control that is already the modern type is still processed, so
        # EXTRA / OVERRIDE / DEFAULTS re-apply. Without this the tool is
        # one-shot: once app/screens holds converted YAML, correcting an icon
        # name or adding a property silently does nothing.
        target = CONTROL_MAP.get(ctype) or (ctype if ctype in ALLOWED else None)

        # A Classic/Button with no text of its own is not a button, it is a
        # painted surface - a card back, a row background, a transparent hit
        # target with labels sitting on top. Those depend on Fill/HoverFill/
        # PressedFill, which no modern control has, so converting them erases
        # the surface instead of restyling it. A button that carries its own
        # Text is a real button and converts fine.
        reason = keep_classic.get(name)
        if reason is None and ctype == "Classic/Button" and is_surface(lines, tline):
            reason = "empty Text - painted surface, needs Fill/HoverFill"

        if target is None or reason:
            if reason and target:
                report.append(f"  KEPT CLASSIC  {name} ({ctype}) - {reason}")
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

        for k, v in list(extra.get(name, {}).items()) + list(DEFAULTS.get(target, {}).items()):
            if k in seen:
                continue
            out.insert(added_at, f"{' ' * (pind + 2)}{k}: ={v}")
            added_at += 1
            seen.add(k)
            report.append(f"  ADDED         {name}.{k} = {v}")

    return "\n".join(out), report


APPTYPE = {"AppType.Display": 32, "AppType.Title": 22, "AppType.Heading": 17,
           "AppType.Body": 14, "AppType.Small": 12, "AppType.Micro": 10}

# Fluent 2's type ramp pairs each font size with a fixed line height. It is a
# lookup, not a ratio - guessing a ratio either misses the tight rows or pads
# ones that were never broken. The +1 is because a box exactly equal to the line
# height still renders the gutter; 16px of text in a 16px box was the case that
# showed bars on the Catalogue screen, while 22px for 14pt type never did.
LINE_HEIGHT = {10: 14, 12: 16, 14: 20, 17: 22, 22: 28, 32: 40}


def fix_text_heights(src):
    """Raise any ModernText box that is shorter than its own line of text.

    Zeroing the padding was not the whole story. A classic Label clipped
    whatever did not fit; ModernText renders an overflow gutter instead, so a
    box sized flush to the glyphs - 16px for 12pt - shows a grey bar down its
    right edge. The screens written with generous rows never showed it; the
    tightly packed ones do.

    Runs over ModernText directly rather than as part of conversion, so it can
    be re-applied to files that were converted earlier.
    """
    lines, report = src.split("\n"), []
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)- ([A-Za-z_]\w*):\s*$", lines[i])
        if not m or not re.match(r"^\s*Control: ModernText\s*$", lines[i + 1] if i + 1 < len(lines) else ""):
            i += 1; continue
        name = m.group(2)
        j = i + 1
        while j < len(lines) and lines[j].strip() != "Properties:":
            j += 1
        if j >= len(lines):
            i += 1; continue
        pind, end = indent_of(lines[j]), j + 1
        while end < len(lines) and (not lines[end].strip() or indent_of(lines[end]) > pind):
            end += 1

        block = lines[j + 1:end]
        def find(k):
            for n, l in enumerate(block):
                mm = re.match(rf"^\s{{{pind + 2}}}{k}:\s*=(.*)$", l)
                if mm:
                    return n, mm.group(1).strip()
            return None, None
        hn, hv = find("Height")
        _, sv = find("Size")
        px = APPTYPE.get(sv)
        if hn is not None and hv and hv.isdigit() and px in LINE_HEIGHT:
            need = LINE_HEIGHT[px] + 1
            if int(hv) < need:
                lines[j + 1 + hn] = re.sub(r"=\d+\s*$", f"={need}", block[hn])
                report.append(f"  height        {name} {hv} -> {need} (size {px}, line {LINE_HEIGHT[px]})")
        i = end
    return "\n".join(lines), report


def modernize_source(src):
    """convert() then fix_text_heights(), for generators to call inline."""
    src, rep = convert(src)
    src, hrep = fix_text_heights(src)
    return src, rep + hrep


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8").read()
    dst, rep = convert(src)
    dst, hrep = fix_text_heights(dst)
    rep += hrep
    open(sys.argv[2], "w", encoding="utf-8", newline="").write(dst)
    print("\n".join(rep) if rep else "  (no changes)")
    print(f"\n{len(rep)} change(s)")
