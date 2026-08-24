r"""Report two text-bearing controls whose rectangles intersect.

Three of these shipped in one session:

  the date picker painted over its own caption    (same Y as the label above it)
  the screen title painted over the first caption (title 68..104 against a caption at 120)
  the age label overlapped the card's meta line   (columns split at 0.55 and 0.62)

None is visible to a compile, none trips any other check, and each looks like a MISSING
label rather than a covered one - which sends you hunting for a control that is right there.

Scanned line by line rather than split with one regex. The first version used
re.finditer with a same-indent lookahead; finditer does not overlap, so the outermost
control swallowed the entire file and exactly one control was ever examined. That is the
same mistake the untyped-variable check shipped with, two hours earlier.

Only controls whose geometry is plain arithmetic are compared; anything sized from a formula
is skipped rather than guessed at. Controls with no Text, or an empty one, are skipped too -
transparent hit targets and rails are meant to sit underneath things.
"""
import re
from pathlib import Path

HEADER = re.compile(r"^(\s*)- (\w+):\s*$")
GEOM = re.compile(r"^\s+(X|Y|Width|Height): =(.+?)\s*$")
TEXT = re.compile(r"^\s+Text: (=)?(.*)$")
NUM = re.compile(r"^[\d\s+\-*/().]+$")


# Resolved at one desktop breakpoint (App.Width 1280), which is enough to catch a control
# sitting on top of another: these collisions are vertical and do not depend on the width.
TOKENS = {
    "ContentWidth": "1100",
    "Parent.Width": "1100",
    "Parent.Height": "740",
    "Gutter": "24",
}


def _val(expr):
    e = expr.strip()
    for k, v in TOKENS.items():
        e = e.replace(k, v)
    if not NUM.match(e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))
    except Exception:
        return None


def _controls(text):
    cur = None
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            if cur:
                yield cur
            cur = {"name": h.group(2), "indent": len(h.group(1)), "text": False,
                   "vis": ""}
            continue
        if cur is None:
            continue
        g = GEOM.match(line)
        if g:
            cur[g.group(1)] = _val(g.group(2))
            continue
        vm = re.match(r"^\s+Visible: =(.+?)\s*$", line)
        if vm:
            cur["vis"] = vm.group(1)
            continue
        t = TEXT.match(line)
        if t:
            # Text: |  starts a block scalar, which is never empty in practice
            cur["text"] = t.group(2).strip() not in ('""', "")
    if cur:
        yield cur


def overlapping_text(text):
    boxes = []
    for c in _controls(text):
        if not c["text"]:
            continue
        if c["vis"] == "false":
            # A parked label carrying a calculation. This app puts several at 0,0 with
            # Width 1 deliberately - they are never drawn.
            continue
        if any(c.get(k) is None for k in ("X", "Y", "Width", "Height")):
            continue
        boxes.append(c)

    out = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a["indent"] != b["indent"]:
                continue                      # not siblings; different coordinate parent
            # Two controls each gated on a different condition are never on screen
            # together, so sharing coordinates is deliberate. A control with no Visible at
            # all is always on screen and can collide with anything.
            if a["vis"] and b["vis"] and a["vis"] != b["vis"]:
                continue
            if (a["X"] < b["X"] + b["Width"] and b["X"] < a["X"] + a["Width"]
                    and a["Y"] < b["Y"] + b["Height"] and b["Y"] < a["Y"] + a["Height"]):
                out.append((0, f"{a['name']} and {b['name']} overlap - both draw text, and "
                               "the one declared later paints over the other"))
    return out


if __name__ == "__main__":
    root = Path(r"E:\Papp\powerappgoofing\app\screens")
    total = 0
    for f in sorted(root.glob("*.pa.yaml")):
        hits = overlapping_text(f.read_text(encoding="utf-8"))
        total += len(hits)
        for _, msg in hits:
            print(f"  {f.name}: {msg}")
    print(f"{total} overlap(s) across the app as it stands")
