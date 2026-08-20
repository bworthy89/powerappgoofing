# Step 1 — App-level properties

Set these three properties on the **App** node in Tree view before pasting any screen.
Nothing else will resolve until `AppTheme` exists.

> ### The one rule
>
> **`Set(` is only ever valid in `OnStart`. It is never valid in `Formulas`.**
>
> These are three separate properties, chosen from the dropdown at the **top-left of the formula
> bar**, and each gets its own paste. Switch the dropdown between them. Pasting a `Set(...)` block
> while the dropdown still reads `Formulas` is the cause of nearly every error below.
>
> | Dropdown reads | Paste this block | Contains `Set(`? |
> |---|---|---|
> | `Formulas` | AppTheme, AppFont, AppType, IsNarrow, Gutter, ContentWidth (see below) | No |
> | `OnStart` | Set(varCustomer, Blank()); Set(varInstallation, Blank()); Set(varExpandedModel, 0) | Yes |
> | `StartScreen` | scrHome | No |

## App.Formulas

```powerfx
AppTheme = {
    Bg:            ColorValue("#F4F6F8"),
    Surface:       ColorValue("#FFFFFF"),
    Sunken:        ColorValue("#E7EBEF"),
    Fg:            ColorValue("#14181C"),
    FgSecondary:   ColorValue("#39424B"),
    Muted:         ColorValue("#66727E"),
    Faint:         ColorValue("#8C97A2"),
    Line:          ColorValue("#DFE4E9"),
    LineSoft:      ColorValue("#EBEEF1"),
    Primary:       ColorValue("#0057B8"),
    PrimaryDark:   ColorValue("#003D82"),
    PrimaryLight:  ColorValue("#E7F0FA"),
    OnPrimary:     ColorValue("#FFFFFF"),
    Ok:            ColorValue("#17795E"),
    OkLight:       ColorValue("#E2F2EC"),
    Warn:          ColorValue("#9A6100"),
    WarnLight:     ColorValue("#FBF0DC"),
    Neutral:       ColorValue("#66727E"),
    NeutralLight:  ColorValue("#EDF0F3")
};

AppFont = Font.'Lato';

AppType = {
    Display:  32,
    Title:    22,
    Heading:  17,
    Body:     14,
    Small:    12,
    Micro:    10
};

IsNarrow = App.Width < 640;

Gutter = If(App.Width < 640, 16, 24);

ContentWidth = Min(App.Width - (Gutter * 2), 1100)
```

Every label sets `Font: =AppFont` and `Size: =AppType.Body` (or similar size name). This
establishes the convention: when you create a label, you choose its semantic role (Body,
Heading, etc.), and the AppType record supplies the corresponding size. Lato is one of the
few faces Power Apps can render; there is no web-font escape hatch, so the type system has to
live entirely inside weights and sizes.

## App.OnStart

```powerfx
Set(varCustomer, Blank());
Set(varInstallation, Blank());
Set(varExpandedModel, 0)
```

## App.StartScreen

```powerfx
scrHome
```

Note: `scrHome` does not exist yet. This formula will error in Studio until Task 8 creates that screen — this is expected rather than a mistake to debug.

## Troubleshooting

Pasting into the wrong property produces a confusing error. Each block is valid in exactly one
place, and using the wrong one produces errors that do not mention the property at all.

| Error you see | What it means | Fix |
|---|---|---|
| `Missing function argument type, for example the ":Text" in "FindMonth( d:Text ):Number = ..."` | `Set(varCustomer, ...)` or another `Set()` block was pasted into **Formulas**. The parser reads `Set(` as the start of a user-defined function, so the variable name looks like an untyped parameter. | Remove `Set(` and its closing `)` so the statement reads `varCustomer = Blank()` (data formulas only); or move the block to **OnStart** where `Set()` is valid. |
| `Name isn't valid. 'AppTheme' isn't recognized` | The **Formulas** block has not been pasted yet, or the property is empty. | Paste the App.Formulas block into the **Formulas** property. |
| `Unexpected characters. The formula contains 'CurlyOpen' where 'Equ' is expected.` | The `=` is missing, usually left over from hand-editing. | Clear the property and paste the block fresh. It must begin `AppTheme = {` and end `};` |
| `Behavior function in a non-behavior property` | `Set(...)` used somewhere that only accepts data formulas (e.g., **Formulas**, **StartScreen**). | Move it to **OnStart**. |

**Quick way to tell which property you are in:** the formula bar's property dropdown reads
`Formulas`, `OnStart`, or `StartScreen`. Only `OnStart` contains the word `Set`.

Do not define `AppTheme` or any other name in both `Formulas` and `OnStart` — defining the
same name twice is an error.

## If App.Formulas is unavailable

Paste the same record into `App.OnStart` wrapped in `Set(AppTheme, {...})`, then right-click
App in Tree view and choose **Run OnStart**. `IsNarrow` must then become
`Set(varNarrow, App.Width < 640)` and every screen reference changes to `varNarrow`, which
will not react to resizing — a real downgrade. Prefer Formulas.
