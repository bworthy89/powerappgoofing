"""Generate scrSolution: the machine detail screen, rebuilt dark.

WHAT WAS WRONG WITH IT

Three things, all structural rather than cosmetic:

1. THE ANSWER WAS NOT THE HEADLINE. "Is this on the current build?" was three 22pt labels
   and a small badge, sitting below a title and a subtitle. Now it is a chamfered hero panel
   with a state-coloured rail, carrying the comparison at Display size - the largest thing on
   the screen, because it is the reason the screen exists.

2. UNIT ROWS WERE PROSE. One concatenated string per row:
       NOTE RECYCLER   SDRB250   3.4.1  ·  standard 3.6.0
   A technician scanning six units read six sentences. Now each row is a status rail, a
   category, a model, and a right-aligned comparison - so the eye runs down one column and
   the mismatches stand out without reading.

3. EVERY Y WAS A HAND-COPIED ARITHMETIC CHAIN. The old file repeated
   "Gutter + 100 + 112 + Gutter + 92 + Gutter + 32 + 160 + Gutter + 32" in full, in six
   controls, each an independent chance to be a pixel out. Positions here chain through
   control references (thing.Y + thing.Height + gap) so each offset has exactly one author.
   The conditional config panel is handled by If(Visible, Height + Gutter, 0) rather than by
   branching the whole chain, which is what forced the copying before.

WHY THE ROW STATUS IS NOT THE COMPONENT

cmpVersionChip cannot go here: "You can't insert a component into a gallery or a form." The
component is used once on this screen, for the hero panel, which is outside any gallery. Row
status is built from controls, so the four-state logic exists twice in this app - once in the
component, once below. They must be changed together.

BEHAVIOUR IS UNCHANGED. Same filters, same navigation, same retired-row exclusions, same
customer-specific document exceptions.
"""
from pathlib import Path

OUT = Path(r"E:\Papp\powerappgoofing\app\screens\scrSolution.pa.yaml")

WM = Path(
    r"C:\Users\bwort\AppData\Local\Temp\claude\E--Papp"
    r"\c7a373b9-de1b-4ba5-a22b-70f79a3b6252\scratchpad\glory_wordmark_b64.txt"
).read_text().strip()

BAND = 56
CW = "Parent.Width - (Gutter * 2)"

# The product this installation is an instance of, and its catalogue standard.
PROD = "LookUp(TB_Products, ID = varInstallation.Product.Id)"

# The installation of a unit row's model under this solution, if one exists. Repeated
# rather than named because this environment has no With/As available inside a gallery row.
FITTED = ("LookUp(TB_Installations, 'Parent'.Id = varInstallation.ID "
          "&& Product.Id = ThisItem.Unit.Id)")
UPROD = "LookUp(TB_Products, ID = ThisItem.Unit.Id)"

# Units attached here that the model does not list. Rare, but silently hiding one would be
# this app's characteristic failure: a correct-looking screen missing a machine.
STRAY = ("CountRows(Filter(TB_Installations As I, I.'Parent'.Id = varInstallation.ID, "
         "I.Status.Value <> \"Retired\", "
         "CountRows(Filter(TB_SolutionUnits, Solution.Id = varInstallation.Product.Id, "
         "Unit.Id = I.Product.Id)) = 0))")


def refs(section):
    """Documents or firmware for this machine OR any unit actually fitted under it.

    "As R" names the outer row so R.Product.Id is not shadowed by TB_Installations' own
    Product column in the nested Filter.
    """
    return f"""=SortByColumns(
                        Filter(
                            TB_References As R,
                            R.Section.Value = "{section}",
                            Or(IsBlank(R.Customer), R.Customer.Id = varCustomer.ID),
                            R.Product.Id = varInstallation.Product.Id
                            || CountRows(
                                   Filter(
                                       TB_Installations,
                                       'Parent'.Id = varInstallation.ID,
                                       Status.Value <> "Retired",
                                       Product.Id = R.Product.Id
                                   )
                               ) > 0
                        ),
                        "TBFeatured",
                        SortOrder.Descending
                    )"""


