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

## Add "Software" to TB_References → Section

One manual change, needed before customer-level software versions work.

**TB_References → Section** (internal name `TBSection`) is a Choice column. Add a third
value alongside the two that exist:

```
Documentation
Firmware & Downloads
Software          <- add this
```

List settings → Columns → Section → add `Software` to the choices → OK.

### What it enables

A `TB_References` row with **Customer**, **Product**, **Section = Software** and a
**Version** becomes the software version for every machine of that model at that site:

```
Customer  Northgate Retail Group
Product   CI 300X
Section   Software
Version   3.4.1
```

Every Northgate CI 300X with a blank Installed Version now shows 3.4.1 and is compared
against the model's Current Standard Version. A machine that has its own Installed Version
keeps it — the machine record always wins, so one unit on a different build stays visible
rather than being hidden by the site default.

Nothing is written to the installation records. This only changes what is displayed and
compared, so a site default can be corrected in one row.

### Two things to expect

- **`Choices()` is a cached snapshot.** The new value will not appear in the admin form's
  Section dropdown until the app is closed and reopened. This is the same trap recorded in
  `app/00_Setup.md`.
- **`Version` was previously write-only.** The admin form has always offered the field and
  nothing ever read it back, so any values already sitting in it will start having an
  effect. Worth a look at existing rows before adding new ones.

## Create TB_SoftwareVersions (replaces the earlier "Software" Section idea)

**The earlier instruction to add `Software` to TB_References → Section is withdrawn.** That
overloaded a pointer list: `TB_References.Version` means "the version of the document or
firmware being linked to", not "the software running at a site". Anyone adding a firmware
link with a version would have silently changed what machines reported as installed. If you
already added the choice value, removing it is optional — nothing reads it now.

### The list

**TB_SoftwareVersions**

| Display | Internal | Type | Required |
|---|---|---|---|
| Title | Title | Text | yes (label, e.g. `Northgate - CI 300X`) |
| Customer | TBCustomer | Lookup → TB_Customers | yes |
| Product | TBProduct | Lookup → TB_Products | yes |
| Software Version | TBSoftwareVersion | Text | no |

`scripts/sharepoint/ToolboxSchema.ps1` defines it, so `Create-ToolboxLists.ps1` and
`Test-ToolboxSchema.ps1` both cover it if you use them.

### What a row means

```
Customer          Northgate Retail Group
Product           CI 300X
Software Version  3.4.1
```

> **Do not name that column `Version`.** It collides with SharePoint's built-in item
> versioning, and a column created by hand in the UI ends up with an internal name Power
> Apps cannot resolve — the app reports `Name isn't valid. 'Version' isn't recognized` while
> the column looks perfectly normal in SharePoint. `TB_References` has a working `Version`
> column only because `Create-ToolboxLists.ps1` sets its internal name (`TBVersion`)
> explicitly, which the UI does not do.

*At this site, every CI 300X runs 3.4.1 — unless that machine's own Installed Version says
otherwise.*

The machine always wins, so one unit on a different build stays visible rather than being
hidden by the site default. Nothing is written back to installation records; this only
changes what is displayed and compared, so a site default is corrected in one row.

### In the app

Admin gains a **Software** tab between Solution units and References, with the same add,
edit and delete behaviour as the other lists. Rows read
`Northgate - CI 300X - Northgate Retail Group | CI 300X | 3.4.1`.

The solution and unit screens show the expected version and say when it came from here
rather than from the machine: *"verified 3 weeks ago · site default for this model"*.

---

## `Last Verified` on `TB_Installations` and `TB_SoftwareVersions`

Add one column to **each** of these two lists, by hand, **before pasting the screens**.

| Display | Internal | Type |
|---|---|---|
| Last Verified | TBLastVerified | Date and Time |

Set **Include Time** to *Date Only*. The app never reads a time from it, and a stored time
makes an age of "verified today" flip to "verified yesterday" depending on the hour.

> As with `Software Version`, check the internal name after creating it. SharePoint derives
> the internal name from whatever the column is first called, so a column created as
> `Last Verified` normally lands on `Last_x0020_Verified`, which is fine — the app refers to
> the **display** name. What breaks is renaming a column later: the display name changes and
> the internal name does not.

### What it means

**Someone confirmed this version against the machine on this date.** Not "when the record
was last touched". That distinction is the whole point: a version verified three weeks ago
is worth acting on, and the same version verified fourteen months ago is worth checking.

Both lists carry it because the expected version can come from either — a machine's own
`Installed Version` wins over the site default — and the date shown always follows whichever
one supplied the version.

### It is not set automatically

Editing a version does **not** stamp the date. That would be convenient and wrong: an admin
correcting a typo in a two-year-old record has not verified anything, and stamping it as a
verification launders a guess into a fact. The field sits directly beneath the version on
the admin form so it is hard to miss, and it can be left blank — blank reads as
*"never verified"*, which is honest.

### In the app

| Where | Shows |
|---|---|
| Version panel, solution and unit screens | the expected version, then `verified 3 weeks ago` |
| Unit rows on a solution | the version, with its age beneath |
| Solution cards on a customer | the same, plus `N to check` for its units |
| Customer list | `N to check` — machines at that site not verified in over a year, or ever |

Twelve months is the threshold, matching the one already used for a document's
`Last Checked`, so the app has one rule for staleness rather than two.

Nothing anywhere compares a machine against its model's `Current Standard Version` any more.
That column stays, and the catalogue still publishes it: it is a real fact about the product
line. It simply stopped being used to judge any particular machine, because the app has no
way to know what a machine is actually running.

## `Last Checked` on `TB_References` — no schema change, new field

This column already exists and always has. It had no field on the admin form, so the user
guide described setting a value there was no way to set. The References form now has a
**Last checked** date field. Nothing to create.
