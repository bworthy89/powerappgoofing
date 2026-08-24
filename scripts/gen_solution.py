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
import screen_parts as P

OUT = Path(r"E:\Papp\powerappgoofing\app\screens\scrSolution.pa.yaml")

# Correct this machine's record, or add a unit inside it. Adding supplies both the customer
# and the parent machine, which were two of the three lookups this task used to cost.
# Only the pencil sits beside the title. Adding a unit belongs under the list of units,
# which is where the mockup put it and where it reads as "and one more".
ACTIONS = [("btnEditSol", "",
            P.admin_open("Inst", "varInstallation", False, back="scrSolution"), 44)]

BAND = P.BAND
CW = P.CW

# The product this installation is an instance of, and its catalogue standard.
PROD = "LookUp(TB_Products, ID = varInstallation.Product.Id)"

# The installation of a unit row's model under this solution, if one exists. Repeated
# rather than named because this environment has no With/As available inside a gallery row.
FITTED = ("LookUp(TB_Installations, 'Parent'.Id = varInstallation.ID "
          "&& Product.Id = ThisItem.Unit.Id)")
UPROD = "LookUp(TB_Products, ID = ThisItem.Unit.Id)"

# A unit row reports its own record's date. Note it does NOT fall back to the site default
# the way the hero does, because the row does not fall back for the version either - that
# asymmetry is older than this change and is called out in the build notes rather than
# quietly altered here.
U_VER   = f"{FITTED}.'Last Verified'"
U_STALE = P.verified_is_stale(U_VER)
U_NOTE  = P.verified_note(U_VER)

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



TAB_H = 44

def tab(key, label, i):
    """One tab. Primary when active, Outline otherwise - the same pairing scrAdmin uses,
    and Outline rather than Secondary because Secondary paints an opaque light fill."""
    return f"""            - btnTab{key}Sol:
                Control: ModernButton
                Properties:
                  Appearance: |
                    =If(varSolTab = "{key}", ButtonAppearance.Primary, ButtonAppearance.Outline)
                  Text: ="{label}"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Semibold
                  Color: =If(varSolTab = "{key}", AppDark.OnBrand, AppDark.Fg)
                  BorderColor: =AppDark.Line
                  BorderThickness: =1
                  Height: ={TAB_H}
                  Width: =(Min({P.CW}, {P.PANEL_MAX}) - 16) / 3
                  X: =Gutter + ((Min({P.CW}, {P.PANEL_MAX}) - 16) / 3 + 8) * {i}
                  Y: |
                    ={Y_TABS}
                  RadiusTopLeft: =6
                  RadiusTopRight: =6
                  RadiusBottomLeft: =6
                  RadiusBottomRight: =6
                  OnSelect: =Set(varSolTab, "{key}")"""

# Vertical chain. Each offset has exactly one author; the config panel contributes its
# height only when it is visible, so nothing downstream needs a branch of its own.
Y_TITLE = f"{BAND} + 24"
Y_SUB = "lblTitleSol.Y + lblTitleSol.Height"
Y_HERO = "lblSubtitleSol.Y + lblSubtitleSol.Height + Gutter"
Y_CFG = "cmpVersionSol.Y + cmpVersionSol.Height + Gutter"
# The three lists now share one origin instead of stacking, so the page height no longer
# grows with the amount of data on it.
Y_TABS = ("conConfigNotesSol.Y + "
          "If(conConfigNotesSol.Visible, conConfigNotesSol.Height + Gutter, 0)")
Y_LIST = f"{Y_TABS} + 44 + 12"
Y_UNITS = Y_LIST
Y_DOCS = Y_LIST
Y_FIRM = Y_LIST

# Each list fills the rest of the screen rather than a fixed window, so it scrolls inside a
# region that ends at the bottom edge instead of running past it.
LIST_H = f"Max(Parent.Height - ({Y_LIST}) - Gutter, 120)"

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
      OnVisible: =Set(varSolTab, "Units")
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
{P.brand_band("Sol", "scrCustomerOverview")}

{P.title_actions("lblTitleSol", ACTIONS)}            - lblTitleSol:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={Y_TITLE}
                  Width: ={P.title_shrink(ACTIONS)}
                  Height: ={P.title_height()}
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

{P.version_hero("Sol", Y_HERO)}
{P.pencil("btnEditHeroSol", P.admin_open("Inst", "varInstallation", False, back="scrSolution"), "Gutter + Min(" + CW + ", 620) - 44", f"({Y_HERO}) + 12")}

{P.config_panel("Sol", Y_CFG)}

