"""Shared YAML fragments for the rebuilt dark screens.

scrSolution and scrUnit are the same shape: a brand band, a title, the version hero, config
notes, then documents and firmware. Only the data differs. Generating both from one set of
fragments means the band cannot drift by two pixels between screens and the document rows
cannot end up with different rules on one screen than the other - which is exactly what
happened to the hand-written versions, where the same "  ·  " separator appeared with three
different spacings.

Anything genuinely screen-specific stays in that screen's generator.
"""
from pathlib import Path

BAND = 56   # the one definition of the band height; generators emit it as a literal
            # so changing it needs no App-level formula and no App.pa.yaml repaste
CW = "Parent.Width - (Gutter * 2)"
PANEL_MAX = 620          # a reading measure; full-bleed panels look unfinished on desktop

WORDMARK = Path(
    r"C:\Users\bwort\AppData\Local\Temp\claude\E--Papp"
    r"\c7a373b9-de1b-4ba5-a22b-70f79a3b6252\scratchpad\glory_wordmark_b64.txt"
).read_text().strip()


def brand_band(sfx, back_target, back_transition="UnCover", back_label="Back",
               back_onselect=None):
    """Compact brand band: back button left, wordmark right.

    Half the height of the home band, because on a detail screen the mark is reassurance
    rather than an entrance. The wordmark is the real Glory artwork, so this band is the
    brand's own lockup - white on #111987 - rather than a tint of it.
    """
    action = back_onselect or f"Navigate({back_target}, ScreenTransition.{back_transition})"
    return f"""            - rec{sfx}Band:
                Control: Rectangle
                Properties:
                  X: =0
                  Y: =0
                  Width: =Parent.Width
                  Height: ={BAND}
                  Fill: =AppDark.Brand
            - imgWordmark{sfx}:
                Control: Image
                Properties:
                  X: =Parent.Width - Gutter - 96
                  Y: =20
                  Width: =96
                  Height: =15
                  Image: |
                    ="data:image/png;base64,{WORDMARK}"
            - btnBack{sfx}:
                Control: ModernButton
                Properties:
                  Appearance: =ButtonAppearance.Subtle
                  Icon: ="ChevronLeft"
                  Layout: =ButtonLayout.IconBefore
                  Text: ="{back_label}"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.OnBrand
                  BorderThickness: =0
                  X: =Gutter - 8
                  Y: =6
                  Width: =140
                  Height: =44
                  OnSelect: |
                    ={action}"""


def config_panel(sfx, y):
    """Free-text notes someone left about this specific installation."""
    return f"""            - conConfigNotes{sfx}:
                Control: GroupContainer
                Variant: ManualLayout
                Properties:
                  X: =Gutter
                  Y: |
                    ={y}
                  Width: =Min({CW}, {PANEL_MAX})
                  Height: =92
                  Fill: =AppDark.Surface
                  Visible: =!IsBlank(varInstallation.'Config Notes')
                Children:
                  - lblConfigHeading{sfx}:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        X: =20
                        Y: =14
                        Width: =Parent.Width - 40
                        Height: =18
                        Text: ="CONFIGURATION NOTES"
                        Font: =AppFont
                        Size: =AppType.Small
                        FontWeight: =FontWeight.Bold
                        Color: =AppDark.Muted
                  - lblConfigNotes{sfx}:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        X: =20
                        Y: =36
                        Width: =Parent.Width - 40
                        Height: =46
                        Text: =varInstallation.'Config Notes'
                        Font: =AppFont
                        Size: =AppType.Body
                        Color: =AppDark.Fg"""