def ref_gallery(key, section, heading, empty, y):
    """A documents-style list. Rows carry a rail only when featured, so the eye is drawn to
    the reference someone deliberately promoted rather than to all of them equally."""
    return f"""
            - lbl{key}HeadingSol:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: |
                    ={y}
                  Width: ={CW}
                  Height: =22
                  Text: ="{heading}"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Bold
                  Color: =AppDark.Muted
            - gal{key}Sol:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: =Gutter
                  Y: =lbl{key}HeadingSol.Y + lbl{key}HeadingSol.Height + 10
                  Width: ={CW}
                  Height: =Min(CountRows(gal{key}Sol.AllItems), 4) * 60
                  TemplateSize: =60
                  TemplatePadding: =0
                  ShowScrollbar: =false
                  Visible: =CountRows(gal{key}Sol.AllItems) > 0
                  Items: |
                    {refs(section)}
                Children:
                  - rec{key}RailSol:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =3
                        Height: =Parent.TemplateHeight - 1
                        Fill: =If(ThisItem.Featured = true, AppDark.Accent, AppDark.Line)
                  - lbl{key}TitleSol:
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
                  - lbl{key}TypeSol:
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
                          =ThisItem.'Reference Type'.Value & "  ·  " & LookUp(TB_Products, ID = ThisItem.Product.Id).Title & If(IsBlank(ThisItem.Customer.Value), "", "  ·  this customer")
                        Font: =AppFont
                        Size: =AppType.Small
                        Color: =AppDark.Muted
                        Wrap: =false
                        AutoHeight: =false
                  - lbl{key}CheckedSol:
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
                  - rec{key}RuleSol:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =59
                        Width: =Parent.TemplateWidth
                        Height: =1
                        Fill: =AppDark.Line
                  - gal{key}HitSol:
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
            - lblNo{key}Sol:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: =gal{key}Sol.Y
                  Width: ={CW}
                  Height: =40
                  Text: ="{empty}"
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Muted
                  Visible: =CountRows(gal{key}Sol.AllItems) = 0"""


# Vertical chain. Each offset has exactly one author; the config panel contributes its
# height only when it is visible, so nothing downstream needs a branch of its own.
Y_TITLE = f"{BAND} + 24"
Y_SUB = "lblTitleSol.Y + lblTitleSol.Height"
Y_HERO = "lblSubtitleSol.Y + lblSubtitleSol.Height + Gutter"
Y_CFG = "cmpVersionSol.Y + cmpVersionSol.Height + Gutter"
Y_UNITS = "conConfigNotesSol.Y + If(conConfigNotesSol.Visible, conConfigNotesSol.Height + Gutter, 0)"
Y_DOCS = "galUnitsSol.Y + galUnitsSol.Height + Gutter"
Y_FIRM = "galDocsSol.Y + Max(galDocsSol.Height, 40) + Gutter"

