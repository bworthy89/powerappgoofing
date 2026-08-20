<#
.SYNOPSIS
    Creates the four Technician Toolbox SharePoint lists from scratch.

.DESCRIPTION
    Builds TB_Customers, TB_Products, TB_Installations and TB_References with the exact
    columns, types and choice values the redesigned app expects.

    Creation order is forced by the lookups: parent lists must exist before a lookup can
    point at them, and TB_Installations.Parent points at its own list, so that field is
    added after the list exists.

    Every choice column is created WITH its real values. SharePoint's default for a new
    choice column is "Choice 1 / Choice 2 / Choice 3", and that default reaching production
    is exactly how the previous generation of these lists ended up with a placeholder
    Deployment Status that surfaced in the app.

    Internal names are all prefixed TB to avoid collisions with SharePoint's built-in field
    names (Description, Status, Order, Category, URL and friends are all taken or risky).
    This is invisible to the app: Power Fx binds SharePoint columns by DISPLAY name, and the
    display names here are the clean ones.

.PARAMETER SiteUrl
    Full URL of the SharePoint site, e.g. https://contoso.sharepoint.com/sites/TechnicianToolbox

.PARAMETER ClientId
    Entra app registration client ID for PnP PowerShell. Since PnP.PowerShell 2.x you must
    bring your own app registration; see README.md for the one-line command that creates it.

.PARAMETER RenameLegacyCustomers
    Renames an existing TB_Customers list to TB_Customers_Legacy before creating the new one.
    Without this switch the script stops if TB_Customers already exists, rather than guessing.

.PARAMETER SkipConnect
    Use an existing PnP connection instead of opening a new one.

.EXAMPLE
    # Dry run first - shows every action, changes nothing
    ./Create-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TT -ClientId <guid> -WhatIf

.EXAMPLE
    ./Create-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TT -ClientId <guid> -RenameLegacyCustomers

.NOTES
    UNVERIFIED. Written without access to a SharePoint tenant and never executed. Run with
    -WhatIf first, and expect to correct at least one thing.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)][string]$SiteUrl,
    [string]$ClientId,
    [switch]$RenameLegacyCustomers,
    [switch]$SkipConnect
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$FieldGroup = 'Technician Toolbox'

# ---------------------------------------------------------------------------
# Schema. One definition, driving creation, defaults and views.
# ---------------------------------------------------------------------------

$ReferenceTypes = @(
    # Documentation section
    'Service Manual'
    'Installation Manual'
    'Error Code Manual'
    'Technical Bulletin'
    'Technical Alert'
    'Product Specification'
    'Customer Specific'
    # Firmware & downloads section
    'Machine Firmware'
    'BV Firmware'
    'Software Download'
    'Driver'
    'Support Tool'
)

$ProductTypes = @(
    'Solution'
    'Note Recycler'
    'Coin Recycler'
    'Drop Vault'
    'Printer'
    'Scanner'
    'Biometric'
    'PC'
    'UPS'
)

