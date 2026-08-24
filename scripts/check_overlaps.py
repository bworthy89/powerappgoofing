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
BLOCK = re.compile(r"^\s+(X|Y|Width|Height|Visible): \|\s*$")
TEXT = re.compile(r"^\s+Text: (=)?(.*)$")
NUM = re.compile(r"^[\d\s+\-*/().]+$")


# Resolved at one desktop breakpoint (App.Width 1280), which is enough to catch a control
# sitting on top of another: these collisions are vertical and do not depend on the width.
TOKENS = {
    "ContentWidth": "1100",
    "Parent.Width": "1100",
    "Parent.Height": "740",
    "Gutter": "24",
    # A gallery row is measured against its template, not the screen.
    "Parent.TemplateWidth": "1052",
    "Parent.TemplateHeight": "56",
}


def _args(e, open_at):
    """Top-level comma-separated arguments of a call whose "(" is at open_at."""
    i, depth, args, arg = open_at + 1, 0, [], ""
    while i < len(e):
        ch = e[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                args.append(arg)
                return args, i
            depth -= 1
        if ch == "," and depth == 0:
            args.append(arg)
            arg = ""
        else:
            arg += ch
        i += 1
    return None, None


def _term(t, wide):
    """One term of a condition: True, False, or None when it cannot be read."""
    t = t.strip()
    t = re.sub(r"\w+\.Size\s*>=\s*ScreenSize\.\w+", "WIDE", t)
    t = re.sub(r"\bIsNarrow\b", "NARROW", t)
    # The admin view is the busier one, and the one whose affordances collide.
    t = re.sub(r"\bvarIsAdmin\b", "True", t)
    t = t.replace("!", " not ").replace("&&", " and ").replace("||", " or ")
    if not re.fullmatch(r"[\s()andortTrueFalseWIDENARROW]+", t):
        return None
    try:
        return bool(eval(t, {"__builtins__": {}},
                         {"WIDE": wide, "NARROW": not wide}))
    except Exception:
        return None


def _cond(c, wide):
    """A condition's value, term by term.

    Split on top-level && first: a conjunction is false as soon as one term is, even when
    the others are things this checker cannot read. CAN TAKE is gated on
    "!IsBlank(varExpandedModel) && varExpandedModel <> 0 && <wide>" - two terms it has no
    opinion about and one that settles it on a phone.
    """
    if not c.strip():
        return None
    whole = _term(c, wide)
    if whole is not None:
        return whole
    depth, terms, cur = 0, [], ""
    i = 0
    while i < len(c):
        if c[i] == "(":
            depth += 1
        elif c[i] == ")":
            depth -= 1
        if depth == 0 and c.startswith("&&", i):
            terms.append(cur)
            cur = ""
            i += 2
            continue
        cur += c[i]
        i += 1
    terms.append(cur)
    if len(terms) < 2:
        return None
    vals = [_term(t, wide) for t in terms]
    if any(v is False for v in vals):
        return False
    if all(v is True for v in vals):
        return True
    return None


def _branch(e, wide):
    """Collapse every If() whose condition this checker can decide."""
    for _ in range(20):
        m = re.search(r"\bIf\(", e)
        if not m:
            return e
        args, close = _args(e, m.end() - 1)
        if not args or len(args) < 3:
            return e
        picked = _cond(args[0], wide)
        if picked is None:
            return e
        e = e[:m.start()] + "(" + args[1 if picked else 2].strip() + ")" + e[close + 1:]
    return e


def _val(expr, wide, known=None):
    e = _branch(expr.strip(), wide)
    for k, v in TOKENS.items():
        e = e.replace(k, v)
    # ctrl.Y / ctrl.Height, resolved from what is already known
    if known:
        for ref, num in known.items():
            e = e.replace(ref, repr(num))
    if not NUM.match(e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))
    except Exception:
        return None


