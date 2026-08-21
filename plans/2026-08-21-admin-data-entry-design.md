# Admin data entry — design

Adding or correcting Technician Toolbox data currently means visiting four SharePoint
lists and linking records by hand. This adds an Admin section to the existing canvas app
so it can be done from one place.

Status: design agreed 2026-08-21. Not yet built.

## Problem

The lists are a hierarchy, and SharePoint's own forms do not know that.

Standing up one customer means creating the customer, then a top-level installation, then
child installations that point back at rows created moments earlier — picking the parent
from a dropdown of every installation in the tenant, by title, with nothing preventing a
Northgate unit being parented to a Harbour solution.

Corrections have the opposite problem: the edit itself is trivial (a version moved from
K36 to K38), but finding the row costs more than changing it.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Where editing lives | New screens in the **existing app** | One app, one login, shares `AppTheme`; the alternative of a second app means keeping two apps visually in sync |
| Entry point | **Admin section only**, reached from `scrHome` | Adding Edit buttons to `scrSolution` / `scrUnit` / `scrCatalogue` is better for corrections but means modifying three working screens. Deferred, not rejected — see Later |
| Form structure | **Four `Form` controls**, one per list, on one screen | A `Form` binds to its data source at author time and cannot be repointed at runtime. Four forms with `Visible` toggles is the idiom |
| Writes | **Direct to SharePoint** | All four sources already report `Writable`. No new connector, no Power Automate, no permissions work |

## Screens

**`scrAdmin`** — four buttons (Customers, Products, Installations, References) set
`varAdminList`. Below them a search box and a gallery of that list's records, filtered by
the search. An **+ Add new** button sits beside the search. Tapping a row sets
`varAdminRecord` and navigates to the form in edit mode; **Add new** navigates in new mode.

**`scrEditForm`** — four `Form` controls, only the one matching `varAdminList` visible.
`SubmitForm` writes. `OnSuccess` returns to `scrAdmin`; `OnFailure` shows the error inline
rather than failing silently.

**`scrHome`** — gains one **Admin** tile. The only change to an existing screen: one
control added, nothing existing modified.

## Fields

| Form | Fields |
|---|---|
| Customers | Title, Description, Support Notes, Active |
| Products | Title, Product Type, Family, Current Standard Version, Description, Active |
| Installations | Title, Customer, Product, **Parent**, Installed Version, Status, Config Notes |
| References | Title, Product, Customer, Section, Reference Type, URL, Version, Featured, Last Checked |

## The Parent field

This is the reason the feature exists. The dropdown lists only top-level installations
belonging to the customer already chosen on the form:

```powerfx
Filter(
    TB_Installations,
    Customer.Id = cmbCustomer.Selected.ID,
    IsBlank('Parent')
)
```

Two things are easy to get wrong here, and both fail silently:

- **`cmbCustomer.Selected.ID`, not `.Id`.** The combobox holds a `TB_Customers` row, whose
  identity is `ID`. `.Id` is the projection off a *lookup* column. Mixing them compiles
  cleanly and returns nothing.
- **`IsBlank('Parent')`, never `Parent = Blank()` or `IsBlank(Parent.Value)`.** See the
  lookup section of `app/00_Setup.md`. The first does not compile; the second returns
  nothing without erroring.

`IsBlank('Parent')` is **runtime-verified**, not merely compiling: `scrCustomerOverview`
uses the identical pattern and was confirmed on 2026-08-21 returning two solutions for
Northgate with two units nested beneath `CI 300X`.

Leaving `Parent` blank is what makes a record a solution rather than a unit. The form
labels that choice explicitly instead of leaving it an unexplained empty lookup. Same
treatment on References: a blank `Customer` is labelled *applies to all customers*.

## Out of scope for v1

- **Delete.** Removing a customer or solution orphans its children silently; there is no
  cascade. Wrong thing to ship before create and edit are trusted.
- **Bulk edit.** A real need, but a different screen and a different design.
- **Role gating.** SharePoint list permissions already decide who can write. A canvas app
  cannot enforce more than the connector allows.

## Later

Edit affordances on `scrSolution`, `scrUnit` and `scrCatalogue` that jump straight to a
prefilled form. Much better for corrections, but it modifies three working screens, so it
should land only once the forms themselves are proven.

## Deployment note

A push is all-or-nothing: delete every screen in Studio, push the complete set, verify
with `sync_canvas`. Adding two screens therefore costs a full cycle, roughly two minutes.
See the deployment section of `app/00_Setup.md`.
