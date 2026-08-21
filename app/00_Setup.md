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