def _controls(text):
    cur, stack, pending = None, [], None
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            if cur:
                yield cur
            ind = len(h.group(1))
            # Indent alone does not identify a parent: the children of two different
            # galleries sit at the same depth. Walk the open ancestors instead.
            while stack and stack[-1][1] >= ind:
                stack.pop()
            parent = stack[-1][0] if stack else ""
            stack.append((h.group(2), ind))
            pending = None
            cur = {"name": h.group(2), "indent": ind, "text": False,
                   "vis": "", "parent": parent}
            continue
        if cur is None:
            continue
        # A long formula is written as a block scalar - "X: |" with the value on the
        # next line - and the single-line pattern never saw those at all. scrCatalogue's
        # whole right-hand pane is positioned that way, which is why the checker called a
        # broken screen clean.
        if pending:
            v = line.strip()
            v = v[1:] if v.startswith("=") else v
            # Visible is routed to its own slot: two controls gated on different
            # conditions are never on screen together, and missing that turned every
            # such pair into a false positive.
            cur["vis" if pending == "Visible" else pending] = v
            pending = None
            continue
        b = BLOCK.match(line)
        if b:
            pending = b.group(1)
            continue
        g = GEOM.match(line)
        if g:
            # kept raw; resolving needs the whole screen, and a width
            cur[g.group(1)] = g.group(2)
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


def overlapping_text(text, wide=True, report_skipped=None):
    ctrls = [c for c in _controls(text)]

    # Resolve what can be resolved, repeatedly: a control positioned from another control
    # only becomes computable once that one is.
    known, raw = {}, {}
    for c in ctrls:
        for k in ("X", "Y", "Width", "Height"):
            if c.get(k) is not None:
                raw[(c["name"], k)] = c[k]
    for _ in range(12):
        moved = False
        for (name, k), expr in raw.items():
            if (name, k) in known:
                continue
            v = _val(expr, wide, {f"{n}.{kk}": val for (n, kk), val in known.items()})
            if v is not None:
                known[(name, k)] = v
                moved = True
        if not moved:
            break

    boxes, skipped = [], []
    for c in ctrls:
        if not c["text"]:
            continue
        # A control this width cannot show is not on this screen. CAN TAKE is wide-only,
        # so on a phone it cannot collide with anything, and comparing the Visible strings
        # as text could never work that out.
        if _cond(c["vis"], wide) is False:
            continue
        g = {k: known.get((c["name"], k)) for k in ("X", "Y", "Width", "Height")}
        if any(v is None for v in g.values()):
            skipped.append(c["name"])
            continue
        boxes.append((c, g))

    if report_skipped is not None:
        report_skipped.extend(skipped)

    out = []
    for i, (a, ga) in enumerate(boxes):
        for b, gb in boxes[i + 1:]:
            if a["parent"] != b["parent"]:
                continue                      # different containers, different coordinates
            if a["vis"] and b["vis"] and a["vis"] != b["vis"]:
                continue
            if (ga["X"] < gb["X"] + gb["Width"] and gb["X"] < ga["X"] + ga["Width"]
                    and ga["Y"] < gb["Y"] + gb["Height"] and gb["Y"] < ga["Y"] + ga["Height"]):
                out.append((0, f"{a['name']} and {b['name']} overlap - both draw text, and "
                               "the one declared later paints over the other"))
    return out


if __name__ == "__main__":
    root = Path(r"E:\Papp\powerappgoofing\app\screens")
    total, skipped_total = 0, 0
    for f in sorted(root.glob("*.pa.yaml")):
        t = f.read_text(encoding="utf-8")
        seen = set()
        for wide, label in ((True, "wide"), (False, "narrow")):
            sk = []
            for _, msg in overlapping_text(t, wide, sk):
                if msg in seen:
                    continue
                seen.add(msg)
                total += 1
                print(f"  {f.name} [{label}]: {msg}")
            skipped_total += len(set(sk))
    print(f"{total} overlap(s); {skipped_total} control(s) skipped as unresolvable")
    import sys
    sys.exit(1 if total else 0)
