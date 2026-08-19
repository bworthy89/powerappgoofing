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
> | Dropdown reads | Paste this | Contains `Set(`? |
> |---|---|---|
> | `Formulas` | the `AppTheme = {
    Bg: ColorValue("#FFFFFF"),
    BgSecondary: ColorValue("#F8F9FA"),
    Card: ColorValue("#FFFFFF"),
    Muted: ColorValue("#F1F3F5"),
    Fg: ColorValue("#1A1B1E"),
    MutedFg: ColorValue("#868E96"),
    TertiaryFg: ColorValue("#ADB5BD"),
    Border: ColorValue("#E9ECEF"),
    BorderStrong: ColorValue("#DEE2E6"),
    Primary: ColorValue("#228BE6"),
    PrimaryDark: ColorValue("#1971C2"),
    PrimaryLight: ColorValue("#E7F5FF"),
    Success: ColorValue("#40C057"),
    SuccessDark: ColorValue("#2B8A3E"),
    SuccessLight: ColorValue("#EBFBEE"),
    Warning: ColorValue("#FD7E14"),
    WarningDark: ColorValue("#E8590C"),
    WarningLight: ColorValue("#FFF4E6"),
    Danger: ColorValue("#FA5252"),
    GrayLight: ColorValue("#F1F3F5"),
    GrayDark: ColorValue("#495057")
};
```

## App.OnStart

```powerfx
Set(varCustomer, Blank());
Set(varSolution, Blank());
Set(varComponent, Blank());
Set(varSelectedSection, "Overview")
```

## Fallback if App.Formulas is unavailable

Put this in **App.OnStart** instead, then right-click App in Tree view and choose **Run OnStart**.

```powerfx
Set(AppTheme, AppTheme = {
    Bg: ColorValue("#FFFFFF"),
    BgSecondary: ColorValue("#F8F9FA"),
    Card: ColorValue("#FFFFFF"),
    Muted: ColorValue("#F1F3F5"),
    Fg: ColorValue("#1A1B1E"),
    MutedFg: ColorValue("#868E96"),
    TertiaryFg: ColorValue("#ADB5BD"),
    Border: ColorValue("#E9ECEF"),
    BorderStrong: ColorValue("#DEE2E6"),
    Primary: ColorValue("#228BE6"),
    PrimaryDark: ColorValue("#1971C2"),
    PrimaryLight: ColorValue("#E7F5FF"),
    Success: ColorValue("#40C057"),
    SuccessDark: ColorValue("#2B8A3E"),
    SuccessLight: ColorValue("#EBFBEE"),
    Warning: ColorValue("#FD7E14"),
    WarningDark: ColorValue("#E8590C"),
    WarningLight: ColorValue("#FFF4E6"),
    Danger: ColorValue("#FA5252"),
    GrayLight: ColorValue("#F1F3F5"),
    GrayDark: ColorValue("#495057")
});
Set(varCustomer, Blank());
Set(varSolution, Blank());
Set(varComponent, Blank());
Set(varSelectedSection, "Overview")
```

A global variable and a named formula are referenced with identical syntax, so **no change to the
screen YAML is needed** — every `AppTheme.Background` keeps working. The only cost is that the theme
is undefined until OnStart has run, so controls show errors in Studio until you use Run OnStart.

Use this or the App.Formulas block, not both — defining the same name twice is an error.

## Troubleshooting these two blocks

The two theme blocks are **not interchangeable**. Each one is valid in exactly one property, and
using the wrong one produces a confusing error that does not mention the theme at all.

| Error you see | What it means | Fix |
|---|---|---|
| `Missing function argument type, for example the ":Text" in "FindMonth( d:Text ):Number = ..."` | `Set(AppTheme, {...})` was pasted into **App.Formulas**. The parser reads `Set(` as the start of a user-defined function, so `AppTheme` looks like an untyped parameter. | Remove `Set(` and its closing `)` so the statement reads `AppTheme = { ... };` |
| `Name isn't valid. 'AppTheme' isn't recognized` | Neither block has been committed yet, or OnStart has not been run. | Define one of the two blocks, and use Run OnStart if you chose the OnStart version |
| `Unexpected characters. The formula contains 'CurlyOpen' where 'Equ' is expected.` | The `=` is missing, usually left over from hand-editing `Set(AppTheme, {` down to `AppTheme {`. | Clear the property and paste the block fresh. It must begin `AppTheme = {` and end `};` |
| `Behavior function in a non-behavior property` | `Set(...)` used somewhere that only accepts data formulas. | Move it to App.OnStart |

Prefer clearing the property and pasting a block whole over editing one form into the other.
Every error in this table so far has come from hand-editing `Set(AppTheme, {...})` into
`AppTheme = {...}` and leaving a fragment behind.

Quick way to tell which property you are in: the formula bar's property dropdown reads either
`Formulas` or `OnStart`. `Formulas` never contains the word `Set`.

Do not define `AppTheme` in both places. Defining the same name twice is an error.

## App.StartScreen

```powerfx
scrCustomers
```

Use StartScreen rather than a `Navigate()` in OnStart — Navigate in OnStart is no longer supported
and StartScreen evaluates before the first screen paints.

## Settings to change

- **Settings > General > Data row limit for non-delegable queries** → `2000`
- **Settings > Display** → turn off Scale to fit, Lock aspect ratio, Lock orientation
- **Settings > Upcoming features** → confirm **Enhanced component properties / Named formulas** is on,
  otherwise the `App.Formulas` property will not appear.

## Data sources to add first

Add all seven SharePoint lists (Data > Add data > SharePoint > your Technician Toolbox site).
The paste will fail validation on any screen whose formulas reference a list that is not connected yet.

- TB_Customers
- TB_CustomerSolutions
- TB_SolutionComponents
- TB_SoftwareInstallations
- TB_CustomerGuides
- TB_ProductReferences
- TB_CustomerReferences
