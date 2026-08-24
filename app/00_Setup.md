# Step 0 — Studio setup, before any paste

**Settings → Display:** turn OFF *Scale to fit*, *Lock aspect ratio* and *Lock orientation*.
Without this, no amount of formula work makes the app responsive.

**Data → Add data**, connect all four in this order:

1. `TB_Customers`
2. `TB_Products`
3. `TB_Installations`
4. `TB_References`

Site: `https://gloryglobal.sharepoint.com/sites/techtips/toolbox`

**Settings → General → Data row limit:** raise to **2000**. Filtering on a lookup's `.Id`
is not delegable against SharePoint, so the client must be able to pull the whole set.

## Pushing screens: one push per screen, and never over an existing one

This is the most expensive thing in this file. It cost a full day to find, it is invisible
to every validator, and nothing in Microsoft's documentation mentions it.

**Overwriting an existing screen through a coauthoring push corrupts that screen.** Creating a
screen that did not exist before is clean. The corrupted screen renders its galleries empty and
Studio shows a red banner reading:

```
The named object '19' could not be found in the runtime.
```

The number varies — `15`, `19`, `185` were all observed — and it is an internal object id, not
anything you will find in your YAML. Orphaned objects are left behind when a screen is replaced
in place rather than created.

### How it was proven

`scrCustomers` had been pushed roughly six times while diagnostics were added and removed. It
showed the banner and an empty gallery. The same file was copied to `scrCustomersFresh`, every
control renamed with an `F` suffix so the names stayed unique, and pushed **once**. Both screens
then sat side by side in the same app, with identical logic against identical data:

| Screen | Times pushed | Result |
|---|---|---|
| `scrCustomers` | ~6 | empty gallery, `'19'` banner |
| `scrCustomersFresh` | 1 | four customer cards, no error |

Every screen that has ever worked in this app was created once. Every screen that showed the
banner had been overwritten. A throwaway probe screen and a diagnostic screen, both pushed once,
never errored.

### A compile mirrors the directory

`compile_canvas` is a **mirror**, not a merge. Screens present in the directory are written;
**screens absent from it are deleted from the app.** Pushing a directory containing one screen
does not update that screen and leave the rest alone — it deletes every other screen in the app.

Confirmed the hard way: a directory holding only `scrCustomers.pa.yaml` was compiled against an
app with six screens. Afterwards `sync_canvas` returned three files, and `_EditorState` read:

```yaml
EditorState:
  ScreensOrder:
    - scrCustomers
```

The other five were gone. This is the same behaviour `sync_canvas` has in the opposite direction,
and it is easy to reason about the read path while forgetting the write path.

### The rule

These two facts together — a push mirrors the directory, and overwriting a screen corrupts it —
leave exactly one safe procedure:

1. **Delete every screen** in Studio's Tree view. (Add a blank screen first if Studio will not
   leave the app empty; the push mirrors it away.)
2. **Push the complete set** of screens in a single compile, so all of them are fresh creations.
3. **Verify with `sync_canvas`** that the control counts match what you pushed.

There is no incremental single-screen path. Do not go looking for one; it was tested and it
deletes the rest of the app.

The practical consequence is that a deployment cycle is all-or-nothing, which suits batching
several changes together and suits rapid visual iteration badly. Budget accordingly.

### Two related mechanics, both of which mimic this bug

**The Studio tab must be open, with coauthoring on, at the moment you compile.** `compile_canvas`
validates against the authoring service *and separately* applies changes through the live
coauthoring session. With the tab closed, validation passes, `0 errors` is reported, warnings come
back naming controls in your files — and **nothing is written to the app**. You then look at older
content and reasonably conclude the push broke something.

**Always verify with `sync_canvas` after a push.** It reads back what the server actually holds,
which is the only trustworthy answer to "did that land?". Checking control counts per screen takes
seconds and catches a silently-discarded push immediately:

```
sync_canvas <a scratch directory>      # server -> local, overwrites that directory
grep -c '^\s*Control:' scr*.pa.yaml    # compare against what you pushed
```

`sync_canvas` **replaces the target directory**; it does not merge. Never point it at a directory
holding work that is not also in git.

### Why this wasted so much time

An empty gallery is produced by all three of these, and they are visually identical:

1. a genuine formula bug,
2. a push that never landed because the tab was closed,
3. a screen corrupted by being overwritten.

Only the first is in the YAML, and it is the only one any validator can see. `compile_canvas`
reported `0 errors`, `scripts/verify_yaml.py` reported `0 findings`, and the SharePoint data was
correct — all true, all simultaneously, while the screen showed nothing.

**When a screen renders blank, instrument it before reading it.** Drop a Label on the screen whose
`Text` prints the intermediate values, and push once:

```powerfx
="all=" & CountRows(TB_Customers)
  & "  filtered=" & CountRows(Filter(TB_Customers, Active = true))
  & "  sorted=" & CountRows(SortByColumns(Filter(TB_Customers, Active = true), "Title", SortOrder.Ascending))
  & "  galAll=" & CountRows(galCustomers.AllItems)
```

That single label eliminated five suspects in one round trip and localised the fault to the gap
between a formula returning four rows and the gallery holding none — which is what pointed at the
deployment mechanism rather than the code. Reading YAML cannot do this; the values are only
observable at runtime.

## Three sources of truth, none complete

`describe_control`, the Power Apps documentation, and the YAML compiler each know
a different subset of what a control supports. Confirmed against the live
environment on 2026-08-21 while building the admin forms:

| Property | describe_control | Documentation | YAML compiler |
|---|---|---|---|
| `Classic/DropDown.Value` | not listed | "a key property" | `Unknown property` |
| `Classic/ComboBox.SearchItems` | not listed | not covered | `Unknown property`, yet reports errors *against* it |

`SearchItems` is the sharper trap. Studio seeds every new `Classic/ComboBox` with
a default of `Search(ComboBoxSample, ..., "Value1")` -- a sample data source that
does not exist in this app -- so five ComboBoxes produced fifteen errors about a
property none of them set. It cannot be overridden from YAML, and
`IsSearchable: =false` does not stop it being evaluated. **`Classic/ComboBox` is
therefore unusable through this pipeline**, however well it fits the job.

### Lookup dropdowns must use `Choices()`

Because `Value` cannot be set, the display column has to come from the shape of
`Items` itself. A raw SharePoint table has no designated display column, so a
Drop down bound to `Sort(TB_Customers, Title, SortOrder.Ascending)` renders an
empty list. The documented form is:

```powerfx
Choices(TB_Installations.Customer)
```

`Choices()` returns a table already shaped for that lookup. It also removes the
need to hand-build the write: its records are exactly what the lookup accepts, so
`Patch` takes `.Selected` directly rather than a
`'@odata.type': "#...SPListExpandedReference"` literal.

To scope such a dropdown, note that `Choices()` carries only `{Id, Value}` --
no other columns to filter on. Ask per option whether a qualifying row exists,
naming the outer scope so its `Id` is not shadowed:

```powerfx
Filter(Choices(TB_Installations.'Parent') As Opt,
       CountRows(Filter(TB_Installations,
                        ID = Opt.Id,
                        Customer.Id = ddCustomerInst.Selected.Id,
                        IsBlank('Parent'))) > 0)
```

`ShowColumns(..., "ID")` was tried first and rejected with *"Expected identifier
name"*. **`As` works here** and is verified at runtime, despite the previous
generation of this app having banned it.

## Control property support, confirmed against Studio

Studio's paste validator rejects `RadiusTopLeft` / `RadiusTopRight` / `RadiusBottomLeft` /
`RadiusBottomRight` on `Rectangle` and `GroupContainer` with `PA2108: Unknown property`. Corner
radius is supported only on `Classic/Button` and `Classic/TextInput`, which is why the archived kit
used it exclusively on those two.

