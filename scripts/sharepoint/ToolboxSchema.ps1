<#
.SYNOPSIS
    The Technician Toolbox list schema - the single definition of what the four
    lists contain.

.DESCRIPTION
    Dot-sourced by Create-ToolboxLists.ps1, which builds the lists, and by
    Test-ToolboxSchema.ps1, which checks a live site against them. Keeping one
    copy is the point: the app's formulas address columns by display name, but
    the SharePoint connector binds by internal name, so a list built with
    different internal names compiles clean and returns nothing.

    Changing a column here means changing it in both the app and the seed CSVs.
#>

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
