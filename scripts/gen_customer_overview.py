"""Generate scrCustomerOverview: what a site has, rebuilt dark.

THE ONE REAL DESIGN CHANGE: THE NESTED UNIT GALLERY IS GONE

Each solution card was 252px tall and contained a scrolling 128px gallery of 28px unit rows.
That is three problems in one control:

  - 28px rows are well under the 44px tap floor, and they are the rows a technician hits
    while holding a torch.
  - A nested Gallery captures its own taps rather than bubbling them, so the card needed a
    hit target covering only its top 100px and a second one inside the rows. Getting that
    wrong makes a region look tappable and silently do nothing - it already had a comment
    warning about exactly this.
  - At 252px a laptop shows two solutions. A site with four means scrolling to find out
    whether anything needs attention.

Cards are now 88px and carry a summary instead: "Recycler · 4 units · 1 needs update". Five
solutions fit where two did, and the question this screen exists to answer - does anything
here need attention - is answerable without scrolling or tapping.

THE COST, STATED PLAINLY: reaching a specific unit is now two taps (solution, then unit)
rather than one. That is the trade. scrSolution lists units at 56px with their own version
comparison and room to read, which is a better place to choose one than a 28px row inside a
scrolling region inside a card.

TWO SIGNALS, NOT ONE BLENDED ONE

The rail carries the SOLUTION's own version state. The summary line carries its UNITS'
state, in Warn when any needs checking. Blending them into a single worst-of indicator would tell
you something needs attention while hiding which thing, on a screen whose whole job is to
point you at the right machine.
"""
from pathlib import Path
import screen_parts as P

OUT = Path(r"E:\Papp\powerappgoofing\app\screens\scrCustomerOverview.pa.yaml")

# Edit the customer you are looking at, and add a machine to it. The customer is supplied by
# where you tapped, so the form never asks which site this is.
ACTIONS = [
    ("btnEditCustOvw", "Edit",
     P.admin_open("Cust", "LookUp(TB_Customers, ID = varCustomer.ID)", False,
                  back="scrCustomerOverview"), 84),
    ("btnAddMachOvw", "+  Add a machine",
     P.admin_open("Inst",
                  "Patch(Defaults(TB_Installations), { Customer: "
                  + P.seed("TB_Installations", "Customer", "varCustomer.ID") + " })",
                  True, back="scrCustomerOverview"), 158),
]

CARD_H = 88
PROD = "LookUp(TB_Products, ID = ThisItem.Product.Id)"

# The version in force for a solution row: its own, else the site default for that
# model. Identical in meaning to screen_parts.effective_version and to the count
# below - the hero and this card disagreeing is exactly what this change removes.
EFF_READ = "lblEffVerOvw.Text"


def _effective(inst, product_id):
    """The version in force for one installation: its own, else the site baseline.

    One definition for both the solution card and the per-unit count below. They were
    written out separately and a rename reached one and not the other, which put a Section
    filter on a list that has no Section and read a column that had been renamed - both of
    which shipped.
    """
    return (f"Coalesce({inst}.'Installed Version', "
            f"LookUp(TB_SoftwareVersions, Customer.Id = varCustomer.ID "
            f"&& Product.Id = {product_id}).'Software Version')")


def _verified(inst, product_id):
    """The date belonging to whichever source supplied the version.

    Mirrors _effective's precedence exactly: a machine's own version wins over the site
    default, so the date has to follow it rather than report the site survey's age against
    a machine version nobody confirmed.
    """
    return (f"If(!IsBlank({inst}.'Installed Version'), {inst}.'Last Verified', "
            f"LookUp(TB_SoftwareVersions, Customer.Id = varCustomer.ID "
            f"&& Product.Id = {product_id}).'Last Verified')")


EFF_ROW = _effective("ThisItem", "ThisItem.Product.Id")
VER_ROW = _verified("ThisItem", "ThisItem.Product.Id")
ROW_STALE = P.verified_is_stale(VER_ROW)
ROW_NOTE = P.verified_note(VER_ROW)

# Units under this solution row. "As U" names the outer row so U.Product.Id is not shadowed
# by the nested LookUp's own scope.
UNITS = ("Filter(TB_Installations As U, U.'Parent'.Id = ThisItem.ID, "
         "U.Status.Value <> \"Retired\")")
UNIT_N = f"CountRows({UNITS})"
# Same rule as the hero and as scrCustomers: the machine's own version, else the site
# default recorded against that model. varCustomer is the site being viewed.
_EFF = _effective("U", "U.Product.Id")

# Units under this solution that nobody has confirmed within a year, or ever. A count is
# asking "how many should someone look at", so never-verified belongs in it - unlike the
# single-record panel, where "never" is better said than coloured.
_VER_U = _verified("U", "U.Product.Id")

CHECK_N = ("CountRows(Filter(TB_Installations As U, U.'Parent'.Id = ThisItem.ID, "
           "U.Status.Value <> \"Retired\", "
           f"{P.verified_needs_check(_VER_U)}))")

