"""Generate scrAdmin.pa.yaml and scrEditForm.pa.yaml from a field spec.

Only controls whose properties were confirmed via describe_control are used:
Label, Classic/Button, Classic/TextInput, Classic/DropDown, Classic/Toggle,
GroupContainer, Gallery.

Form / DataCard are deliberately avoided: describe_control returns HTTP 500
for both, so their properties cannot be verified.
"""
import io, sys

# ---------------------------------------------------------------- field spec
# kind: text | note | choice | bool | lookup | url
# The Access tab. Deliberately not a member of LISTS: it has no edit form, no
# Add new, and its rows act rather than navigate, so every loop over LISTS would
# need to except it. The label carries the pending count because nothing else
# tells an admin a request is waiting.
ACCESS = dict(key="Acc",
              label='"Access" & If(CountRows(Filter(TB_Admins, Status.Value = "Pending")) > 0, "  (" & CountRows(Filter(TB_Admins, Status.Value = "Pending")) & ")", "")',
              raw_label=True)

LISTS = [
    dict(key="Cust", label="Customers", source="TB_Customers",
         deps="CountRows(Filter(TB_Installations, Customer.Id = varRecCust.ID))"
              " + CountRows(Filter(TB_References, Customer.Id = varRecCust.ID))",
         depsLabel="installations or documents", fields=[
        dict(n="Title",           kind="text",   caption="Name"),
        dict(n="Description",     kind="note",   caption="Description"),
        dict(n="'Support Notes'", kind="note",   caption="Support notes", id="SupportNotes"),
        dict(n="Active",          kind="bool",   caption="Active"),
    ]),
    dict(key="Prod", label="Products", source="TB_Products",
         deps="CountRows(Filter(TB_Installations, Product.Id = varRecProd.ID))"
              " + CountRows(Filter(TB_References, Product.Id = varRecProd.ID))"
              " + CountRows(Filter(TB_SolutionUnits, Solution.Id = varRecProd.ID))"
              " + CountRows(Filter(TB_SolutionUnits, Unit.Id = varRecProd.ID))",
         depsLabel="installations, documents or solution-unit rows", fields=[
        dict(n="Title",                        kind="text",   caption="Model"),
        dict(n="'Product Type'",               kind="choice", caption="Product type", id="ProductType"),
        dict(n="Family",                       kind="choice", caption="Family"),
        dict(n="'Current Standard Version'",   kind="text",   caption="Current standard version", id="StdVersion"),
        dict(n="Description",                  kind="note",   caption="Description"),
        dict(n="Active",                       kind="bool",   caption="Active"),
    ]),
    dict(key="Inst", label="Installations", source="TB_Installations",
         deps="CountRows(Filter(TB_Installations, 'Parent'.Id = varRecInst.ID))",
         depsLabel="units attached to it", fields=[
        dict(n="Title",                 kind="text",   caption="Name"),
        dict(n="Customer",              kind="lookup", caption="Customer", target="TB_Customers"),
        dict(n="Product",               kind="lookup", caption="Product",  target="TB_Products"),
        dict(n="'Parent'",              kind="lookup", caption="Parent solution (blank = this IS a solution)",
             target="TB_Installations", id="Parent", parent=True),
        dict(n="'Installed Version'",   kind="text",   caption="Installed version", id="InstVersion"),
        dict(n="Status",                kind="choice", caption="Status"),
        dict(n="'Config Notes'",        kind="note",   caption="Config notes", id="ConfigNotes"),
    ]),
    dict(key="SolU", label="Solution units", source="TB_SolutionUnits", fields=[
        dict(n="Title",    kind="text",   caption="Label, e.g. CI 300X - SDRB250"),
        dict(n="Solution", kind="lookup", caption="Solution model", target="TB_Products"),
        dict(n="Unit",     kind="lookup", caption="Unit model that attaches to it", target="TB_Products"),
        dict(n="Standard", kind="bool",   caption="Part of the standard build"),
    ]),
    dict(key="Ref", label="References", source="TB_References", fields=[
        dict(n="Title",              kind="text",   caption="Title"),
        dict(n="Product",            kind="lookup", caption="Product", target="TB_Products"),
        dict(n="Customer",           kind="lookup", caption="Customer (blank = applies to all customers)",
             target="TB_Customers"),
        dict(n="Section",            kind="choice", caption="Section"),
        dict(n="'Reference Type'",   kind="choice", caption="Reference type", id="RefType"),
        dict(n="URL",                kind="url",    caption="URL"),
        dict(n="Version",            kind="text",   caption="Version"),
        dict(n="Featured",           kind="bool",   caption="Featured"),
    ]),
]

