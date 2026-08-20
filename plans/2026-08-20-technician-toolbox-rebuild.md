# Technician Toolbox Rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a six-screen Power Apps canvas app over the four rebuilt SharePoint lists, delivered as paste-ready `.pa.yaml` source.

**Architecture:** Four SharePoint lists provide all data. The model catalogue (`TB_Products`) is the join hub: documents attach to a model, not a customer, so one row reaches every customer running that model. `TB_Installations` says "this customer runs this model, at this version", nesting solution → units through a self-lookup. Screens are pasted into Studio's Code view one at a time; there is no packing step, because `pac canvas pack` is deprecated and its replacement needs premium licensing.

**Tech Stack:** Power Apps canvas app (`.pa.yaml`, Studio Code view paste), SharePoint Online lists via the standard connector, Power Fx. Python 3 for the local YAML verification harness.

**Spec:**
- Product truth: `PRODUCT.md` (uncommitted, local — the repo is public)
- Screen designs, every element keyed to its column: https://claude.ai/code/artifact/6829b0ef-f31b-4d77-b386-ae55ac348911
- List provisioning as built: `scripts/sharepoint/Create-ToolboxLists.ps1`
- Environment constraints learned the hard way: `tasks/lessons.md`

---

## Global Constraints

These apply to **every** task. Violating any one of them produces an error that points at the wrong place.

1. **Power Fx binds SharePoint columns by DISPLAY name.** `ThisItem.'Config Notes'`, never `ThisItem.TBConfigNotes`. Any display name containing a space or non-alphanumeric character must be single-quoted.
2. **This environment rejects every locally-introduced name.** No `AddColumns` columns, no `With` bindings, no `As` aliases. Where a value is needed twice, repeat the `LookUp`. Three separate paste attempts failed on this; see `tasks/lessons.md`.
3. **The proven lookup idiom is** `LookUp(TB_Products, ID = <row>.Product.Id).'Column Name'` — a record-returning `LookUp` followed by dot access. `<row>` is `ThisItem` inside a gallery child, or the bare row scope inside a gallery's `Items`.
4. **Any Power Fx value containing `: ` must go in a YAML `|` block scalar.** An inline scalar with a colon-space makes the parser read a nested mapping and the whole file fails to load.
5. **`Set(` is only ever valid in `App.OnStart`.** It is never valid in `App.Formulas`. These are separate properties chosen from the dropdown at the top-left of the formula bar, each pasted separately.
6. **Version comparison is equality only.** Never render an arrow, "upgrade to", or any direction. Versions read `K36`, `V4.21`, `3.10.0` — no ordering exists.
7. **Blank installed version is a third state**, rendered `not recorded`. Never counted as current, never counted as off standard.
8. **Retired rows are excluded everywhere:** `Status.Value <> "Retired"`. There is no `Active` column on `TB_Installations`.
9. **Fonts:** Lato only. `Font.'Lato'` with weights via `FontWeight.Light|Normal|Semibold|Bold`. No monospace anywhere — Courier New is the only option and it is not acceptable.
10. **Brand colour is `#0057B8`, a placeholder.** It is not Glory's confirmed value. Every use goes through `AppTheme.Primary` so one edit changes all of them.
11. **Red is unused.** Status is green / amber / neutral only. Brand blue carries identity and primary action, never alarm.
12. **One breakpoint: `App.Width < 640`.** Below it, single column. No second breakpoint.
13. **Commit after every task.** Branch is `rebuild-lists-from-scratch`.

### The four lists as built

| List | Columns (display names) |
|---|---|
| `TB_Customers` | `Title` · `Description` · `Support Notes` · `Active` |
| `TB_Products` | `Title` · `Product Type` · `Family` · `Current Standard Version` · `Description` · `Active` |
| `TB_Installations` | `Title` · `Customer` · `Parent` · `Product` · `Installed Version` · `Status` · `Config Notes` |
| `TB_References` | `Title` · `Product` · `Customer` · `Section` · `Reference Type` · `URL` · `Version` · `Featured` · `Last Checked` |