def ref_gallery(key, sfx, heading, empty, y, items, meta=None, height=None,
                visible=None, empty_visible=None, x=None, width=None):
    """A documents-or-firmware list.

    A row carries an accent rail only when Featured, so the eye goes to the reference
    someone deliberately promoted rather than to all of them equally. Everything else gets
    the neutral line, which still gives the row a left edge to align against.

    The "last checked" column is deliberately loud when stale: a service manual nobody has
    verified in eighteen months is a different object from one checked last month, and the
    old screen said so in the same grey as everything else.

    meta/height/visible let a caller vary the parts that genuinely differ. scrCatalogue
    names the owning product only when the document belongs to a UNIT rather than to the
    model being viewed - repeating "CI 300X" on every row of the CI 300X panel is noise -
    and it lives in a responsive split whose height is not derived from its own row count.
    """
    meta = meta or (
        "=ThisItem.'Reference Type'.Value & \"  ·  \" & "
        "LookUp(TB_Products, ID = ThisItem.Product.Id).Title & "
        "If(IsBlank(ThisItem.Customer.Value), \"\", \"  ·  this customer\")")
    height = height or f"=Min(CountRows(gal{key}{sfx}.AllItems), 4) * 60"
    visible = visible or f"=CountRows(gal{key}{sfx}.AllItems) > 0"
    # The empty state answers the same gate as the gallery, inverted. Passed
    # explicitly rather than derived, because negating an arbitrary caller
    # expression textually produces things like "X > 0 = false".
    empty_visible = empty_visible or f"=CountRows(gal{key}{sfx}.AllItems) = 0"
    # scrCatalogue places this list in the right-hand column of a responsive
    # split rather than at the page gutter.
    # A heading may be a literal or a formula; a caller passing one starting
    # with "=" wants it evaluated (scrCatalogue names the selected model).
    heading_text = heading if heading.startswith("=") else f'="{heading}"'
    # No heading means no space for one: the label collapses to zero height and the
    # gallery starts at the origin rather than 32px below it.
    head_h = 0 if heading == "" else 22
    head_gap = 0 if heading == "" else 10
    x = x or "=Gutter"
    width = width or f"={CW}"
    return f"""
            - lbl{key}Heading{sfx}:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: |
                    {x}
                  Y: |
                    ={y}
                  Width: |
                    {width}
                  Height: ={head_h}
                  Visible: ={str(heading != "").lower()}
                  Wrap: =false
                  AutoHeight: =false
                  Text: |
                    {heading_text}
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Bold
                  Color: =AppDark.Muted
            - gal{key}{sfx}:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: |
                    {x}
                  Y: =lbl{key}Heading{sfx}.Y + {head_h} + {head_gap}
                  Width: |
                    {width}
                  Height: |
                    {height}
                  TemplateSize: =60
                  TemplatePadding: =0
                  ShowScrollbar: =true
                  Visible: |
                    {visible}
                  Items: |
                    {items}
                Children:
                  - rec{key}Rail{sfx}:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =3
                        Height: =Parent.TemplateHeight - 1
                        Fill: =If(ThisItem.Featured = true, AppDark.Accent, AppDark.Line)
                  - lbl{key}Title{sfx}:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16
                        Y: =9
                        Width: =Parent.TemplateWidth - 32
                        Height: =22
                        Text: =ThisItem.Title
                        Font: =AppFont
                        Size: =AppType.Body
                        FontWeight: =FontWeight.Semibold
                        Color: =If(IsBlank(ThisItem.URL), AppDark.Faint, AppDark.Fg)
                        Wrap: =false
                        AutoHeight: =false
                  - lbl{key}Type{sfx}:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16
                        Y: =32
                        Width: =(Parent.TemplateWidth - 32) * 0.6
                        Height: =18
                        Text: |
                          {meta}
                        Font: =AppFont
                        Size: =AppType.Small
                        Color: =AppDark.Muted
                        Wrap: =false
                        AutoHeight: =false
                  - lbl{key}Checked{sfx}:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16 + ((Parent.TemplateWidth - 32) * 0.6)
                        Y: =32
                        Width: =(Parent.TemplateWidth - 32) * 0.4
                        Height: =18
                        Align: =Align.Right
                        Font: =AppFont
                        Size: =AppType.Small
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          =If(
                              IsBlank(ThisItem.'Last Checked'),
                              "never checked",
                              DateDiff(ThisItem.'Last Checked', Today(), TimeUnit.Months) >= 12,
                              "not checked in " & DateDiff(ThisItem.'Last Checked', Today(), TimeUnit.Months) & " months",
                              "checked " & Text(ThisItem.'Last Checked', "dd mmm yyyy")
                          )
                        Color: |
                          =If(
                              IsBlank(ThisItem.'Last Checked'),
                              AppDark.Muted,
                              DateDiff(ThisItem.'Last Checked', Today(), TimeUnit.Months) >= 12,
                              AppDark.Warn,
                              AppDark.Ok
                          )
                  - rec{key}Rule{sfx}:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =59
                        Width: =Parent.TemplateWidth
                        Height: =1
                        Fill: =AppDark.Line
                  - gal{key}Hit{sfx}:
                      Control: Classic/Button
                      Properties:
                        OnSelect: =Launch(ThisItem.URL)
                        X: =0
                        Y: =0
                        Width: =Parent.TemplateWidth
                        Height: =Parent.TemplateHeight
                        Text: =""
                        Fill: =RGBA(0, 0, 0, 0)
                        HoverFill: =RGBA(255, 255, 255, 0.06)
                        PressedFill: =RGBA(106, 115, 230, 0.18)
                        BorderThickness: =0
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        FocusedBorderThickness: =2
                        FocusedBorderColor: =AppDark.Accent
            - lblNo{key}{sfx}:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: |
                    {x}
                  Y: =gal{key}{sfx}.Y
                  Width: |
                    {width}
                  Height: =40
                  Text: ="{empty}"
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Muted
                  Visible: |
                    {empty_visible}"""