Cards and panels in these screens are therefore **square-cornered**. If the flat look matters, the
fix is to rebuild a card background as a `Classic/Button` with `DisplayMode: =DisplayMode.View`,
which accepts radius and does not respond to taps. Do not put radius back on a `Rectangle`.

## Choice columns are records, not scalars

Every SharePoint Choice column (`Product Type`, `Family`, `Status`, `Section`, `Reference Type`)
must be read as `.Value`. Using one bare — concatenating it with `&`, or comparing it — gives
*"Invalid argument type. Expecting one of the following: Text, Number, ... ViewValue"*.

The same applies to sorting: **`SortByColumns` cannot sort on a Choice column at all.** It accepts
only primitive columns. The document galleries therefore sort by `Featured` alone and the catalogue
by `Title` alone, rather than the three-key order the design describes. To restore the full order,
use nested `Sort()` calls, which take an expression and so can reach `.Value`:
`Sort(Sort(tbl, 'Reference Type'.Value), Featured, SortOrder.Descending)` — innermost key applies
last. Untested against Studio.

`scripts/verify_yaml.py` now catches both mistakes.

## Every control in a gallery template needs `OnSelect: =Select(Parent)`

Controls inside a gallery's row template do **not** pass their clicks up to the gallery. Without
`Select(Parent)` the row shows, but does not highlight on hover and does not respond to a tap, and
`Gallery.OnSelect` never fires. There is no error - the screen simply looks finished and does
nothing.

This is not a workaround. Insert a blank vertical gallery in Studio and read its Code view: every
child Studio generates - labels, images, icons, rectangles - carries `OnSelect: =Select(Parent)`.

It applies to labels too, not only to shapes. A nested gallery keeps its own `OnSelect`; only leaf
controls forward to the parent.

## Testing whether a SharePoint lookup is empty

Use `Column = Blank()`, comparing the column itself:

```powerfx
Filter(TB_Installations, Customer.Id = varCustomer.ID, Parent = Blank())
```

Microsoft's SharePoint delegation notes state it directly: *"A filter using `IsBlank(CustomerId)`
will not delegate to SharePoint. However, `Filter(..., CustomerId = Blank())` will delegate."* So
the comparison form is both correct and delegable, where `IsBlank` is neither.

Do **not** reach into the lookup - `IsBlank(Parent.Value)`, `Parent.Id = 0` and similar are guesses
about how an empty lookup is represented, they vary by how the item was written, and reading `.Id`
off a blank lookup can poison the whole expression so the filter silently returns nothing.

This matters twice over. `Parent` is what distinguishes a solution from a unit - get it wrong and a
customer appears to run nothing at all. And a blank `Customer` is what makes a reference universal -
get it wrong and every document disappears.

> **Correction, confirmed against the tenant on 2026-08-21.** The `Column = Blank()` form above
> **does not compile**. The authoring service rejects it:
>
> ```
> Incompatible types for comparison. These types can't be compared: Record, Blank.
> ```
>
> A SharePoint lookup projects as a Record, and a Record cannot be compared to Blank. Microsoft's
> delegation note quoted above is about a scalar `<Name>Id` field, which this connector does not
> surface here.
>
> Use **`IsBlank(Column)`** — testing the column itself, never a projection off it:
>
> ```powerfx
> Filter(TB_Installations, Customer.Id = varCustomer.ID, IsBlank('Parent'))
> Filter(TB_References, Product.Id = ThisItem.ID, IsBlank(Customer))
> ```
>
> This keeps the principle the section is really about — do not reach into a blank lookup — while
> satisfying the type checker. The cost is that these filters are no longer delegable, which is
> immaterial at 10 installations and 21 references but would matter past 500 rows.
>
> Note the trap: `IsBlank(Parent.Value)` and `IsBlank(Customer.Id)` both compile cleanly and both
> silently return nothing. Compiling is not evidence of correctness here.

## Responsive layout: how to test it, and how to not break it

**The Studio authoring canvas does not respond to sizing formulas.** Microsoft's documentation says
so directly: to test responsive behaviour, save and publish the app, then open it in browser windows
of different sizes or on a real device. Resizing inside the editor shows nothing moving, however
correct the formulas are - which reads exactly like a broken layout.

**Dragging a control in the editor overwrites its `X`, `Y`, `Width` and `Height` formulas with
constants.** A screen laid out by formula must be adjusted by editing formulas, never by dragging.
This is the most common way a responsive app quietly becomes a fixed one, and nothing warns you.

Layout decisions use `Screen.Size` against the `ScreenSize` constants - `Small` (phone), `Medium`
(tablet portrait), `Large` (tablet landscape), `ExtraLarge` (desktop) - rather than raw pixel
comparisons. `Screen.Size` is derived from `App.SizeBreakpoints`, set explicitly to the platform
default `[600, 900, 1200]` in `01_App_Properties.md`, so changing that one table moves every layout
decision in the app at once.

Also required, and set in step 0 above: **Scale to fit off.** With it on, the app renders at a fixed
design size and scales to fit, so `App.Width` never changes and no responsive formula can fire.

## Label text: `Wrap` and `AutoHeight` are not optional

Microsoft's Label reference: **`AutoHeight` false truncates the text to the assigned height**, and
that is the default. `Wrap` decides whether text flows onto a second line. Leave both unset and a
label silently clips - and it only shows up once something makes the control narrower, such as a
gallery with more than one column.

Every data-bound label in a gallery template therefore states both explicitly:

- One-line identifiers - titles, types, versions, status - use `Wrap: =false`. They end at the edge
  rather than wrapping into a second line that the fixed height then cuts in half.
- Descriptions use `Wrap: =true` with a height sized for two lines.

`WrapCount` on a gallery divides the gallery's width, so `Parent.TemplateWidth` shrinks in
proportion. Multi-column lists therefore need a card wide enough for their longest realistic
content, not just a column count that looks good on a wide monitor. The thresholds here start at
`ScreenSize.Large` rather than `Medium` for exactly that reason.

## Make the whole gallery item clickable

From Microsoft's Gallery reference: *"If clicking anywhere in a gallery item should select it...
adding a Button control with its OnSelect property set to `Select(Parent)`."*

The important part is **where** that button sits. A button behind the labels only receives clicks
on the margins the labels do not cover, so a row appears to need a precisely aimed click. The hit
target must be the **last child in the template**, on top of everything, with a transparent `Fill`.

Every gallery here therefore ends with a `<gallery>Hit` button: full template width and height,
`Fill: =RGBA(0, 0, 0, 0)`, and translucent `HoverFill` and `PressedFill` so it carries the feedback
as well as the hit area.

One constraint: a hit target must never cover a **nested** gallery, or it blocks the inner rows the
way the labels were blocking the outer ones. `galSolutions`' hit target is height-limited to 100 so
it stops above the units gallery inside it.

## `PA1001 ... Property 'X' not found on type 'ControlInstance'`

This means a property key landed on the control node instead of inside its `Properties:` block -
level with `Properties:` rather than indented under it. The file is still valid YAML, so nothing
catches it until Studio refuses the paste.

The nesting Studio expects, with the indents this kit uses:

```yaml
- btnExample:            # control node
    Control: Classic/Button
    Properties:          # + 4 from the control node
      OnSelect: =Select(Parent)   # + 2 from Properties
```

`scripts/verify_yaml.py` now checks this.

## `Parent` is a reserved word, and one of our columns is called Parent

In Power Fx `Parent` means the **parent control** - `Parent.Width`, `Parent.TemplateWidth`. The
`Parent` column on `TB_Installations` collides with it. Inside a record scope such as
`Filter(TB_Installations, ...)`, an unqualified `Parent` resolves to the *control*, which has no
`.Value` or `.Id`, so the expression errors.

