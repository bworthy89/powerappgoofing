"""Flatten the provisioning scripts into one file you can paste into a PnP session.

deploy/New-ToolboxLists.ps1 is generated, never hand-edited. It is a splice of

    a config header, replacing the param() block
  + ToolboxSchema.ps1          - the schema
  + Create-ToolboxLists.ps1    - the helpers and the work, from after param()

so the schema and the creation logic each keep exactly one definition. Editing the
generated file would give them two.

Two substitutions make the body work outside a script file:

  $PSCmdlet       is only bound inside an advanced function. Pasted into a session it is
                  null, and every ShouldProcess call would throw. A stand-in object with
                  the same method keeps all those call sites untouched.

  $WhatIfPreference  is set by the -WhatIf switch, which a pasted script cannot receive.
                     It becomes $DryRun, which the header defines.

Usage:  python scripts/sharepoint/build_standalone.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "deploy" / "New-ToolboxLists.ps1"

schema = (HERE / "ToolboxSchema.ps1").read_text(encoding="utf-8")
creator = (HERE / "Create-ToolboxLists.ps1").read_text(encoding="utf-8")

# The schema file's comment header describes dot-sourcing, which no longer applies.
schema_body = schema[schema.index("$ReferenceTypes"):]

# Everything after the param() block. Set-StrictMode and $FieldGroup live in there.
body = creator[creator.index("$ErrorActionPreference"):]
body = body.replace(
    "# The schema lives in one file so the creator and the verifier cannot drift.\n"
    ". (Join-Path $PSScriptRoot 'ToolboxSchema.ps1')\n",
    schema_body)

assert "$PSCmdlet" in body and "$WhatIfPreference" in body
body = body.replace("$PSCmdlet.", "$Toolbox.")
body = body.replace("$WhatIfPreference", "$DryRun")
assert "ToolboxSchema.ps1" not in body, "schema was not inlined"

HEADER = '''<#
    Technician Toolbox - create the four SharePoint lists
    ======================================================

    GENERATED FILE. Built by scripts/sharepoint/build_standalone.py from
    ToolboxSchema.ps1 and Create-ToolboxLists.ps1. Edit those, then regenerate.

    One file, nothing to dot-source. Paste the whole thing into a PowerShell window
    with PnP.PowerShell installed.

    WHICH POWERSHELL depends on how you are signing in, and the two do not mix:

      With an Entra app registration - the supported route:
          PowerShell 7  (pwsh)
          Install-Module PnP.PowerShell -Scope CurrentUser
          set $ClientId below

      Without one - $UseWebLogin:
          Windows PowerShell 5.1  (powershell)
          Install-Module PnP.PowerShell -RequiredVersion 1.12.0 -Scope CurrentUser -Force -AllowClobber
          set $UseWebLogin = $true below

      -UseWebLogin was removed in PnP 2.0, and PnP 2.x and later will not load on 5.1,
      so each route needs its own module version. The script checks and says which you
      have if they do not match.

    THEN

      1. Edit the settings below.
      2. Paste the whole file. Read the output.
      3. Set $DryRun to $false, paste again.

    $DryRun is $true to begin with on purpose. The dry run is how you catch a wrong
    site URL before it creates four lists somewhere you did not intend.

    Safe to run more than once. Anything that already exists is left alone, so a
    partial run can simply be repeated.

    AFTERWARDS, verify with Test-ToolboxSchema.ps1. The app addresses columns by
    display name while the SharePoint connector binds by internal name, so a list
    that looks right in the browser can still return nothing to every formula in
    the app, with no error anywhere.
#>

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# The site, not a list and not a page. Ends at /sites/<something>, unless you are
# deliberately targeting a subsite.
$SiteUrl  = 'https://contoso.sharepoint.com/sites/TechnicianToolbox'

# From Register-PnPEntraIDAppForInteractiveLogin. A bare guid, no angle brackets.
# Leave as-is if you are using $UseWebLogin below.
$ClientId = '00000000-0000-0000-0000-000000000000'

# $true skips the Entra app registration entirely - but only works on
# PnP.PowerShell 1.12, which only runs on Windows PowerShell 5.1:
#
#     Install-Module PnP.PowerShell -RequiredVersion 1.12.0 -Scope CurrentUser -Force -AllowClobber
#
# The script checks and tells you if the version you have cannot do it.
$UseWebLogin = $false

# $true prints what would happen and changes nothing.
$DryRun   = $true

# ---------------------------------------------------------------------------

# Rename an existing TB_Customers to TB_Customers_Legacy rather than stopping.
# Only relevant on a site that carried an earlier version of these lists.
$RenameLegacyCustomers = $false

# Reuse a Connect-PnPOnline session you already opened, instead of connecting.
$SkipConnect = $false

# $PSCmdlet is bound only inside an advanced function, so it does not exist in a
# pasted script. This stand-in carries the same ShouldProcess method, which lets
# every call site below stay exactly as it is in Create-ToolboxLists.ps1.
$Toolbox = [pscustomobject]@{}
Add-Member -InputObject $Toolbox -MemberType ScriptMethod -Name ShouldProcess -Value {
    param([string]$Target, [string]$Action)
    if ($script:DryRun) {
        Write-Host "  What if: $Action -> $Target" -ForegroundColor Yellow
        return $false
    }
    return $true
}

if ($SiteUrl -notmatch '^https://[^/]+\\.sharepoint\\.com/') {
    throw "SiteUrl does not look like a SharePoint site: '$SiteUrl'. Expected something like https://contoso.sharepoint.com/sites/TechnicianToolbox"
}
if ($ClientId -eq '00000000-0000-0000-0000-000000000000' -and -not $SkipConnect -and -not $UseWebLogin) {
    throw "Set `$ClientId to the client id from Register-PnPEntraIDAppForInteractiveLogin, or set `$UseWebLogin, or set `$SkipConnect if you have already connected."
}

'''

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(HEADER + body, encoding="utf-8", newline="")
lines = (HEADER + body).count("\n")
print(f"wrote {OUT}  ({lines} lines)")