def version_hero(sfx, y, customer_id="varCustomer.ID",
                 product_id="varInstallation.Product.Id"):
    """The version answer, as a component instance.

    Control is the literal CanvasComponent; the definition is named in the sibling
    ComponentName key. Writing the component's own name as the control type is rejected
    with PA2101 - see 00_Setup.md.

    This is the only place a component is allowed to live in this app: one cannot be
    inserted into a gallery or a form, which rules out every list here.
    """
    eff = effective_version("varInstallation", customer_id, product_id)
    ver = effective_verified("varInstallation", customer_id, product_id)
    vnote = verified_note(ver)
    vstale = verified_is_stale(ver)
    note = version_source_note("varInstallation", customer_id, product_id)
    return f"""            - cmpVersion{sfx}:
                Control: CanvasComponent
                ComponentName: cmpVersionChip
                Properties:
                  X: =Gutter
                  Y: |
                    ={y}
                  Width: =Min({CW}, {PANEL_MAX})
                  Height: =116
                  ExpectedVersion: |
                    ={eff}
                  VerifiedNote: |
                    ={vnote}
                  IsStale: |
                    ={vstale}
                  SourceNote: |
                    ={note}"""


def effective_version(inst, customer_id, product_id):
    """The software version in force for an installation.

    The machine's own Installed Version, or failing that the Software reference recorded
    for this customer and this model. Coalesce treats a zero-length string as blank, so a
    field someone cleared behaves the same as one never filled in.

    The installation record is never written by this - it only changes what is displayed
    and compared, so a site default can be corrected without touching machine records.
    """
    return (f"Coalesce({inst}.'Installed Version', "
            f"LookUp(TB_SoftwareVersions, Customer.Id = {customer_id} "
            f"&& Product.Id = {product_id}).'Software Version')")


# ------------------------------------------------------------------- admin affordances
#
# One set of screens serves both roles. Edit powers are switched on by varIsAdmin rather
# than duplicated into a parallel set of admin screens, which would drift apart. Nothing
# about the technician view changes: every affordance here is invisible without the flag.
#
# Outlined and muted throughout, never filled. These land on screens that were deliberately
# decluttered, and a row of solid buttons would undo that in one paste.
#
# They sit on each object's own screen rather than on every gallery row. A row already
# navigates to the object, so a per-row edit button duplicates the destination it sits next
# to while adding the most clutter to the busiest screens.