$Schema = [ordered]@{

    'TB_Customers' = @{
        Description = 'Customers. One row per customer, not per site.'
        TitleLabel  = 'Customer'
        Fields      = @(
            @{ Display = 'Description';   Internal = 'TBDescription';  Type = 'Note';    Lines = 3 }
            @{ Display = 'Support Notes'; Internal = 'TBSupportNotes'; Type = 'Note';    Lines = 6 }
            @{ Display = 'Active';        Internal = 'TBActive';       Type = 'Boolean'; Default = '1' }
        )
    }

    'TB_Products' = @{
        Description = 'Model catalogue. Every solution model and every unit model.'
        TitleLabel  = 'Model'
        Fields      = @(
            @{ Display = 'Product Type';             Internal = 'TBProductType';     Type = 'Choice'; Choices = $ProductTypes }
            @{ Display = 'Family';                   Internal = 'TBFamily';          Type = 'Choice'; Choices = @('CashInfinity','Retail','Banking','Self Service') }
            @{ Display = 'Current Standard Version'; Internal = 'TBStandardVersion'; Type = 'Text' }
            @{ Display = 'Description';              Internal = 'TBDescription';     Type = 'Note';    Lines = 4 }
            @{ Display = 'Active';                   Internal = 'TBActive';          Type = 'Boolean'; Default = '1' }
        )
    }

    'TB_Installations' = @{
        Description = 'What each customer runs. One row per customer per model.'
        TitleLabel  = 'Row label'
        Fields      = @(
            @{ Display = 'Installed Version'; Internal = 'TBInstalledVersion'; Type = 'Text' }
            @{ Display = 'Status';            Internal = 'TBStatus';           Type = 'Choice'; Choices = @('In Service','Upgrade Planned','Retired'); Default = 'In Service' }
            @{ Display = 'Config Notes';      Internal = 'TBConfigNotes';      Type = 'Note';   Lines = 6 }
        )
        Lookups     = @(
            @{ Display = 'Customer'; Internal = 'TBCustomer'; Target = 'TB_Customers';     Required = $true  }
            @{ Display = 'Product';  Internal = 'TBProduct';  Target = 'TB_Products';      Required = $true  }
            @{ Display = 'Parent';   Internal = 'TBParent';   Target = 'TB_Installations'; Required = $false }
        )
    }

    'TB_References' = @{
        Description = 'Documents and firmware links, keyed to a model.'
        TitleLabel  = 'Document title'
        Fields      = @(
            @{ Display = 'Section';        Internal = 'TBSection';       Type = 'Choice';   Choices = @('Documentation','Firmware & Downloads') }
            @{ Display = 'Reference Type'; Internal = 'TBReferenceType'; Type = 'Choice';   Choices = $ReferenceTypes }
            @{ Display = 'URL';            Internal = 'TBUrl';           Type = 'URL' }
            @{ Display = 'Version';        Internal = 'TBVersion';       Type = 'Text' }
            @{ Display = 'Featured';       Internal = 'TBFeatured';      Type = 'Boolean';  Default = '0' }
            @{ Display = 'Last Checked';   Internal = 'TBLastChecked';   Type = 'DateTime' }
        )
        Lookups     = @(
            @{ Display = 'Product';  Internal = 'TBProduct';  Target = 'TB_Products';  Required = $true  }
            # Blank = applies to every customer. Set = this customer's exception.
            @{ Display = 'Customer'; Internal = 'TBCustomer'; Target = 'TB_Customers'; Required = $false }
        )
    }
}

# Column order in the default view. Chosen for grid-view data entry: the things you
# type most, leftmost, and lookups before the values that depend on them.
$ViewFields = @{
    'TB_Customers'     = @('Title','TBDescription','TBSupportNotes','TBActive')
    'TB_Products'      = @('Title','TBProductType','TBFamily','TBStandardVersion','TBDescription','TBActive')
    'TB_Installations' = @('Title','TBCustomer','TBParent','TBProduct','TBInstalledVersion','TBStatus','TBConfigNotes')
    'TB_References'    = @('Title','TBProduct','TBCustomer','TBSection','TBReferenceType','TBUrl','TBVersion','TBFeatured','TBLastChecked')
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step { param([string]$Message) Write-Host "  $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "  $Message" -ForegroundColor Green }
function Write-Skip { param([string]$Message) Write-Host "  $Message" -ForegroundColor DarkGray }

function Test-ListExists {
    param([string]$Title)
    $null -ne (Get-PnPList -Identity $Title -ErrorAction SilentlyContinue)
}

function Test-FieldExists {
    param([string]$List, [string]$InternalName)
    $null -ne (Get-PnPField -List $List -Identity $InternalName -ErrorAction SilentlyContinue)
}

function New-ToolboxList {
    param([string]$Title, [string]$Description)

    if (Test-ListExists -Title $Title) {
        Write-Skip "list $Title already exists, leaving it alone"
        return
    }
    if ($PSCmdlet.ShouldProcess($Title, 'Create list')) {
        New-PnPList -Title $Title -Template GenericList -OnQuickLaunch | Out-Null
        Set-PnPList -Identity $Title -Description $Description | Out-Null
        Write-Ok "created list $Title"
    }
}

function New-ToolboxField {
    param([string]$List, [hashtable]$Field)

    if (Test-FieldExists -List $List -InternalName $Field.Internal) {
        Write-Skip "$List.$($Field.Display) already exists"
        return
    }
    if (-not $PSCmdlet.ShouldProcess("$List.$($Field.Display)", "Add $($Field.Type) column")) { return }

    $params = @{
        List         = $List
        DisplayName  = $Field.Display
        InternalName = $Field.Internal
        Type         = $Field.Type
        Group        = $FieldGroup
    }
    if ($Field.ContainsKey('Choices')) { $params['Choices'] = $Field.Choices }

    Add-PnPField @params | Out-Null

    # Post-creation settings that Add-PnPField cannot express directly.
    $values = @{}
    if ($Field.ContainsKey('Default')) { $values['DefaultValue'] = $Field.Default }
    if ($Field.Type -eq 'Note') {
        # Plain text, not rich text. Rich text arrives in Power Apps as HTML markup.
        $values['RichText']      = $false
        $values['NumberOfLines'] = $(if ($Field.ContainsKey('Lines')) { $Field.Lines } else { 4 })
    }
    if ($Field.Type -eq 'DateTime') {
        $values['DisplayFormat'] = 0   # 0 = date only, 1 = date and time
    }
    if ($values.Count -gt 0) {
        Set-PnPField -List $List -Identity $Field.Internal -Values $values | Out-Null
    }

    Write-Ok "$List.$($Field.Display)  ($($Field.Type))"
}

function New-ToolboxLookup {
    param([string]$List, [hashtable]$Lookup)

    if (Test-FieldExists -List $List -InternalName $Lookup.Internal) {
        Write-Skip "$List.$($Lookup.Display) already exists"
        return
    }
    if (-not $PSCmdlet.ShouldProcess("$List.$($Lookup.Display)", "Add lookup to $($Lookup.Target)")) { return }

    $target = Get-PnPList -Identity $Lookup.Target
    $required = if ($Lookup.Required) { 'TRUE' } else { 'FALSE' }

    # Lookups have to go in as field XML: Add-PnPField cannot name a target list.
    $xml = @"
<Field Type="Lookup"
       DisplayName="$($Lookup.Display)"
       Name="$($Lookup.Internal)"
       StaticName="$($Lookup.Internal)"
       List="{$($target.Id)}"
       ShowField="Title"
       Required="$required"
       Group="$FieldGroup" />
"@

    Add-PnPFieldFromXml -List $List -FieldXml $xml | Out-Null
    Write-Ok "$List.$($Lookup.Display)  (lookup -> $($Lookup.Target))"
}

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Technician Toolbox - list provisioning" -ForegroundColor White
Write-Host "  site: $SiteUrl"
if ($WhatIfPreference) { Write-Host "  DRY RUN - nothing will be changed" -ForegroundColor Yellow }
Write-Host ""

if (-not $SkipConnect) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw "PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser"
    }
    Import-Module PnP.PowerShell
    Write-Step "connecting..."
    if ($ClientId) {
        Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
    } else {
        Connect-PnPOnline -Url $SiteUrl -Interactive
    }
}

