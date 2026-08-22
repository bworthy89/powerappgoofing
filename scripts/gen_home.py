"""Generate scrHome as a dark, brand-led screen.

WHY A REBUILD AND NOT ANOTHER PASS

The previous pass raised type sizes and fixed tap targets. Measurable, correct, and
invisible to the person using it - which was the point of the feedback. A canvas app reads
as a canvas app because of the things the control set gives you for free: a white screen, a
title in the corner, rounded rectangles, stock Fluent glyphs. Changing the point sizes
inside that vocabulary does not leave it.

Three things here leave it, and none of them are available from the control picker:

1. GLORY'S OWN LOCKUP. The header band is #111987 with the real wordmark on it, extracted
   from the logo artwork and embedded as a base64 PNG. That is not an approximation of the
   brand - white-on-#111987 IS how Glory presents the mark.

2. CHAMFERED PANELS, drawn as inline SVG. The wordmark's letterforms have cut corners and
   squared terminals; the cards echo that with a 18px chamfer on the top-right. Power Apps
   has no chamfer - only four independent corner radii - so this shape cannot be made with
   controls at all. It is the single strongest "this was designed" signal on the screen,
   and it is derived from the logo rather than invented.

3. DARK GROUND. The player's default is white, so a graphite app does not read as one.
   It also suits the work: technicians are usually in back-offices and server rooms, not
   under branch lighting.

WHY THE ACCENT IS NOT THE BRAND COLOUR

#111987 is nearly black - 13.88:1 against white, 1.36:1 against this background. It is a
superb surface colour and an unusable accent on dark. AppDark.Accent (#6A73E6) is the same
hue lightened until it clears 4.5:1 on the background; AppDark.AccentSolid (#2E3AD4) is the
darker step for filled shapes that carry white text. Using #111987 for accents on dark
would render them invisible, which is the trap this palette exists to avoid.

SVG IN A CANVAS APP

    Image: ="data:image/svg+xml;utf8, " & EncodeUrl("<svg xmlns='...'>...</svg>")

Single quotes inside the SVG, because the formula is already double-quoted. EncodeUrl
handles the '#' in hex colours. Dimensions are interpolated from Power Fx so the panels
stay responsive - the viewBox has to track the real pixel width or the chamfer distorts.

Behaviour is unchanged: same three search galleries, same filters, same navigation. Only
the surface is new.
"""
import textwrap
from pathlib import Path

OUT = Path(r"E:\Papp\powerappgoofing\app\screens\scrHome.pa.yaml")
WORDMARK = Path(
    r"C:\Users\bwort\AppData\Local\Temp\claude\E--Papp"
    r"\c7a373b9-de1b-4ba5-a22b-70f79a3b6252\scratchpad\glory_wordmark_b64.txt"
).read_text().strip()

HEADER_H = 72
CARD_H = 104
CARD_GAP = 16

# Card width as Power Fx, used in both the SVG viewBox and the path geometry.
CW = "Parent.Width - (Gutter * 2)"


def svg(body):
    """Wrap an SVG body as a canvas-app data URI formula."""
    return f'"data:image/svg+xml;utf8, " & EncodeUrl(\n{body}\n                    )'


def card_bg(accent):
    """A chamfered panel with an accent rail down its left edge.

    The chamfer is on the top-right at 18px, matching the cut corners of the wordmark.
    Width is interpolated twice - once for the svg/viewBox attributes and once for the
    path - because an SVG whose viewBox does not match its rendered box will stretch the
    chamfer into a diagonal smear as the window resizes.
    """
    return svg(f"""                        "<svg xmlns='http://www.w3.org/2000/svg' width='" & Round({CW}, 0) & "' height='{CARD_H}' viewBox='0 0 " & Round({CW}, 0) & " {CARD_H}' preserveAspectRatio='none'>" &
                        "<path d='M0 0 H" & Round({CW} - 18, 0) & " L" & Round({CW}, 0) & " 18 V{CARD_H} H0 Z' fill='#171A21' stroke='#2A2F3A' stroke-width='1'/>" &
                        "<rect x='0' y='0' width='3' height='{CARD_H}' fill='{accent}'/>" """)


ICON_SITE = ("<path d='M3 21h18M5 21V8l7-4 7 4v13M9.5 21v-4.5h5V21M9 11.5h.01M15 11.5h.01'/>")
ICON_GRID = ("<rect x='3' y='4' width='7.5' height='7' rx='1'/>"
             "<rect x='13.5' y='4' width='7.5' height='7' rx='1'/>"
             "<rect x='3' y='13' width='7.5' height='7' rx='1'/>"
             "<rect x='13.5' y='13' width='7.5' height='7' rx='1'/>")


