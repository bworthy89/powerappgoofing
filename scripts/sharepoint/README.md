# Provisioning the Technician Toolbox lists

Three scripts and a shared schema.

| file | what it does |
| --- | --- |
| `ToolboxSchema.ps1` | The definition of the four lists. Dot-sourced by the others, so creation and verification cannot drift apart. |
| `Create-ToolboxLists.ps1` | Builds the lists, columns, choices and default views. Idempotent. |
| `Test-ToolboxSchema.ps1` | Read-only check that a site matches. Run it before pointing the app at anything. |
| `Remove-ToolboxLists.ps1` | Removes them, so you can try again. |

For a full install into another tenant, follow `deploy/README.md` instead - this file covers
the SharePoint half only.

> **Run and proven**, on 2026-08-21, against a real tenant: PowerShell 7 with
> PnP.PowerShell 3.4.1, connecting interactively with `-ClientId`. They built all four lists
> and 26 columns on the first attempt, and `Test-ToolboxSchema.ps1` now passes 22 checks
> against the result.
>
> Still use `-WhatIf` first on a site that matters. The scripts are idempotent - they skip
> anything that already exists - but a dry run is how you catch a wrong `-SiteUrl` before it
> creates four lists somewhere unintended.

## What gets created

| List | Purpose | Columns |
|---|---|---|
| `TB_Customers` | One row per customer. Not per site. | Title, Description, Support Notes, Active |
| `TB_Products` | The model catalogue — every solution model and every unit model | Title, Product Type, Family, Current Standard Version, Description, Active |
| `TB_Installations` | What each customer runs, one row per customer per model | Title, Customer, Parent, Product, Installed Version, Status, Config Notes |
| `TB_References` | Documents and firmware links, keyed to a model | Title, Product, Customer, Section, Reference Type, URL, Version, Featured, Last Checked |
| `TB_SolutionUnits` | Which unit models attach to which solution model | Title, Solution, Unit, Standard |
| `TB_Admins` | Who may reach the Admin section. Empty means everyone. | Title, Person |

32 columns across six lists, including the `Title` column SharePoint provides on each.

## Prerequisites

Which set you need depends on your PowerShell version. Check first:

```powershell
$PSVersionTable.PSVersion
```

### On Windows PowerShell 5.1 (the default on Windows)

PnP.PowerShell 2.x and later require PowerShell 7 and will not work here. Pin to 1.12.0, the last
5.1-compatible release. In exchange you get `-UseWebLogin`, which needs **no Entra app registration
and no admin consent** — a real advantage if you do not administer the tenant.

```powershell
# 5.1 defaults to TLS 1.0; PSGallery refuses it
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force -Scope CurrentUser
Install-Module PnP.PowerShell -RequiredVersion 1.12.0 -Scope CurrentUser -Force -AllowClobber

Get-Module -ListAvailable PnP.PowerShell | Select-Object Name, Version   # expect 1.12.0
```

Connect separately, then run the script with `-SkipConnect` so it reuses your session:

```powershell
Connect-PnPOnline -Url https://contoso.sharepoint.com/sites/TechnicianToolbox -UseWebLogin
```

`-UseWebLogin` can fail under conditional access policies, and it does not exist in 2.x. Treat it
as the route that gets you moving, not the permanent one.

### On PowerShell 7

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

2.x and later need **your own Entra app registration**; the shared multi-tenant app was retired.
One command, run once, prints the client ID you pass to both scripts:

```powershell
Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP PowerShell — Technician Toolbox" `
    -Tenant contoso.onmicrosoft.com `
    -Interactive
```

This needs someone who can consent to app permissions in your tenant. If that is not you, this is
the step to take to whoever administers it. Everything else is ordinary site-owner work.

> `Register-PnPEntraIDAppForInteractiveLogin` does not exist in 1.12. On 5.1 the equivalent is
> `Register-PnPAzureADApp`, but with `-UseWebLogin` you do not need either.

### Either way

You need **site owner or full control** on the target site.

## Running it

Dry run first. It prints every action and changes nothing:

