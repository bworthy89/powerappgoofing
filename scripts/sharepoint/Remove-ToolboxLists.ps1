<#
.SYNOPSIS
    Deletes the four Technician Toolbox lists so the build can be retried cleanly.

.DESCRIPTION
    Removes TB_References, TB_Installations, TB_Products and TB_Customers, in that order,
    because a list cannot be deleted while another list's lookup points at it.

    This exists so you can experiment. Run Create, look at what you got, run Remove, adjust,
    run Create again.

    It will NOT touch the legacy lists. TB_CustomerSolutions, TB_SolutionComponents,
    TB_SoftwareInstallations, TB_CustomerGuides, TB_ProductReferences, TB_CustomerReferences
    and TB_Customers_Legacy are all explicitly protected, and the script refuses to delete
    anything not on its own four-name list.

    Deleted lists go to the site recycle bin, so a mistake is recoverable from there.

.PARAMETER SiteUrl
    Full URL of the SharePoint site.

.PARAMETER ClientId
    Entra app registration client ID for PnP PowerShell.

.PARAMETER Force
    Skip the confirmation prompt. Without it you are asked once per list.

.EXAMPLE
    ./Remove-ToolboxLists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/TT -ClientId <guid> -WhatIf

.NOTES
    UNVERIFIED. Written without access to a SharePoint tenant and never executed.
    This one deletes things. Run it with -WhatIf first.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][string]$SiteUrl,
    [string]$ClientId,
    [switch]$Force,
    [switch]$SkipConnect
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Deletion order matters: a list holding a lookup target cannot go first.
# References points at Products and Customers; Installations points at both and at itself.
$Targets = @(
    'TB_References'
    'TB_Installations'
    'TB_Products'
    'TB_Customers'
)

# Anything not in $Targets is never touched. Named here so the intent is on the page.
$Protected = @(
    'TB_Customers_Legacy'
    'TB_CustomerSolutions'
    'TB_SolutionComponents'
    'TB_SoftwareInstallations'
    'TB_CustomerGuides'
    'TB_ProductReferences'
    'TB_CustomerReferences'
)

Write-Host ""
Write-Host "Technician Toolbox — remove the four rebuilt lists" -ForegroundColor White
Write-Host "  site: $SiteUrl"
Write-Host "  protected, will not be touched: $($Protected -join ', ')" -ForegroundColor DarkGray
if ($WhatIfPreference) { Write-Host "  DRY RUN — nothing will be deleted" -ForegroundColor Yellow }
Write-Host ""

if (-not $SkipConnect) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw "PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser"
    }
    Import-Module PnP.PowerShell
    if ($ClientId) {
        Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
    } else {
        Connect-PnPOnline -Url $SiteUrl -Interactive
    }
}

$removed = 0
foreach ($name in $Targets) {

    if ($Protected -contains $name) {
        # Belt and braces: this can only fire if someone edits the arrays badly.
        Write-Warning "$name is protected and will not be deleted"
        continue
    }

    $list = Get-PnPList -Identity $name -ErrorAction SilentlyContinue
    if ($null -eq $list) {
        Write-Host "  $name not present" -ForegroundColor DarkGray
        continue
    }

    if ($list.ItemCount -gt 0) {
        Write-Warning "$name holds $($list.ItemCount) item(s) — they go to the recycle bin with it"
    }

    if ($PSCmdlet.ShouldProcess($name, 'Delete list')) {
        Remove-PnPList -Identity $name -Force:$Force
        Write-Host "  deleted $name" -ForegroundColor Yellow
        $removed++
    }
}

Write-Host ""
if (-not $WhatIfPreference) {
    Write-Host "$removed list(s) deleted. They are in the site recycle bin if you need them back." -ForegroundColor White
    Write-Host "Re-run Create-ToolboxLists.ps1 to rebuild." -ForegroundColor White
}
Write-Host ""
