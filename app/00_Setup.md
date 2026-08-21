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
