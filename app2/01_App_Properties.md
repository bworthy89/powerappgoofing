# Step 1 — App-level properties

Three properties, three separate pastes, chosen from the dropdown at the top-left of the
formula bar. `Set(` is valid ONLY in `OnStart`.

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

## If App.Formulas is unavailable

Paste the same record into `App.OnStart` wrapped in `Set(AppTheme, {...})`, then right-click
App in Tree view and choose **Run OnStart**. `IsNarrow` must then become
`Set(varNarrow, App.Width < 640)` and every screen reference changes to `varNarrow`, which
will not react to resizing — a real downgrade. Prefer Formulas.
