# Step 1 — App-level properties

Set these three properties on the **App** node in Tree view before pasting any screen.
Nothing else will resolve until `AppTheme` exists.

## App.Formulas  (preferred)

Select **App** in Tree view, then open the **property dropdown at the top-left of the formula bar**
and choose **Formulas**. It is in the same dropdown as OnStart, not in the right-hand pane, which is
the usual reason people cannot find it. Paste the block below and click away from the formula bar to
commit it.

If `Formulas` is not in that dropdown, skip to the fallback below — the app works either way.

```powerfx
AppTheme = {
    Primary: ColorValue("#003B5C"),
    Secondary: ColorValue("#0078D4"),
    Background: ColorValue("#F5F7FA"),
    Card: Color.White,
    Text: ColorValue("#202124"),
    MutedText: ColorValue("#605E5C"),
    Border: ColorValue("#D2D6DC"),
    Success: ColorValue("#107C10"),
    SuccessLight: ColorValue("#DFF6DD"),
    Warning: ColorValue("#FFB900"),
    WarningLight: ColorValue("#FFF4CE"),
    Error: ColorValue("#A80000")
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
Set(AppTheme, {
    Primary: ColorValue("#003B5C"),
    Secondary: ColorValue("#0078D4"),
    Background: ColorValue("#F5F7FA"),
    Card: Color.White,
    Text: ColorValue("#202124"),
    MutedText: ColorValue("#605E5C"),
    Border: ColorValue("#D2D6DC"),
    Success: ColorValue("#107C10"),
    SuccessLight: ColorValue("#DFF6DD"),
    Warning: ColorValue("#FFB900"),
    WarningLight: ColorValue("#FFF4CE"),
    Error: ColorValue("#A80000")
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
| `Behavior function in a non-behavior property` | `Set(...)` used somewhere that only accepts data formulas. | Move it to App.OnStart |

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
