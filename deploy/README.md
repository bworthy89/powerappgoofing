# Installing the Technician Toolbox in another environment

Written for moving the app out of the development tenant and into a work Power Apps
environment with its own SharePoint site.

Work through it in order. Steps 1 and 2 are independent of each other, but the app cannot
be pointed at lists that do not exist yet, so do the SharePoint half first.

---

## What you need before starting

| | |
| --- | --- |
| A SharePoint site | Site owner or better. A dedicated site is easier to permission than a subsite of something busy. |
| An Entra app registration | For PnP.PowerShell. See below - this is the step most likely to need someone else. |
| PowerShell 7.2 or later | `winget install Microsoft.PowerShell`. PnP.PowerShell 2.x and later refuse to load on Windows PowerShell 5.1, so **every command below runs in PowerShell 7**, not the blue Windows PowerShell window. |
| Maker access to both environments | To export from development and import at work. |

### The Entra app registration

PnP.PowerShell 2.x removed the old `-UseWebLogin` route, so every connection now needs a
`-ClientId`. If you cannot register applications in the work tenant, this is the point to
involve whoever can - it blocks everything else.

Start PowerShell 7 first - type `pwsh`, or launch "PowerShell 7" from Start - and check
before going further, because the failure mode is confusing:

```powershell
$PSVersionTable.PSVersion        # must be 7.x

Install-Module PnP.PowerShell -Scope CurrentUser
Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP Toolbox Provisioning" `
    -Tenant contoso.onmicrosoft.com `
    -Interactive
```

> Running this in Windows PowerShell 5.1 reports
> `The term 'Register-PnPEntraIDAppForInteractiveLogin' is not recognized`, which reads like
> a wrong cmdlet name or an out-of-date module. It is neither - the module simply is not
> there, and installing it into 5.1 will not help, because PnP.PowerShell 3.x requires
> PowerShell 7. Check `$PSVersionTable.PSVersion` before believing any "not recognized"
> error from these scripts.

That prints a client id and asks an administrator to consent. Keep the id - every script
below takes it.

---

## Step 1 - the SharePoint lists

### 1.1 Create them

```powershell
cd scripts\sharepoint
.\Create-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TechnicianToolbox `
                          -ClientId <guid> -WhatIf
```

`-WhatIf` first, every time. It prints what it would build without touching the site. When
the output looks right, run it again without the switch.

Four lists, 26 columns. `TB_Installations.Parent` is a lookup onto its own list, which is
what lets a recycler hang off the machine it sits in.

### 1.2 Check them

```powershell
.\Test-ToolboxSchema.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TechnicianToolbox `
                         -ClientId <guid>
```

**Do not skip this.** The app addresses columns by display name while the SharePoint
connector binds by internal name, so a list that looks perfectly correct in the browser can
return nothing to every formula in the app. There is no error when that happens - the app
compiles clean and the screens are simply empty. This script asserts both names, the column
types, the choice values, and that each lookup points at the list it should.

It exits non-zero on any failure, so it can gate a pipeline.

### 1.3 Seed data - probably not

`seed/*.csv` and `Import-ToolboxSeed.ps1` contain **demonstration data**: four invented
customers, eleven models, and their documents. Useful for a sandbox, wrong for a live
install.

Load it only if you want something to look at while testing. Otherwise start with empty
lists and add a real customer through the app's own guided setup, which is the flow you
want to exercise anyway.

```powershell
# only if you want the demo data
.\Import-ToolboxSeed.ps1 -SiteUrl <url> -ClientId <guid> -WhatIf
```

---

## Step 2 - the app

Two routes. Importing is fewer steps; pasting avoids the re-pointing problem in 2.3
entirely, because the app is built against the target site's lists from the start. If the
import gives trouble, follow `deploy/PASTE.md` instead of the rest of this section.

`pac canvas download` needs a Dataverse organisation in the environment. The development
environment has none, so the export is done through the maker portal.

### 2.1 Export from development

1. <https://make.powerapps.com> - development environment
2. **Apps**, find **Technician Toolbox**
3. **...** > **Export package (.zip)**
4. Give it a name and a version note, then **Export**

That produces a `.zip` package. A `.msapp` from Studio's **File > Save as > This computer**
also works and is smaller, but the package carries the app's metadata and is the better
thing to keep alongside a release.

### 2.2 Import at work

1. <https://make.powerapps.com> - work environment
2. **Apps** > **Import canvas app**
3. Upload the `.zip`, then **Import**

### 2.3 Re-point the data sources

**This is the step that catches people out.** The imported app still references the
development SharePoint site by URL and list id. Importing does not remap that, and there is
no prompt telling you so - the app opens, looks complete, and every gallery is empty.

For each of the four lists:

1. Open the app for editing
2. **Data** in the left rail
3. Remove the four `TB_*` data sources
4. **Add data** > **SharePoint** > your work connection > the work site
5. Tick all four lists and add them
6. **Save**, then **Publish**

Add all four before saving. `TB_Installations` has lookups into `TB_Customers` and
`TB_Products`, and adding it alone can leave those columns unresolved.

Because `Create-ToolboxLists.ps1` builds the same display names the app already uses, no
formulas need editing. That is the reason for step 1.2 - if the names differ, this is where
you find out, and the symptom is silence.

---

## Step 3 - verify

Walk the app once. Each of these exercises a different join, so a failure tells you which
half is wrong:

| check | proves |
| --- | --- |
| Home shows two cards and the search box | the app imported |
| Admin > Customers > Guided setup opens on step 1 | screen state initialises |
| Create a customer, add a solution, tick a component | writes reach SharePoint, and lookups resolve |
| Find a customer > the new customer > its solution | reads work, and the parent-child join is intact |
| Catalogue lists models | `TB_Products` is bound |

Then confirm the rows landed, rather than trusting the screens:

```powershell
Get-PnPListItem -List TB_Installations | ForEach-Object {
    '{0,4}  {1,-40} cust={2}' -f $_['ID'], $_['Title'], $_['TBCustomer'].LookupValue
}
```

An install that looks right and has written nothing is the failure mode this app has
produced most often. Check the data.

---

## Known sharp edges

- **No delete in the app.** Records are created and edited, never removed. Clearing test
  data means SharePoint or PnP. Delete `TB_Installations` rows before `TB_Customers` rows,
  or you leave lookups pointing at nothing.
- **Delegation.** Every list filter is delegable except a handful of `CountRows` calls and
  the choice-column comparisons, which SharePoint cannot delegate. Under the 500-row limit
  this does not matter. Past a few hundred installations, revisit
  `app/00_Setup.md`.
- **Updating the app later.** Export and import again, and re-point the data sources again.
  There is no build from source: `app/screens/*.pa.yaml` in this repository is a mirror of
  what was pushed through a live authoring session, not something that compiles to a
  `.msapp` on its own.
