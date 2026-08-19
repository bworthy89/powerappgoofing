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