def admin_open(key, record_expr, is_new, back="scrAdmin", extra=None):
    """The single way any screen opens the edit form.

    scrEditForm reads four variables: which list it is editing, the record, whether this
    is a create, and where to return. That last one is what makes editing in place work at
    all - the form used to navigate to scrAdmin unconditionally, so editing a machine from
    its own screen would have dropped the admin on a list of database tables. Seeding the record with context - the customer whose page you are on,
    the machine you are inside - is what separates "add a unit here" from "add a unit": the
    form's defaults read that record variable directly, so anything patched into it arrives
    already filled in, and the admin never answers a question the screen already knew.
    """
    return (clear_stash() + "; "
            + (extra + "; " if extra else "")
            + f"Set(varRec{key}, {record_expr}); "
            f'Set(varAdminList, "{key}"); '
            f"Set(varAdminNew, {'true' if is_new else 'false'}); "
            f"Set(varAdminReturn, {back}); "
            "Navigate(scrEditForm, ScreenTransition.Cover)")


# One per lookup field on scrEditForm, each holding a real row from that field's
# target table. gen_form asserts this list still matches the fields it generates, so
# the two cannot drift apart silently.
STASH_VARS = [
    "varStCustomerInst",
    "varStParentInst",
    "varStProductInst",
    "varStProductRef",
    "varStProductSwVer",
    "varStSolutionSolU",
    "varStUnitSolU",
]


def clear_stash():
    """Blank every stash variable.

    Called from admin_open and from scrAdmin's entries - deliberately not from OnVisible,
    which runs after the OnSelect that navigated and would wipe the seed it just set.
    """
    return "; ".join(f"Set({n}, Blank())" for n in STASH_VARS)


def stash(pairs):
    """Set named stash variables to rows already in hand.

    A row from the table has the lookup's type because it came from the table. Building the
    record by hand does not work in either direction: with '@odata.type' it has a field too
    many for a structural merge, without it a field too few.
    """
    return "; ".join(f"Set({k}, {v})" for k, v in pairs)


def admin_button(name, label, on_select, x, y, width, height=40, ind=12,
                 visible="varIsAdmin"):
    """An outlined, admin-only button. Used for both "+ Add ..." and "Edit".

    Written as a literal block and indented afterwards rather than assembled from escaped
    fragments: an escaped newline has been eaten in transit three times on this project,
    each time producing a file that looked plausible and did not parse.
    """
    # An empty label means an icon button - a pencil. Same control, same geometry
    # machinery, so the responsive wrap and the title shrink need to know nothing about it.
    face = '      Icon: ="Edit"\n      Text: =""' if not label else f'      Text: ="{label}"'
    body = f"""- {name}:
    Control: ModernButton
    Properties:
      Appearance: =ButtonAppearance.Outline
{face}
      Font: =AppFont
      Size: =AppType.Body
      FontWeight: =FontWeight.Semibold
      Color: ={"AppDark.Muted" if not label else "AppDark.Accent"}
      BorderColor: =AppDark.Line
      BorderThickness: =1
      RadiusTopLeft: =6
      RadiusTopRight: =6
      RadiusBottomLeft: =6
      RadiusBottomRight: =6
      X: |
        ={x}
      Y: |
        ={y}
      Width: |
        ={width}
      Height: ={height}
      Visible: |
        ={visible}
      OnSelect: |
        ={on_select}
"""
    pad = " " * ind
    return "".join(pad + ln if ln.strip() else ln
                   for ln in body.splitlines(keepends=True))


ACTION_GAP = 8


ACTION_H = 40
ACTION_ROW = 48          # the band a wrapped button row occupies, including its gap


def pencil(name, on_select, x, y, ind=12, visible="varIsAdmin", size=32):
    """A square edit affordance somewhere other than the title row - on a hero panel, say.

    An empty label is what makes admin_button render an icon, so this is that call with the
    geometry named rather than a second control definition to keep in step.
    """
    return admin_button(name, "", on_select, x=x, y=y, width=str(size), height=size,
                        ind=ind, visible=visible)


