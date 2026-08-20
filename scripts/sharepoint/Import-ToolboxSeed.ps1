<#
.SYNOPSIS
    Imports the seed CSVs into the four Technician Toolbox lists.

.DESCRIPTION
    Grid-view paste resolves a lookup by matching the parent's Title text, and a mismatch fails
    SILENTLY - the row lands with an empty cell and nothing says so. This script resolves every
    lookup to a real item ID and stops with a named error if one cannot be resolved, which is the
    whole reason to prefer it.

    Order is forced by the lookups, and Parent points at TB_Installations itself:

      1. TB_Customers and TB_Products      - no lookups, these are the roots
      2. TB_Installations, pass 1          - Customer and Product resolved, Parent left blank
      3. TB_Installations, pass 2          - Parent resolved now that every row has an ID
      4. TB_References                     - Product, and Customer for the exceptions

    Values are set by INTERNAL name (TBCustomer, TBStandardVersion...) because that is what
    Add-PnPListItem takes. The CSV headers are DISPLAY names, because that is what the SharePoint
    grid shows and what Power Fx binds. The map between them lives in $FIELD_MAP below.

.PARAMETER SiteUrl
    Full URL of the SharePoint web, e.g. https://contoso.sharepoint.com/sites/team/toolbox

.PARAMETER SeedPath
    Folder holding the four numbered CSVs. Defaults to ../../seed relative to this script.

.PARAMETER Replace
    Delete every existing item from the four lists first. Without it the script refuses to run
    against a list that already has rows, rather than creating duplicates.

.PARAMETER SkipConnect
    Use an existing PnP connection instead of opening one.

.EXAMPLE
    Connect-PnPOnline -Url https://contoso.sharepoint.com/sites/team/toolbox -UseWebLogin
    .\Import-ToolboxSeed.ps1 -SiteUrl https://contoso.sharepoint.com/sites/team/toolbox -SkipConnect -WhatIf

.NOTES
    UNVERIFIED. Written without access to a SharePoint tenant and never executed.
    Run with -WhatIf first. Every earlier script in this folder needed at least one correction on
    first contact.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SiteUrl,
    [string]$SeedPath,
    [switch]$Replace,
    [switch]$SkipConnect
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $SeedPath) {
    $SeedPath = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'seed'
}

# CSV header (display name) -> SharePoint internal name.
$FIELD_MAP = @{
    'TB_Customers' = @{
        'Title' = 'Title'; 'Description' = 'TBDescription'
        'Support Notes' = 'TBSupportNotes'; 'Active' = 'TBActive'
    }
    'TB_Products' = @{
        'Title' = 'Title'; 'Product Type' = 'TBProductType'; 'Family' = 'TBFamily'
        'Current Standard Version' = 'TBStandardVersion'; 'Description' = 'TBDescription'
        'Active' = 'TBActive'
    }
    'TB_Installations' = @{
        'Title' = 'Title'; 'Customer' = 'TBCustomer'; 'Parent' = 'TBParent'
        'Product' = 'TBProduct'; 'Installed Version' = 'TBInstalledVersion'
        'Status' = 'TBStatus'; 'Config Notes' = 'TBConfigNotes'
    }
    'TB_References' = @{
        'Title' = 'Title'; 'Product' = 'TBProduct'; 'Customer' = 'TBCustomer'
        'Section' = 'TBSection'; 'Reference Type' = 'TBReferenceType'; 'URL' = 'TBUrl'
        'Version' = 'TBVersion'; 'Featured' = 'TBFeatured'; 'Last Checked' = 'TBLastChecked'
    }
}

# Which CSV columns are lookups, and into which list.
$LOOKUPS = @{
    'TB_Installations' = @{ 'Customer' = 'TB_Customers'; 'Product' = 'TB_Products'; 'Parent' = 'TB_Installations' }
    'TB_References'    = @{ 'Product'  = 'TB_Products';  'Customer' = 'TB_Customers' }
}

$BOOLEANS = @('Active', 'Featured')
$DATES    = @('Last Checked')

function Write-Ok   { param([string]$m) Write-Host "  $m" -ForegroundColor Green }
function Write-Step { param([string]$m) Write-Host "  $m" -ForegroundColor Cyan }
function Write-Skip { param([string]$m) Write-Host "  $m" -ForegroundColor DarkGray }

function Get-SeedRows {
    param([string]$FileName)
    $path = Join-Path $SeedPath $FileName
    if (-not (Test-Path $path)) { throw "seed file not found: $path" }
    return @(Import-Csv -Path $path)
}

