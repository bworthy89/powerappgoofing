# Step 0 — The real SharePoint schema

Everything in this kit is written against the exports in `app/TB_*.csv`, taken from the live
Technician Toolbox site. Six of the seven files carry a `ListSchema={...}` block with the field
XML; `TB_CustomerGuides.csv` exported with its header row only.

> ### The one rule
>
> **Power Fx binds SharePoint columns by *display name*, not internal name.**
>
> `MachineModel` is the internal name of the column displayed as `Solution Model`, and only the
> second one resolves in a formula. Any display name containing a space, or any character that
> is not a letter or digit, must be single-quoted: `ThisItem.'Solution Model'`.

## Traps in this particular site

These are real, they are in the exported schema, and each one produces a `Name isn't valid`
error that points at the formula rather than at the list.

| Trap | Where | What the formula must say |
|---|---|---|
| `Solution Famility` — misspelled display name | `TB_CustomerSolutions` | `'Solution Famility'.Value` |
| `Document Status ` — **trailing space** | `TB_CustomerGuides` | `'Document Status '.Value` |
| `Solution ` — **trailing space** in a choice *value* | `TB_CustomerReferences.'Applies To'` | compare against `"Solution "`, not `"Solution"` |
| `SIA Documantation` — misspelled choice value | `TB_ProductReferences.'Reference Type'` | match the typo exactly |
| `Choice 1 / Choice 2 / Choice 3` — placeholder choices | `TB_CustomerSolutions.'Deployment Status'` | see the fix list below |
| `Verifiedby` vs `VerifiedBy` — inconsistent internal names | several lists | irrelevant in formulas; the display name is `Verified by` / `Verified By` |

The same concept is also spelled differently per list. `'Applies To'` offers `Customer / Solution /
Component` on `TB_SoftwareInstallations`, but `Customer / Solution  / Component` (trailing space)
on `TB_CustomerReferences`, and `Solution / Component / Software / Accessory / General` on
`TB_ProductReferences`. Never copy an `'Applies To'` comparison between lists without rechecking.

## Fix these on the lists before the app is fully correct

1. **`TB_CustomerSolutions.'Deployment Status'`** still has the default `Choice 1 / Choice 2 /
   Choice 3`. The app is written against the vocabulary already configured on
   `TB_SoftwareInstallations` — `Current Standard`, `Installed`, `Upgrade Planned`,
   `Upgrade Required`, `Retired`, `Unknown`. Set those same choices on the solutions list, or the
   status badge renders the raw placeholder text with neutral gray styling.
2. **`TB_CustomerGuides` was exported without its schema.** The app assumes `Guide Type` and
   `Document Status ` are Choice columns and `Document URL` is a Hyperlink. If any of them is
   plain text, drop the `.Value` from that reference in `scrSolutionDetails.pa.yaml`.
3. **Trailing spaces** on `Document Status ` and on the `Solution ` choice are worth cleaning up
   at the source. If you do clean them, update the two places noted in the table above.

## Lookup columns

The `ListSchema` block **omits lookup fields** — they appear only in the CSV header row. The
relationships the app relies on, all single-value lookups onto the `Title` of the parent list:

| List | Lookup columns |
|---|---|
| `TB_CustomerSolutions` | `Customer` |
| `TB_SolutionComponents` | `Customer Solution` |
| `TB_SoftwareInstallations` | `Customer`, `Customer Solution`, `Solution Component` |
| `TB_CustomerGuides` | `Customer`, `Customer Solution`, `Solution Component` |
| `TB_CustomerReferences` | `Customer`, `Customer Solution`, `Solution Component`, `Product Reference` |
| `TB_Customers`, `TB_ProductReferences` | none — these are the roots |

