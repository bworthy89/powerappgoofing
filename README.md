# powerappgoofing

Paste-ready source for a SharePoint-backed Power Apps canvas app: a technician reference
tool that drills from customer, to installed solution, to component, and surfaces the
software versions, guides, documentation, and firmware that apply.

Start with [`app/README.md`](app/README.md) — it covers why this is a Code view paste kit
rather than an importable package, and the order the pieces have to go in.

```
app/
├── README.md                        paste order, failure recovery, design notes
├── 01_App_Properties.md             App.Formulas, OnStart, StartScreen, settings
└── screens/
    ├── scrCustomers.pa.yaml         Customer directory        (11 controls)
    ├── scrCustomerToolbox.pa.yaml   Customer toolbox          (16 controls)
    └── scrSolutionDetails.pa.yaml   Solution details          (49 controls)
```

The seven backing SharePoint lists (`TB_Customers`, `TB_CustomerSolutions`,
`TB_SolutionComponents`, `TB_SoftwareInstallations`, `TB_CustomerGuides`,
`TB_ProductReferences`, `TB_CustomerReferences`) must exist and be connected as data
sources before pasting.