function ConvertTo-FieldValues {
    <#  Turn one CSV row into the @{internalName = value} hashtable Add-PnPListItem wants.
        $TitleMaps is a hashtable of listName -> (Title -> ID) for resolving lookups. #>
    param(
        [string]$ListName,
        [psobject]$Row,
        [hashtable]$TitleMaps,
        [string[]]$SkipColumns = @()
    )

    $map    = $FIELD_MAP[$ListName]
    $values = @{}

    foreach ($display in $map.Keys) {
        if ($SkipColumns -contains $display) { continue }
        if (-not ($Row.PSObject.Properties.Name -contains $display)) { continue }

        $raw = $Row.$display
        # A genuinely blank cell is meaningful in this schema - a blank Installed Version is the
        # "not recorded" state, a blank Customer means a universal reference. Leave them unset.
        if ($null -eq $raw -or $raw -eq '') { continue }

        $internal = $map[$display]

        if ($LOOKUPS.ContainsKey($ListName) -and $LOOKUPS[$ListName].ContainsKey($display)) {
            $targetList = $LOOKUPS[$ListName][$display]
            if (-not $TitleMaps[$targetList].ContainsKey($raw)) {
                throw "row '$($Row.Title)': $display = '$raw' does not match any Title in $targetList. This is the silent failure the script exists to prevent."
            }
            $values[$internal] = $TitleMaps[$targetList][$raw]
        }
        elseif ($BOOLEANS -contains $display) {
            $values[$internal] = ($raw -eq 'Yes' -or $raw -eq 'TRUE' -or $raw -eq 'True' -or $raw -eq '1')
        }
        elseif ($DATES -contains $display) {
            $values[$internal] = [datetime]::Parse($raw)
        }
        else {
            $values[$internal] = $raw
        }
    }
    return $values
}

function Clear-ToolboxList {
    param([string]$ListName)
    $items = Get-PnPListItem -List $ListName -PageSize 500
    if (-not $items -or $items.Count -eq 0) { Write-Skip "$ListName already empty"; return }
    if ($PSCmdlet.ShouldProcess($ListName, "Delete $($items.Count) item(s)")) {
        foreach ($i in $items) { Remove-PnPListItem -List $ListName -Identity $i.Id -Force | Out-Null }
        Write-Ok "$ListName cleared ($($items.Count) removed)"
    }
}

# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Technician Toolbox - seed import" -ForegroundColor White
Write-Host "  site: $SiteUrl"
Write-Host "  seed: $SeedPath"
if ($WhatIfPreference) { Write-Host "  DRY RUN - nothing will be written" -ForegroundColor Yellow }
Write-Host ""

if (-not $SkipConnect) {
    Import-Module PnP.PowerShell
    Connect-PnPOnline -Url $SiteUrl -UseWebLogin
}

# Fail early and clearly if this PnP version lacks what we need.
foreach ($c in @('Get-PnPListItem', 'Add-PnPListItem', 'Remove-PnPListItem', 'Get-PnPWeb')) {
    if (-not (Get-Command $c -ErrorAction SilentlyContinue)) {
        throw "$c is not available in this PnP.PowerShell version. Nothing has been changed."
    }
}

try {
    $web = Get-PnPWeb -ErrorAction Stop
    Write-Ok "connected to web: $($web.Title)"
} catch {
    throw "Connected, but $SiteUrl is not a SharePoint web. Strip the URL back to .../sites/<site>. Nothing has been changed."
}

# --- guard against duplicating existing data -------------------------------

$lists = @('TB_Customers', 'TB_Products', 'TB_Installations', 'TB_References')
foreach ($l in $lists) {
    $existing = @(Get-PnPListItem -List $l -PageSize 500)
    if ($existing.Count -gt 0) {
        if ($Replace) {
            Clear-ToolboxList -ListName $l
        } else {
            throw "$l already holds $($existing.Count) item(s). Re-run with -Replace to clear the four lists first, or empty them yourself. Nothing has been changed."
        }
    }
}

$TitleMaps = @{ 'TB_Customers' = @{}; 'TB_Products' = @{}; 'TB_Installations' = @{} }

# --- step 1: the two root lists --------------------------------------------

Write-Host ""
Write-Host "Step 1 - roots" -ForegroundColor White

