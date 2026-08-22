# What changed from the original seven lists

The first version of the Technician Toolbox ran on seven SharePoint lists. It now runs on
four. This is what moved where, and what was dropped.

Read this if the site you are installing onto already carries the older lists. On a fresh
site it is background: `Create-ToolboxLists.ps1` builds the new four and nothing here
applies.

> The old columns below were read from SharePoint list exports, and **those exports silently
> omit Lookup columns** - nine of them across five lists, which is a trap this project fell
> into once already. So the old lists carried relationships that the tables here do not show.

---

## The mapping

| was | is now |
| --- | --- |
| `TB_Customers` | `TB_Customers`, trimmed |
| `TB_CustomerSolutions`<br>`TB_SolutionComponents`<br>`TB_SoftwareInstallations` | `TB_Installations` |
| `TB_ProductReferences`<br>`TB_CustomerReferences`<br>`TB_CustomerGuides` | `TB_References` |
| *nothing* | `TB_Products` |

Roughly 70 columns across seven lists became 26 across four.

---

## The three changes that matter

### A product catalogue now exists

The old lists stored model names as free text: `Solution Model`, `Component Model`,
`Software Name` and `Product Family` were all `Text` columns. Nothing tied *the CI 300X at
Northgate* to *the CI 300X* as a thing in its own right, so there was nowhere to record what
version a CI 300X is supposed to be on.

`TB_Products` is that missing list. It is why the app can now say "installed 4.0.1, standard
is K38" at all, and it is what the guided setup reads to suggest which components hang off a
solution.

### One self-referencing list replaced a three-level hierarchy

Solutions, their components, and software installed on them were three lists, and the shape
of the hierarchy was fixed by which list a row sat in.

`TB_Installations` has a `Parent` lookup pointing at its own list. A recycler hangs off the
machine it sits in because its `Parent` says so, not because it lives in a different list.
Depth is data now, not schema.

### References merged, with the customer lookup carrying the meaning

Three reference lists became one. `TB_References.Customer` is left **blank for a universal
document** and **set for a customer-specific exception**, which is what previously required
separate product and customer reference lists.

---

## What was dropped, and why

| dropped | how many | reason |
| --- | --- | --- |
| Computed display-name columns | 7 | one per list. The app composes its own titles - `"<customer> - <product>"` - so a stored copy could only go stale. |
| `Verified By` / `Reviewed By` (User) | 5 | there is no review workflow, and adding columns for one that was never built is how schemas rot. |
| `Last Verified` / `Last Reviewed` | 5 | same. Only `Last Checked` survives, on references, where it means something. |
| `Sort Order` / `Display Order` | 3 | galleries sort by Title. A manual order is a thing to maintain forever. |
| `Customer Code`, `Customer Logo` | 2 | never displayed. |
| `Restricted`, `Release Status`, `Windows Version`, `Required Component`, `Deployment Scope`, `Deployment Status` | 6 | no screen read them. `Status` on an installation covers what was actually used. |

Nothing here was deleted because it was wrong. It was deleted because no screen read it, and
a column nobody reads is a column somebody eventually has to explain.

---

## If the target site already has the old lists

`Create-ToolboxLists.ps1` will not touch `TB_CustomerSolutions` and the rest - it only knows
about the four new names. The two collide in one place:

**`TB_Customers` exists in both.** The old one has ten columns, the new one four, and only
`Title`, `Description`, `Support Notes` and `Active` are common. Pointing the app at the old
list would work for those four and fail on nothing else, because the app asks for no more
than that - but the extra columns would stay, and `Customer Name` being a computed column
tends to surprise people editing rows later.

Two options:

```powershell
# keep the old data, park the old list out of the way
.\Create-ToolboxLists.ps1 -SiteUrl <url> -ClientId <guid> -RenameLegacyCustomers
```

That renames the existing list to `TB_Customers_Legacy` and builds a clean one beside it, so
nothing is lost and nothing is in the way. Or delete the old seven lists first, if the data
in them is genuinely dead.

Run `Test-ToolboxSchema.ps1` afterwards either way. A `TB_Customers` that is *nearly* right
is the case most likely to look fine and behave strangely.

---

## Two footnotes from the old schema

`TB_CustomerSolutions` had a column named `Solution Famility`. It has no successor, so the
typo did not survive the rebuild.

`TB_CustomerGuides` is the one old list whose export could not be parsed - it is in a
different format from the other six. Its contents folded into `TB_References` along with the
other two reference lists, but the column-by-column detail is not recorded here.