# ---------------------------------------------------------------------------
# Sanity check - is this URL actually a web?
#
# A URL copied from the browser address bar usually is not. Paths ending in
# /sitepages, /lists/<name> or /<page>.aspx point inside a web, not at one, and
# every later cmdlet fails with a different and less helpful message.
# ---------------------------------------------------------------------------

try {
    $web = Get-PnPWeb -ErrorAction Stop
    Write-Ok "connected to web: $($web.Title)  [$($web.ServerRelativeUrl)]"
} catch {
    throw @"
Connected, but $SiteUrl is not a SharePoint web.

  $($_.Exception.Message)

This is almost always a URL copied from the browser while looking at a page or a
library. Strip it back to the site itself and try again:

  .../sites/team/SitePages/Home.aspx   ->  .../sites/team
  .../sites/team/Lists/Something       ->  .../sites/team

To find the right one, connect to the parent site and look:

  Connect-PnPOnline -Url https://<tenant>.sharepoint.com/sites/<site> -UseWebLogin
  Get-PnPSubWeb -Recurse | Select-Object Title, ServerRelativeUrl
  Get-PnPList | Select-Object Title

The web whose Get-PnPList shows your existing TB_* lists is the one to use.
Nothing has been changed.
"@
}

# ---------------------------------------------------------------------------
# Step 0 - the one name collision with the legacy set
# ---------------------------------------------------------------------------

Write-Host "Step 0 - legacy check" -ForegroundColor White

# Identify OUR list positively, and treat anything else as legacy.
#
# The reverse test - looking for a legacy-only column such as CustomerCode - fails
# dangerously: one false negative and the script skips list creation, then adds the
# new columns to the legacy list. Asking "is this ours?" fails safely instead, because
# an unrecognised list stops the run rather than being written to.
$legacyCustomersIsOld = $false
if (Test-ListExists -Title 'TB_Customers') {
    $isOurs = Test-FieldExists -List 'TB_Customers' -InternalName 'TBSupportNotes'
    $legacyCustomersIsOld = -not $isOurs
    if ($isOurs) { Write-Skip "TB_Customers is already the rebuilt list" }
}

