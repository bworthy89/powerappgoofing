# Step 1 — App-level properties

Set these three properties on the **App** node in Tree view before pasting any screen.
Nothing else will resolve until `AppTheme` exists.

## App.Formulas

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