def icon(paths):
    return svg(f"""                        "<svg xmlns='http://www.w3.org/2000/svg' width='30' height='30' viewBox='0 0 24 24' fill='none' stroke='#6A73E6' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'>{paths}</svg>" """)


def card(n, key, title, desc, paths, target, y):
    """One action card: chamfered panel, icon, title, description, full-area hit target."""
    return f"""
            # ---- action card: {title}
            # The panel, the icon and the hit target are three separate controls stacked in
            # Z order. The panel is an Image because the shape is SVG; an Image cannot take
            # an OnSelect, so the transparent Classic/Button on top carries the tap.
            - imgCard{key}Bg:
                Control: Image
                Properties:
                  X: =Gutter
                  Y: ={y}
                  Width: ={CW}
                  Height: ={CARD_H}
                  Visible: =Len(Trim(txtSearchHome.Text)) < 2
                  Image: |
                    ={card_bg('#6A73E6')}
            - imgCard{key}Icon:
                Control: Image
                Properties:
                  X: =Gutter + 26
                  Y: ={y} + 37
                  Width: =30
                  Height: =30
                  Visible: =Len(Trim(txtSearchHome.Text)) < 2
                  Image: |
                    ={icon(paths)}
            - lblCard{key}Title:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter + 76
                  Y: ={y} + 28
                  Width: ={CW} - 100
                  Height: =26
                  Text: ="{title}"
                  Font: =AppFont
                  Size: =AppType.Heading
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.Fg
                  Wrap: =false
                  AutoHeight: =false
                  Visible: =Len(Trim(txtSearchHome.Text)) < 2
            - lblCard{key}Desc:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter + 76
                  Y: ={y} + 56
                  Width: ={CW} - 100
                  Height: =22
                  Text: ="{desc}"
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.FgSecondary
                  Wrap: =false
                  AutoHeight: =false
                  Visible: =Len(Trim(txtSearchHome.Text)) < 2
            - btnCard{key}Hit:
                Control: Classic/Button
                Properties:
                  Text: =""
                  OnSelect: =Navigate({target}, ScreenTransition.Cover)
                  X: =Gutter
                  Y: ={y}
                  Width: ={CW}
                  Height: ={CARD_H}
                  Visible: =Len(Trim(txtSearchHome.Text)) < 2
                  Fill: =RGBA(0, 0, 0, 0)
                  HoverFill: =RGBA(106, 115, 230, 0.10)
                  PressedFill: =RGBA(106, 115, 230, 0.18)
                  BorderThickness: =0
                  HoverBorderColor: =RGBA(0, 0, 0, 0)
                  PressedBorderColor: =RGBA(0, 0, 0, 0)
                  FocusedBorderThickness: =2
                  FocusedBorderColor: =AppDark.Accent"""


def search_gallery(key, label, items, head_y, name_text, meta_text, on_select):
    """One search result gallery plus its section label, restyled for the dark ground."""
    return f"""
            - lblSearch{key}Head:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: |
                    ={head_y}
                  Width: ={CW}
                  Height: =20
                  Text: ="{label}"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Bold
                  Color: =AppDark.Muted
                  Visible: =galSearch{key}.Visible
            - galSearch{key}:
                Control: Gallery
                Variant: Vertical
                Properties:
                  X: =Gutter
                  Y: =lblSearch{key}Head.Y + lblSearch{key}Head.Height + 4
                  Width: ={CW}
                  Height: =Min(CountRows(galSearch{key}.AllItems), 4) * 56
                  TemplateSize: =56
                  TemplatePadding: =0
                  ShowScrollbar: =false
                  Visible: =Len(Trim(txtSearchHome.Text)) >= 2 && CountRows(galSearch{key}.AllItems) > 0
                  Items: |
                    ={items}
                Children:
                  - lblSrch{key}Name:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =14
                        Y: =8
                        Width: =Parent.TemplateWidth - 28
                        Height: =22
                        Text: |
                          ={name_text}
                        Font: =AppFont
                        Size: =AppType.Body
                        FontWeight: =FontWeight.Semibold
                        Color: =AppDark.Fg
                        Wrap: =false
                        AutoHeight: =false
                  - lblSrch{key}Meta:
                      Control: ModernText
                      Properties:
                        PaddingTop: =0
                        PaddingBottom: =0
                        OnSelect: =Select(Parent)
                        X: =14
                        Y: =30
                        Width: =Parent.TemplateWidth - 28
                        Height: =18
                        Text: |
                          ={meta_text}
                        Font: =AppFont
                        Size: =AppType.Small
                        Color: =AppDark.Muted
                        Wrap: =false
                        AutoHeight: =false
                  - recSrch{key}Rule:
                      Control: Rectangle
                      Properties:
                        OnSelect: =Select(Parent)
                        X: =0
                        Y: =55
                        Width: =Parent.TemplateWidth
                        Height: =1
                        Fill: =AppDark.Line
                  - galSearch{key}Hit:
                      Control: Classic/Button
                      Properties:
                        OnSelect: |
                          ={on_select}
                        X: =0
                        Y: =0
                        Width: =Parent.TemplateWidth
                        Height: =Parent.TemplateHeight
                        Text: =""
                        Fill: =RGBA(0, 0, 0, 0)
                        HoverFill: =RGBA(106, 115, 230, 0.10)
                        PressedFill: =RGBA(106, 115, 230, 0.18)
                        BorderThickness: =0
                        HoverBorderColor: =RGBA(0, 0, 0, 0)
                        PressedBorderColor: =RGBA(0, 0, 0, 0)
                        FocusedBorderThickness: =2
                        FocusedBorderColor: =AppDark.Accent"""