def fid(f):
    return f.get("id") or f["n"].strip("'").replace(" ", "")

# ------------------------------------------------------------------ emitters
def prop(o, k, v, ind):
    # A ": " inside a Power Fx value terminates the YAML key when written
    # inline. Emit those as block scalars. See gen_onboard.py for the full note.
    if ": " in v:
        o.write(f"{ind}{k}: |\n{ind}  ={v}\n")
    else:
        o.write(f"{ind}{k}: ={v}\n")

def ctrl(o, name, control, ind, variant=None):
    o.write(f"{ind}- {name}:\n{ind}    Control: {control}\n")
    if variant:
        o.write(f"{ind}    Variant: {variant}\n")
    o.write(f"{ind}    Properties:\n")
    return ind + "      "

# =============================================================== scrAdmin
def gen_admin():
    o = io.StringIO()
    o.write("# Generated by scripts/gen_admin.py - admin record picker.\n")
    o.write("# One gallery per list, toggled by varAdminList. Each row is a single\n")
    o.write("# Classic/Button so the whole row is the tap target and the text is the\n")
    o.write("# button's own Text - no separate label to keep aligned.\n")
    # The screen turns people away itself. Hiding the button on home is tidiness;
    # this is the part that holds if anyone arrives by another route. Neither is a
    # security boundary - a technician with Contribute can edit the lists directly
    # in SharePoint, so the real control is list permissions.
    o.write('Screens:\n  scrAdmin:\n    Properties:\n      Fill: =AppTheme.Bg\n'
            '      OnVisible: |\n'
            '        =If(!varIsAdmin, Navigate(scrHome, ScreenTransition.UnCoverRight))\n'
            '    Children:\n')
    ind = "      "
    p = ctrl(o, "conRootAdm", "GroupContainer", ind, "ManualLayout")
    prop(o, "Fill", "AppTheme.Bg", p)
    prop(o, "Height", "Parent.Height", p)
    prop(o, "Width", "ContentWidth", p)
    prop(o, "X", "Max((Parent.Width - ContentWidth) / 2, Gutter)", p)
    o.write(f"{p[:-2]}Children:\n")
    c = p

    q = ctrl(o, "btnBackAdm", "Classic/Button", c)
    for k, v in [("BorderThickness","0"),("Color","AppTheme.Primary"),("Fill","AppTheme.Bg"),
                 ("Font","AppFont"),("Height","28"),("HoverColor","AppTheme.PrimaryDark"),
                 ("HoverFill","AppTheme.Sunken"),("OnSelect","Navigate(scrHome, ScreenTransition.CoverRight)"),
                 ("Size","AppType.Small"),("Text",'"<  Home"'),("Width","Gutter * 8"),
                 ("X","Gutter"),("Y","Gutter"),("FocusedBorderThickness","2"),
                 ("FocusedBorderColor","AppTheme.Primary")]:
        prop(o, k, v, q)

    q = ctrl(o, "lblTitleAdm", "Label", c)
    for k, v in [("Color","AppTheme.Fg"),("Font","AppFont"),("FontWeight","FontWeight.Bold"),
                 ("Height","36"),("Size","AppType.Title"),("Text",'"Admin"'),("Wrap","false"),
                 ("AutoHeight","false"),("Width","ContentWidth - (Gutter * 2)"),
                 ("X","Gutter"),("Y","Gutter + 34")]:
        prop(o, k, v, q)

    # The tab bar divides by however many lists there are. It was hardcoded to
    # four, which silently pushed the fifth tab off the right edge.
    TABW = f"(ContentWidth - (Gutter * 2) - {8 * len(LISTS)}) / {len(LISTS) + 1}"

    # list selector buttons
    for i, L in enumerate(LISTS + [ACCESS]):
        q = ctrl(o, f"btnList{L['key']}", "Classic/Button", c)
        sel = f'varAdminList = "{L["key"]}"'
        for k, v in [("Font","AppFont"),("Size","AppType.Small"),
                     ("Text", L["label"] if L.get("raw_label") else f'"{L["label"]}"'),
                     ("Fill",f'If({sel}, AppTheme.Primary, AppTheme.Surface)'),
                     ("Color",f'If({sel}, AppTheme.OnPrimary, AppTheme.Fg)'),
                     ("HoverFill",f'If({sel}, AppTheme.PrimaryDark, AppTheme.Sunken)'),
                     ("BorderColor","AppTheme.Line"),("BorderThickness","1"),
                     ("Height","34"),("Width",TABW),
                     ("X",f"Gutter + ({TABW} + 8) * {i}"),
                     ("Y","Gutter + 80"),
                     ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                     ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                     ("OnSelect",f'Set(varAdminList, "{L["key"]}")'),
                     ("FocusedBorderThickness","2"),("FocusedBorderColor","AppTheme.Primary")]:
            prop(o, k, v, q)

    q = ctrl(o, "txtSearchAdm", "Classic/TextInput", c)
    for k, v in [("BorderColor","AppTheme.Line"),("BorderThickness","1"),("Color","AppTheme.Fg"),
                 ("Default",'""'),("Fill","AppTheme.Surface"),("Font","AppFont"),("Height","40"),
                 ("HintText",'"Search"'),("Size","AppType.Body"),
                 ("Width","ContentWidth - (Gutter * 2) - 130"),("X","Gutter"),("Y","Gutter + 126"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6")]:
        prop(o, k, v, q)

    # The wizard, reachable only from here. "Add new" creates a bare customer
    # row through scrEditForm; this walks the whole site - customer, its
    # solutions, and the components under them - in one pass. Only meaningful
    # on the Customers list, so it hides on the other three.
    # Empty TB_Admins means everyone is an admin. That is deliberate - the
    # alternative locks out the person who has to add the first row - but it
    # should never be quiet about it.
    q = ctrl(o, "lblAdminOpen", "Label", c)
    for k, v in [("Text",'"Anyone can reach Admin: TB_Admins is empty. Add yourself to it to lock this down."'),
                 ("Color","AppTheme.Warn"),("Fill","AppTheme.WarnLight"),
                 ("Font","AppFont"),("Size","AppType.Small"),
                 ("FontWeight","FontWeight.Semibold"),
                 ("Align","Align.Center"),("Wrap","true"),("AutoHeight","false"),
                 ("PaddingTop","6"),("PaddingBottom","6"),
                 ("X","Gutter"),("Y","Gutter + 74"),("Height","28"),
                 ("Width","ContentWidth - (Gutter * 2)"),
                 ("Visible","CountRows(TB_Admins) = 0"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6")]:
        prop(o, k, v, q)

    q = ctrl(o, "btnGuidedSetup", "Classic/Button", c)
    for k, v in [("Font","AppFont"),("Size","AppType.Small"),
                 ("Text",'"Guided setup"'),
                 ("Tooltip",'"Add a customer with its solutions and components"'),
                 ("Fill","AppTheme.Surface"),("Color","AppTheme.Primary"),
                 ("HoverFill","AppTheme.Sunken"),("BorderColor","AppTheme.Line"),
                 ("BorderThickness","1"),
                 ("Height","40"),("Width","150"),
                 ("X","ContentWidth - Gutter - 118 - 8 - 150"),("Y","Gutter + 126"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                 ("Visible",'varAdminList = "Cust"'),
                 ("OnSelect","Navigate(scrOnboard, ScreenTransition.Cover)"),
                 ("FocusedBorderThickness","2"),("FocusedBorderColor","AppTheme.Primary")]:
        prop(o, k, v, q)

    q = ctrl(o, "btnAddNew", "Classic/Button", c)
    for k, v in [("Font","AppFont"),("Size","AppType.Small"),("Text",'"+  Add new"'),
                 ("Fill","AppTheme.Ok"),("Color","AppTheme.OnPrimary"),
                 ("HoverFill","AppTheme.Primary"),("BorderThickness","0"),
                 ("Height","40"),("Width","118"),
                 ("X","ContentWidth - Gutter - 118"),("Y","Gutter + 126"),
                 ("Visible",'varAdminList <> "Acc"'),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                 ("OnSelect","PLACEHOLDER"),
                 ("FocusedBorderThickness","2"),("FocusedBorderColor","AppTheme.Primary")]:
        if k == "OnSelect":
            # One typed variable per list. Power Fx infers a variable's type from
            # its Set() calls, so a single variable Set to records of four
            # different tables has no coherent type. Defaults(<table>) yields an
            # empty record that still carries a schema.
            sw = ",\n".join(
                f'{q}      "{X["key"]}", Set(varRec{X["key"]}, Defaults({X["source"]}))'
                for X in LISTS)
            o.write(f"{q}OnSelect: |\n"
                    f"{q}  =Set(varAdminNew, true);\n"
                    f"{q}  Switch(varAdminList,\n{sw}\n{q}  );\n"
                    f"{q}  Navigate(scrEditForm, ScreenTransition.Cover)\n")
        else:
            prop(o, k, v, q)

    # one gallery per list
    sub = {"Cust": '" - " & Coalesce(ThisItem.Description, "no description")',
           "Prod": '" - " & Coalesce(ThisItem.\'Product Type\'.Value, "no type") & "  |  standard " & Coalesce(ThisItem.\'Current Standard Version\', "not set")',
           "Inst": '" - " & Coalesce(ThisItem.Customer.Value, "no customer") & If(IsBlank(ThisItem.\'Parent\'), "  |  SOLUTION", "  |  unit of " & ThisItem.\'Parent\'.Value)',
           "Ref":  '" - " & Coalesce(ThisItem.Product.Value, "no product") & "  |  " & Coalesce(ThisItem.Section.Value, "no section")',
           "SolU": '" - " & Coalesce(ThisItem.Unit.Value, "no unit") & If(ThisItem.Standard, "  |  standard", "  |  option")'}
    for L in LISTS:
        q = ctrl(o, f"galAdm{L['key']}", "Gallery", c, "Vertical")
        o.write(f"{q}Items: |\n{q}  =SortByColumns(\n"
                f"{q}      Filter({L['source']}, StartsWith(Title, Trim(txtSearchAdm.Text))),\n"
                f"{q}      \"Title\",\n{q}      SortOrder.Ascending\n{q}  )\n")
        for k, v in [("Visible",f'varAdminList = "{L["key"]}"'),
                     ("X","Gutter"),("Y","Gutter + 180"),
                     ("Width","ContentWidth - (Gutter * 2)"),
                     ("Height","Parent.Height - (Gutter + 180) - Gutter"),
                     ("TemplateSize","44"),("TemplatePadding","6"),("ShowScrollbar","true")]:
            prop(o, k, v, q)
        o.write(f"{q[:-2]}Children:\n")
        r = ctrl(o, f"btnRow{L['key']}", "Classic/Button", q)
        o.write(f"{r}Text: |\n{r}  =ThisItem.Title & {sub[L['key']]}\n")
        o.write(f"{r}OnSelect: |\n{r}  =Set(varRec{L['key']}, ThisItem);\n"
                f"{r}  Set(varAdminNew, false);\n"
                f"{r}  Navigate(scrEditForm, ScreenTransition.Cover)\n")
        for k, v in [("Align","Align.Left"),("Font","AppFont"),("Size","AppType.Small"),
                     ("Color","AppTheme.Fg"),("Fill","AppTheme.Surface"),
                     ("HoverFill","AppTheme.PrimaryLight"),("PressedFill","AppTheme.PrimaryLight"),
                     ("BorderColor","AppTheme.LineSoft"),("BorderThickness","1"),
                     ("PaddingLeft","12"),
                     ("X","0"),("Y","0"),("Width","Parent.TemplateWidth"),("Height","44"),
                     ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                     ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                     ("FocusedBorderThickness","2"),("FocusedBorderColor","AppTheme.Primary")]:
            prop(o, k, v, r)

    # ---- Access: approve or deny, in the row
    VIS = 'varAdminList = "Acc"'
    q = ctrl(o, "galAdmAcc", "Gallery", c, "Vertical")
    # Pending first, so the thing needing a decision is at the top.
    o.write(f"{q}Items: |\n"
            f"{q}  =Sort(TB_Admins, If(Status.Value = \"Pending\", 0, 1), SortOrder.Ascending)\n")
    for k, v in [("Visible",VIS),("X","Gutter"),("Y","Gutter + 180"),
                 ("Width","ContentWidth - (Gutter * 2)"),
                 ("Height","Parent.Height - (Gutter + 180) - Gutter"),
                 ("TemplateSize","56"),("TemplatePadding","6"),
                 ("ShowScrollbar","true")]:
        prop(o, k, v, q)
    o.write(f"{q[:-2]}Children:\n")

    r = ctrl(o, "rectAccRow", "Classic/Button", q)
    for k, v in [("Text",'""'),("X","0"),("Y","0"),
                 ("Width","Parent.TemplateWidth"),("Height","50"),
                 ("Fill","AppTheme.Surface"),("HoverFill","AppTheme.Surface"),
                 ("BorderColor","AppTheme.LineSoft"),("BorderThickness","1"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6")]:
        prop(o, k, v, r)

    r = ctrl(o, "lblAccName", "Label", q)
    o.write(f'{r}Text: |\n{r}  =Coalesce(ThisItem.Person.DisplayName, ThisItem.Title, "unknown")\n')
    for k, v in [("Color","AppTheme.Fg"),("Font","AppFont"),("Size","AppType.Body"),
                 ("FontWeight","FontWeight.Semibold"),("Wrap","false"),
                 ("AutoHeight","false"),("X","Gutter"),("Y","6"),
                 ("Width","Parent.TemplateWidth - 300"),("Height","20")]:
        prop(o, k, v, r)

    r = ctrl(o, "lblAccMeta", "Label", q)
    o.write(f'{r}Text: |\n{r}  =Coalesce(ThisItem.Person.Email, "no email") & "   ·   " '
            f'& ThisItem.Status.Value & "   ·   asked " & Text(ThisItem.Created, "d mmm")\n')
    for k, v in [("Color","AppTheme.Muted"),("Font","AppFont"),("Size","AppType.Small"),
                 ("Wrap","false"),("AutoHeight","false"),("X","Gutter"),("Y","26"),
                 ("Width","Parent.TemplateWidth - 300"),("Height","18")]:
        prop(o, k, v, r)

    # Approve shows unless already approved; Deny unless already denied. Nothing
    # is deleted - a denied row is a record that the question was asked.
    r = ctrl(o, "btnAccApprove", "Classic/Button", q)
    o.write(f'{r}OnSelect: |\n'
            f'{r}  =Patch(TB_Admins, ThisItem, {{ Status: {{ Value: "Approved" }} }})\n')
    for k, v in [("Text",'"Approve"'),("Font","AppFont"),("Size","AppType.Small"),
                 ("FontWeight","FontWeight.Semibold"),
                 ("Fill","AppTheme.Ok"),("Color","AppTheme.OnPrimary"),
                 ("HoverFill","AppTheme.Primary"),("BorderThickness","0"),
                 ("X","Parent.TemplateWidth - 200"),("Y","8"),
                 ("Width","92"),("Height","34"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                 ("Visible",'ThisItem.Status.Value <> "Approved"')]:
        prop(o, k, v, r)

    r = ctrl(o, "btnAccDeny", "Classic/Button", q)
    o.write(f'{r}OnSelect: |\n'
            f'{r}  =Patch(TB_Admins, ThisItem, {{ Status: {{ Value: "Denied" }} }})\n')
    for k, v in [("Text",'"Deny"'),("Font","AppFont"),("Size","AppType.Small"),
                 ("FontWeight","FontWeight.Semibold"),
                 ("Fill","AppTheme.Surface"),("Color","RGBA(176, 0, 32, 1)"),
                 ("HoverFill","AppTheme.Sunken"),
                 ("BorderColor","RGBA(176, 0, 32, 1)"),("BorderThickness","1"),
                 ("X","Parent.TemplateWidth - 100"),("Y","8"),
                 ("Width","92"),("Height","34"),
                 ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                 ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                 ("Visible",'ThisItem.Status.Value <> "Denied"')]:
        prop(o, k, v, r)

    q = ctrl(o, "lblAccEmpty", "Label", c)
    for k, v in [("Text",'"Nobody has requested access. While no request is approved, everyone is an admin."'),
                 ("Align","Align.Center"),("Color","AppTheme.Muted"),("Font","AppFont"),
                 ("Size","AppType.Small"),("Wrap","true"),("AutoHeight","false"),
                 ("X","Gutter"),("Y","Gutter + 200"),("Height","40"),
                 ("Width","ContentWidth - (Gutter * 2)"),
                 ("Visible",f'{VIS} && CountRows(TB_Admins) = 0')]:
        prop(o, k, v, q)

    q = ctrl(o, "lblAdmEmpty", "Label", c)
    cond = " || ".join(
        f'(varAdminList = "{L["key"]}" && CountRows(galAdm{L["key"]}.AllItems) = 0)' for L in LISTS)
    for k, v in [("Align","Align.Center"),("Color","AppTheme.Muted"),("Font","AppFont"),
                 ("Size","AppType.Small"),("Text",'"Nothing matches that search."'),
                 ("Height","40"),("Width","ContentWidth - (Gutter * 2)"),
                 ("X","Gutter"),("Y","Gutter + 190"),("Visible",cond)]:
        prop(o, k, v, q)
    return o.getvalue()


# The generators emit classic controls; modernize.py owns the single mapping to
# their Fluent equivalents, so regenerating never silently reverts a screen.
import importlib.util as _ilu, os as _os
_spec = _ilu.spec_from_file_location(
    "modernize", _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "modernize.py"))
_mz = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mz)

def _modern(src):
    src, rep = _mz.modernize_source(src)
    for line in rep:
        print(line)
    return src


open(r"E:\Papp\tt2\scrAdmin.pa.yaml", "w", encoding="utf-8", newline="").write(_modern(gen_admin()))
print("wrote scrAdmin.pa.yaml")