# The card's rail, coloured by verification age rather than by currency - the same rule as
# cmpVersionChip and the unit rows, and all three now read screen_parts for the threshold
# instead of each carrying their own copy of it.
STATE_COLOUR = f"""=If(
                              IsBlank({EFF_READ}),
                              AppDark.Line,
                              {ROW_STALE},
                              AppDark.Warn,
                              AppDark.Muted
                          )"""

Y_TITLE = f"{P.BAND} + 24"
Y_SUB = "lblTitleOvw.Y + lblTitleOvw.Height"
Y_NOTES = "lblSubtitleOvw.Y + lblSubtitleOvw.Height + Gutter"
Y_HEAD = ("conSupportNotes.Y + "
          "If(conSupportNotes.Visible, conSupportNotes.Height + Gutter, 0)")

doc = f'''# Screen — Customer overview  (GENERATED by scripts/gen_customer_overview.py)
#
# What a site has. See the generator docstring for the one real design change: the nested
# per-card unit gallery is replaced by a summary line, trading one tap for the ability to
# see every solution at a site at once.
#
# varCustomer is set by whoever navigated here. Solutions are installations with no Parent;
# units are installations whose Parent is a solution.

Screens:
  scrCustomerOverview:
    Properties:
      Fill: =AppDark.Bg
    Children:
      - conRootOvw:
          Control: GroupContainer
          Variant: ManualLayout
          Properties:
            X: =0
            Y: =0
            Width: =Parent.Width
            Height: =Parent.Height
            Fill: =AppDark.Bg
          Children:
{P.brand_band("Ovw", "scrCustomers", back_transition="CoverRight", back_label="Customers")}

{P.title_actions("lblTitleOvw", ACTIONS)}            - lblTitleOvw:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={Y_TITLE}
                  Width: ={P.title_shrink(ACTIONS)}
                  Height: ={P.title_height()}
                  Text: =varCustomer.Title
                  Font: =AppFont
                  Size: =If(IsNarrow, AppType.Title, AppType.Display)
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.Fg
                  Wrap: =false
                  AutoHeight: =false
            # The count is the first thing worth knowing about a site and it was not shown
            # anywhere before - you had to scroll the cards and add them up yourself.
            - lblSubtitleOvw:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={Y_SUB}
                  Width: ={P.CW}
                  Height: =22
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.FgSecondary
                  Wrap: =false
                  AutoHeight: =false
                  Text: |
                    =CountRows(Filter(TB_Installations, Customer.Id = varCustomer.ID, IsBlank(ThisRecord.'Parent'), Status.Value <> "Retired")) & " solution(s) on site" & If(IsBlank(varCustomer.Description), "", "  ·  " & varCustomer.Description)

            - conSupportNotes:
                Control: GroupContainer
                Variant: ManualLayout
                Properties:
                  X: =Gutter
                  Y: ={Y_NOTES}
                  Width: =Min({P.CW}, {P.PANEL_MAX})
                  Height: =92
                  Fill: =AppDark.Surface
                  Visible: =!IsBlank(varCustomer.'Support Notes')
                Children:
                  - lblSupportNotesHeading:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        X: =20
                        Y: =14
                        Width: =Parent.Width - 40
                        Height: =18
                        Text: ="SUPPORT NOTES"
                        Font: =AppFont
                        Size: =AppType.Small
                        FontWeight: =FontWeight.Bold
                        Color: =AppDark.Muted
                  - lblSupportNotes:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        X: =20
                        Y: =36
                        Width: =Parent.Width - 40
                        Height: =46
                        Text: =varCustomer.'Support Notes'
                        Font: =AppFont
                        Size: =AppType.Body
                        Color: =AppDark.Fg

            - lblSolutionsHeading:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: |
                    ={Y_HEAD}
                  Width: ={P.CW}
                  Height: =22
                  Text: ="SOLUTIONS"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Bold
                  Color: =AppDark.Muted
            - galSolutions:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: =Gutter
                  Y: =lblSolutionsHeading.Y + lblSolutionsHeading.Height + 10
                  Width: ={P.CW}
                  Height: =Max(Parent.Height - (lblSolutionsHeading.Y + lblSolutionsHeading.Height + 10) - Gutter, {CARD_H})
                  TemplateSize: ={CARD_H + 12}
                  TemplatePadding: =0
                  ShowScrollbar: =true
                  Items: |
                    =SortByColumns(
                        Filter(
                            TB_Installations,
                            Customer.Id = varCustomer.ID,
                            IsBlank(ThisRecord.'Parent'),
                            Status.Value <> "Retired"
                        ),
                        "Title",
                        SortOrder.Ascending
                    )
                  OnSelect: |
                    =Set(varInstallation, ThisItem);
                    Navigate(scrSolution, ScreenTransition.Cover)
                Children:
                  # The chamfered card. Its width is interpolated into the SVG twice - once
                  # for the attributes, once for the path - because a viewBox that does not
                  # track the rendered box smears the chamfer as the window resizes.
                  - imgCardOvw:
                      Control: Image
                      Properties:
                        X: =0
                        Y: =0
                        Width: =Parent.TemplateWidth
                        Height: ={CARD_H}
                        Image: |
                          ="data:image/svg+xml;utf8, " & EncodeUrl(
                              "<svg xmlns='http://www.w3.org/2000/svg' width='" & Round(Parent.TemplateWidth, 0) & "' height='{CARD_H}' viewBox='0 0 " & Round(Parent.TemplateWidth, 0) & " {CARD_H}' preserveAspectRatio='none'>" &
                              "<path d='M0 0 H" & Round(Parent.TemplateWidth - 16, 0) & " L" & Round(Parent.TemplateWidth, 0) & " 16 V{CARD_H} H0 Z' fill='#171A21' stroke='#2A2F3A' stroke-width='1'/>" &
                              "</svg>"
                          )
                  # The effective version is a non-delegable LookUp per row, and the card
                  # formulas below reference it a dozen times. Evaluated once here and read
                  # back, the same parking idiom scrCustomers uses for its check count.
                  - lblEffVerOvw:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =1
                        Height: =1
                        Visible: =false
                        Font: =AppFont
                        Size: =AppType.Small
                        Color: =AppDark.Muted
                        Text: |
                          ={EFF_ROW}

                  - recCardRailOvw:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =4
                        Height: ={CARD_H}
                        Fill: |
                          {STATE_COLOUR}
                  - lblModel:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =20
                        Y: =18
                        Width: =(Parent.TemplateWidth - 40) * 0.55
                        Height: =26
                        Text: ={PROD}.Title
                        Font: =AppFont
                        Size: =AppType.Heading
                        FontWeight: =FontWeight.Semibold
                        Color: =AppDark.Fg
                        Wrap: =false
                        AutoHeight: =false
                  # Family, unit count, and how many of those units nobody has confirmed
                  # lately. That count is the only thing on this screen not derivable by
                  # looking, so it is the only part allowed to shout.
                  - lblCardMetaOvw:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =20
                        Y: =46
                        Width: =(Parent.TemplateWidth - 40) * 0.62
                        Height: =20
                        Font: =AppFont
                        Size: =AppType.Small
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          ={PROD}.Family.Value & "  ·  " & {UNIT_N} & " unit(s)" & If({CHECK_N} > 0, "  ·  " & {CHECK_N} & " to check", "") & If(ThisItem.Status.Value = "In Service", "", "  ·  " & Lower(ThisItem.Status.Value))
                        Color: |
                          =If({CHECK_N} > 0, AppDark.Warn, AppDark.Muted)
                  # Right-aligned so versions form one column down the list, the same
                  # treatment as the unit rows on scrSolution.
                  - lblCardVerOvw:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =20 + ((Parent.TemplateWidth - 40) * 0.55)
                        Y: =30
                        Width: =(Parent.TemplateWidth - 40) * 0.45 - 12
                        Height: =26
                        Align: =Align.Right
                        Font: =AppFont
                        Size: =AppType.Body
                        FontWeight: =FontWeight.Semibold
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          =If(
                              IsBlank({EFF_READ}),
                              "not recorded",
                              {EFF_READ}
                          )
                        Color: |
                          =If(
                              IsBlank({EFF_READ}),
                              AppDark.Faint,
                              AppDark.Fg
                          )
                  # The date, on its own row. It cannot sit beside the meta line: that
                  # runs to 0.62 of the card and the version column starts at 0.55, so
                  # their boxes overlapped - and on a 303px card there is no split that
                  # fits a family, a unit count and an age across one line.
                  - lblCardAgeOvw:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =20
                        Y: =67
                        Width: =(Parent.TemplateWidth - 40)
                        Height: =18
                        Align: =Align.Left
                        Font: =AppFont
                        Size: =AppType.Small
                        Wrap: =false
                        AutoHeight: =false
                        Text: |
                          ={ROW_NOTE}
                        Color: |
                          =If({ROW_STALE}, AppDark.Warn, AppDark.Muted)
                  - galSolutionsHit:
                      Control: Classic/Button
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =0
                        Width: =Parent.TemplateWidth
                        Height: ={CARD_H}
                        Text: =""
                        Fill: =RGBA(0, 0, 0, 0)
                        HoverFill: =RGBA(106, 115, 230, 0.10)
                        PressedFill: =RGBA(106, 115, 230, 0.18)
                        BorderThickness: =0
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        FocusedBorderThickness: =2
                        FocusedBorderColor: =AppDark.Accent
            - lblNoSolutions:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: =galSolutions.Y
                  Width: ={P.CW}
                  Height: =40
                  Text: ="No active solutions are recorded for this customer."
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Muted
                  Visible: =CountRows(galSolutions.AllItems) = 0
'''

OUT.write_text(doc, encoding="utf-8", newline="")
print(f"wrote {OUT}  ({len(doc.splitlines())} lines)")