def title_actions(title, specs, ind=12):
    """Admin buttons on a screen's title row.

    The title row is the one element every screen here shares, and it is the only place an
    affordance fits without disturbing a layout tuned for a technician - a button below a
    list would have to push a gallery down, and every gallery in this app is sized from the
    control above it.

    Wide: right-aligned beside the title, in declared order, rightmost last.
    Narrow: their own row underneath, left to right in declared order, because two buttons
    beside a title on a phone leave the title about ninety pixels.
    """
    widths = [w for *_rest, w in specs]
    out = []
    for i, (name, label, on_select, w) in enumerate(specs):
        left = sum(widths[:i]) + i * ACTION_GAP
        right = sum(widths[i:]) + (len(specs) - i) * ACTION_GAP
        x = (f"If(IsNarrow, Gutter + {left}, "
             f"Gutter + ({CW}) - {right})")
        y = f"{title}.Y + If(IsNarrow, 41, 0)"
        out.append(admin_button(name, label, on_select, x=x, y=y,
                                width=str(w), height=ACTION_H, ind=ind))
    return "".join(out)


def title_shrink(specs):
    """A title's Width, leaving room for buttons that sit beside it.

    Only when there are buttons AND they are beside it. On narrow they are on their own row,
    so the title keeps the full measure; for a technician the If is false either way and the
    screen is byte-identical to what it was.
    """
    total = sum(w + ACTION_GAP for *_rest, w in specs) + ACTION_GAP
    return f"({CW}) - If(varIsAdmin && !IsNarrow, {total}, 0)"


def title_height(base=41):
    """A title's Height. Just the title.

    It used to carry the wrapped button row as extra height, so that whatever laid itself
    out at lblTitle.Y + lblTitle.Height cleared the buttons. That reserved the space by
    making the LABEL taller - and a ModernText centres its text vertically, so on a narrow
    screen an admin's title drifted down into the middle of its own buttons.

    Reserving space below a control by inflating that control only works if nothing draws
    in the reserved part. The allowance lives in title_gap now, added by whatever comes
    next, which is what it always meant.
    """
    return str(base)


def title_gap():
    """The room a wrapped button row needs, for the control that follows the title."""
    return f"If(varIsAdmin && IsNarrow, {ACTION_ROW}, 0)"


# ------------------------------------------------------------------- admin affordances
#
# One set of screens serves both roles. Edit powers are switched on by varIsAdmin rather
# than duplicated into a parallel set of admin screens, which would drift apart. Nothing
# about the technician view changes: every affordance here is invisible without the flag.
#
# Outlined and muted throughout, never filled. These land on screens that were deliberately
# decluttered, and a row of solid buttons would undo that in one paste.
#
# They sit on each object's own screen rather than on every gallery row. A row already
# navigates to the object, so a per-row edit button duplicates the destination it sits next
# to while adding the most clutter to the busiest screens.


def admin_open(key, record_expr, is_new, back="scrAdmin", extra=None):
    """The single way any screen opens the edit form.

    scrEditForm reads four variables: which list it is editing, the record, whether this
    is a create, and where to return. That last one is what makes editing in place work at
    all - the form used to navigate to scrAdmin unconditionally, so editing a machine from
    its own screen would have dropped the admin on a list of database tables. Seeding the record with context - the customer whose page you are on,
    the machine you are inside - is what separates "add a unit here" from "add a unit": the
    form's defaults read that record variable directly, so anything patched into it arrives
    already filled in, and the admin never answers a question the screen already knew.
    """
    return (clear_stash() + "; "
            + (extra + "; " if extra else "")
            + f"Set(varRec{key}, {record_expr}); "
            f'Set(varAdminList, "{key}"); '
            f"Set(varAdminNew, {'true' if is_new else 'false'}); "
            f"Set(varAdminReturn, {back}); "
            "Navigate(scrEditForm, ScreenTransition.Cover)")


