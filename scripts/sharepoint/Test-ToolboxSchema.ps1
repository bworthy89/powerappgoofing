<#
.SYNOPSIS
    Check a SharePoint site against the Technician Toolbox schema.

.DESCRIPTION
    Run this after Create-ToolboxLists.ps1, and before importing the app, on any
    site the app will point at.

    It exists because of how the two halves address columns differently. The
    app's formulas use display names - 'Installed Version', Customer, Product -
    while the SharePoint connector binds by internal name, TBInstalledVersion
    and friends. A list built by hand, or by a modified script, can look correct
    in the browser and still return nothing to every formula in the app. Nothing
    reports that: the app compiles clean and the screens are simply empty.

    So this asserts the internal names and types, not the display names.

    Read-only. It creates and changes nothing.

.PARAMETER SiteUrl
    The site to check, for example
    https://contoso.sharepoint.com/sites/TechnicianToolbox

.PARAMETER ClientId
    Entra app registration to authenticate with. Required by PnP.PowerShell 2.x
    and later. Omit only if you are connecting some other way and passing
    -SkipConnect.

.PARAMETER SkipConnect
    Reuse an existing Connect-PnPOnline session instead of opening one.

.EXAMPLE
    .\Test-ToolboxSchema.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TT -ClientId <guid>

.EXAMPLE
    Connect-PnPOnline -Url https://contoso.sharepoint.com/sites/TT -Interactive -ClientId <guid>
    .\Test-ToolboxSchema.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TT -SkipConnect
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SiteUrl,
    [string]$ClientId,
    [switch]$UseWebLogin,
    [switch]$SkipConnect
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'ToolboxSchema.ps1')

# SharePoint's TypeAsString for each schema Type. Lookups are checked separately
# because their target list matters as much as their type.
$ExpectedType = @{
    'Text'     = 'Text'
    'Note'     = 'Note'
    'Boolean'  = 'Boolean'
    'Choice'   = 'Choice'
    'URL'      = 'URL'
    'DateTime' = 'DateTime'
    'User'     = 'User'
}

$script:Failures = 0
function Pass { param([string]$m) Write-Host "  PASS  $m" -ForegroundColor Green }
function Fail { param([string]$m) $script:Failures++; Write-Host "  FAIL  $m" -ForegroundColor Red }
function Info { param([string]$m) Write-Host "  $m" -ForegroundColor DarkGray }

Write-Host ""
Write-Host "Technician Toolbox - schema check" -ForegroundColor Cyan
Write-Host "  site: $SiteUrl"
Write-Host ""

if (-not $SkipConnect) {
    Import-Module PnP.PowerShell
    if ($UseWebLogin) {
        if (-not (Get-Command Connect-PnPOnline).Parameters.ContainsKey('UseWebLogin')) {
            throw "-UseWebLogin does not exist in PnP.PowerShell $((Get-Module PnP.PowerShell).Version). It requires 1.12 on Windows PowerShell 5.1. Use -ClientId instead."
        }
        Connect-PnPOnline -Url $SiteUrl -UseWebLogin
    }
    elseif ($ClientId) {
        Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
    }
    else {
        throw "Pass -ClientId <guid>, or -UseWebLogin on PnP 1.12, or -SkipConnect if you have already connected."
    }
}

# A wrong site is the likeliest mistake, and every later failure would be a
# confusing consequence of it rather than a real schema problem.
try {
    $web = Get-PnPWeb
} catch {
    throw "Could not read $SiteUrl as a SharePoint web. Check the URL ends at the site, not a list or a page. $($_.Exception.Message)"
}
Info "connected to '$($web.Title)'"
Write-Host ""

foreach ($listName in $Schema.Keys) {
    Write-Host $listName -ForegroundColor White

    $list = $null
    try { $list = Get-PnPList -Identity $listName } catch { }
    if (-not $list) {
        Fail "list does not exist"
        Write-Host ""
        continue
    }
    Pass "list exists ($($list.ItemCount) items)"

    $fields = Get-PnPField -List $listName
    $byInternal = @{}
    foreach ($f in $fields) { $byInternal[$f.InternalName] = $f }

    foreach ($spec in $Schema[$listName].Fields) {
        $f = $byInternal[$spec.Internal]
        if (-not $f) {
            Fail "$($spec.Internal) missing  (display '$($spec.Display)')"
            continue
        }
        $want = $ExpectedType[$spec.Type]
        if ($f.TypeAsString -ne $want) {
            Fail "$($spec.Internal) is $($f.TypeAsString), expected $want"
            continue
        }
        if ($f.Title -ne $spec.Display) {
            # The app addresses columns by display name, so this breaks formulas
            # even though the internal name is right.
            Fail "$($spec.Internal) display name is '$($f.Title)', app expects '$($spec.Display)'"
            continue
        }
        if ($spec.Type -eq 'Choice' -and $spec.Choices) {
            $missing = @($spec.Choices | Where-Object { $_ -notin $f.Choices })
            if ($missing.Count -gt 0) {
                Fail "$($spec.Internal) is missing choices: $($missing -join ', ')"
                continue
            }
        }
        Pass "$($spec.Internal)  $($f.TypeAsString)"
    }

    foreach ($spec in $Schema[$listName].Lookups) {
        $f = $byInternal[$spec.Internal]
        if (-not $f) {
            Fail "$($spec.Internal) missing  (lookup to $($spec.Target))"
            continue
        }
        if ($f.TypeAsString -notlike 'Lookup*') {
            Fail "$($spec.Internal) is $($f.TypeAsString), expected a Lookup"
            continue
        }
        # A lookup pointing at the wrong list is the failure that looks most
        # like working software: the column exists, the type is right, and every
        # related record silently resolves to nothing.
        $targetList = $null
        try { $targetList = Get-PnPList -Identity $f.LookupList } catch { }
        $targetName = if ($targetList) { $targetList.Title } else { '<unresolved>' }
        if ($targetName -ne $spec.Target) {
            Fail "$($spec.Internal) points at '$targetName', expected '$($spec.Target)'"
            continue
        }
        if ($f.Required -ne [bool]$spec.Required) {
            Fail "$($spec.Internal) Required is $($f.Required), expected $([bool]$spec.Required)"
            continue
        }
        Pass "$($spec.Internal)  Lookup -> $targetName"
    }
    Write-Host ""
}

Write-Host ""
if ($script:Failures -eq 0) {
    Write-Host "All checks passed. This site matches what the app expects." -ForegroundColor Green
    exit 0
}
Write-Host "$($script:Failures) check(s) failed." -ForegroundColor Red
Write-Host "Fix these before importing the app. Every one of them produces an app that" -ForegroundColor Red
Write-Host "compiles cleanly and shows nothing, which is far harder to diagnose later." -ForegroundColor Red
exit 1
