"""Give every text-bearing control an explicit colour, so nothing relies on the theme default.

WHY THE MIGRATION MISSED THESE

migrate_dark.py rewrote colours that were written down. 75 controls never had a Color at
all - they inherited Power Apps' default, which is dark text because the app's modern theme
is a light theme. Swapping the backgrounds to graphite left those inheriting exactly the
same dark grey, now on a dark ground.

This is the inverse of the failure already in 00_Setup.md ("Dropping Fill can leave a Color
that no longer reads"): there a colour survived its background, here no colour existed to
survive. Both have the same root cause - a control whose appearance depends on something
that changed underneath it - and both are invisible to a compile.

The real fix would be a dark modern theme, so the Fluent defaults are correct without
per-control overrides. Power Apps' theme editor generates a palette from a seed colour and
offers no dark-mode switch, so there is nothing to set. Explicit colours are the available
answer, and they are also self-documenting.

THREE ROLES, NOT ONE

- ModernText: AppDark.Fg. These are titles, headings and content.
- Text inputs: Color AND Fill. They had no Fill either, so they were white boxes on a
  dark screen - worse than the dark text, and easy to miss when scanning for colour
  problems because the text inside them was perfectly readable.
- Dropdowns: a LIGHT field with dark ink, and the pair is rewritten even when already
  set. A ModernDropdown takes its surface from the modern theme and ignores Fill, the
  same way ModernButton does, so the dark pair every other field uses put near-white
  text on a near-white control. Light-on-light is readable whichever way Fill behaves.
- Buttons: Color only, and only when Appearance is not Primary. A Primary button gets white
  on the accent from the theme and is already correct; forcing Fg onto the others stops
  Subtle and Outline rendering the light theme's near-black.

THE CURRENCY BADGES

lblCurrencySol / lblCurrencyUnit / lblCurrencyOvw sit on a rectangle whose Fill is a Switch
across OkTint, WarnTint and NeutralTint. Rather than mirror that Switch in the text colour,
they take AppDark.Fg: it clears 12:1 on all three tints, and the state is still encoded by
the fill behind it plus the words in the label itself. Mirroring the Switch would be a
second copy of the same logic to keep in step for no gain.
"""
import re
from pathlib import Path

SCREENS = Path(r"E:\Papp\powerappgoofing\app\screens")

TEXTY = {"ModernText", "Label"}
FIELDY = {"ModernTextInput", "Classic/TextInput"}
# Dropdowns are handled separately: their surface comes from the theme, not from Fill.
DROPDOWNY = {"ModernDropdown", "ModernCombobox", "Classic/DropDown"}
BUTTONY = {"ModernButton", "Classic/Button"}
TOGGLY = {"ModernToggle", "Classic/CheckBox", "ModernCheckBox"}


def indent_of(block):
    """The property indentation inside this control's Properties block."""
    m = re.search(r"^(\s+)Control: ", block, re.M)
    return " " * (len(m.group(1)) + 2)


def fix(path):
    s = path.read_text(encoding="utf-8")
    added = {"Color": 0, "Fill": 0}
    out, blocks = [], re.split(r"(?=\n\s*- \w+:\n)", s)

    for b in blocks:
        m = re.search(r"\n(\s*)- (\w+):\n", b)
        c = re.search(r"^\s+Control: ([\w/]+)", b, re.M)
        if not (m and c):
            out.append(b)
            continue
        ctl = c.group(1)
        ind = indent_of(b)
        has_color = re.search(rf"^{ind}Color: ", b, re.M)
        has_fill = re.search(rf"^{ind}Fill: ", b, re.M)
        # A dropdown carrying the dark pair is wrong rather than merely missing, so those
        # are rewritten instead of skipped.
        if ctl in DROPDOWNY:
            b = re.sub(rf"^{ind}(Color|Fill): =AppDark\.\w+\n", "", b, flags=re.M)
            has_color = has_fill = None
        # A transparent hit target shows no text, so a colour on it means nothing.
        invisible = re.search(r'Text: =""', b) and ctl in BUTTONY
        want = []

        if ctl in TEXTY and not has_color:
            want.append(("Color", "=AppDark.Fg"))
        elif ctl in DROPDOWNY:
            # A ModernDropdown renders its surface from the modern theme - which is light -
            # and ignores Fill, exactly as ModernButton does. Near-white text on it is
            # invisible, which is what "the choices are white with light font" was.
            #
            # So dropdowns are light fields with dark ink. That is readable whether or not
            # Fill is honoured: if it is, the field matches the ink; if it is not, the
            # theme's own light surface does. Literals rather than AppDark tokens because
            # AppDark has no light-field pair and adding one costs an App.pa.yaml repaste
            # for two values used in one place.
            want.append(("Color", '=ColorValue("#14181C")'))
            want.append(("Fill", '=ColorValue("#F2F4F8")'))
        elif ctl in FIELDY:
            if not has_color:
                want.append(("Color", "=AppDark.Fg"))
            if not has_fill:
                want.append(("Fill", "=AppDark.Surface"))
        elif ctl in BUTTONY and not has_color and not invisible:
            # Primary already renders white on the accent; the others would inherit the
            # light theme's near-black foreground.
            if not re.search(r"Appearance: =ButtonAppearance\.Primary\s*$", b, re.M):
                want.append(("Color", "=AppDark.Fg"))
        elif ctl in TOGGLY and not has_color:
            want.append(("Color", "=AppDark.Fg"))

        if want:
            # Insert straight after Control:, which every block has exactly once.
            anchor = re.search(r"^\s+Properties:\n", b, re.M)
            assert anchor, f"{path.name}: {m.group(2)} has no Properties block"
            ins = "".join(f"{ind}{k}: {v}\n" for k, v in want)
            b = b[:anchor.end()] + ins + b[anchor.end():]
            for k, _ in want:
                added[k] += 1
        out.append(b)

    s2 = "".join(out)
    if s2 != s:
        path.write_text(s2, encoding="utf-8", newline="")
    return added


tot = {"Color": 0, "Fill": 0}
for p in sorted(SCREENS.glob("*.pa.yaml")):
    if p.name == "scrHome.pa.yaml":
        continue                       # generated dark, every colour already explicit
    a = fix(p)
    if a["Color"] or a["Fill"]:
        print(f"  {p.name:30} +{a['Color']:3} Color  +{a['Fill']:3} Fill")
    for k in tot:
        tot[k] += a[k]
print(f"\n{tot['Color']} Color and {tot['Fill']} Fill properties added")