```powershell
# PowerShell 5.1 — after Connect-PnPOnline -UseWebLogin
./Create-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TechnicianToolbox -SkipConnect -WhatIf

# PowerShell 7 — let the script connect
./Create-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TechnicianToolbox -ClientId <guid> -WhatIf
```

Then for real:

```powershell
# PowerShell 5.1
./Create-ToolboxLists.ps1 -SiteUrl <url> -SkipConnect -RenameLegacyCustomers

# PowerShell 7
./Create-ToolboxLists.ps1 -SiteUrl <url> -ClientId <guid> -RenameLegacyCustomers
```

`-RenameLegacyCustomers` handles the single name collision with the old schema: it renames the
existing `TB_Customers` to `TB_Customers_Legacy` so the new list can take the clean name. Without
the switch the script stops rather than guessing. It only fires if the existing list actually
looks legacy — it checks for a `CustomerCode` column first.

The script is **re-runnable**. It skips anything that already exists, so if it fails halfway you
fix the cause and run it again rather than cleaning up by hand.

## Starting over

```powershell
# PowerShell 5.1, after Connect-PnPOnline -UseWebLogin
./Remove-ToolboxLists.ps1 -SiteUrl <url> -SkipConnect -WhatIf   # look first
./Remove-ToolboxLists.ps1 -SiteUrl <url> -SkipConnect

# PowerShell 7
./Remove-ToolboxLists.ps1 -SiteUrl <url> -ClientId <guid> -WhatIf
```

Deletes only those four lists, in an order that respects the lookups, and refuses to touch any
of the legacy ones. Everything lands in the site recycle bin.

## Decisions the script encodes

Four things in here are deliberate rather than incidental.

**Every choice column is created with its real values.** SharePoint defaults a new choice column
to `Choice 1 / Choice 2 / Choice 3`. That default reaching production is exactly how the old
`TB_CustomerSolutions.Deployment Status` ended up as a placeholder that surfaced in the app. The
verification pass at the end fails the run if it finds `Choice 1` anywhere.

**Internal names are prefixed `TB`, display names are clean.** `Description`, `Status`, `Order`,
`Category` and `URL` are all either taken by SharePoint or risky as internal names. Prefixing
sidesteps every collision, and it costs nothing in the app: Power Fx binds SharePoint columns by
**display** name, so formulas still read `ThisItem.'Config Notes'`.

**Multi-line columns are plain text, not rich text.** SharePoint defaults these to rich text,
which arrives in Power Apps as raw HTML markup in a label.

**`Last Checked` is date-only.** No time component to render or ignore.

## Creation order

Forced by the lookups, and the script does it for you:

1. `TB_Customers` and `TB_Products` — no lookups, these are the roots
2. `TB_Installations` — needs Customers and Products
3. `TB_References` — needs Products and Customers
4. Lookups added in a second pass, once every target list exists

`TB_Installations.Parent` points at `TB_Installations` itself, which is why lookups are a
separate pass rather than part of list creation.

## What this does not do

- **No data.** The lists come out empty. Seeding is a separate job.
- **No Power Apps work.** You still connect the four lists as data sources in Studio.
- **No permissions.** Site permissions are left exactly as they are.
- **Nothing to the legacy lists** beyond the one optional rename.

## If it goes wrong

The most likely failures, in the order you will meet them:

| Symptom | Cause |
|---|---|
| `Register-PnPEntraIDAppForInteractiveLogin` not recognised | You are on PowerShell 5.1 / PnP 1.12. Use `-UseWebLogin` instead |
| `Connect-PnPOnline` fails on client ID | App registration missing or unconsented (PowerShell 7 route only) |
| `There is no Web named ".../_vti_bin/sites.asmx"` | The `-SiteUrl` is a page or library path, not a web. Strip it back to `.../sites/<site>` |
| `Add-PnPFieldFromXml` fails on a lookup | The target list did not exist yet — re-run, since creation is idempotent |
| Access denied on `New-PnPList` | Not a site owner on that site |
| Default view not set | Non-fatal; the script warns and continues. Set the columns by hand in list settings |

Every step reports what it did. If a run stops partway, read the last green line to see how far
it got, then run it again.