foreach ($pair in @(@('TB_Customers','1_TB_Customers.csv'), @('TB_Products','2_TB_Products.csv'))) {
    $listName = $pair[0]; $file = $pair[1]
    foreach ($row in (Get-SeedRows -FileName $file)) {
        $values = ConvertTo-FieldValues -ListName $listName -Row $row -TitleMaps $TitleMaps
        if ($PSCmdlet.ShouldProcess("$listName / $($row.Title)", 'Add item')) {
            $item = Add-PnPListItem -List $listName -Values $values
            $TitleMaps[$listName][$row.Title] = $item.Id
        } else {
            $TitleMaps[$listName][$row.Title] = -1   # so a dry run can still resolve lookups
        }
    }
    Write-Ok "$listName : $($TitleMaps[$listName].Count) row(s)"
}

# --- step 2: installations, Parent deferred --------------------------------

Write-Host ""
Write-Host "Step 2 - installations (Parent deferred)" -ForegroundColor White

$installRows = Get-SeedRows -FileName '3_TB_Installations.csv'
foreach ($row in $installRows) {
    $values = ConvertTo-FieldValues -ListName 'TB_Installations' -Row $row -TitleMaps $TitleMaps -SkipColumns @('Parent')
    if ($PSCmdlet.ShouldProcess("TB_Installations / $($row.Title)", 'Add item')) {
        $item = Add-PnPListItem -List 'TB_Installations' -Values $values
        $TitleMaps['TB_Installations'][$row.Title] = $item.Id
    } else {
        $TitleMaps['TB_Installations'][$row.Title] = -1
    }
}
Write-Ok "TB_Installations : $($TitleMaps['TB_Installations'].Count) row(s)"

# --- step 3: second pass, resolve Parent -----------------------------------

Write-Host ""
Write-Host "Step 3 - installations (Parent resolved)" -ForegroundColor White

$parented = 0
foreach ($row in $installRows) {
    if ([string]::IsNullOrEmpty($row.Parent)) { continue }
    if (-not $TitleMaps['TB_Installations'].ContainsKey($row.Parent)) {
        throw "row '$($row.Title)': Parent = '$($row.Parent)' does not match any installation Title."
    }
    $childId  = $TitleMaps['TB_Installations'][$row.Title]
    $parentId = $TitleMaps['TB_Installations'][$row.Parent]
    if ($PSCmdlet.ShouldProcess("TB_Installations / $($row.Title)", "Set Parent = $($row.Parent)")) {
        Set-PnPListItem -List 'TB_Installations' -Identity $childId -Values @{ 'TBParent' = $parentId } | Out-Null
    }
    $parented++
}
Write-Ok "$parented row(s) given a Parent"

# --- step 4: references ----------------------------------------------------

Write-Host ""
Write-Host "Step 4 - references" -ForegroundColor White

$refCount = 0
foreach ($row in (Get-SeedRows -FileName '4_TB_References.csv')) {
    $values = ConvertTo-FieldValues -ListName 'TB_References' -Row $row -TitleMaps $TitleMaps
    if ($PSCmdlet.ShouldProcess("TB_References / $($row.Title)", 'Add item')) {
        Add-PnPListItem -List 'TB_References' -Values $values | Out-Null
    }
    $refCount++
}
Write-Ok "TB_References : $refCount row(s)"

# --- verify ----------------------------------------------------------------

if (-not $WhatIfPreference) {
    Write-Host ""
    Write-Host "Verification" -ForegroundColor White
    $problems = 0
    foreach ($l in $lists) {
        $n = @(Get-PnPListItem -List $l -PageSize 500).Count
        Write-Host "  $l : $n item(s)" -ForegroundColor Green
    }

    # The failure this script exists to prevent: a lookup that did not resolve.
    foreach ($i in (Get-PnPListItem -List 'TB_Installations' -PageSize 500)) {
        if (-not $i['TBCustomer']) { Write-Warning "  installation $($i.Id) has no Customer"; $problems++ }
        if (-not $i['TBProduct'])  { Write-Warning "  installation $($i.Id) has no Product";  $problems++ }
    }
    foreach ($i in (Get-PnPListItem -List 'TB_References' -PageSize 500)) {
        if (-not $i['TBProduct']) { Write-Warning "  reference $($i.Id) has no Product"; $problems++ }
    }

    Write-Host ""
    if ($problems -eq 0) {
        Write-Host "Every lookup resolved. Refresh the app and press F5." -ForegroundColor Green
    } else {
        Write-Warning "$problems unresolved lookup(s). Re-run with -Replace after fixing the CSVs."
    }
}

Write-Host ""