{P.admin_button("btnAddUnitSol", "+  Add a unit",
                        P.admin_open("Inst", "Defaults(TB_Installations)", True,
                                     back="scrSolution",
                                     extra=P.stash([("varStCustomerInst",
                                                     "LookUp(TB_Customers, ID = varCustomer.ID)"),
                                                    ("varStParentInst", "varInstallation")])),
                        x="Gutter", y="galUnitsSol.Y + galUnitsSol.Height + 12",
                        width=CW, height=44,
                        visible='varIsAdmin && varSolTab = "Units"')}
{tab("Units", "Units", 0)}
{tab("Docs", "Documents", 1)}
{tab("Firmware", "Firmware", 2)}

            # ---- units
            # A row is a unit the MODEL takes, so it may have nothing behind it. That is the
            # point: "do they have a barcode scanner" was unanswerable when the list only
            # showed what happened to be attached, because absent and uncatalogued looked
            # identical.
            # The tab names the section, so this line carries only the exception worth
            # knowing about: something attached here that the model does not list.
            - lblUnitsHeading:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: |
                    ={Y_UNITS}
                  Width: ={CW}
                  Height: =20
                  Font: =AppFont
                  Size: =AppType.Small
                  Color: =AppDark.Warn
                  Wrap: =false
                  AutoHeight: =false
                  Visible: |
                    =varSolTab = "Units" && {STRAY} > 0
                  Text: |
                    ={STRAY} & " also attached, not on the model's list"
            - galUnitsSol:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: =Gutter
                  Y: |
                    ={Y_UNITS} + If(lblUnitsHeading.Visible, 26, 0)
                  Width: ={CW}
                  Visible: =varSolTab = "Units"
                  Height: |
                    ={LIST_H} - If(lblUnitsHeading.Visible, 26, 0) - If(varIsAdmin, 56, 0)
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
                              {U_STALE},
                              AppDark.Warn,
                              AppDark.Muted
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
                  # Right-aligned so the versions form one column down the list, with the
                  # date they were last confirmed directly beneath each one.
                  - lblUnitVerSol:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16 + ((Parent.TemplateWidth - 32) * 0.55)
                        Y: =10
                        Width: =(Parent.TemplateWidth - 32) * 0.45 - If(varIsAdmin, 40, 0)
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
                              {FITTED}.'Installed Version'
                          )
                        Color: |
                          =If(
                              IsBlank({FITTED}),
                              AppDark.Faint,
                              IsBlank({FITTED}.'Installed Version'),
                              AppDark.Muted,
                              AppDark.Fg
                          )
                  # The date under the number. Without it the version is a bare
                  # assertion; with it a reader can weigh how far to trust it before
                  # driving out. Blank when nothing is fitted - there is no record to date,
                  # and "never verified" would read as a finding about a machine that is
                  # not there.
                  - lblUnitAgeSol:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =16 + ((Parent.TemplateWidth - 32) * 0.55)
                        Y: =32
                        Width: =(Parent.TemplateWidth - 32) * 0.45 - If(varIsAdmin, 40, 0)
                        Height: =18
                        Align: =Align.Right
                        Font: =AppFont
                        Size: =AppType.Small
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          =If(IsBlank({FITTED}), "", {U_NOTE})
                        Color: |
                          =If({U_STALE}, AppDark.Warn, AppDark.Muted)
                  # Declared after the hit target so the tap lands here rather than
                  # navigating. Hidden where nothing is fitted - there is no record to edit.
                  - btnEditUnitRowSol:
                      Control: ModernButton
                      Properties:
                        Appearance: =ButtonAppearance.Outline
                        Icon: ="Edit"
                        Text: =""
                        Color: =AppDark.Muted
                        BorderColor: =AppDark.Line
                        BorderThickness: =1
                        RadiusTopLeft: =6
                        RadiusTopRight: =6
                        RadiusBottomLeft: =6
                        RadiusBottomRight: =6
                        X: =Parent.TemplateWidth - 44
                        Y: =12
                        Width: =32
                        Height: =32
                        Visible: |
                          =varIsAdmin && !IsBlank({FITTED})
                        OnSelect: |
                          ={P.admin_open("Inst", FITTED, False, back="scrSolution")}
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
                  Visible: |
                    =varSolTab = "Units" && CountRows(Filter(TB_SolutionUnits, Solution.Id = varInstallation.Product.Id)) = 0
{P.ref_gallery("Docs", "Sol", "", "No documentation is on file for this system.", Y_DOCS, refs("Documentation"), height=f"={LIST_H}", visible='=varSolTab = "Docs"', empty_visible='=varSolTab = "Docs" && CountRows(galDocsSol.AllItems) = 0')}
{P.ref_gallery("Firmware", "Sol", "", "No firmware or downloads are on file for this system.", Y_FIRM, refs("Firmware & Downloads"), height=f"={LIST_H}", visible='=varSolTab = "Firmware"', empty_visible='=varSolTab = "Firmware" && CountRows(galFirmwareSol.AllItems) = 0')}
'''

OUT.write_text(doc, encoding="utf-8", newline="")
print(f"wrote {OUT}  ({len(doc.splitlines())} lines)")
