<#
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

if ($SiteUrl -notmatch '^https://[^/]+\.sharepoint\.com/') {
    throw "SiteUrl does not look like a SharePoint site: '$SiteUrl'. Expected something like https://contoso.sharepoint.com/sites/TechnicianToolbox"
}
if ($ClientId -eq '00000000-0000-0000-0000-000000000000' -and -not $SkipConnect -and -not $UseWebLogin) {
    throw "Set `$ClientId to the client id from Register-PnPEntraIDAppForInteractiveLogin, or set `$UseWebLogin, or set `$SkipConnect if you have already connected."
}

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

    'TB_SolutionUnits' = @{
        Description = 'Which unit models attach to which solution model. Standard marks the usual build.'
        TitleLabel  = 'Label'
        Fields      = @(
            @{ Display = 'Standard'; Internal = 'TBStandard'; Type = 'Boolean'; Default = '1' }
        )
        Lookups     = @(
            @{ Display = 'Solution'; Internal = 'TBSolution'; Target = 'TB_Products'; Required = $true }
            @{ Display = 'Unit';     Internal = 'TBUnit';     Target = 'TB_Products'; Required = $true }
        )
    }

    'TB_Admins' = @{
        Description = 'Who may reach the Admin section. Empty means everyone.'
        TitleLabel  = 'Name'
        Fields      = @(
            @{ Display = 'Person'; Internal = 'TBPerson'; Type = 'User' }
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
    'TB_SolutionUnits' = @('Title','TBSolution','TBUnit','TBStandard')
    'TB_Admins'        = @('Title','TBPerson')
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step { param([string]$Message) Write-Host "  $Message" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Message) Write-Host "  $Message" -ForegroundColor Green }
function Write-Skip { param([string]$Message) Write-Host "  $Message" -ForegroundColor DarkGray }

function Get-FieldChoices {
    # Get-PnPField hands back a generic CSOM Field, not a typed FieldChoice, so .Choices
    # is not there to read. SchemaXml is present on every field and carries the values.
    param($Field)
    try {
        $xml = [xml]$Field.SchemaXml
        return @($xml.SelectNodes('//CHOICES/CHOICE') | ForEach-Object { $_.InnerText })
    } catch {
        return @()
    }
}

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
    if ($Toolbox.ShouldProcess($Title, 'Create list')) {
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
    if (-not $Toolbox.ShouldProcess("$List.$($Field.Display)", "Add $($Field.Type) column")) { return }

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
    if (-not $Toolbox.ShouldProcess("$List.$($Lookup.Display)", "Add lookup to $($Lookup.Target)")) { return }

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
if ($DryRun) { Write-Host "  DRY RUN - nothing will be changed" -ForegroundColor Yellow }
Write-Host ""

if (-not $SkipConnect) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw "PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser"
    }
    Import-Module PnP.PowerShell
    $pnpVersion = (Get-Module PnP.PowerShell).Version

    Write-Step "connecting..."
    if ($UseWebLogin) {
        # -UseWebLogin was removed in PnP.PowerShell 2.0. It survives only in 1.12,
        # which in turn runs only on Windows PowerShell 5.1. Its attraction is that it
        # needs no Entra app registration and no admin consent - the reason to accept a
        # pinned, superseded module at all.
        if (-not (Get-Command Connect-PnPOnline).Parameters.ContainsKey('UseWebLogin')) {
            throw @"
-UseWebLogin does not exist in PnP.PowerShell $pnpVersion. It was removed in 2.0.

To use it, run this in Windows PowerShell 5.1, not PowerShell 7, with the last version
that has it:

    Install-Module PnP.PowerShell -RequiredVersion 1.12.0 -Scope CurrentUser -Force -AllowClobber

Otherwise drop -UseWebLogin and pass -ClientId instead, which needs an app registration
from Register-PnPEntraIDAppForInteractiveLogin.
"@
        }
        Connect-PnPOnline -Url $SiteUrl -UseWebLogin
    }
    elseif ($ClientId) {
        Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
    }
    else {
        throw @"
No way to authenticate. Pass one of:

  -ClientId <guid>   an Entra app registration, from Register-PnPEntraIDAppForInteractiveLogin.
                     Needs admin consent once. This is the supported route.

  -UseWebLogin       no app registration, but requires PnP.PowerShell 1.12 on Windows
                     PowerShell 5.1, and it fails under some conditional access policies.

  -SkipConnect       you have already run Connect-PnPOnline yourself.
"@
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
        if ($Toolbox.ShouldProcess('TB_Customers', 'Rename to TB_Customers_Legacy')) {
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
    if ($Toolbox.ShouldProcess("$listName default view", 'Set columns')) {
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

if (-not $DryRun) {
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
                try {
                    if ($f.ContainsKey('Choices')) {
                        # The whole point of scripting this: prove no Choice 1/2/3 survived.
                        $actualChoices = Get-FieldChoices -Field $actual
                        if ($actualChoices -contains 'Choice 1') {
                            Write-Warning "    PLACEHOLDER CHOICES on $($f.Display)"; $problems++
                        } elseif ($actualChoices.Count -ne $f.Choices.Count) {
                            Write-Warning "    $($f.Display): expected $($f.Choices.Count), found $($actualChoices.Count)"; $problems++
                        } else {
                            $note = "  [$($actualChoices.Count) choices]"
                        }
                    }
                } catch {
                    # A report must never abort the run.
                    $note = "  [could not read choices]"
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