# One per lookup field on scrEditForm, each holding a real row from that field's
# target table. gen_form asserts this list still matches the fields it generates, so
# the two cannot drift apart silently.
STASH_VARS = [
    "varStCustomerInst",
    "varStParentInst",
    "varStProductInst",
    "varStProductRef",
    "varStProductSwVer",
    "varStSolutionSolU",
    "varStUnitSolU",
]


def clear_stash():
    """Blank every stash variable.

    Called from admin_open and from scrAdmin's entries - deliberately not from OnVisible,
    which runs after the OnSelect that navigated and would wipe the seed it just set.
    """
    return "; ".join(f"Set({n}, Blank())" for n in STASH_VARS)


def stash(pairs):
    """Set named stash variables to rows already in hand.

    A row from the table has the lookup's type because it came from the table. Building the
    record by hand does not work in either direction: with '@odata.type' it has a field too
    many for a structural merge, without it a field too few.
    """
    return "; ".join(f"Set({k}, {v})" for k, v in pairs)


def admin_button(name, label, on_select, x, y, width, height=40, ind=12,
                 visible="varIsAdmin"):
    """An outlined, admin-only button. Used for both "+ Add ..." and "Edit".

    Written as a literal block and indented afterwards rather than assembled from escaped
    fragments: an escaped newline has been eaten in transit three times on this project,
    each time producing a file that looked plausible and did not parse.
    """
    # An empty label means an icon button - a pencil. Same control, same geometry
    # machinery, so the responsive wrap and the title shrink need to know nothing about it.
    face = '      Icon: ="Edit"\n      Text: =""' if not label else f'      Text: ="{label}"'
    body = f"""- {name}:
    Control: ModernButton
    Properties:
      Appearance: =ButtonAppearance.Outline
{face}
      Font: =AppFont
      Size: =AppType.Body
      FontWeight: =FontWeight.Semibold
      Color: ={"AppDark.Muted" if not label else "AppDark.Accent"}
      BorderColor: =AppDark.Line
      BorderThickness: =1
      RadiusTopLeft: =6
      RadiusTopRight: =6
      RadiusBottomLeft: =6
      RadiusBottomRight: =6
      X: |
        ={x}
      Y: |
        ={y}
      Width: |
        ={width}
      Height: ={height}
      Visible: |
        ={visible}
      OnSelect: |
        ={on_select}
"""
    pad = " " * ind
    return "".join(pad + ln if ln.strip() else ln
                   for ln in body.splitlines(keepends=True))


ACTION_GAP = 8


ACTION_H = 40
ACTION_ROW = 48          # the band a wrapped button row occupies, including its gap


def pencil(name, on_select, x, y, ind=12, visible="varIsAdmin", size=32):
    """A square edit affordance somewhere other than the title row - on a hero panel, say.

    An empty label is what makes admin_button render an icon, so this is that call with the
    geometry named rather than a second control definition to keep in step.
    """
    return admin_button(name, "", on_select, x=x, y=y, width=str(size), height=size,
                        ind=ind, visible=visible)


def title_actions(title, specs, ind=12):
    """Admin buttons on a screen's title row.

    The title row is the one element every screen here shares, and it is the only place an
    affordance fits without disturbing a layout tuned for a technician - a button below a
    list would have to push a gallery down, and every gallery in this app is sized from the
    control above it.

    Wide: right-aligned beside the title, in declared order, rightmost last.
    Narrow: their own row underneath, left to right in declared order, because two buttons
    beside a title on a phone leave the title about ninety pixels.
    """
    widths = [w for *_rest, w in specs]
    out = []
    for i, (name, label, on_select, w) in enumerate(specs):
        left = sum(widths[:i]) + i * ACTION_GAP
        right = sum(widths[i:]) + (len(specs) - i) * ACTION_GAP
        x = (f"If(IsNarrow, Gutter + {left}, "
             f"Gutter + ({CW}) - {right})")
        y = f"{title}.Y + If(IsNarrow, 41, 0)"
        out.append(admin_button(name, label, on_select, x=x, y=y,
                                width=str(w), height=ACTION_H, ind=ind))
    return "".join(out)