if ($legacyCustomersIsOld) {
    if ($RenameLegacyCustomers) {
        if ($PSCmdlet.ShouldProcess('TB_Customers', 'Rename to TB_Customers_Legacy')) {
            Set-PnPList -Identity 'TB_Customers' -Title 'TB_Customers_Legacy' | Out-Null
            Write-Ok "renamed TB_Customers -> TB_Customers_Legacy"
        }
    } else {
        throw @"
TB_Customers already exists and is not the rebuilt list - it has no TBSupportNotes column,
so it is either the legacy list or something else this script did not create.

Re-run with -RenameLegacyCustomers to rename it to TB_Customers_Legacy, or rename it
yourself first. Nothing has been changed.
"@
    }
} else {
    Write-Skip "no legacy TB_Customers in the way"
}

# ---------------------------------------------------------------------------
# Step 1 - lists and their non-lookup columns
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Step 1 - lists and columns" -ForegroundColor White

foreach ($listName in $Schema.Keys) {
    $def = $Schema[$listName]
    New-ToolboxList -Title $listName -Description $def.Description

    foreach ($field in $def.Fields) {
        New-ToolboxField -List $listName -Field $field
    }
}

# ---------------------------------------------------------------------------
# Step 2 - lookups, once every target list exists
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Step 2 - lookups" -ForegroundColor White

foreach ($listName in $Schema.Keys) {
    $def = $Schema[$listName]
    if (-not $def.ContainsKey('Lookups')) { continue }
    foreach ($lookup in $def.Lookups) {
        New-ToolboxLookup -List $listName -Lookup $lookup
    }
}

# ---------------------------------------------------------------------------
# Step 3 - default views, ordered for grid-view data entry
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Step 3 - default views" -ForegroundColor White

foreach ($listName in $ViewFields.Keys) {
    if (-not (Test-ListExists -Title $listName)) { Write-Skip "$listName not present, skipping view"; continue }
    if ($PSCmdlet.ShouldProcess("$listName default view", 'Set columns')) {
        try {
            $view = Get-PnPView -List $listName | Where-Object { $_.DefaultView } | Select-Object -First 1
            if ($view) {
                Set-PnPView -List $listName -Identity $view.Id -Fields $ViewFields[$listName] | Out-Null
                Write-Ok "$listName view: $($ViewFields[$listName] -join ', ')"
            }
        } catch {
            Write-Warning "could not set the default view on ${listName}: $($_.Exception.Message)"
        }
    }
}

# ---------------------------------------------------------------------------
# Step 4 - verify, by reading back what is actually there
# ---------------------------------------------------------------------------

if (-not $WhatIfPreference) {
    Write-Host ""
    Write-Host "Step 4 - verification" -ForegroundColor White

    $problems = 0
    foreach ($listName in $Schema.Keys) {
        if (-not (Test-ListExists -Title $listName)) {
            Write-Warning "MISSING LIST: $listName"; $problems++; continue
        }
        Write-Host ""
        Write-Host "  $listName" -ForegroundColor White

        $expected = @()
        $expected += $Schema[$listName].Fields | ForEach-Object { $_ }
        if ($Schema[$listName].ContainsKey('Lookups')) {
            $expected += $Schema[$listName].Lookups | ForEach-Object { $_ }
        }

        foreach ($f in $expected) {
            $actual = Get-PnPField -List $listName -Identity $f.Internal -ErrorAction SilentlyContinue
            if ($null -eq $actual) {
                Write-Warning "    MISSING: $($f.Display)"; $problems++
            } else {
                $note = ''
                if ($f.ContainsKey('Choices')) {
                    # The whole point of scripting this: prove no Choice 1/2/3 survived.
                    $actualChoices = @($actual.Choices)
                    if ($actualChoices -contains 'Choice 1') {
                        Write-Warning "    PLACEHOLDER CHOICES on $($f.Display)"; $problems++
                    } else {
                        $note = "  [$($actualChoices.Count) choices]"
                    }
                }
                Write-Host "    ok  $($actual.Title)$note" -ForegroundColor Green
            }
        }
    }

    Write-Host ""
    if ($problems -eq 0) {
        Write-Host "All four lists verified. Nothing missing, no placeholder choices." -ForegroundColor Green
        Write-Host "Next: connect them as data sources in Power Apps Studio." -ForegroundColor Green
    } else {
        Write-Warning "$problems problem(s) found. Fix and re-run - the script skips what already exists."
    }
}

Write-Host ""