ORIGIN = "txtSearchHome.Y + txtSearchHome.Height + Gutter"
GAL_BLOCK = "If(galSearch{k}.Visible, galSearch{k}.Height + 32, 0)"

doc = f'''# Screen — Home  (GENERATED by scripts/gen_home.py — edit the generator, not this file)
#
# {__doc__.strip().splitlines()[0]}
#
# See the generator's docstring for why this is a rebuild rather than a restyle, why the
# accent is not the brand colour, and how the SVG panels are constructed.
#
# Two mutually exclusive regions share one origin, exactly as before: the three search
# galleries when the box has two or more characters, and the action cards otherwise. Every
# control in both regions repeats its own Len(Trim(txtSearchHome.Text)) guard, because this
# environment has no shared-state construct that a Visible can read.

Screens:
  scrHome:
    Properties:
      Fill: =AppDark.Bg
      OnVisible: =Set(varExpandedModel, 0)
    Children:
      - conHomeRoot:
          Control: GroupContainer
          Variant: ManualLayout
          Properties:
            X: =0
            Y: =0
            Width: =Parent.Width
            Height: =Parent.Height
            Fill: =AppDark.Bg
          Children:
            # ---- brand band
            # Full-bleed #111987 with the real wordmark on it. This is Glory's own lockup,
            # not a tint of it: the artwork is white-on-#111987 and so is this.
            - recBrandBand:
                Control: Rectangle
                Properties:
                  X: =0
                  Y: =0
                  Width: =Parent.Width
                  Height: ={HEADER_H}
                  Fill: =AppDark.Brand
            - imgWordmarkHome:
                Control: Image
                Properties:
                  X: =Gutter
                  Y: =27
                  Width: =112
                  Height: =18
                  Image: |
                    ="data:image/png;base64,{WORDMARK}"
            - lblAppNameHome:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter + 126
                  Y: =27
                  Width: =200
                  Height: =18
                  Text: ="TECHNICIAN TOOLBOX"
                  Font: =AppFont
                  Size: =AppType.Micro
                  FontWeight: =FontWeight.Semibold
                  Color: =RGBA(255, 255, 255, 0.62)
                  Wrap: =false
                  AutoHeight: =false
                  Visible: =!IsNarrow
            - btnRequestAccess:
                Control: ModernButton
                Properties:
                  Visible: =!varIsAdmin
                  Appearance: =ButtonAppearance.Subtle
                  Icon: ="People"
                  Layout: =If(IsNarrow, ButtonLayout.IconOnly, ButtonLayout.IconBefore)
                  Text: ="Request access"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.OnBrand
                  BorderThickness: =0
                  Height: =44
                  Width: =If(IsNarrow, 44, 170)
                  X: =Parent.Width - Gutter - If(IsNarrow, 44, 170)
                  Y: =14
                  OnSelect: =Navigate(scrRequestAccess, ScreenTransition.Cover)
            - btnTileAdmin:
                Control: ModernButton
                Properties:
                  Visible: =varIsAdmin
                  Appearance: =ButtonAppearance.Subtle
                  Icon: ="Settings"
                  Layout: =If(IsNarrow, ButtonLayout.IconOnly, ButtonLayout.IconBefore)
                  Text: ="Admin"
                  Font: =AppFont
                  Size: =AppType.Small
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.OnBrand
                  BorderThickness: =0
                  Height: =44
                  Width: =If(IsNarrow, 44, 110)
                  X: =Parent.Width - Gutter - If(IsNarrow, 44, 110)
                  Y: =14
                  OnSelect: =Navigate(scrAdmin, ScreenTransition.Cover)

            # ---- headline, in two tones
            # The name is the greeting and the question is the instruction, so they are
            # coloured differently rather than run together. The accent carries the half
            # that asks for an action.
            - lblGreetHome:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={HEADER_H} + 34
                  Width: ={CW}
                  Height: =41
                  Text: |
                    ="Hi " & Coalesce(Match(User().FullName, ",\\s*(?<fn>[^\\s(,]+)").fn, Match(User().FullName, "^\\s*(?<fn>[^\\s(,]+)").fn, "there") & ","
                  Font: =AppFont
                  Size: =If(IsNarrow, AppType.Title, AppType.Display)
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.Fg
                  Wrap: =false
                  AutoHeight: =false
            - lblAskHome:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: =lblGreetHome.Y + lblGreetHome.Height
                  Width: ={CW}
                  Height: =41
                  Text: ="what do you need?"
                  Font: =AppFont
                  Size: =If(IsNarrow, AppType.Title, AppType.Display)
                  FontWeight: =FontWeight.Semibold
                  Color: =AppDark.Accent
                  Wrap: =false
                  AutoHeight: =false

            - txtSearchHome:
                Control: ModernTextInput
                Properties:
                  Type: =TextInputType.Search
                  X: =Gutter
                  Y: =lblAskHome.Y + lblAskHome.Height + Gutter
                  Width: ={CW}
                  Height: =48
                  Default: =""
                  Placeholder: ="Search customers, models, documents"
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Fg
                  Fill: =AppDark.Surface
                  BorderColor: =AppDark.Line
                  BorderThickness: =1
                  RadiusTopLeft: =6
                  RadiusTopRight: =6
                  RadiusBottomLeft: =6
                  RadiusBottomRight: =6
{card(1, "Cust", "Find a customer", "See what a site runs, and its documents", ICON_SITE, "scrCustomers", f"{ORIGIN} + 8")}
{card(2, "Cat", "Browse the catalogue", "Every model, its documents and firmware", ICON_GRID, "scrCatalogue", f"{ORIGIN} + 8 + {CARD_H} + {CARD_GAP}")}
{search_gallery("Customers", "CUSTOMERS", "Filter(TB_Customers, Active = true, StartsWith(Title, Trim(txtSearchHome.Text)))", f"{ORIGIN}", "ThisItem.Title", 'Coalesce(ThisItem.Description, "No description")', "Set(varCustomer, ThisItem); Navigate(scrCustomerOverview, ScreenTransition.Cover)")}
{search_gallery("Products", "MODELS", "Filter(TB_Products, Active = true, StartsWith(Title, Trim(txtSearchHome.Text)))", "lblSearchCustomersHead.Y + " + GAL_BLOCK.format(k="Customers"), "ThisItem.Title", 'ThisItem.\'Product Type\'.Value & "  ·  " & Coalesce(ThisItem.\'Current Standard Version\', "no standard")', "Set(varExpandedModel, ThisItem.ID); Navigate(scrCatalogue, ScreenTransition.Cover)")}
{search_gallery("Docs", "DOCUMENTS", "Filter(TB_References, Trim(txtSearchHome.Text) in Title, IsBlank(Customer))", "lblSearchProductsHead.Y + " + GAL_BLOCK.format(k="Products"), "ThisItem.Title", 'If(!IsBlank(ThisItem.Product.Value), LookUp(TB_Products, ID = ThisItem.Product.Id).Title, "")', "Launch(ThisItem.URL)")}

            - lblNoSearchResults:
                Control: ModernText
                Properties:
                  PaddingTop: =0
                  PaddingBottom: =0
                  X: =Gutter
                  Y: ={ORIGIN} + 8
                  Width: ={CW}
                  Height: =40
                  Align: =Align.Center
                  Font: =AppFont
                  Size: =AppType.Body
                  Color: =AppDark.Muted
                  Text: ="No matches for this search."
                  Visible: |
                    =Len(Trim(txtSearchHome.Text)) >= 2 &&
                    CountRows(galSearchCustomers.AllItems) = 0 &&
                    CountRows(galSearchProducts.AllItems) = 0 &&
                    CountRows(galSearchDocs.AllItems) = 0
'''

OUT.write_text(doc, encoding="utf-8", newline="")
print(f"wrote {OUT}  ({len(doc.splitlines())} lines, wordmark {len(WORDMARK)} b64 chars)")