A lookup gives you `.Id` (the parent's numeric ID, used for every join in this app) and `.Value`
(the parent's Title). Filtering on `.Id` is **not delegable** against SharePoint, which is why
`01_App_Properties.md` raises the non-delegable row limit to 2000.

## Columns by list

Display name first — that is what you type. Internal name in parentheses only where it differs.

### TB_Customers
`Title` · `Customer Code` (CustomerCode) · `Customer Logo` (Thumbnail) · `Description` (Note) ·
`Support Notes` (Note) · `Active` (Yes/No) · `Sort Order` (Number) · `Last Reviewed` (Date) ·
`Reviewed By` (Person)

Note this list uses **`Last Reviewed`**, while every other list uses `Last Verified`.

### TB_CustomerSolutions
`Title` · `Customer` (lookup) · `Solution Model` (MachineModel, text) · `Solution Famility`
(ProductFamily, choice: CashInfinity / Retail / Banking / Self Service) · `Solution Type` (choice:
Front Office / Back Office / Retail / Financial / Gaming / Hospitality) · `Deployment Status`
(choice, **placeholder values**) · `Deployment Scope` (Note) · `Customer Configuration` (Note) ·
`Active` (Yes/No, required) · `Sort Order` (Number) · `Support Notes` (Note) · `Notes` (Note) ·
`Last Verified` · `Verified By`

`Solution Model` is required. There is no `Solution Family` column — only the misspelled one.

### TB_SolutionComponents
`Title` · `Customer Solution` (lookup) · `Component Model` (text) · `Component Role` (text) ·
`Required Component` (Yes/No) · `Installed` (Yes/No)

The smallest list, and the one that lost the most: **no `Display Order`, no `Active`, no
`Component Category`**. The component gallery therefore sorts on `Title` alone and badges on
`Component Role`. `Component Category` exists as a choice on `TB_ProductReferences` instead.

### TB_SoftwareInstallations
`Title` · `Customer` · `Customer Solution` · `Solution Component` (lookups) · `Applies To`
(choice: Customer / Solution / Component) · `Software Name` (text) · `Software Version` (text) ·
`Windows Version` (text) · `Deployment Status` (choice: Current Standard / Installed / Upgrade
Planned / Upgrade Required / Retired / Unknown) · `Deployment Scope` (Note) · `Last Verified` ·
`Verified by` · `Notes`

There is **no `Current Standard` Yes/No column** — "is this the current standard" is
`'Deployment Status'.Value = "Current Standard"`. There are also no separate `Image Version`,
`Database Version` or `Configuration Version` columns; `Windows Version` is the only secondary
version recorded.

### TB_CustomerGuides — *schema not exported, types assumed*
`Title` · `Customer` · `Customer Solution` · `Solution Component` (lookups) · `Applies To` ·
`Guide Type` · `Document URL` · `Revision` · `Document Status ` · `Description` · `Active` ·
`Last Verified` · `Verified By` · `Multiple Notes`

### TB_ProductReferences
The master catalogue. No lookups — customer-specific meaning comes from `TB_CustomerReferences`.

`Title` · `Reference Type` (choice, 13 values) · `Applies To` (choice: Solution / Component /
Software / Accessory / General) · `Product Family` (text) · `Solution Model` (text) ·
`Component Category` (choice: Note Recycler / Coin Recycler / Drop Vault / Printer / Scanner /
Biometric / PC / UPS) · `Component Model` (text) · `Software Name` (text) · `ReferenceVersion`
(text) · `Reference URL` (Hyperlink) · `Release Status` (choice: Current / Previous / Under Review
/ Restricted / Retired / Unknown) · `Description` (Note) · `Restricted` (Restricted0, Yes/No) ·
`Last Verified` · `Verified by` · `Notes`

`Reference Type` drives the two reference sections in the app:

| Section | `Reference Type` values |
|---|---|
| **SIA documentation** (`galSIA`) | SIA Product Page, SIA Documantation, Installation Manual, Service Manual, Troubleshooting Guide, Technical Bulletin, Technical Alert, Product Specification |
| **Firmware and downloads** (`galFirmware`) | Machine Firmware, BV Firmware, Software Download, Driver, Support Tool |

Add a new choice to `Reference Type` and it appears in **neither** gallery until you add it to one
of those two lists in `scrSolutionDetails.pa.yaml`.

### TB_CustomerReferences
`Title` · `Customer` · `Customer Solution` · `Solution Component` · `Product Reference` (lookups) ·
`Applies To` (choice: Customer / `Solution ` / Component) · `Featured` (Yes/No) · `Active` (Yes/No) ·
`Display Order` (Number) · `Last Verified` · `Verified By`

**This is a junction list.** It carries no URL, no status, no category and no notes of its own — it
only says "this product reference is relevant to this customer, at this scope, in this order."
Everything the SIA and Firmware galleries display about a reference comes from the joined
`TB_ProductReferences` row:

```powerfx
AddColumns(
    Filter(TB_CustomerReferences, ...) As Map,
    "RefRec", LookUp(TB_ProductReferences, ID = Map.'Product Reference'.Id)
)
```

`Featured` and `Display Order` stay on the mapping row; `Reference Type`, `Release Status`,
`Restricted`, `Reference URL` and `Description` are read through `ThisItem.RefRec`.

## Re-checking this document

`app/TB_*.csv` are the exports themselves — re-export from SharePoint, overwrite them, and diff.
Take the export from a view that shows **all** columns, otherwise the header row silently omits
the lookups and you lose the only record of them.
