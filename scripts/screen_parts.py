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
                  Height: =22
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
                  Y: =lbl{key}Heading{sfx}.Y + lbl{key}Heading{sfx}.Height + 10
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


def version_hero(sfx, y, product_expr, customer_id="varCustomer.ID",
                 product_id="varInstallation.Product.Id"):
    """The version answer, as a component instance.

    Control is the literal CanvasComponent; the definition is named in the sibling
    ComponentName key. Writing the component's own name as the control type is rejected
    with PA2101 - see 00_Setup.md.

    This is the only place a component is allowed to live in this app: one cannot be
    inserted into a gallery or a form, which rules out every list here.
    """
    eff = effective_version("varInstallation", customer_id, product_id)
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
                  InstalledVersion: |
                    ={eff}
                  StandardVersion: =Coalesce({product_expr}.'Current Standard Version', "")
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
            f"LookUp(TB_References, Customer.Id = {customer_id} "
            f"&& Product.Id = {product_id} "
            f"&& Section.Value = \"Software\").Version)")


def version_source_note(inst, customer_id, product_id):
    """Says where a displayed version came from, when it was not the machine itself.

    Without this the hero asserts a version the installation record does not contain, and
    the next person to open the admin form finds the field empty and assumes a bug.
    """
    return (f"If(!IsBlank({inst}.'Installed Version'), \"\", "
            f"!IsBlank(LookUp(TB_References, Customer.Id = {customer_id} "
            f"&& Product.Id = {product_id} "
            f"&& Section.Value = \"Software\").Version), "
            f"\"  ·  site default for this model\", \"\")")