doc = f'''# Screen — Solution  (GENERATED by scripts/gen_solution.py — edit the generator)
#
# The machine detail screen. See the generator docstring for what was rebuilt and why: the
# version answer is now the headline rather than a footnote, unit rows are scannable columns
# rather than sentences, and vertical positions chain through control references instead of
# repeating a hand-copied arithmetic sum in six places.
#
# varInstallation is the solution installation; varCustomer is the site. Both are set by
# whoever navigated here and are never re-derived on this screen.

Screens:
  scrSolution:
    Properties:
      Fill: =AppDark.Bg
    Children:
      - conRootSol:
          Control: GroupContainer
          Variant: ManualLayout
          Properties:
            X: =0
            Y: =0
            Width: =Parent.Width
            Height: =Parent.Height
            Fill: =AppDark.Bg
          Children:
            # Compact brand band. Half the height of the home band because this is a detail
            # screen and the mark is reassurance, not an entrance.
            - recSolBand:
                Control: Rectangle
                Properties:
                  X: =0
                  Y: =0
                  Width: =Parent.Width
                  Height: ={BAND}
                  Fill: =AppDark.Brand
            - imgWordmarkSol:
                Control: Image
                Properties:
                  X: =Parent.Width - Gutter - 96
                  Y: =20
                  Width: =96
                  Height: =15
                  Image: |
                    ="data:image/png;base64,{WM}"
            - btnBackSol:
                Control: ModernButton
                Properties:
                  Appearance: =ButtonAppearance.Subtle
                  Icon: ="ChevronLeft"
                  Layout: =ButtonLayout.IconBefore
                  Text: ="Back"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.OnBrand
                  BorderThickness: =0
                  X: =Gutter - 8
                  Y: =6
                  Width: =110
                  Height: =44
                  OnSelect: =Navigate(scrCustomerOverview, ScreenTransition.UnCover)

            - lblTitleSol:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={Y_TITLE}
                  Width: ={CW}
                  Height: =41
                  Text: ={PROD}.Title
                  Font: =AppFont
                  Size: =If(IsNarrow, AppType.Title, AppType.Display)
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.Fg
                  Wrap: =false
                  AutoHeight: =false
            - lblSubtitleSol:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={Y_SUB}
                  Width: ={CW}
                  Height: =22
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.FgSecondary
                  Wrap: =false
                  AutoHeight: =false
                  Text: |
                    ={PROD}.Family.Value & "  ·  " & varCustomer.Title & If(varInstallation.Status.Value = "In Service", "", "  ·  " & Lower(varInstallation.Status.Value))

            # The answer. A component so scrUnit can show the identical comparison from one
            # definition - the only two places it is allowed, since a component cannot go in
            # a gallery.
            - cmpVersionSol:
                Control: cmpVersionChip
                Properties:
                  X: =Gutter
                  Y: ={Y_HERO}
                  Width: =Min({CW}, 620)
                  Height: =116
                  InstalledVersion: =Coalesce(varInstallation.'Installed Version', "")
                  StandardVersion: =Coalesce({PROD}.'Current Standard Version', "")

            - conConfigNotesSol:
                Control: GroupContainer
                Variant: ManualLayout
                Properties:
                  X: =Gutter
                  Y: ={Y_CFG}
                  Width: =Min({CW}, 620)
                  Height: =92
                  Fill: =AppDark.Surface
                  Visible: =!IsBlank(varInstallation.'Config Notes')
                Children:
                  - lblConfigHeadingSol:
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
                  - lblConfigNotesSol:
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
                        Color: =AppDark.Fg

            # ---- units
            # A row is a unit the MODEL takes, so it may have nothing behind it. That is the
            # point: "do they have a barcode scanner" was unanswerable when the list only
            # showed what happened to be attached, because absent and uncatalogued looked
            # identical.
            - lblUnitsHeading:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: |
                    ={Y_UNITS}
                  Width: ={CW}
                  Height: =22
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Bold
                  Color: =AppDark.Muted
                  Wrap: =false
                  AutoHeight: =false
                  Text: |
                    ="UNITS" & If({STRAY} > 0, "   (" & {STRAY} & " also attached, not on the model's list)", "")
            - galUnitsSol:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: =Gutter
                  Y: =lblUnitsHeading.Y + lblUnitsHeading.Height + 10
                  Width: ={CW}
                  Height: =Max(Min(CountRows(galUnitsSol.AllItems), 5), 1) * 56
                  TemplateSize: =56
                  TemplatePadding: =0
                  ShowScrollbar: =false
                  Items: |
                    =Sort(
                        Filter(TB_SolutionUnits, Solution.Id = varInstallation.Product.Id),
                        Unit.Value,
                        SortOrder.Ascending
                    )
                Children:
                  # The rail is the whole point of the row. Four states, same order and same
                  # meaning as the component - change both together.
                  - recUnitRailSol:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =3
                        Height: =Parent.TemplateHeight - 1
                        Fill: |
                          =If(
                              IsBlank({FITTED}),
                              AppDark.Line,
                              IsBlank({FITTED}.'Installed Version'),
                              AppDark.Muted,
                              IsBlank({UPROD}.'Current Standard Version'),
                              AppDark.Muted,
                              {FITTED}.'Installed Version' = {UPROD}.'Current Standard Version',
                              AppDark.Ok,
                              AppDark.Warn
                          )
                  - lblUnitTypeSol:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16
                        Y: =8
                        Width: =(Parent.TemplateWidth - 32) * 0.55
                        Height: =18
                        Text: =Upper({UPROD}.'Product Type'.Value)
                        Font: =AppFont
                        Size: =AppType.Small
                        FontWeight: =FontWeight.Semibold
                        Color: =AppDark.Muted
                        Wrap: =false
                        AutoHeight: =false
                  - lblUnitModelSol:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16
                        Y: =27
                        Width: =(Parent.TemplateWidth - 32) * 0.55
                        Height: =22
                        Text: =ThisItem.Unit.Value
                        Font: =AppFont
                        Size: =AppType.Body
                        FontWeight: =FontWeight.Semibold
                        Color: =If(IsBlank({FITTED}), AppDark.Faint, AppDark.Fg)
                        Wrap: =false
                        AutoHeight: =false
                  # Right-aligned so the versions form one column down the list. A mismatch
                  # then shows as a break in the column rather than as a sentence to read.
                  - lblUnitVerSol:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16 + ((Parent.TemplateWidth - 32) * 0.55)
                        Y: =17
                        Width: =(Parent.TemplateWidth - 32) * 0.45
                        Height: =22
                        Align: =Align.Right
                        Font: =AppFont
                        Size: =AppType.Body
                        FontWeight: =FontWeight.Semibold
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          =If(
                              IsBlank({FITTED}),
                              "not recorded",
                              IsBlank({FITTED}.'Installed Version'),
                              "version not recorded",
                              IsBlank({UPROD}.'Current Standard Version'),
                              {FITTED}.'Installed Version',
                              {FITTED}.'Installed Version' = {UPROD}.'Current Standard Version',
                              {FITTED}.'Installed Version',
                              {FITTED}.'Installed Version' & "  →  " & {UPROD}.'Current Standard Version'
                          )
                        Color: |
                          =If(
                              IsBlank({FITTED}),
                              AppDark.Faint,
                              IsBlank({FITTED}.'Installed Version'),
                              AppDark.Muted,
                              IsBlank({UPROD}.'Current Standard Version'),
                              AppDark.Muted,
                              {FITTED}.'Installed Version' = {UPROD}.'Current Standard Version',
                              AppDark.Ok,
                              AppDark.Warn
                          )
                  - recUnitRuleSol:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =55
                        Width: =Parent.TemplateWidth
                        Height: =1
                        Fill: =AppDark.Line
                  - galUnitsHitSol:
                      Control: Classic/Button
                      Properties:
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
                        OnSelect: |
                          =If(
                              !IsBlank({FITTED}),
                              Set(varInstallation, {FITTED});
                              Navigate(scrUnit, ScreenTransition.Cover)
                          )
            - lblNoUnits:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: =galUnitsSol.Y
                  Width: ={CW}
                  Height: =40
                  Text: ="No units are on file for this model. Add them under Admin, Solution units."
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Muted
                  Visible: =CountRows(Filter(TB_SolutionUnits, Solution.Id = varInstallation.Product.Id)) = 0
{ref_gallery("Docs", "Documentation", "DOCUMENTATION", "No documentation is on file for this system.", Y_DOCS)}
{ref_gallery("Firmware", "Firmware & Downloads", "FIRMWARE & DOWNLOADS", "No firmware or downloads are on file for this system.", Y_FIRM)}
'''

OUT.write_text(doc, encoding="utf-8", newline="")
print(f"wrote {OUT}  ({len(doc.splitlines())} lines)")