def title_shrink(specs):
    """A title's Width, leaving room for buttons that sit beside it.

    Only when there are buttons AND they are beside it. On narrow they are on their own row,
    so the title keeps the full measure; for a technician the If is false either way and the
    screen is byte-identical to what it was.
    """
    total = sum(w + ACTION_GAP for *_rest, w in specs) + ACTION_GAP
    return f"({CW}) - If(varIsAdmin && !IsNarrow, {total}, 0)"


# ---------------------------------------------------------------------------- verification
#
# Twelve months, matching the threshold already applied to a document's Last Checked, so the
# app has one rule for staleness rather than two.
STALE_MONTHS = 12


def effective_verified(inst, customer_id, product_id):
    """The verification date belonging to whichever source supplied the version.

    A machine's own Installed Version wins over the site default, so the date has to follow
    it. A date that did not track its source would report the site survey's age against a
    version nobody has confirmed on this machine, which is the failure this whole change
    exists to remove.

    Mirrors effective_version()'s precedence exactly. The two must move together.
    """
    return (f"If(!IsBlank({inst}.'Installed Version'), {inst}.'Last Verified', "
            f"LookUp(TB_SoftwareVersions, Customer.Id = {customer_id} "
            f"&& Product.Id = {product_id}).'Last Verified')")


def _days(d):
    return f"DateDiff({d}, Today(), TimeUnit.Days)"


def verified_months(d):
    """Whole months since a date, derived from days.

    NOT DateDiff(..., TimeUnit.Months), which counts calendar-month boundaries rather than
    elapsed time - the documented example returns 6 for July 15 to January 1 - so a >= 12
    test on it fires at eleven months and a day.

    30.4375 is 365.25 / 12, so >= 12 here means a full year has actually passed. The label
    below prints this same number, which is the point: the amber threshold and the words on
    screen read one value and cannot disagree.
    """
    return f"RoundDown({_days(d)} / 30.4375, 0)"


def verified_note(d):
    """'verified 3 weeks ago', or 'never verified'.

    The thresholds are picked so no branch can ever print a 1 and no plural has to be
    special-cased: days covers 2-13, weeks starts at 14 (2 weeks), months starts at 61
    (2 months).
    """
    dd = _days(d)
    return (f'If(IsBlank({d}), "never verified", '
            f'{dd} < 1, "verified today", '
            f'{dd} < 2, "verified yesterday", '
            f'{dd} < 14, "verified " & {dd} & " days ago", '
            f'{dd} < 61, "verified " & RoundDown({dd} / 7, 0) & " weeks ago", '
            f'"verified " & {verified_months(d)} & " months ago")')


def verified_is_stale(d):
    """Amber: a date that is over the threshold.

    Deliberately NOT true for a missing date. "never verified" already says so in words,
    and painting a fresh dataset amber says nothing at all.
    """
    return f"(!IsBlank({d}) && {verified_months(d)} >= {STALE_MONTHS})"


def verified_needs_check(d):
    """The counts on the customer list and solution cards: over the threshold OR never.

    A different predicate from verified_is_stale, which is why it has a different name. A
    count is asking "how many should someone look at", and a machine nobody has ever checked
    belongs in that answer; a single panel is describing one record, and there "never" is
    better said than coloured.
    """
    return f"(IsBlank({d}) || {verified_months(d)} >= {STALE_MONTHS})"


def version_source_note(inst, customer_id, product_id):
    """Says where a displayed version came from, when it was not the machine itself.

    Without this the hero asserts a version the installation record does not contain, and
    the next person to open the admin form finds the field empty and assumes a bug.
    """
    return (f"If(!IsBlank({inst}.'Installed Version'), \"\", "
            f"!IsBlank(LookUp(TB_SoftwareVersions, Customer.Id = {customer_id} "
            f"&& Product.Id = {product_id}).'Software Version'), "
            f"\"  ·  site default for this model\", \"\")")
