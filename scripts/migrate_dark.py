"""Migrate the nine non-home screens onto the dark palette.

This is a recolour, not a redesign. Every layout, formula and navigation target is left
alone; only colour tokens move. That is the point: it makes the app coherent end to end in
one pass, so scrHome stops looking like a different product, and it leaves the structural
work for the two screens where design actually changes the job.

WHAT IT DOES NOT DO

No chamfered panels, no brand band, no rebuilt version display. Those are structural and
belong to the per-screen rebuilds. What every screen does gain is a 3px accent rule at
Y=0 - enough to read as continuity from the home band, and safe because every screen's
content starts at Y=Gutter (16 narrow, 24 wide), so nothing collides and no Y arithmetic
needs touching.

The rule is AppDark.Accent, not AppDark.Brand. The brand indigo is 1.36:1 against this
background: as a 3px line on graphite it would be invisible. Same reason the accent is a
lightened hue rather than the brand hex.

THE DANGER RED IS NOT A STRAIGHT SWAP

RGBA(176, 0, 32, 1) - the delete affordance - is 2.38:1 on the dark surface. Migrating it
unchanged would leave the "Cannot delete: N things still reference this" warning nearly
unreadable, on the one screen where misreading it destroys data. It splits by role:
BasePaletteColor takes DangerSolid (a fill, white text sits on it), while Color and
BorderColor take Danger (a lighter red that clears 4.5:1 as text).

Contrast for every token was verified before this script was written; see the AppDark
block in App.pa.yaml.
"""
import re
from pathlib import Path

SCREENS = Path(r"E:\Papp\powerappgoofing\app\screens")

# Straight token renames. Primary becomes Accent rather than Brand for the reason above.
TOKENS = {
    "Bg": "Bg", "Surface": "Surface", "Sunken": "Sunken",
    "Fg": "Fg", "FgSecondary": "FgSecondary", "Muted": "Muted", "Faint": "Faint",
    "Line": "Line", "LineSoft": "LineSoft",
    "Primary": "Accent", "PrimaryDark": "AccentSolid", "PrimaryLight": "AccentTint",
    "OnPrimary": "OnBrand",
    "Ok": "Ok", "OkLight": "OkTint",
    "Warn": "Warn", "WarnLight": "WarnTint",
    "Neutral": "Muted", "NeutralLight": "NeutralTint",
}

# Interaction fills were tuned for a light ground: a 4% black wash is invisible on
# graphite, and the pressed tint is built from the retired #0057B8.
LITERALS = {
    "RGBA(0, 0, 0, 0.04)": "RGBA(255, 255, 255, 0.06)",
    "RGBA(0, 87, 184, 0.10)": "RGBA(106, 115, 230, 0.18)",
}

RULE = """            # Brand continuity with the band on scrHome. 3px at Y=0, above all screen
            # content, which starts at Y=Gutter - so no existing Y arithmetic moves.
            - rec{sfx}BrandRule:
                Control: Rectangle
                Properties:
                  X: =0
                  Y: =0
                  Width: =Parent.Width
                  Height: =3
                  Fill: =AppDark.Accent
"""


def migrate(path):
    s = path.read_text(encoding="utf-8")
    orig = s
    counts = {}

    # 1. tokens, longest name first so Primary does not eat PrimaryLight
    for old in sorted(TOKENS, key=len, reverse=True):
        pat = rf"AppTheme\.{old}\b"
        n = len(re.findall(pat, s))
        if n:
            s = re.sub(pat, f"AppDark.{TOKENS[old]}", s)
            counts[f"AppTheme.{old}"] = n

    # 2. interaction literals
    for old, new in LITERALS.items():
        n = s.count(old)
        if n:
            s = s.replace(old, new)
            counts[old] = n

    # 3. the danger red, split by the property it sits on
    def danger(m):
        return f"{m.group(1)}=AppDark.{'DangerSolid' if m.group(1).startswith('BasePaletteColor') else 'Danger'}"
    n = len(re.findall(r"RGBA\(176, 0, 32, 1\)", s))
    if n:
        s = re.sub(r"(BasePaletteColor: |Color: |BorderColor: )=RGBA\(176, 0, 32, 1\)", danger, s)
        counts["danger red"] = n
        leftover = len(re.findall(r"RGBA\(176, 0, 32, 1\)", s))
        assert not leftover, f"{path.name}: {leftover} danger reds on an unexpected property"

    # 4. the brand rule, as first child of the root container.
    # Skipped on screens carrying the full 56px brand band - a 3px accent line at Y=0
    # would draw straight across it. The rule gives continuity to screens that have no
    # band; it is not decoration for the ones that do.
    if re.search(r"- rec\w+Band:\n\s*Control: Rectangle", s):
        return counts
    m = re.search(r"      - (conRoot\w+):\n", s)
    assert m, f"{path.name}: no conRoot container"
    sfx = m.group(1).replace("conRoot", "")
    if f"rec{sfx}BrandRule" not in s:
        anchor = "          Children:\n"
        i = s.index(anchor, m.end())
        s = s[:i + len(anchor)] + RULE.format(sfx=sfx) + s[i + len(anchor):]
        counts["brand rule"] = 1

    if s != orig:
        path.write_text(s, encoding="utf-8", newline="")
    return counts


total = 0
for p in sorted(SCREENS.glob("*.pa.yaml")):
    if p.name == "scrHome.pa.yaml":
        continue                      # generated dark already
    c = migrate(p)
    total += sum(c.values())
    print(f"  {p.name:30} {sum(c.values()):4} change(s)")
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"      {v:4}x  {k}")

print(f"\n{total} changes across 9 screens")
left = sum(len(re.findall(r"AppTheme\.", p.read_text(encoding='utf-8')))
           for p in SCREENS.glob("*.pa.yaml"))
print(f"AppTheme references remaining in app/screens: {left}")