Choice values, exactly:
- `Product Type`: Solution, Note Recycler, Coin Recycler, Drop Vault, Printer, Scanner, Biometric, PC, UPS
- `Family`: CashInfinity, Retail, Banking, Self Service
- `Status`: In Service, Upgrade Planned, Retired
- `Section`: Documentation, Firmware & Downloads
- `Reference Type`: Service Manual, Installation Manual, Error Code Manual, Technical Bulletin, Technical Alert, Product Specification, Customer Specific, Machine Firmware, BV Firmware, Software Download, Driver, Support Tool

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/verify_yaml.py` | Local test harness: parses every screen file, enforces the block-scalar rule and the display-name rule |
| `app2/00_Setup.md` | Data source connection order and Studio settings |
| `app2/01_App_Properties.md` | `App.Formulas` (theme + named formulas), `App.OnStart`, display settings |
| `app2/screens/scrCustomers.pa.yaml` | Customer directory |
| `app2/screens/scrCustomerOverview.pa.yaml` | One customer: support notes, what they run |
| `app2/screens/scrSolution.pa.yaml` | One solution: version pair, config, units, documents |
| `app2/screens/scrUnit.pa.yaml` | One unit: firmware pair, config, documents |
| `app2/screens/scrCatalogue.pa.yaml` | Browse models, no customer needed |
| `app2/screens/scrHome.pa.yaml` | Search, backlog figure, entry tiles, recent |
| `seed/*.csv` | Grid-paste seed data, numbered in dependency order |

`app2/` rather than `app/` so the previous generation stays readable side by side until this one
works. Tasks 1-9 below were built and committed under that name; the paths in those tasks'
Files/Steps sections are accurate to when they ran. **At cutover (Task 10) the previous generation
was archived to `archive/` rather than deleted — its `TB_*.csv` exports are the only surviving
record of the old SharePoint schema — and `app2/` was renamed to `app/`, which is where this app
now lives.**

---

## Task 1: YAML verification harness

The only automated test available. It catches the two failure classes that have actually bitten this project: an inline scalar containing `: ` that silently breaks the document, and a reference to a column name that does not exist in the schema.

**Files:**
- Create: `scripts/verify_yaml.py`
- Create: `app2/screens/.gitkeep`

**Interfaces:**
- Produces: `python3 scripts/verify_yaml.py [path]` — exit 0 clean, exit 1 with findings. Every later task runs this before pasting.

- [ ] **Step 1: Write the failing test fixture**

Create `scripts/testdata/bad_inline_colon.pa.yaml`:

```yaml
- lblBad:
    Control: Label
    Properties:
      Text: =ThisItem.'Product: Reference Type'.Value
```

- [ ] **Step 2: Write the harness**

Create `scripts/verify_yaml.py`:

```python
#!/usr/bin/env python3
"""Verify Power Apps .pa.yaml screen files before pasting them into Studio.

Two checks, both earned from real failures:

  1. An inline scalar containing ": " makes the YAML parser read a nested
     mapping and the whole document fails to load. Projected SharePoint
     columns always contain ": ", so this is not hypothetical.

  2. A column name that is not in the schema produces a "Name isn't valid"
     error in Studio that points at the formula rather than at the list.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required:  pip install pyyaml")

SCHEMA = {
    "TB_Customers": {"Title", "Description", "Support Notes", "Active"},
    "TB_Products": {"Title", "Product Type", "Family",
                    "Current Standard Version", "Description", "Active"},
    "TB_Installations": {"Title", "Customer", "Parent", "Product",
                         "Installed Version", "Status", "Config Notes"},
    "TB_References": {"Title", "Product", "Customer", "Section",
                      "Reference Type", "URL", "Version", "Featured",
                      "Last Checked"},
}
ALL_COLUMNS = set().union(*SCHEMA.values())

# Names the environment rejects. See tasks/lessons.md.
BANNED = [
    (r"\bAddColumns\s*\(", "AddColumns introduces a local name this environment rejects"),
    (r"\bWith\s*\(", "With introduces a local name this environment rejects"),
    (r"\s+As\s+[A-Za-z_]", "As aliases are rejected by this environment"),
]


def check_file(path):
    findings = []
    text = path.read_text(encoding="utf-8")

    # 1. does it parse at all
    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        findings.append((0, f"YAML does not parse: {exc}"))

    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # 2. inline scalar carrying ": " outside a block scalar
        m = re.match(r"^(\w+):\s*=(.*)$", stripped)
        if m and ": " in m.group(2):
            findings.append((n, f"inline value contains ': ' — use a | block scalar: {stripped[:60]}"))

        # 3. locally-introduced names
        for pattern, why in BANNED:
            if re.search(pattern, line):
                findings.append((n, f"{why}: {stripped[:60]}"))

        # 4. quoted names that look like columns but are not in the schema
        for quoted in re.findall(r"'([^']{2,40})'", line):
            looks_like_column = " " in quoted or quoted[0].isupper()
            if looks_like_column and quoted not in ALL_COLUMNS and quoted not in SCHEMA:
                if not quoted.startswith(("scr", "gal", "lbl", "btn", "con", "ico", "rect", "img")):
                    findings.append((n, f"'{quoted}' is not a column in any of the four lists"))

    return findings


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "app2/screens")
    files = sorted(root.rglob("*.pa.yaml")) if root.is_dir() else [root]
    if not files:
        sys.exit(f"no .pa.yaml files under {root}")

    total = 0
    for f in files:
        findings = check_file(f)
        total += len(findings)
        status = "ok" if not findings else f"{len(findings)} finding(s)"
        print(f"{f}: {status}")
        for line_no, msg in findings:
            print(f"  line {line_no}: {msg}")

    print(f"\n{len(files)} file(s), {total} finding(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it against the bad fixture, confirm it fails**

```bash
python3 scripts/verify_yaml.py scripts/testdata/bad_inline_colon.pa.yaml
```

Expected: exit 1, reporting `inline value contains ': '` on line 4 and `'Product: Reference Type' is not a column`.

- [ ] **Step 4: Run it against the old kit, confirm it finds the historical bugs**

```bash
python3 scripts/verify_yaml.py app/screens
```

Expected: findings against the old schema's column names — that is correct, those columns no longer exist. This proves the schema check works rather than passing everything.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_yaml.py scripts/testdata app2/screens/.gitkeep
git commit -m "Add a YAML harness that checks the two failures we have actually hit"
```

---

## Task 2: App foundation

Nothing resolves until `AppTheme` exists. This task also sets the responsive switch every screen reads.

**Files:**
- Create: `app2/00_Setup.md`
- Create: `app2/01_App_Properties.md`

**Interfaces:**
- Produces: `AppTheme` record (colours, referenced by every screen), `IsNarrow` boolean named formula, `varCustomer` / `varInstallation` context variables.

- [ ] **Step 1: Write `app2/00_Setup.md`**

````markdown
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
````

- [ ] **Step 2: Write `app2/01_App_Properties.md`**

The theme, as three separate pastes. Note `Set(` appears only in the OnStart block.

````markdown
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

Every label then sets `Font: =AppFont` and `Size: =AppType.Body` or similar. Lato is one of the
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

## If App.Formulas is unavailable

Paste the same record into `App.OnStart` wrapped in `Set(AppTheme, {...})`, then right-click
App in Tree view and choose **Run OnStart**. `IsNarrow` must then become
`Set(varNarrow, App.Width < 640)` and every screen reference changes to `varNarrow`, which
will not react to resizing — a real downgrade. Prefer Formulas.
````

- [ ] **Step 3: Paste both into Studio and confirm**

Paste `App.Formulas` first. Expected: no red error under the formula bar. Then `App.OnStart`, then `App.StartScreen` (it will error until `scrHome` exists — that is expected, set it in Task 8).

- [ ] **Step 4: Commit**

```bash
git add app2/00_Setup.md app2/01_App_Properties.md
git commit -m "Add app foundation: Glory blue theme, one breakpoint, four data sources"
```

---

## Task 3: scrCustomers

First real screen, and deliberately the simplest one that exercises the whole data path: a gallery, a filter, and the three-state currency computation. If this pastes and renders, the connection and the formula idioms are proven and every later screen is a variation.

**Files:**
- Create: `app2/screens/scrCustomers.pa.yaml`

**Interfaces:**
- Consumes: `AppTheme`, `IsNarrow`, `Gutter`, `ContentWidth` from Task 2.
- Produces: sets `varCustomer` on selection and navigates to `scrCustomerOverview`. Later screens read `varCustomer`.

- [ ] **Step 1: Write the screen**

Control tree: `conRoot` (GroupContainer) → `lblTitle`, `txtSearch`, `galCustomers` → `lblName`, `lblDesc`, `lblChip`, `rectChip`.

The two formulas that carry this screen. `galCustomers.Items`:

```powerfx
SortByColumns(
    Filter(
        TB_Customers,
        Active = true,
        StartsWith(Title, Trim(txtSearch.Text))
    ),
    "Title",
    SortOrder.Ascending
)
```

`lblChip.Text` — the three-state summary for one customer. Note the repeated `LookUp`: no `With`, no alias.

```powerfx
If(
    CountRows(
        Filter(
            TB_Installations,
            Customer.Id = ThisItem.ID,
            Status.Value <> "Retired",
            !IsBlank('Installed Version'),
            'Installed Version' <> LookUp(TB_Products, ID = Product.Id).'Current Standard Version'
        )
    ) > 0,
    CountRows(
        Filter(
            TB_Installations,
            Customer.Id = ThisItem.ID,
            Status.Value <> "Retired",
            !IsBlank('Installed Version'),
            'Installed Version' <> LookUp(TB_Products, ID = Product.Id).'Current Standard Version'
        )
    ) & " off standard",
    CountRows(
        Filter(
            TB_Installations,
            Customer.Id = ThisItem.ID,
            Status.Value <> "Retired",
            IsBlank('Installed Version')
        )
    ) > 0,
    CountRows(
        Filter(
            TB_Installations,
            Customer.Id = ThisItem.ID,
            Status.Value <> "Retired",
            IsBlank('Installed Version')
        )
    ) & " not recorded",
    CountRows(Filter(TB_Installations, Customer.Id = ThisItem.ID, Status.Value <> "Retired")) = 0,
    "nothing recorded",
    "all on standard"
)
```

`rectChip.Fill` follows the same branch order, returning `AppTheme.WarnLight`, `AppTheme.NeutralLight`, `AppTheme.NeutralLight`, `AppTheme.OkLight`.

`galCustomers.OnSelect`:

```powerfx
Set(varCustomer, ThisItem);
Navigate(scrCustomerOverview, ScreenTransition.Cover)
```

Responsive sizing on `conRoot`:

```powerfx
X: =Max((Parent.Width - ContentWidth) / 2, Gutter)
Width: =ContentWidth
```

Every child width is `Parent.Width - (Gutter * 2)`. **No fixed widths.** That is what broke the old kit on a phone.

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens/scrCustomers.pa.yaml
```

Expected: `ok`, 0 findings. If it reports a column name, the formula references something that is not in the four lists — fix before pasting.

- [ ] **Step 3: Paste into Studio**

Insert a blank screen, rename it `scrCustomers`, select it in Tree view, open Code view, paste. Expected: controls appear, no red error markers.

- [ ] **Step 4: Verify on a real width**

With the lists still empty, expected: the gallery renders empty and no formula errors. Resize the Studio canvas below 640 and confirm nothing overflows.

- [ ] **Step 5: Commit**

```bash
git add app2/screens/scrCustomers.pa.yaml
git commit -m "Add the customer directory screen"
```

---

## Task 4: scrCustomerOverview

**Files:**
- Create: `app2/screens/scrCustomerOverview.pa.yaml`

**Interfaces:**
- Consumes: `varCustomer` set by Task 3.
- Produces: sets `varInstallation` and navigates to `scrSolution`.

- [ ] **Step 1: Write the screen**

`lblSupportNotes.Text`: `=varCustomer.'Support Notes'`
`conSupportNotes.Visible`: `=!IsBlank(varCustomer.'Support Notes')` — blank hides the whole card, it does not render "none".

`galSolutions.Items` — a blank `Parent` is what makes a row a solution:

```powerfx
SortByColumns(
    Filter(
        TB_Installations,
        Customer.Id = varCustomer.ID,
        IsBlank(Parent.Value),
        Status.Value <> "Retired"
    ),
    "Title",
    SortOrder.Ascending
)
```

`lblModel.Text`: `=LookUp(TB_Products, ID = ThisItem.Product.Id).Title`

`lblVersion.Text`:

```powerfx
LookUp(TB_Products, ID = ThisItem.Product.Id).Family & "  •  software " &
Coalesce(ThisItem.'Installed Version', "—")
```

`lblCurrency.Text` — the three states, stated as fact with no direction:

```powerfx
If(
    IsBlank(ThisItem.'Installed Version'),
    "not recorded",
    IsBlank(LookUp(TB_Products, ID = ThisItem.Product.Id).'Current Standard Version'),
    "",
    ThisItem.'Installed Version' = LookUp(TB_Products, ID = ThisItem.Product.Id).'Current Standard Version',
    "on standard",
    "standard " & LookUp(TB_Products, ID = ThisItem.Product.Id).'Current Standard Version'
)
```

`lblStatus.Text`: `=If(ThisItem.Status.Value = "In Service", "", Lower(ThisItem.Status.Value))` — shown *alongside* the currency chip, never instead of it.

`galUnits.Items` (nested gallery inside each solution card):

```powerfx
SortByColumns(
    Filter(TB_Installations, Parent.Id = ThisItem.ID, Status.Value <> "Retired"),
    "Title",
    SortOrder.Ascending
)
```

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens/scrCustomerOverview.pa.yaml
```

Expected: `ok`, 0 findings.

- [ ] **Step 3: Paste and verify**

Expected: no errors. Nested gallery `Items` referencing the outer `ThisItem.ID` is the risky construct here — if Studio rejects it, the fallback is a flat gallery filtered on `Parent.Id` rendered under each card by `Customer.Id` and `Parent` matching.

- [ ] **Step 4: Commit**

```bash
git add app2/screens/scrCustomerOverview.pa.yaml
git commit -m "Add the customer overview screen"
```

---

## Task 5: scrSolution

**Files:**
- Create: `app2/screens/scrSolution.pa.yaml`

**Interfaces:**
- Consumes: `varCustomer`, `varInstallation`.
- Produces: sets `varInstallation` to a unit and navigates to `scrUnit`.

- [ ] **Step 1: Write the screen**

Version pair, side by side, separator is `=` or `≠` and never an arrow:

`lblInstalled.Text`: `=Coalesce(varInstallation.'Installed Version', "not recorded")`
`lblStandard.Text`: `=Coalesce(LookUp(TB_Products, ID = varInstallation.Product.Id).'Current Standard Version', "—")`
`lblSeparator.Text`:

```powerfx
If(
    IsBlank(varInstallation.'Installed Version'),
    "",
    IsBlank(LookUp(TB_Products, ID = varInstallation.Product.Id).'Current Standard Version'),
    "",
    varInstallation.'Installed Version' = LookUp(TB_Products, ID = varInstallation.Product.Id).'Current Standard Version',
    "=",
    "≠"
)
```

The second branch matters: with no catalogue standard there is nothing to compare against, so the
separator must be blank. Without it, an installed version against a blank standard renders `≠` and
claims the machine is off standard when no standard exists — and it contradicts the badge beside it,
which correctly goes invisible.

`galUnits.Items`:

```powerfx
SortByColumns(
    Filter(TB_Installations, Parent.Id = varInstallation.ID, Status.Value <> "Retired"),
    "Title",
    SortOrder.Ascending
)
```

`galDocs.Items` — universal documents plus this customer's exceptions, in one gallery:

```powerfx
SortByColumns(
    Filter(
        TB_References,
        Product.Id = varInstallation.Product.Id,
        Section.Value = "Documentation",
        Or(IsBlank(Customer.Value), Customer.Id = varCustomer.ID)
    ),
    "Featured",
    SortOrder.Descending,
    "Reference Type",
    SortOrder.Ascending,
    "Title",
    SortOrder.Ascending
)
```

`galFirmware.Items` — identical but `Section.Value = "Firmware & Downloads"`.

`lblChecked.Text` — the 12-month staleness rule:

```powerfx
If(
    IsBlank(ThisItem.'Last Checked'),
    "never checked",
    DateDiff(ThisItem.'Last Checked', Today(), TimeUnit.Months) >= 12,
    "not checked in " & DateDiff(ThisItem.'Last Checked', Today(), TimeUnit.Months) & " months",
    "checked " & Text(ThisItem.'Last Checked', "dd mmm yyyy")
)
```

`lblException.Text`: `=If(IsBlank(ThisItem.Customer.Value), "", "this customer")`

`galDocs.OnSelect`: `=If(!IsBlank(ThisItem.URL), Launch(ThisItem.URL))`

A row with no URL must be visible but inert. **Do not put `DisplayMode` on the Gallery** —
`Gallery.DisplayMode` is a single value evaluated at screen scope, where `ThisItem` does not exist.
`OnSelect` is the documented exception that IS row-scoped, so the tap is guarded there, and the row
is dimmed through a template child: `lblDocTitle.Color: =If(IsBlank(ThisItem.URL), AppTheme.Faint,
AppTheme.Fg)`.

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens/scrSolution.pa.yaml
```

Expected: `ok`. Watch for the `≠` character — it is non-ASCII, so confirm the file is UTF-8 and that Studio accepts it. If it does not, substitute `"vs"`.

- [ ] **Step 3: Paste and verify**

- [ ] **Step 4: Commit**

```bash
git add app2/screens/scrSolution.pa.yaml
git commit -m "Add the solution detail screen"
```

---

## Task 6: scrUnit

Structurally the same as Task 5, scoped to one unit, plus a breadcrumb. Written separately rather than reused because the two screens diverge: units get a warning-tinted config card and no nested unit gallery.

**Files:**
- Create: `app2/screens/scrUnit.pa.yaml`

**Interfaces:**
- Consumes: `varCustomer`, `varInstallation` (a unit row, so `Parent` is set).

- [ ] **Step 1: Write the screen**

`lblCrumb.Text` — customer, parent solution, kind:

```powerfx
varCustomer.Title & "  ›  " &
LookUp(TB_Products, ID = LookUp(TB_Installations, ID = varInstallation.Parent.Id).Product.Id).Title &
"  ›  " &
Lower(LookUp(TB_Products, ID = varInstallation.Product.Id).'Product Type'.Value)
```

Version pair identical to Task 5 but reading the **unit's own** product standard — the comparison is never inherited from the solution above it.

`conConfigNotes.Fill`: `=AppTheme.WarnLight` (Task 5 uses `AppTheme.Surface`). A non-standard part is what bites mid-job, so it gets the warning tint here.

`galDocs.Items` and `galFirmware.Items` identical to Task 5 — same shape, `varInstallation.Product.Id` now resolves to the unit's model.

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens/scrUnit.pa.yaml
```

Expected: `ok`. The nested `LookUp` inside a `LookUp` in the breadcrumb is the risky construct — if Studio rejects it, split it across two labels rather than introducing a `With`.

- [ ] **Step 3: Paste and verify**

- [ ] **Step 4: Commit**

```bash
git add app2/screens/scrUnit.pa.yaml
git commit -m "Add the unit detail screen"
```

---

## Task 7: scrCatalogue

The only route to a document without going through a customer, and the screen the previous app never had.

**Files:**
- Create: `app2/screens/scrCatalogue.pa.yaml`

- [ ] **Step 1: Write the screen**

`galModels.Items`:

```powerfx
SortByColumns(
    Filter(
        TB_Products,
        Active = true,
        StartsWith(Title, Trim(txtSearch.Text))
    ),
    "Product Type",
    SortOrder.Ascending,
    "Title",
    SortOrder.Ascending
)
```

`lblDocCount.Text`: `=CountRows(Filter(TB_References, Product.Id = ThisItem.ID, IsBlank(Customer.Value))) & " documents"`

`lblStandard.Text`: `=Coalesce(ThisItem.'Current Standard Version', "no standard set")` — this is the screen that lets you audit the catalogue's own accuracy while populating it.

Selecting a model reveals its documents without navigating. A seventh screen would carry no
information this one cannot show, and the screen count stays at six.

**`galModelDocs` is a SIBLING of `galModels`, not nested inside its row template.** `TemplateSize`
is a single scalar for a whole gallery, so a nested document list forces every row — expanded or
not — to reserve the expanded height. On a phone that leaves roughly two models visible out of
thirty-eight, which defeats a browse screen. A flat sibling filtered by the selected id costs less
Power Fx, keeps the model list dense, and removes the gallery-inside-a-gallery construct entirely.

`galModels.OnSelect`: `=Set(varExpandedModel, ThisItem.ID)`
`galModels.TemplateSize`: `=72`
`galModelDocs.Visible`: `=!IsBlank(varExpandedModel) && varExpandedModel <> 0`

`galModelDocs.Items`:

```powerfx
SortByColumns(
    Filter(TB_References, Product.Id = varExpandedModel, IsBlank(Customer.Value)),
    "Section",
    SortOrder.Ascending,
    "Title",
    SortOrder.Ascending
)
```

Customer-specific references are deliberately excluded here — without a customer in context they have no meaning.

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens/scrCatalogue.pa.yaml
```

- [ ] **Step 3: Paste and verify**

- [ ] **Step 4: Commit**

```bash
git add app2/screens/scrCatalogue.pa.yaml
git commit -m "Add the catalogue browse screen"
```

---

## Task 8: scrHome

Last, because it navigates to all five other screens and they must exist for the formulas to resolve.

**Files:**
- Create: `app2/screens/scrHome.pa.yaml`
- Modify: `app2/01_App_Properties.md` — `App.StartScreen` now resolves, `App.OnStart` gains `LoadData`
- Modify: `app2/screens/scrCustomers.pa.yaml` — `galCustomers.OnSelect` gains the `colRecent` writes

- [ ] **Step 1: Write the screen**

`galSearch.Items` — three sources, grouped. Power Fx cannot union three tables without a local name, so use three separate galleries stacked, each visible only when it has rows:

```powerfx
// galSearchCustomers.Items
Filter(TB_Customers, Active = true, StartsWith(Title, Trim(txtSearch.Text)))

// galSearchProducts.Items
Filter(TB_Products, Active = true, StartsWith(Title, Trim(txtSearch.Text)))

// galSearchDocs.Items
Filter(TB_References, Trim(txtSearch.Text) in Title)
```

Each gallery's `Visible`: `=Len(Trim(txtSearch.Text)) >= 2 && CountRows(Self.AllItems) > 0`

`lblBacklogFigure.Text` — the whole estate, off standard:

```powerfx
CountRows(
    Filter(
        TB_Installations,
        Status.Value <> "Retired",
        !IsBlank('Installed Version'),
        'Installed Version' <> LookUp(TB_Products, ID = Product.Id).'Current Standard Version'
    )
)
```

`lblBacklogCaption.Text`:

```powerfx
"of " & CountRows(Filter(TB_Installations, Status.Value <> "Retired")) & " installations"
```

`lblUnknownCount.Text`:

```powerfx
CountRows(
    Filter(TB_Installations, Status.Value <> "Retired", IsBlank('Installed Version'))
) & " not recorded"
```

The proportion bar is two rectangles, widths driven by the counts:

```powerfx
// rectOnStandard.Width
(Parent.Width - 6) * (CountRows(Filter(TB_Installations, Status.Value <> "Retired", !IsBlank('Installed Version'), 'Installed Version' = LookUp(TB_Products, ID = Product.Id).'Current Standard Version')) / Max(CountRows(Filter(TB_Installations, Status.Value <> "Retired")), 1))
```

Tiles: `lblCustomerCount.Text` is `=CountRows(Filter(TB_Customers, Active = true))`, `lblModelCount.Text` is `=CountRows(Filter(TB_Products, Active = true))`.

Responsive: `conDashboard.LayoutDirection` is `=If(IsNarrow, LayoutDirection.Vertical, LayoutDirection.Horizontal)`. Recent-customer cards stack when `IsNarrow`.

**Recently opened** is device-local, no list involved:

```powerfx
// galCustomers.OnSelect in Task 3 gains:
RemoveIf(colRecent, Id = ThisItem.ID);
Collect(colRecent, {Id: ThisItem.ID, Name: ThisItem.Title, At: Now()});
If(CountRows(colRecent) > 3,
   RemoveIf(colRecent, At = First(Sort(colRecent, At, SortOrder.Ascending)).At));
SaveData(colRecent, "recent")

// App.OnStart gains:
LoadData(colRecent, "recent", true)
```

- [ ] **Step 2: Run the harness**

```bash
python3 scripts/verify_yaml.py app2/screens
```

Expected: all six files `ok`, 0 findings.

- [ ] **Step 3: Paste, then set App.StartScreen to scrHome**

- [ ] **Step 4: Walk all four journeys in Studio preview**

Prep, currency, find a document, at-the-machine. With empty lists this only proves navigation and absence of errors.

- [ ] **Step 5: Commit**

```bash
git add app2/screens/scrHome.pa.yaml app2/01_App_Properties.md
git commit -m "Add the home dashboard and wire it as the start screen"
```

---

## Task 9: Seed data

The lists are empty, which is what has blocked judging whether any of this works since the beginning.

**Files:**
- Create: `seed/1_TB_Customers.csv`, `seed/2_TB_Products.csv`, `seed/3_TB_Installations.csv`, `seed/4_TB_References.csv`
- Create: `seed/README.md`

- [ ] **Step 1: Write the CSVs**

Headers must be the **display names** exactly. Lookup columns hold the parent's `Title` text, matched exactly by grid view.

`seed/1_TB_Customers.csv`:

```csv
Title,Description,Support Notes,Active
Northgate Retail Group,"Regional supermarket group, north west","Goods entrance only, 06:00-14:00. Ask for Dawn on the service desk.",Yes
Harbour Savings Bank,Retail banking and one central cash centre,,Yes
Coastway Fuel,"Forecourt operator, unattended payment",,Yes
```

`seed/2_TB_Products.csv`:

```csv
Title,Product Type,Family,Current Standard Version,Description,Active
CI 300X,Solution,CashInfinity,K38,Front office cash recycling solution,Yes
CI 300,Solution,CashInfinity,K38,Front office cash recycling solution,Yes
RBW 100,Note Recycler,CashInfinity,V4.21,Note recycling module,Yes
CI CS,Coin Recycler,CashInfinity,4.0.1,Coin recycling module,Yes
```

- [ ] **Step 2: Write `seed/README.md`**

Paste order and the one rule that matters:

````markdown
# Seeding

**Order matters.** Lookups resolve on the parent's exact `Title` text, and the parent row must
already exist:

1. `TB_Customers` and `TB_Products` — no lookups, these are the roots
2. `TB_Installations` — needs both
3. `TB_References` — needs Products, and Customers for exceptions only

Open the list, **Edit in grid view**, paste the block under the matching headers.

A lookup that does not match a parent Title exactly fails silently and leaves an empty cell.
After pasting `TB_Installations`, sort by `Product` and confirm no blanks.
````

- [ ] **Step 3: Paste into SharePoint, verify no empty lookups**

- [ ] **Step 4: Commit**

```bash
git add seed/
git commit -m "Add seed data in dependency order"
```

---

## Task 10: End-to-end verification and cutover

- [ ] **Step 1: Walk all four journeys against real data**

With seeded lists: Northgate should show two solutions, `CI 300X` off standard (`K36` against `K38`), `CI 300` on standard, and the `RBW 100` unit under `CI 300X` off standard against `V4.21`.

- [ ] **Step 2: Check the three states all render**

At least one row must show `on standard`, one `standard K38`, and one `not recorded`. If the third never appears, leave an installation's version blank deliberately — an unfillable state is a state nobody has tested.

- [ ] **Step 3: Check both widths**

Studio preview at tablet width, then below 640. Nothing overflows, nothing is hidden that was visible.

- [x] **Step 4: Cut over**

As executed, this step differed from the command block originally drafted here. `app/TB_*.csv`
are the only surviving record of the previous SharePoint schema, including its real defects, and
are cited as evidence elsewhere — deleting them with `git rm -r app` would have destroyed that
record. The kit was archived instead of deleted:

```bash
git mv app archive
git mv app2 app
python3 scripts/verify_yaml.py app/screens
git add -A
git commit -m "Cut over: archive the previous generation, promote the rebuild to app/"
```

- [ ] **Step 5: Delete the legacy lists**

Once the app runs against the new four, remove the six remaining `TB_*` legacy lists in SharePoint. They go to the recycle bin.

- [x] **Step 6: Update the docs**

`archive/00_Schema_Reference.md` describes the previous generation. Retitled as history rather
than deleted: its header now states plainly that the current four lists are `TB_Customers`,
`TB_Products`, `TB_Installations` and `TB_References`, and that the trap table's defects
(misspelled `Solution Famility`, trailing-space `Document Status `, placeholder `Choice 1/2/3`)
no longer exist on the new, script-provisioned lists.

---

## Open risks

Recorded rather than hidden. Each is a construct this environment may reject, with the fallback already chosen so nobody has to guess mid-build.

| Risk | Where | Fallback |
|---|---|---|
| Nested gallery reading the outer `ThisItem.ID` | Task 4 | Flatten to one gallery per solution card |
| `LookUp` inside a `LookUp` in the breadcrumb | Task 6 | Split across two labels |
| `Distinct` + `SaveData` on a collection | Task 8 | Drop "recently opened"; it is the least load-bearing element on the screen |
| `≠` renders as a box in the Power Apps player | Task 5, 6 | Substitute `"vs"` |
| Repeated `CountRows(Filter(...))` is slow at scale | Tasks 3, 8 | Acceptable to low thousands of rows; revisit only if it drags |
