"""Generate scrEditForm.pa.yaml (and patch scrAdmin to match).

Four typed record variables - varRecCust / varRecProd / varRecInst / varRecRef -
rather than one polymorphic varAdminRecord. Power Fx infers a variable's type
from its Set() calls, and a single variable Set to records of four different
tables has no coherent type. Defaults(<table>) gives an empty record WITH a
schema, the same reason App.OnStart uses it instead of Blank().
"""

import screen_parts as P
import io, sys, importlib.util, re

import os
spec = importlib.util.spec_from_file_location(
    "g", os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_admin.py"))
# gen_admin writes a file on import; re-exec just for LISTS is fine
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
LISTS, fid = g.LISTS, g.fid

def prop(o, k, v, ind):
    # A ": " inside a Power Fx value terminates the YAML key when written
    # inline. Emit those as block scalars. See gen_onboard.py for the full note.
    if ": " in v:
        o.write(f"{ind}{k}: |\n{ind}  ={v}\n")
    else:
        o.write(f"{ind}{k}: ={v}\n")
def blk(o, k, lines, ind):
    o.write(f"{ind}{k}: |\n")
    for i, l in enumerate(lines):
        o.write(f"{ind}  {'=' if i == 0 else ''}{l}\n")
def ctrl(o, name, control, ind, variant=None):
    o.write(f"{ind}- {name}:\n{ind}    Control: {control}\n")
    if variant: o.write(f"{ind}    Variant: {variant}\n")
    o.write(f"{ind}    Properties:\n")
    return ind + "      "

def var(L): return "varRec" + L["key"]

def input_name(L, f): return {"text":"txt","note":"txt","url":"txt","choice":"dd","bool":"tgl","lookup":"dd","date":"dtp"}[f["kind"]] + fid(f) + L["key"]

# value written by Patch for one field
def patch_value(L, f):
    n, k = input_name(L, f), f["kind"]
    if k in ("text", "note", "url"): return f"{n}.Text"
    if k == "bool":                  return f"{n}.Checked"
    # SelectedDate is the date picker's output; blank when nothing is chosen,
    # which is what a never-verified record should write.
    if k == "date":                  return f"{n}.SelectedDate"
    if k == "choice":                return f"{{ Value: {n}.Selected.Value }}"
    if k == "lookup":
        # The dropdown now yields a real row from the target list, not a {Id, Value} choice
        # record, so the reference is built literally. 00_Setup.md: "Writing a lookup - build
        # the record, don't look it up."
        #
        # .Selected.ID is the list's own column; .Selected.Id would be the choice record's
        # field, which a table row does not have.
        return ("If(IsBlank(" + n + ".Selected), Blank(), "
                "{ '@odata.type': "
                '"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference", '
                "Id: " + n + ".Selected.ID, Value: " + n + ".Selected.Title })")
    raise ValueError(k)

# What the "+ New" detour writes back into the record variable.
#
# Same values as patch_value, except a lookup carries no '@odata.type'. This goes through
# Patch(record, changes) - two arguments, no data source - which merges structurally and
# rejects a record whose field set differs. patch_value's odata field is required for the
# three-argument write and fatal here.
def stash_value(L, f):
    n, k = input_name(L, f), f["kind"]
    if k == "lookup":
        return (f"If(IsBlank({n}.Selected), Blank(), "
                f"{{ Id: {n}.Selected.ID, Value: {n}.Selected.Title }})")
    return patch_value(L, f)


# Default shown in the input.
#
# These used to read If(varAdminNew, <empty>, varRec.<field>), which forced every field on a
# new record to open blank no matter what the record variable held. Reading the variable
# unconditionally is identical for a plain new record - Defaults() gives "" for text, blank
# for lookups - and it is what lets a caller open this form with context already supplied:
#
#     Set(varRecInst, Patch(Defaults(TB_Installations),
#                           { Customer: LookUp(Choices(TB_Installations.Customer),
#                                              Id = varCustomer.ID) }))
#
# arrives with the customer filled in. It also means a Choice column's own SharePoint
# default now shows up preselected, which the wrapper was suppressing.
def default_expr(L, f):
    v, n = var(L), f["n"]
    k = f["kind"]
    # Reading the record directly means a column's SharePoint default now reaches a new
    # record, where the old If(varAdminNew, ...) wrapper suppressed it. That is a fix for
    # Active and sensible for Status, but see gen_admin: one field wants the opposite and
    # says so there rather than having this function know about individual columns.
    if "new_default" in f:
        return f'If(varAdminNew, {f["new_default"]}, {v}.{n})' 
    if k in ("text", "note", "url"): return f"{v}.{n}"
    if k == "bool":                  return f"{v}.{n}"
    if k == "date":                  return f"{v}.{n}"
    if k == "choice":                return f"{v}.{n}.Value"
    if k == "lookup":                return f"{v}.{n}.Value"

def default_record_expr(L, f):
    """Preselection for a ModernDropdown, whose Default is a Record.

    A lookup is preselected by fetching the row back out of the target table by Id. A choice
    is still matched inside its own option set.

    The classic control took the display Text, so an edit could just hand it
    the stored value. A record has to be found in the same option set the
    control is showing, hence the LookUp by Value.

    On a record with nothing in the field the LookUp matches nothing and yields blank, which
    is what the old If(varAdminNew, Blank(), ...) wrapper produced by hand.
    """
    v, n = var(L), f["n"]
    if f["kind"] == "lookup":
        return f"LookUp({f['target']}, ID = {v}.{n}.Id)"
    return f"LookUp(Choices({L['source']}.{n}), Value = {v}.{n}.Value)"


def default_items_expr(L, f):
    """ComboBox preselection.

    DefaultSelectedItems takes a Table, and a SharePoint lookup projects as
    {Id, Value} -- which is not a row of the target list -- so the row has to be
    fetched back by Id rather than handed over directly.
    """
    v, n, t = var(L), f["n"], f["target"]
    return f"Filter({t}, ID = {v}.{n}.Id)"

def items_expr(L, f):
    """What a dropdown lists.

    Choice columns read Choices(); it is built for exactly that and their option sets do not
    change while the app is open. Lookups read the target table directly, because every one
    of their targets can now be added to from inside the app, and Choices() is a snapshot
    taken when the app loaded - see 00_Setup.md.
    """
    if f["kind"] == "choice":
        return f"Choices({L['source']}.{f['n']})"

    t = f["target"]
    if f.get("parent"):
        # Solutions at the chosen customer: an installation with no Parent of its own.
        # Against the table this is an ordinary Filter. It used to be an intersection
        # against Choices() - asking, per option, whether a qualifying row existed - purely
        # because a choice record carries no columns to filter on.
        cond = ("Customer.Id = ddCustomerInst.Selected.ID, IsBlank('Parent'), "
                "ID <> " + var(L) + ".ID")
    elif t == "TB_Products":
        # A model can be retired while sites still have it installed - the delete guard
        # refuses to remove it - so Active is what stops it being OFFERED.
        #
        # The second clause keeps a retired model visible on the records already using it.
        # Without it, opening such a record finds no matching option, the dropdown renders
        # blank, and saving an unrelated edit writes that blank back.
        cond = f"Active = true || ID = {var(L)}.{f['n']}.Id"
    else:
        cond = None

    inner = f"Filter({t}, {cond})" if cond else t
    return f"Sort({inner}, Title, SortOrder.Ascending)"


# ------------------------------------------------------------------ generate
o = io.StringIO()
o.write("# Generated by scripts/gen_form.py - create / edit any TB_* record.\n"
        "# Deliberately built from Classic inputs + Patch(), NOT Form + SubmitForm:\n"
        "# describe_control returns HTTP 500 for Form and DataCard, so their\n"
        "# properties cannot be verified and must not be guessed at.\n"
        "Screens:\n  scrEditForm:\n    Properties:\n      Fill: =AppDark.Bg\n"
        "      OnVisible: |\n"
        "        =Set(varConfirmDelete, false); Set(varResumeList, Blank())\n"
        "    Children:\n")
ind = "      "
p = ctrl(o, "conRootEdit", "GroupContainer", ind, "ManualLayout")
for k, v in [("Fill","AppDark.Bg"),("Height","Parent.Height"),("Width","ContentWidth"),
             ("X","Max((Parent.Width - ContentWidth) / 2, Gutter)")]: prop(o, k, v, p)
o.write(f"{p[:-2]}Children:\n"); c = p
o.write(P.brand_band("Edit", "varAdminReturn", back_transition="UnCoverRight",
               back_label="Cancel",
               back_onselect=("If(!IsBlank(varResumeList), "
                              "Set(varAdminList, varResumeList); "
                              "Set(varAdminNew, varResumeNew); "
                              "Set(varResumeList, Blank()), "
                              "Navigate(varAdminReturn, "
                              "ScreenTransition.UnCoverRight))")) + "\n")

# The back button comes from the brand band above; a second one here collided with it
# as a duplicate control name.

q = ctrl(o, "lblTitleEdit", "Label", c)
title = ('If(varAdminNew, "New ", "Edit ") & Switch(varAdminList, '
         + ", ".join(f'"{L["key"]}", "{L["singular"]}"' for L in LISTS) + ', "record")')
for k, v in [("Color","AppDark.Fg"),("Font","AppFont"),("FontWeight","FontWeight.Bold"),
             ("Height","36"),("Size","AppType.Title"),("Text",title),("Wrap","false"),
             ("AutoHeight","false"),("Width","ContentWidth - (Gutter * 2)"),
             ("X","Gutter"),("Y","56 + Gutter + 34")]: prop(o, k, v, q)

# ---- fields, grouped per list, only the selected list visible
for L in LISTS:
    y = 120
    vis = f'varAdminList = "{L["key"]}"'
    for f in L["fields"]:
        nm, k = input_name(L, f), f["kind"]
        cap = ctrl(o, "lblCap" + fid(f) + L["key"], "Label", c)
        for kk, vv in [("Text",f'"{f["caption"]}"'),("Color","AppDark.Muted"),
                       ("Font","AppFont"),("Size","AppType.Small"),
                       ("FontWeight","FontWeight.Semibold"),("Wrap","false"),
                       ("AutoHeight","false"),("Height","18"),
                       ("Width","ContentWidth - (Gutter * 2)"),("X","Gutter"),
                       ("Y",str(y)),("Visible",vis)]: prop(o, kk, vv, cap)
        # The date picker is taller than a text input; setting h here means the shared
        # advance at the bottom of the loop handles it, rather than the branch keeping
        # its own copy of the same arithmetic.
        h = 64 if k == "note" else (44 if k == "date" else 40)
        if k == "date":
            # Properties per learn.microsoft.com .../modern-controls/modern-control-date-picker
            # (note the SINGULAR "modern-control-"; a near-identical "modern-controls-"
            # page exists, is older, and does not list DefaultDate - a review flagged this
            # property as invented on the strength of that page):
            #
            #   DefaultDate   "the initial date selected in the control before the user
            #                 makes a change", listed under General and again under Recent
            #                 updates as a new property. NOT the bare `Default` the other
            #                 modern inputs here use.
            #   SelectedDate  the output, read by patch_value.
            #   Format        "accepts DatePickerFormat enum values" - the enum type name
            #                 is stated there, so DatePickerFormat.LongAbbreviated is safe.
            #   Placeholder   spelled that way under General, matching this app's other
            #                 modern inputs.
            #   Color/Size    replaced FontColor/FontSize in the updated control.
            #
            # Fill is NOT in that documentation. It is written anyway because ModernDropdown
            # takes it and the two controls are documented together for every other styling
            # property. If the compiler rejects it, deleting it costs nothing visually: the
            # ink is dark and the theme's own surface is light, which is the whole reason
            # this control is in the light-field family.
            i = ctrl(o, nm, "ModernDatePicker", c)
            for kk, vv in [("DefaultDate", default_expr(L,f)),
                           ("Placeholder", '"Not verified"'),
                           ("Format", "DatePickerFormat.LongAbbreviated"),
                           ("Font","AppFont"),("Size","AppType.Body"),
                           # Same family as ModernDropdown: the modern theme paints the
                           # surface light and ignores Fill, so this wants dark ink on a
                           # light field. The AppDark pair is written here and rewritten to
                           # that light pair by fix_dark_defaults, which owns the rule for
                           # every modern picker. Writing the literals here instead put the
                           # same property on the control twice.
                           ("Color","AppDark.Fg"),("Fill","AppDark.Surface"),
                           ("BorderColor","AppDark.Line"),("BorderThickness","1"),
                           ("Height","44"),("Width","ContentWidth - (Gutter * 2)"),
                           # y+18 clears the caption, as every other branch does. At y the
                           # picker's opaque surface covered its own label and the field
                           # shipped looking unlabelled.
                           #
                           # No Radius: 00_Setup.md's confirmed radius list does not include
                           # this control, and Rectangle rejects those same properties with
                           # PA2108. Square corners are cheaper than a failed paste.
                           ("X","Gutter"),("Y",str(y+18)),("Visible",vis)]:
                prop(o, kk, vv, i)
        elif k in ("text","note","url"):
            i = ctrl(o, nm, "Classic/TextInput", c)
            for kk, vv in [("Default",default_expr(L,f)),("Mode",
                            "TextMode.MultiLine" if k=="note" else "TextMode.SingleLine"),
                           ("HintText",'""'),("BorderColor","AppDark.Line"),
                           ("BorderThickness","1"),("Color","AppDark.Fg"),
                           ("Fill","AppDark.Surface"),("Font","AppFont"),
                           ("Size","AppType.Body"),("Height",str(h)),
                           ("Width","ContentWidth - (Gutter * 2)"),("X","Gutter"),
                           ("Y",str(y+18)),("Visible",vis),
                           ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                           ("RadiusBottomLeft","6"),("RadiusBottomRight","6")]: prop(o, kk, vv, i)
        elif k == "bool":
            # TrueFill / FalseFill do not exist on ModernToggle - the theme
            # paints it. Its output is Checked, which patch_value() reads.
            i = ctrl(o, nm, "ModernToggle", c)
            for kk, vv in [("Default",default_expr(L,f)),("Font","AppFont"),
                           ("Size","AppType.Body"),("Height","36"),("Width","110"),
                           ("X","Gutter"),("Y",str(y+18)),("Visible",vis)]: prop(o, kk, vv, i)
            h = 36
        elif k == "choice":
            i = ctrl(o, nm, "ModernDropdown", c)
            o.write(f"{i}Items: |\n{i}  ={items_expr(L,f)}\n")
            for kk, vv in [("Default",default_record_expr(L,f)),
                           ("ItemDisplayText","ThisItem.Value"),
                           ("BorderColor","AppDark.Line"),("BorderThickness","1"),
                           ("Color","AppDark.Fg"),("Fill","AppDark.Surface"),
                           ("Font","AppFont"),("Size","AppType.Body"),("Height","40"),
                           ("Width","ContentWidth - (Gutter * 2)"),("X","Gutter"),
                           ("Y",str(y+18)),("Visible",vis)]: prop(o, kk, vv, i)
        else:
            # Lookups use a Drop down with an explicit Value column.
            #
            # Per the Drop down control reference: "Items - The source of data
            # that contains the items that appear in the control. If the source
            # has multiple columns, set the control's Value property to the
            # column of data that you want to show." A SharePoint list is always
            # multi-column, so without Value the control has no display column
            # and renders an empty list.
            #
            # Note describe_control does not return Value among Classic/DropDown's
            # input properties, though the documentation lists it as a key one.
            #
            # ComboBox was tried and abandoned: Studio seeds it with a SearchItems
            # default of Search(ComboBoxSample, ..., "Value1"), a sample source
            # that does not exist here, and that property cannot be overridden
            # from YAML ("Unknown property 'SearchItems'"). IsSearchable: =false
            # does not stop it being evaluated either.
            i = ctrl(o, nm, "ModernDropdown", c)
            o.write(f"{i}Items: |\n{i}  ={items_expr(L,f)}\n")
            # A model dropdown makes room for the "+ New" button beside it, but only for an
            # admin - a technician never sees the button and the field keeps its full width.
            model = f.get("target") == "TB_Products"
            dw = ("ContentWidth - (Gutter * 2) - If(varIsAdmin, 96, 0)" if model
                  else "ContentWidth - (Gutter * 2)")
            for kk, vv in [("Default",default_record_expr(L,f)),
                           ("ItemDisplayText","ThisItem.Title"),
                           ("BorderColor","AppDark.Line"),("BorderThickness","1"),
                           ("Color","AppDark.Fg"),("Fill","AppDark.Surface"),
                           ("Font","AppFont"),("Size","AppType.Body"),("Height","40"),
                           ("Width",dw),("X","Gutter"),
                           ("Y",str(y+18)),("Visible",vis)]: prop(o, kk, vv, i)
            if model:
                # Write what is on screen back into the record variable before detouring.
                # The form's defaults read that variable, so returning repopulates the
                # fields with no further work - and nothing the admin typed is lost.
                stash = ", ".join(f"{g['n']}: {stash_value(L, g)}" for g in L["fields"])
                b = ctrl(o, "btnNew" + fid(f) + L["key"], "ModernButton", c)
                go = (f"Set({var(L)}, Patch({var(L)}, {{ {stash} }})); "
                      f'Set(varResumeList, "{L["key"]}"); '
                      "Set(varResumeNew, varAdminNew); "
                      f'Set(varResumeField, "{fid(f)}"); '
                      "Set(varRecProd, Defaults(TB_Products)); "
                      'Set(varAdminList, "Prod"); '
                      "Set(varAdminNew, true)")
                for kk, vv in [("Appearance","ButtonAppearance.Outline"),
                               ("Text",'"+ New"'),("Font","AppFont"),
                               ("Size","AppType.Body"),("FontWeight","FontWeight.Semibold"),
                               ("Color","AppDark.Accent"),("BorderColor","AppDark.Line"),
                               ("BorderThickness","1"),("Height","40"),("Width","88"),
                               ("X","Gutter + ContentWidth - (Gutter * 2) - 88"),
                               ("Y",str(y+18)),
                               ("Visible",f"{vis} && varIsAdmin"),
                               ("RadiusTopLeft","6"),("RadiusTopRight","6"),
                               ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
                               ("OnSelect",go)]: prop(o, kk, vv, b)
        y += 18 + h + 14

# ---- save
# Handed back into a record variable by Patch(record, changes), so the plain lookup shape -
# the odata field belongs only on the three-argument write. See stash_value.
REF = "{ Id: varSaved.ID, Value: varSaved.Title }"

q = ctrl(o, "btnSaveEdit", "Classic/Button", c)
lines = ["IfError("]
for idx, L in enumerate(LISTS):
    # each assignment must be its own entry: blk() prefixes per line, so a
    # multi-line string here would leave later lines under-indented and
    # silently terminate the YAML block scalar.
    fl = [f"                {f['n']}: {patch_value(L, f)}" for f in L["fields"]]
    fl = [x + ("," if i < len(fl) - 1 else "") for i, x in enumerate(fl)]
    lines += [f'    If(varAdminList = "{L["key"]}",',
              f"        Set(varSaved, Patch({L['source']},",
              f"            If(varAdminNew, Defaults({L['source']}), {var(L)}),",
              "            {"] + fl + [
              "            }",
              "        ))",
              "    );"]
# Saving the model created on a detour hands it back to the field that asked for it, and
# the form returns to that list rather than leaving. One clause per model field: a Switch
# would need every branch to be the same record type, and they are not.
resume = "; ".join(
    f'If(varResumeList = "{L["key"]}" && varResumeField = "{fid(f)}", '
    f"Set({var(L)}, Patch({var(L)}, {{ {f['n']}: " + REF + " })))"
    for L in LISTS for f in L["fields"] if f.get("target") == "TB_Products")
resume += ("; Set(varAdminList, varResumeList); Set(varAdminNew, varResumeNew); "
           "Set(varResumeList, Blank())")

# A new machine arrives with its model's standard build.
#
# The design called for a ticked list on the form. The form has no room for one: its
# deepest list already reaches 754px against a Save button pinned to the bottom of the
# screen, so a 160px gallery would land behind it on any laptop. The standard build is the
# usual case by definition, the units appear on the machine's own screen immediately, and
# removing one costs a tap - so this creates them and says so, rather than asking.
#
# "As SU" names the outer row: TB_Installations has its own Product and Customer, which
# would otherwise shadow the ones being read from TB_SolutionUnits.
STD = "Filter(TB_SolutionUnits, Solution.Id = varSaved.Product.Id, Standard = true)"


def _ref(id_expr, title_expr):
    return ("{ '@odata.type': " + SP_REF_LITERAL + ", "
            + "Id: " + id_expr + ", Value: " + title_expr + " }")


SP_REF_LITERAL = '"#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference"'

build = " ".join([
    'If(varAdminList = "Inst" && varAdminNew && IsBlank(varSaved.' + "'Parent'" + "),",
    "    ForAll(" + STD + " As SU,",
    "        Patch(TB_Installations, Defaults(TB_Installations), {",
    '            Title: varSaved.Customer.Value & " - " & SU.Unit.Value,',
    "            Customer: " + _ref("varSaved.Customer.Id", "varSaved.Customer.Value") + ",",
    "            Product: " + _ref("SU.Unit.Id", "SU.Unit.Value") + ",",
    "            " + "'Parent': " + _ref("varSaved.ID", "varSaved.Title") + ",",
    '            Status: { Value: "In Service" }',
    "        })",
    "    );",
    "    If(CountRows(" + STD + ") > 0,",
    '        Notify("Added " & varSaved.Title & " with " & CountRows(' + STD + ")",
    '               & " standard unit(s).", NotificationType.Success))',
    ");",
])

lines += ["    " + build.strip(),
          '    Set(varEditError, "");',
          "    If(!IsBlank(varResumeList),",
          "        " + resume + ",",
          "        Navigate(varAdminReturn, ScreenTransition.UnCoverRight)",
          "    ),",
          "    Set(varEditError, FirstError.Message)",
          ")"]
blk(o, "OnSelect", lines, q)
for k, v in [("Font","AppFont"),("Size","AppType.Body"),("FontWeight","FontWeight.Semibold"),
             ("Text",'"Save"'),("Fill","AppDark.Accent"),("Color","AppDark.OnBrand"),
             ("HoverFill","AppDark.AccentSolid"),("BorderThickness","0"),
             ("Height","44"),("Width","160"),("X","Gutter"),
             ("Y","Parent.Height - Gutter - 44"),
             ("RadiusTopLeft","6"),("RadiusTopRight","6"),
             ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
             ("FocusedBorderThickness","2"),("FocusedBorderColor","AppDark.Accent")]: prop(o, k, v, q)

# ---- delete
# Only for an existing record, and only when nothing points at it. SharePoint
# lookups do not cascade: deleting a product referenced by an installation
# leaves that installation with a required column pointing at nothing, which is
# worse than refusing.
# One line. prop() writes a value inline, and an embedded newline ends the YAML
# key early - the same trap as an inline ": ", and it fails the same way, with a
# parse error hundreds of lines from the cause. Long but generated, not read.
DEPS = "Switch(varAdminList, " + ", ".join(
    f'"{L["key"]}", {L["deps"]}' for L in LISTS if L.get("deps")) + ", 0)"
DEPSLABEL = 'Switch(varAdminList, ' + ", ".join(
    f'"{L["key"]}", "{L["depsLabel"]}"' for L in LISTS if L.get("deps")) + ', "")'

q = ctrl(o, "lblDeleteBlocked", "Label", c)
blocked = (f'"Cannot delete: " & ({DEPS}) & " " & ({DEPSLABEL}) & '
           '" still reference this. Remove those first."')
for k, v in [("Text",blocked),("Color","AppDark.Danger"),("Font","AppFont"),
             ("Size","AppType.Small"),("Wrap","true"),("AutoHeight","false"),
             ("Align","Align.Right"),("Height","36"),
             ("Width","ContentWidth - (Gutter * 2) - 360"),
             ("X","Gutter + 360"),("Y","Parent.Height - Gutter - 88"),
             ("Visible",f"!varAdminNew && ({DEPS}) > 0")]: prop(o, k, v, q)

q = ctrl(o, "btnDeleteEdit", "Classic/Button", c)
# Notify rather than a label. A delete either happens or it does not, and the
# first version reported failure into lblEditError, which sits along the bottom
# where these buttons now are - so a real error could render behind them and
# look like nothing happening at all.
#
# Refresh after Remove because the gallery on scrAdmin reads a filtered view of
# the same source, and without it the row can survive the trip back.
blk(o, "OnSelect", [
    "If(!varConfirmDelete,",
    "    Set(varConfirmDelete, true),",
    "    IfError(",
    "        Switch(varAdminList,"] + [
    f'            "{L["key"]}", Remove({L["source"]}, {var(L)}); Refresh({L["source"]}),'
    for L in LISTS] + [
    "            Notify(\"Nothing was selected to delete.\", NotificationType.Error)",
    "        );",
    '        Set(varConfirmDelete, false);',
    '        Notify("Deleted.", NotificationType.Success);',
    "        Navigate(varAdminReturn, ScreenTransition.UnCoverRight),",
    '        Notify("Could not delete: " & FirstError.Message, NotificationType.Error);',
    "        Set(varConfirmDelete, false)",
    "    )",
    ")"], q)
for k, v in [("Font","AppFont"),("Size","AppType.Body"),("FontWeight","FontWeight.Semibold"),
             ("Text",'If(varConfirmDelete, "Confirm delete", "Delete")'),
             # No Fill or Color here. ModernButton has no Fill, so the conversion
             # drops it - but Color survives, and a Color that only made sense
             # against the dropped Fill left white text on a light button.
             # Appearance and BasePaletteColor carry both states instead; see
             # EXTRA in scripts/modernize.py.
             ("BorderThickness","1"),
             ("Height","44"),("Width","170"),
             ("X","ContentWidth - Gutter - 170"),
             ("Y","Parent.Height - Gutter - 44"),
             ("RadiusTopLeft","6"),("RadiusTopRight","6"),
             ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
             ("Visible",f"!varAdminNew && ({DEPS}) = 0"),
             ("FocusedBorderThickness","2"),
             ("FocusedBorderColor","AppDark.Danger")]: prop(o, k, v, q)

q = ctrl(o, "btnCancelDelete", "Classic/Button", c)
for k, v in [("Font","AppFont"),("Size","AppType.Small"),("Text",'"Cancel"'),
             ("Fill","AppDark.Surface"),("Color","AppDark.Fg"),
             ("HoverFill","AppDark.Sunken"),
             ("BorderColor","AppDark.Line"),("BorderThickness","1"),
             ("Height","44"),("Width","110"),
             ("X","ContentWidth - Gutter - 170 - 8 - 110"),
             ("Y","Parent.Height - Gutter - 44"),
             ("RadiusTopLeft","6"),("RadiusTopRight","6"),
             ("RadiusBottomLeft","6"),("RadiusBottomRight","6"),
             ("OnSelect","Set(varConfirmDelete, false)"),
             ("Visible","varConfirmDelete")]: prop(o, k, v, q)

q = ctrl(o, "lblEditError", "Label", c)
# AppTheme on this branch has Warn / WarnLight but no Danger slot, so the
# save-failure message uses an explicit error red rather than an amber.
for k, v in [("Text","varEditError"),("Color","AppDark.Danger"),("Font","AppFont"),
             ("Size","AppType.Small"),("Wrap","true"),("AutoHeight","false"),
             ("Height","44"),("Width","ContentWidth - (Gutter * 2) - 176"),
             ("X","Gutter + 176"),("Y","Parent.Height - Gutter - 44"),
             ("Visible","!IsBlank(varEditError)")]: prop(o, k, v, q)


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


open(r"E:\Papp\powerappgoofing\app\screens\scrEditForm.pa.yaml", "w", encoding="utf-8", newline="").write(_modern(o.getvalue()))
print("wrote scrEditForm.pa.yaml")