The failure gives you nothing to work with: **the control renders blank.** No error banner, no red
marker at runtime. A gallery shows no rows and a label shows no text, including its literal strings.

Always qualify it:

```powerfx
Filter(TB_Installations, Customer.Id = varCustomer.ID, IsBlank(ThisRecord.Parent.Value))
Filter(TB_Installations, ThisRecord.Parent.Id = varInstallation.ID)
```

`varInstallation.Parent.Id` needs no qualification - a variable is not a record scope, so nothing
collides there.

**Worth fixing at the source.** Renaming the SharePoint column from `Parent` to something like
`Parent Solution` removes the trap permanently. It means updating the column in SharePoint,
`Create-ToolboxLists.ps1`, the seed CSVs and importer, and every formula above - but a reserved
word as a column name will keep catching people.

`scripts/verify_yaml.py` now flags any unqualified use.

## A nested LookUp cannot see the outer row by bare column name

`LookUp` opens its own record scope. Inside
`Filter(TB_Installations, ..., LookUp(TB_Products, ID = Product.Id)...)` the innermost scope is
`TB_Products`, which has no `Product` column, so the bare reference to the outer row fails with
*"Name isn't valid. 'Product' isn't recognized."*

The documented disambiguation for a nested record scope is `Table[@FieldName]`:

```powerfx
Filter(
    TB_Installations,
    Status.Value <> "Retired",
    'Installed Version' <> LookUp(TB_Products, ID = TB_Installations[@Product].Id).'Current Standard Version'
)
```

`ThisRecord` does not help here - it also refers to the innermost scope. The `@` operator is what
reaches outward.

Note the distinction from `ThisItem.Product.Id`, which is fine: `ThisItem` is a gallery row, not a
record scope, so nothing shadows it.

This is the same trap recorded in `tasks/lessons.md` from the previous generation, where a nested
`LookUp` reaching the outer row implicitly produced three consecutive failed pastes.


## Reading a gallery's rows back out with `ForAll`

Ticking checkboxes in a gallery and then writing one record per ticked row is the
documented bulk pattern, but it has one rule that is easy to get wrong:

