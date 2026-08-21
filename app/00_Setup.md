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

## An empty SharePoint lookup has three shapes

`IsBlank(Parent.Value)` alone is not a reliable test for "this lookup is empty". Depending on how
the item was written, an empty lookup presents as a blank record, a blank `.Value`, or an `.Id` of
`0` - and grid-view paste and `Add-PnPListItem` take different write paths, so a test that works
after one can silently fail after the other. The failure is invisible: the filter returns nothing
and the gallery renders empty with no error.

Every blank-lookup test in these screens therefore reads:

```powerfx
Or(IsBlank(Customer.Value), IsBlank(Customer.Id), Customer.Id = 0)
```

This matters most for two clauses. `Parent` is what distinguishes a solution from a unit on
`scrCustomerOverview` - get it wrong and the customer appears to run nothing. And the blank
`Customer` half of the reference filter is what makes a document universal - get it wrong and every
document disappears.

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