> The disambiguation operator can't be used on the Gallery's items. Instead, you can store a
> label within the gallery and reference it for comparison.
>
> -- [Create or update bulk records](https://learn.microsoft.com/power-apps/maker/canvas-apps/create-update-records-bulk)

So this does **not** work, even though `As` is fine everywhere else:

```powerfx
ForAll(Filter(galComponents.AllItems, chkPick.Value = true) As Row,
    Patch(TB_Installations, Defaults(TB_Installations), { Title: Row.Title })
)
```

Inside the `ForAll` scope you address the template's controls **by name**, and any value you
need from the underlying row has to be parked in a control first:

```powerfx
ForAll(Filter(galComponents.AllItems, chkPick.Value = true),
    Patch(TB_Installations, Defaults(TB_Installations),
        {
            Title: varCust.Title & " - " & lblCompName.Text,
            Product: LookUp(Choices(TB_Installations.Product), Id = Value(lblCompId.Text))
        }
    )
)
```

`lblCompId` and `lblCompName` are 1x1 `Visible: =false` labels in the template holding
`ThisItem.ID` and `ThisItem.Title`. Labels stringify, so a numeric key needs `Value()` on the
way back. `scrOnboard`'s step 3 is built this way.

## Clearing controls that live inside a gallery

`Reset(control)` cannot reach into a gallery:

> You cannot reset controls that are within a **Gallery** or **Edit form** control from outside
> those controls. [...] Toggling the **Reset** property can be done [...] from a variable with
> `Reset = MyVar` and toggling `MyVar` with the formula
> `Button.OnSelect = Set( MyVar, true ); Set( MyVar, false )`.
>
> -- [Reset function](https://learn.microsoft.com/power-platform/power-fx/reference/function-reset)

`Reset(Gallery)` is not the answer either - it rewinds the gallery's own selection and scroll,
and the docs are explicit that it "does not recursively reset all the children".

So every control in the template that needs clearing binds `Reset: =varSomethingReset`, and the
button that consumed their values ends with `Set(varSomethingReset, true); Set(varSomethingReset, false)`.
The pair runs in one behaviour formula and the controls still observe the transition.

## Suggesting related records instead of asking for them

`TB_Products` carries a `Family` on every row, and within a family exactly one row has
`'Product Type' = "Solution"` while the rest are its components. That is enough to stop asking
the technician which recyclers hang off a CI 300X - pick the solution, and the candidates are
`Filter(TB_Products, Family.Value = varFamily, 'Product Type'.Value <> "Solution", Active = true)`.

Two things this has to get right:

- The family comes from the *installation*, not the dropdown: the parent picker yields a
  `TB_Installations` id, so `OnChange` walks id -> `Product.Id` -> `TB_Products.Family.Value`
  and parks it in a variable. Doing that walk inline in the gallery's `Items` works but is
  unreadable and re-evaluates constantly.
- A family with no solution row (Retail and Self Service, today) suggests nothing. That is a
  legitimate state, not a bug, so it gets an empty-state label that distinguishes "you have not
  picked a solution yet" from "this family has no components catalogued" - otherwise the blank
  panel reads as a failure and sends someone debugging.


## `Choices()` is a snapshot, so it cannot see a record you just created

This one silently wrote nothing at all for two builds of the wizard, and the
symptom appeared a whole step away from the cause.

`Choices(TB_Installations.Customer)` is the documented way to populate a lookup
*dropdown*, and it is correct for that. But its result is a cached snapshot of the
target list, taken when the app loads. A customer the wizard created ten seconds
earlier on step 1 is **not in it**. So:

```powerfx
Customer: LookUp(Choices(TB_Installations.Customer), Id = varWizCust.ID)   -- Blank()
```

`Customer` and `Product` are `required=True` on `TB_Installations`, so the `Patch`
was rejected outright and no installation row was ever written. Step 3's solution
picker then had nothing to list, which is where it was finally noticed.

Two rules fall out of this:

**Writing a lookup — build the record, don't look it up.** When you already hold the
target record, construct the reference literally. `scripts/gen_form.py` has always
done this, which is why the admin form never had the bug:

```powerfx
Customer:
    { '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference",
      Id: varWizCust.ID, Value: varWizCust.Title }
```

**Reading rows back — filter the table, not `Choices()`.** `Patch` updates the data
source's local cache, so a `Filter` over the table sees the new row immediately:

```powerfx
Sort(Filter(TB_Installations, Customer.Id = varWizCust.ID, IsBlank('Parent')),
     Title, SortOrder.Ascending)
```

A dropdown fed this way yields a real `TB_Installations` record from `.Selected`, not
a `{Id, Value}` choice record - so it is `.Selected.ID` (the list column) rather than
`.Selected.Id`, and related columns like `.Selected.Product.Id` are reachable directly
without a second `LookUp`.

The earlier entry above still stands: `Choices()` remains the right answer for a
dropdown over a *stable* list, which is why the product and status pickers keep using
it. The distinction is whether the rows can have been created during this session.

### How to catch this class of bug quickly

`IfError` was already wrapped around the `Patch` and `varWizError` was already bound to
a label, and it still went unnoticed - the error surfaces on the step you are leaving,
and it is easy to walk past. Querying the list directly settled it in one command:

```powershell
Get-PnPListItem -List TB_Installations -PageSize 200 |
    ForEach-Object { '{0,4}  {1}' -f $_['ID'], $_['Title'] }
```

Ten rows, all of them seed data, no wizard output at all. That is a far stronger signal
than reasoning about the formula, and it takes under a minute. Check the data before
theorising about the app.

Related: a required column turns a silently-blank value into a hard write failure, so
`Get-PnPField -List <list> | Select InternalName, Required` is worth running before
assuming a blank is harmless.

## A `Classic/DropDown` renders blank unless its `Items` is single-column

The docs are unambiguous about the rule:

> **Items** - The source of data that contains the items that appear in the control. If the
> source has multiple columns, set the control's **Value** property to the column of data
> that you want to show.
>
> -- [Drop down control](https://learn.microsoft.com/power-apps/maker/canvas-apps/controls/control-drop-down)

But `Value` is the property this environment rejects as unknown - the contradiction already
recorded further up this file. So a multi-column `Items` can *never* render here: the control
has no way to be told which column to show, and it shows nothing.

The failure is quiet and misleading. The control still selects, `OnChange` still fires, and
everything downstream still works - it is only the closed dropdown's caption that is empty. On
`scrOnboard` this looked like "the picker is broken" while the component list it drove was
filling in correctly right below it.

Two ways out, both fine:

- **`Choices()`** returns `{Id, Value}`, and the control displays `Value` without being asked.
  This is why every dropdown on `scrEditForm` renders. Use it whenever the target rows existed
  when the app loaded.
- **`ShowColumns(..., Title)`** pins `Items` to one column, so there is nothing to guess at.
  Needed when the rows may have been created during this session, since `Choices()` cannot see
  those. `.Selected` then carries only that column, so resolve the full row once in `OnChange`:

```powerfx
Set(varWizParent,
    LookUp(TB_Installations,
        Customer.Id = varWizCust.ID && IsBlank('Parent')
        && Title = ddWizUnitParent.Selected.Title))
```

`LookUp` takes one condition and an optional result column, so the predicates join with `&&` -
commas would be read as the result argument. `Filter` is the one that takes several.

The remaining sharp edge is that this resolves by title. Within one customer's top-level
installations titles are `"<customer> - <product>"`, so a customer with two of the same solution
would have both units attach to the first. Worth knowing; not worth a schema change yet.

Column names in `ShowColumns` / `DropColumns` / `RenameColumns` / `AddColumns` are **identifiers,
not quoted strings**. The quoted form was retired in version 3.24042 and this compiler answers it
with `Expected identifier name` followed by a cascade of `'Title' isn't recognized` and
`has some invalid arguments` - four errors from one pair of quotes.

The compiler also confirmed the diagnosis on the way past, with a warning on the *old*
multi-column `Items`:

> The columns produced by this rule are all nested tables and/or records, however the property
> expects at least some columns of simple values (such as text, or numbers).

That is the blank dropdown stated outright. Worth grepping the warning list for, since it is easy
to lose among ninety delegation notices.

## Migrating to modern controls: the breaks a property filter cannot see

`scripts/modernize.py` converts classic controls by filtering against the property list
`describe_control` returns, and reports everything it drops. That catches styling changes
cleanly - a `Classic/Button` paints itself with `Fill`/`HoverFill`, a `ModernButton` takes an
`Appearance` enum - but it is blind to three classes of break, because the damage is not in the
control's own properties.

**Renamed output properties.** `ModernToggle` and `ModernCheckbox` expose `Checked`, where the
classic controls exposed `Value`. Every `Patch` in the generators read `.Value`. The reference
lives inside *another* control's formula, so the converter never sees it - the screen would have
compiled clean and silently written nothing. The generators emit these controls directly for
exactly this reason: the rename belongs next to the field spec that knows what the control means.

**Retyped input properties.** `ModernDropdown.Default` is a **Record**; `Classic/DropDown.Default`
was the display **Text**. Dropping it as unsupported would compile and quietly stop the edit form
preselecting an existing record's value. The replacement finds the record in the same option set
the control is showing:

```powerfx
If(varAdminNew, Blank(), LookUp(Choices(TB_Installations.Customer), Value = varRecInst.Customer.Value))
```

**Properties with no equivalent at all.** `ModernTextInput` and `ModernCheckbox` have no `Reset`.
Three controls in the wizard are cleared after a write - two by `Reset()`, one by a `Reset`
property bound to a variable because it sits inside a gallery. Those stay classic. There is no
modern replacement, and converting them would have compiled clean and stopped the form clearing
itself.

**A default that is not neutral.** `ModernButton` defaults to `ButtonAppearance.Primary`. Every
converted button has just had its `Fill` dropped, so with no fallback a quiet list row becomes the
loudest thing on the screen. Nine buttons landed that way before a scan for `ModernButton` without
an `Appearance` caught them. `Secondary` is now the fallback and `EXTRA` is applied first so
explicit choices win.

The general lesson: a conversion tool that only reads one control at a time cannot verify a
migration. Grep the whole app for the old output property name, and scan for controls that came
out of the conversion with a meaningful property missing entirely.

### What `ModernDropdown` retires

`ItemDisplayText` names the column to display, which is the property `Classic/DropDown` lacked
in this environment. That removes the `ShowColumns` reduction recorded above *and* the workaround
it forced: `Selected` now returns the whole record, so `scrOnboard`'s solution picker sets
`varWizParent` to the installation row directly instead of matching it back by title. The
duplicate-title edge case documented earlier is gone with it.

The classic entry above still stands for any `Classic/DropDown` that remains.

## Screen state belongs in `OnVisible`, not in the button that navigates

`scrOnboard` renders three steps on one screen, each gated on `varWizStep`. Nothing on the
screen ever set that variable to 1 - the calling button did, as part of its `OnSelect`:

```powerfx
Set(varWizStep, 1);
Set(varWizError, "");
Navigate(scrOnboard, ScreenTransition.Cover)
```

When home was redesigned and that button was rewritten, the two `Set` lines went with it.
The wizard then opened with `varWizStep` blank, `varWizStep = 1` was false for every
control on step 1, and the screen rendered **completely empty**. It compiled clean, because
nothing is wrong with any individual formula.

The fix is not to restore the `Set` on the new caller - that is the same arrangement, still
one rewrite away from breaking again, and by then there may be several callers to keep in
step. The screen initialises itself:

```yaml
  scrOnboard:
    Properties:
      OnVisible: |
        =Set(varWizStep, 1);
        Set(varWizError, "");
        Set(varWizParent, Defaults(TB_Installations));
        ...
```

The distinction worth holding on to:

- **Screen-internal state** - a step counter, an error line, a scratch selection - is the
  screen's own business. Reset it in `OnVisible`. No caller can forget what it never had to
  remember, and re-entering mid-flow starts clean instead of resuming stale state.
- **Parameters** - `varCustomer` before `scrCustomerOverview`, `varAdminNew` and
  `varRec<List>` before `scrEditForm`, `varInstallation` before `scrUnit` - genuinely differ
  per invocation, so they belong on the caller.

`Defaults(TB_Installations)` rather than `Blank()` for the record, matching `App.OnStart`:
it clears the value while keeping a schema, so downstream `.Product.Id` still type-checks.

An empty screen with a clean compile is the signature of this class of bug. Check what
gates visibility before looking at anything else.

## `User().Email` is the UPN; a SharePoint Person column stores the mail attribute

They are not the same value, and in a tenant that sets them differently, matching a
signed-in user against a Person column by email silently matches nobody.

Measured on the Glory tenant:

```
User().Email      worthyb@us.glory-global.com
Person.Email      Bakari.Worthy@us.glory-global.com
Person.Claims     i:0#.f|membership|worthyb@us.glory-global.com
```

`User().Email` returns the **UPN**. SharePoint's Person column exposes `.Email` from the
directory's **mail** attribute, which many organisations set to `firstname.lastname` while
the UPN is a shorter sign-in name. `.Claims` is built from the login name, so it carries the
UPN and is the field that matches.

Nothing reports the mismatch. The row is there, the status is right, and the lookup returns
blank - so an approved admin is told to request access. It reads like the approval did not
save.

Match on claims, with email as a fallback for tenants where the two agree:

```powerfx
LookUp(TB_Admins,
    (Lower(Person.Claims) = "i:0#.f|membership|" & Lower(User().Email)
     || Lower(Person.Email) = Lower(User().Email))
    && Status.Value = "Approved")
```

Prefer the exact claims comparison over `EndsWith(Person.Claims, User().Email)`. EndsWith
looks tidier and would also match a *different* user whose address is a suffix of this one.

The prefix `i:0#.f|membership|` applies to member accounts in SharePoint Online. Entra B2B
guests are encoded differently, so an external user would need the fallback - or their own
case - if this app ever admits one.

When writing a Person column with `Patch`, construct the same shape:

```powerfx
Person: { '@odata.type': "#Microsoft.Azure.ActiveDirectory.Connectors.Model.GraphUser",
          Claims: "i:0#.f|membership|" & Lower(User().Email),
          DisplayName: User().FullName,
          Email: User().Email,
          Department: "", JobTitle: "", Picture: "" }
```

### `User().FullName` is a display name, not a first and last name

Same tenant, same diagnostic: `Worthy, Bakari (Watertown)`. Surname first, then the given
name, then a site. Taking the first word to greet someone gets you "Worthy," and taking the
last gets you "(Watertown)".

`Match` with a named submatch reads both orders without knowing which it has:

```powerfx
Coalesce(
    Match(User().FullName, ",\s*(?<fn>[^\s(,]+)").fn,
    Match(User().FullName, "^\s*(?<fn>[^\s(,]+)").fn,
    "there")
```

Comma first, because a comma means surname-first and the given name follows it. No comma
means the first token already is the given name. `Match` returns blank when nothing matches,
so `Coalesce` walks the cases in order and lands on a neutral word rather than showing
nobody's name.

Not `Split`. Its own reference page documents the result column as `Value` in the examples
table and uses `.Result` in the substring example two sections later, and that page also
recommends `Match` for this. An ambiguity between two column names is exactly what cost a
deployment cycle on `ShowColumns`.

### How this was found

Four counters on a label, printed on screen:

```
me: worthyb@us.glory-global.com | rows: 1 | approved: 1 | match: 0 | isAdmin: false
```

`rows` and `approved` proved the data was right, `match` proved the comparison was wrong, and
`isAdmin` ruled out a stale variable. One label separated four candidate causes in a single
look, and it is the same technique that settled the blank-screen and empty-wizard bugs.
Reach for it second, not tenth.

## Dropping `Fill` can leave a `Color` that no longer reads

`ModernButton` has no `Fill`, so the converter drops it and reports doing so. `Color`
survives, because `ModernButton` does have one - and a foreground chosen to sit on the
removed background is now sitting on whatever `Appearance` provides.

The delete button was `Fill: If(armed, red, Surface)` with `Color: If(armed, OnPrimary,
red)`. After conversion the fill was gone, the button fell to `ButtonAppearance.Secondary` -
pale - and the armed state rendered white text on it. Invisible, and reported as "the button
goes white and you can't see the words".

Two rules fall out:

- Replace a dropped `Fill` with `Appearance`, and a non-default colour with
  `BasePaletteColor`. `Primary` fills with the palette colour and picks a readable
  foreground itself; `Outline` draws it in that colour on the page background. Then delete
  the `Color` rather than leaving it.
- If a `Color` stays, it has to make sense against the `Appearance` on its own. A conditional
  `Color` paired with a matching conditional `Appearance` is fine - that is what the admin
  tabs do.

`scripts/modernize.py` now flags the specific case: a `ModernButton` that lost its `Fill`,
keeps a light `Color`, and has no `Appearance` of its own, so it falls to the pale default.

A first version of that check flagged any surviving `Color` at all. It found ten controls and
all ten were correct - blue text on a Subtle button, mostly. A check that cries wolf ten
times out of ten is worse than no check, because the eleventh is ignored too.

### The related failure

`btnListSolU` and `btnListAcc` were added to the admin screen after the tab styling rules
were written, so they never got an `Appearance` and stayed pale while the other four
highlighted. Nothing reported it: they were styled, just not the way the rest were. When a
`DEFAULTS` fallback exists, a missing rule looks like a deliberate choice.

## A gallery selects its first row, so `ThisItem.IsSelected` styling reads as "already chosen"

Every card and row in this app was styled from `ThisItem.IsSelected` - a tinted fill, a
coloured border, and on two screens a 4px accent rail. A canvas `Gallery` selects its first
row when it loads, so the top card rendered as picked before anyone touched the screen.
Reported as *"the solution card looks like it's already selected and could confuse users"*,
which is exactly what it was.

The styling came from Studio's own generated browse gallery, where it makes sense: there, the
gallery drives a detail pane on the same screen, and the highlight tells you which record the
pane is showing.

It makes no sense here. Every one of these rows navigates on tap, so by the time a selection
would mean anything the screen has gone. There is nothing left to mark.

Hover and pressed feedback stay, on the transparent hit target. Those are what tell you the
row is live, and they respond to what the user is doing rather than to a default.

Sixteen instances across five screens. Worth grepping `IsSelected` after adding any gallery,
because one card looking pre-selected reads as a bug in the data rather than in the styling -
the reasonable assumption is "why is that one highlighted", not "all galleries do this".

## `Rectangle` has no corner radius; a rounded surface is a `ModernText`

`Classic/Rectangle` rejects all four radius keys:

```
PA2108 : Unknown property 'RadiusTopLeft' for control type 'Rectangle'.
```

and the same for `RadiusTopRight`, `RadiusBottomLeft`, `RadiusBottomRight`.

This is easy to get wrong from a property census. 57 controls in this app carry
`RadiusTopLeft: =6`, so radius looks universal — but every one of them is a `ModernButton`,
`ModernTextInput`, `Classic/Button`, or `ModernText`. Not one is a `Rectangle`. The four
Rectangles in the app (`rectCurrencySol`, `rectCurrencyUnit`, `rectCurrencyOvw`,
`rectUnitsDividerOvw`) are all square blocks, which is why the omission never surfaced.

**A rounded, filled surface is a `ModernText` with empty `Text`.** It takes `Fill`,
`BorderColor`, `BorderThickness` and all four radius keys. `lblReqStatus` on
`scrRequestAccess` is the proven instance — a status pill whose `Fill` switches on the
request state.

```yaml
- recChipFill:
    Control: ModernText
    Properties:
      Text: |-
        =""
      PaddingTop: =0
      PaddingBottom: =0
      Width: =Parent.Width
      Height: =Parent.Height
      Fill: =AppTheme.OkLight
      RadiusTopLeft: =6
      RadiusTopRight: =6
      RadiusBottomLeft: =6
      RadiusBottomRight: =6
```

Set `PaddingTop`/`PaddingBottom` to 0 as on every other `ModernText`, or the empty string
still reserves Fluent's default padding and the surface is taller than its `Height`.

Corollary worth acting on separately: the three currency badges are square because they are
Rectangles. Converting them to this pattern is what makes them look designed rather than
drawn.

## Inside a component, a custom property is `ComponentName.Property`, never the bare name

A child control referring to one of its own component's custom properties by bare name is
rejected:

```
Name isn't valid. 'StandardVersion' isn't recognized.
```

The component's own name is the qualifier:

```yaml
Text: =cmpVersionChip.InstalledVersion        # correct
Text: =InstalledVersion                       # "isn't recognized"
Text: =Parent.InstalledVersion                # also wrong
```

`Parent` is not the escape hatch. Inside a component, `Parent` resolves to the component for
*layout* — `Parent.Width` and `Parent.Height` work, and are the right way to size children
against the component — but it does not reach custom properties. The two look like they
should behave the same and don't.

This matches Microsoft's own walkthrough, which writes `MenuComponent.Items` and
`Component1.SliderColor` from inside those components.

**Consequence worth planning around:** the component's name is baked into every child
formula that reads a custom property. Renaming the component in Studio breaks all of them at
once, with one error per reference. Name it before wiring it up, not after.

The declarations themselves stay bare, because they are YAML keys rather than references:

```yaml
    CustomProperties:
      InstalledVersion:          # bare here
        PropertyKind: Input
        DataType: Text
```

## Inline SVG and embedded images both work, and they are the way out of the control set

Confirmed working in Studio 2026-08-22 on `scrHome`.

### SVG as a data URI

```yaml
Image: |
  ="data:image/svg+xml;utf8, " & EncodeUrl(
      "<svg xmlns='http://www.w3.org/2000/svg' width='" & Round(Parent.Width - (Gutter * 2), 0) & "' height='104' viewBox='0 0 " & Round(Parent.Width - (Gutter * 2), 0) & " 104' preserveAspectRatio='none'>" &
      "<path d='M0 0 H" & Round(Parent.Width - (Gutter * 2) - 18, 0) & " L" & Round(Parent.Width - (Gutter * 2), 0) & " 18 V104 H0 Z' fill='#171A21' stroke='#2A2F3A' stroke-width='1'/>" &
      "<rect x='0' y='0' width='3' height='104' fill='#6A73E6'/>"
  )
```

Rules that matter:

- **Single quotes inside the SVG.** The formula is already double-quoted; escaping doubles
  is possible but unreadable at this length.
- **`EncodeUrl` is required** and handles the `#` in hex colours.
- **`xmlns` is required.** Without it the image renders blank with no error.
- **Keep `viewBox` equal to the rendered pixel size.** With `preserveAspectRatio='none'` a
  mismatched viewBox stretches the artwork — a chamfer becomes a diagonal smear as the
  window resizes. Interpolate the width into both the attributes and the path.
- `Round(..., 0)` on every interpolated number. A fractional pixel in a path is legal SVG
  but produces soft edges.

**This is the only way to draw a shape the control set does not have.** Power Apps offers
four independent corner radii and no chamfer, no gradient, no real shadow, no arbitrary
polygon. Everything on that list is one SVG away.

An `Image` has no `OnSelect`. A tappable SVG panel is two controls: the `Image`, then a
transparent `Classic/Button` at the same X/Y/Width/Height on top of it.

### A raster asset as base64

```yaml
Image: |
  ="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
```

The Glory wordmark is a 4,025-character line built this way and it pastes and renders
fine, so the practical ceiling is well above one logo. Extract, recolour and downscale
before encoding — the source artwork was 602x590; the embedded copy is 200px wide.

### Verifier interaction

`verify_yaml.py` skips lines matching `SVG_MARKUP_RE`. SVG attributes are single-quoted,
which is exactly the shape its quoted-token check treats as a SharePoint column name — one
card background produced eleven false findings before the guard existed.

## A control with no `Color` inherits the theme's, which is dark — swapping to a dark ground breaks all of them at once

After migrating nine screens to the dark palette, every heading, field and non-primary
button on them rendered near-black on graphite. The migration was not at fault: it rewrote
every colour that was **written down**, and 75 controls had never had a `Color` at all.
Those inherit the modern theme's default foreground, which is dark because the theme is a
light theme, and no background swap changes that.

This is the inverse of the `Fill`/`Color` failure recorded above. There a colour outlived
its background; here no colour existed to outlive one. Both share a root cause — appearance
depending on something that changed underneath — and neither is visible to a compile.

**A dark modern theme would be the real fix and does not exist.** The theme editor generates
a palette from a seed colour and exposes no dark-mode switch, so `AppDark` is a Power Fx
record and every control states its own colour.

Three roles, not one:

| control | needs |
|---|---|
| `ModernText`, `Label` | `Color` |
| `ModernTextInput`, `ModernDropdown` | `Color` **and** `Fill` |
| `ModernButton` (not Primary) | `Color` |
| `ModernToggle`, checkboxes | `Color` |

The field case is the one that hides. Those controls also had no `Fill`, so they were white
boxes on a dark screen — and because the text inside them was perfectly readable, they do
not register when you scan for a contrast problem. A `Primary` button is already correct
(white on the accent, from the theme); forcing a colour onto it would fight the theme.

`scripts/fix_dark_defaults.py` applies this and reports what it added. Run it after any
change that introduces controls, and treat a non-zero count as a real finding rather than
noise — it means new controls shipped depending on a default that is wrong for this app.

## A component cannot go inside a gallery, which decides what components are worth building

Microsoft's documented limitation: *"You can't insert a component into a gallery or a form
(including SharePoint form)."*

That removes every list in this app — unit rows, solution cards, document rows, search
results — from the set of places a component can live. A reusable status chip, which is
exactly the thing worth sharing, is banned from the rows that would use it most.

What is left is standalone placements. `cmpVersionChip` is used on `scrSolution` and
`scrUnit`, which show the same comparison against a different record. Two instances is a
thin case, but those two screens are where the logic being wrong matters most, and one
definition cannot drift from itself.

**Consequence to plan around:** row-level status has to be built from ordinary controls, so
the four-state logic exists twice — once in the component, once inline in the gallery
template. They must be changed together. That duplication is forced by the platform, not a
shortcut, and it should be written down wherever both copies live.

Corollary: design components around *what can hold them*. A component sized for a gallery
row is a component that can never be used. `cmpVersionChip` was originally a 190x44 pill for
exactly that; it is now a full-width hero, which is what its actual placements needed.

## A component instance is `Control: CanvasComponent` with `ComponentName:` beside it

Naming the component as the control type is rejected:

```
PA2101 : Unknown control type 'cmpVersionChip'.
```

The schema's `ControlTypeId` pattern is `^([A-Z][a-zA-Z0-9]*/)?[A-Z][a-zA-Z0-9]*$` — a
capitalised built-in type name. A component name is not one, and `cmpVersionChip` fails the
pattern on the leading lowercase alone. The definition is named in a **sibling key**:

```yaml
- cmpVersionSol:
    Control: CanvasComponent
    ComponentName: cmpVersionChip
    Properties:
      X: =Gutter
      InstalledVersion: =Coalesce(varInstallation.'Installed Version', "")
```

`ComponentName` is required for this control type, and custom properties are set in
`Properties` alongside X/Y/Width/Height like any other control.

Watch out for the editor snippets inside `pa.schema.yaml` itself: they write
`Control: Component`, which does not match the normative `ControlTypeId-CanvasComponent`
definition (`const: CanvasComponent`) a few lines above. The normative definition is the one
the compiler enforces.

The schema is public and worth reading directly when a control shape is in doubt:
https://raw.githubusercontent.com/microsoft/PowerApps-Tooling/refs/heads/master/schemas/pa-yaml/v3.0/pa.schema.yaml

## A generator that still emits the old theme will silently undo a migration

`migrate_dark.py` and `fix_dark_defaults.py` were applied to the *output* .pa.yaml files.
Three screens — `scrAdmin`, `scrEditForm`, `scrOnboard` — are produced by generators, and
those generators still emitted `AppTheme` afterwards. Running any one of them would have
reverted that screen to the light palette and dropped every explicit colour added later.

Nothing about running a generator looks dangerous, which is what made it worth finding
before it fired rather than after.

**The build is now one command**, so the follow-up passes cannot be forgotten either:

```
python scripts/build_screens.py
```

which runs, in order:

```
generators  ->  migrate_dark  ->  fix_dark_defaults  ->  verify_yaml
```

Both middle passes are idempotent, and both still earn their place:

- `migrate_dark` no longer changes tokens (the generators emit `AppDark` directly). What it
  contributes is the 3px brand rule, and only on screens with no full brand band — a 3px
  accent line at Y=0 would otherwise draw straight across one.
- `fix_dark_defaults` adds `Color`/`Fill` to controls that would inherit the light theme's
  near-black default. **A non-zero count from it is a real finding**, not noise: it means new
  controls shipped depending on a default that is wrong for this app. It correctly reports
  zero now, and correctly leaves `Primary` buttons alone — those render white on the accent
  from the theme.

`modernize.py` (the classic→modern converter) had the same latent problem and its tokens
were moved too, but it is no longer part of the build and has not been re-verified against
the rebuilt screens.

**Rule: when a transformation is applied to generated output, apply it to the generator in
the same change, or the generator becomes a way to undo it.**

## Three generators were writing to a different folder than the repo

`gen_admin.py`, `gen_form.py` and `gen_onboard.py` wrote their screens to `E:\Papp\tt2\` — a
leftover working directory from an earlier session — while the other seven generators wrote
to `app/screens/`. The repo copies of those three screens were stale copies someone had
moved across by hand.

The effect: **every generator-level change to those three screens landed somewhere nobody
pastes from.** The build reported success each time, because the generator genuinely
succeeded — it just succeeded into the wrong directory. Two rounds of edits (dark palette,
then the band and type pass) appeared to do nothing, and the obvious explanation — that the
edits were wrong — was not the real one.

What made it findable was checking the *output* against the intent rather than trusting the
build's exit code: the screens still reported `RULE` instead of `yes` for the brand band and
29 controls still at 10pt after a pass that removed every 10pt reference from the generator.
A generator whose source has no `AppType.Micro` cannot emit 29 of them; that contradiction is
what pointed at the path.

Two related traps in the same area:

- **A crashed generator leaves the previous file in place.** `gen_form.py` failed with a
  `NameError` for several runs, and the stale screen sat there looking fine.
  `build_screens.py` now prints a `FAILED:` line at the end naming every generator that did
  not run, and says the screens for those are stale.
- **Do not truncate the build output.** The failure above was invisible because the run was
  piped through `tail`, which showed only the passes.

**Rule: when a change to a generator produces no change in the screen, check where the
generator writes before assuming the change was wrong.**

## `ButtonAppearance.Secondary` is unreadable on a dark screen

The six admin tabs and the five list rows rendered as white buttons with near-white text.
Their `Color` was correct — `AppDark.Fg` — and the fault was the *background*.

`Secondary` paints an **opaque neutral fill taken from the app's modern theme**, and that
theme is a light theme with no dark-mode switch. So a Secondary button is near-white
whatever colour the screen behind it is, and any light foreground lands on top of it.

| Appearance | background | safe on dark |
|---|---|---|
| `Primary` | the accent | yes — white text on the accent |
| `Outline` | transparent, with a border | yes |
| `Subtle` | transparent, no border | yes |
| `Secondary` | **opaque theme neutral** | **no** |

`Outline` is the replacement for anything that needs a boundary — tabs, list rows, secondary
actions. `Subtle` suits controls sitting on a coloured surface, like the back buttons on the
brand band.

This is the same root cause as the uncoloured-control failure above: **a control whose
appearance comes from the theme rather than from a property will follow the theme, and the
theme is light.** Anything that reads the theme has to be checked against the real
background rather than assumed.

`verify_yaml.py` now rejects `Secondary` outright, and `modernize.py` — which owns the
classic→modern mapping and had `Secondary` as its default landing place — emits `Outline`
instead. Fixing it there rather than in the generated YAML matters: patching the output
would be undone by the next build, which is the same trap as the generators that kept
emitting `AppTheme`.

## `LookUp` takes one condition; `Filter` takes many

```powerfx
Filter(T, A = 1, B = 2, C = 3)     -- three conditions, ANDed
LookUp(T, A = 1, B = 2, C = 3)     -- WRONG
LookUp(T, A = 1 && B = 2 && C = 3) -- right
```

`LookUp(Table, Condition [, ReductionFormula])`. The signature has room for exactly one
condition; anything after it is the column to return.

Writing it Filter-style produced four errors at once, none of which named the real problem:

```
Invalid number of arguments: received 4, expected 2-3.
The function 'IsBlank' has some invalid arguments.
The '.' operator cannot be used on Unknown values.
Name isn't valid. 'Section' isn't recognized.
```

"'Section' isn't recognized" is the giveaway and the most misleading of the four — it points
at a column that exists, because the third argument was being read as a reduction formula
evaluated in a scope where the comparison made no sense.

**The three-argument form is the more dangerous mistake**, because it compiles. `LookUp(T,
A = 1, B = 2)` is valid syntax: it finds the first row where `A = 1` and returns the value of
`B = 2` — a boolean — instead of filtering on it. No error, wrong answer.

`verify_yaml.py` now flags both: more than three arguments, and a third argument containing
a comparison operator.

## Custom properties DO survive a component paste — and a stale screen looks identical

I claimed the opposite here and was wrong; this entry is kept because the wrong version was
acted on and cost a round trip.

Pasting a component's YAML brings its `CustomProperties` across with it. Adding `SourceNote`
to `cmpVersionChip` and pasting the component was enough — Studio reported the name "already
in use" when a hand-created property was attempted afterwards.

### What actually caused the errors

```
The function 'Coalesce' has some invalid arguments.
Invalid number of arguments: received 4, expected 2-3.
Name isn't valid. 'Section' isn't recognized.
The '.' operator cannot be used on Error values.
Incompatible types for comparison. These types can't be compared: Error, Text.
```

That is the `LookUp`-given-Filter-conditions signature recorded above, on a **screen that had
not been repasted**. The component was current, the screen was not, and the mismatch looks
exactly like a missing property: a failed binding, an Error value, and every downstream
formula reporting its own symptom.

### The rule that is actually useful

**When a component and its screens change together, repaste both, and suspect the stale one
first.** The error surfaces on the consuming screen either way, so the message cannot tell
you which half is behind. Check the formula named in the error against the file on disk
before concluding anything about component metadata — the answer is one `grep` away and does
not depend on remembering how Studio behaves.

## Do not name a SharePoint column `Version`

It collides with SharePoint's built-in item versioning. The column is created and looks
normal in the SharePoint UI, but Power Apps cannot resolve it:

```
Name isn't valid. 'Version' isn't recognized.
```

The tell is that **only that one column fails** — sibling lookups on the same list resolve
fine, which rules out the list, the data source and the connection, and points at the column
itself.

`TB_References` has a working `Version` column, which makes this confusing. That one was
created by `Create-ToolboxLists.ps1`, which sets the internal name (`TBVersion`) and the
display name separately. A column typed into the SharePoint UI gets its internal name derived
from the display name, and for `Version` that derivation collides.

**So: a column created by the script can carry a name a hand-created column cannot.** Any
list a person is expected to build by hand should avoid reserved-ish names entirely rather
than rely on the script's escape. `TB_SoftwareVersions` uses `Software Version`
(`TBSoftwareVersion`), which also reads better on the form.

Power Fx needs the single quotes once a column name contains a space:
`LookUp(TB_SoftwareVersions, ...).'Software Version'`.

## A canvas screen does not scroll, and neither does a ManualLayout container

`scrSolution` stacked its version panel, config notes, units, documentation and firmware to
1273px on a viewport of roughly 750. The last two sections were simply unreachable — no
scrollbar, no wheel response, nothing cut off in a way that suggested more content below.

Nothing in a canvas app scrolls by default. A **Gallery** scrolls its own rows, and an
**auto-layout container** scrolls when its Vertical Overflow is set to Scroll. A
`ManualLayout` GroupContainer has no overflow behaviour at all, and the screen itself never
scrolls.

So a screen whose content is taller than the viewport is not a styling problem — it is
content that does not exist as far as the user is concerned.

**Check the arithmetic when a screen gains a section.** Sum the fixed heights and the gallery
heights; if the total can exceed roughly 700px, the layout needs one of:

- one region that fills the remaining height and scrolls internally (a Gallery)
- an auto-layout container with Vertical Overflow set to Scroll
- fewer things on screen at once

`scrSolution` took the third with a tab strip: Units, Documents and Firmware share one origin
and one region. The page is now 455px before the list starts, and the list fills whatever is
left — so the page stops growing as a site gains documents, which the stacked version did
without limit.

Row counts were tried in the tab labels and removed. They answered a question nobody was
asking — a technician opens Documents to find a document, not to learn there are seven — and
they cost a `CountRows` per tab on every render of the screen.

Auto-layout was the obvious fix and was not used: its `Variant` and `Layout*` property names
could not be verified against this compiler with the authoring MCP disconnected, and an
earlier attempt in this project was abandoned for the same reason (see the comment in
`scrHome`). Tabs use a button that sets a variable and a `Visible` that reads it, both proven
here many times over.

## An unresolved `{Placeholder}` ships silently and reads as a layout bug

These screens are built by f-string templating, so a brace escaped but never substituted
reaches the app as literal text:

```yaml
Height: ={TAB_H}
Y: ={Y_TABS}
```

Studio reports *unexpected characters*, and the control **falls back to zero** — so three tab
buttons rendered stacked at the top of the screen. The reported symptom is a layout problem;
the cause is a build one.

Nothing else catches it. The YAML is well-formed, every other check passes, and the value is
merely wrong rather than malformed.

The mistake underneath: a helper returning an f-string wrote `{{NAME}}` to escape the braces
from *its own* interpolation, expecting a later pass to substitute them. **There is no later
pass** — the helper's result is inserted into the document verbatim. Single braces are
correct, because Python resolves the name when the helper is *called*, which happens inside
the document f-string where the value is already defined.

`verify_yaml.py` now flags any `{Identifier}` surviving in a formula. Power Fx has no use for
one, and record literals (`{ Value: "x" }`) are excluded because the pattern requires the
whole brace to be a single identifier.

## Internally consistent arithmetic is not correct arithmetic

Adding a seventh tab to the admin strip updated every formula correctly — the width divided
by the new count, each button's X multiplier lined up, the selected-state mapping was there.
Reviewed on its own terms it was clean, and it was called clean.

What none of that answered is what the numbers *produce*:

| App.Width | 6 tabs | 7 tabs |
|---|---|---|
| 375 | 45.2px | **37.6px** |
| 390 | 47.7px | **39.7px** |
| 414 | 51.7px | **43.1px** |

The row went from just clearing the 44px tap floor to failing on every mainstream phone.
Nothing in the file was wrong; the result was unusable. **A formula that agrees with itself
can still be checked for whether its output is sane**, and for anything responsive that means
evaluating it at the actual breakpoints rather than reading it.

`Gutter` and `ContentWidth` are named formulas in `App.pa.yaml`, so any width or offset can
be computed for a given `App.Width` without opening Studio:

```python
g  = 16 if w < 640 else 24
cw = min(w - g * 2, 1100)
```

Do that whenever a count changes in a row of anything.

The related lesson: **the same review that called the arithmetic correct also missed it**, so
"I checked the geometry" is not a claim worth making unless the check included the output at
the sizes the app actually runs at.

## A property set twice is kept once, silently

`fix_dark_defaults` clears a picker's generator colours before writing its own light-field
pair. The pattern it used to clear them with matched only `=AppDark.<token>`, so when
`gen_form` wrote the literal pair directly, both survived:

```yaml
- dtpLastVerifiedInst:
    Control: ModernDatePicker
    Properties:
      Color: =ColorValue("#14181C")     # from the pass
      Fill:  =ColorValue("#F2F4F8")
      Color: =ColorValue("#14181C")     # from the generator
      Fill:  =ColorValue("#F2F4F8")
```

YAML keeps the last occurrence of a duplicated key and discards the rest without complaint.
Here both copies happened to agree, so nothing looked wrong — but the same shape with two
*different* values is a control that looks configured and behaves otherwise, and no compiler
will mention it.

Two guards now exist: the strip clears any single-line value rather than one spelling, and
`verify_yaml.duplicate_properties` reports a key set twice inside one control. **One owner per
property.** If a pass writes a property, the generator must not, and vice versa.

## `If(varAdminNew, "", …)` suppresses the column's own default

`scrEditForm` gave every field on a new record a hardcoded empty value:

```powerfx
Default: =If(varAdminNew, false, varRecCust.Active)
```

`Defaults(TB_Customers)` already returns the list's configured defaults, so the wrapper was
not filling a gap — it was overriding one. `TB_Customers.Active` and `TB_Products.Active`
both default to true in the schema; the form wrote **false**.

Every browse list filters on `Active = true`. So a customer or model created through
*Admin → Add new* existed and was invisible — absent from the customer list, the catalogue
and search — until someone reopened the record and moved a toggle they had no reason to
suspect. It survived because the guided setup's own toggle defaults to true, so the two paths
that create a customer disagreed, and whichever one you used looked self-consistent.

The rule that generalises: **a default that restates what the data source already provides is
not a safety net, it is a second opinion**, and when the two disagree the data source is
usually right. Override one only where the column's default is wrong *for a new record
specifically* — `TB_SolutionUnits.Standard` is the single case here, and it says so at the
field definition rather than in the form.

## A SharePoint lookup record cannot be built by hand for `Patch(record, changes)`

```powerfx
Patch( Source, Base, Changes )   -- writes. Coerces Changes against the list schema.
Patch( Record, Changes )         -- merges two records. No schema, no coercion.
```

The three-argument write **requires** the odata field on a lookup:

```powerfx
Customer: { '@odata.type': "#Microsoft.Azure.Connectors.SharePoint.SPListExpandedReference",
            Id: varCustomer.ID, Value: varCustomer.Title }
```

The two-argument merge accepts **neither** that shape nor the plain `{ Id, Value }`. Both
fail identically:

```
The type of this argument 'Customer' does not match the expected type 'Record'.
Found type 'Record'.
```

With the odata field the literal has one field too many; without it, one too few. The message
names neither the offending field nor the direction, and "Record does not match Record" reads
like a compiler fault rather than a shape mismatch. **The first fix — dropping the odata
field — looked obviously right and was still wrong**, which is what makes this worth a rule:
the error is identical either way, so the second attempt gives no more information than the
first.

Do not construct one. A row read from the table already has the type, because it came from
the table:

```powerfx
Set(varStCustomerInst, LookUp(TB_Customers, ID = varCustomer.ID))   -- fine
```

`scrEditForm` keeps one such variable per lookup field and each dropdown prefers it over the
record:

```powerfx
Default: =If(!IsBlank(varStCustomerInst), varStCustomerInst,
             LookUp(TB_Customers, ID = varRecInst.Customer.Id))
```

They are cleared in `admin_open` and in scrAdmin's own entries — **not** in `OnVisible`, which
runs *after* the `OnSelect` that navigated and would wipe the value it was meant to carry.

`screen_parts.STASH_VARS` lists them and `gen_form` asserts the list still matches its lookup
fields, so a field added in one place and not the other fails the build rather than pre-filling
with whatever the previous visit left behind.

`verify_yaml.odata_in_record_merge` still reports the odata field inside a two-argument
`Patch`, which catches the first of the two wrong shapes.
