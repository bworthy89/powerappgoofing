# powerappgoofing

Paste-ready source for a SharePoint-backed Power Apps canvas app: a technician reference tool
that drills from customer, to installed solution, to component, and surfaces the software
versions, guides, documentation, and firmware that apply.

Start with [`app/00_Setup.md`](app/00_Setup.md) — Studio settings and data connections — then
[`app/01_App_Properties.md`](app/01_App_Properties.md) for App.Formulas, App.OnStart and
App.StartScreen. Canvas app source is Code-view paste, not an importable package; that
constraint, and why, is explained there.

```
app/
├── 00_Setup.md                      Studio settings, data connections
├── 01_App_Properties.md             App.Formulas, OnStart, StartScreen, settings
└── screens/
    ├── scrHome.pa.yaml              Landing screen — search, backlog, recently viewed
    ├── scrCustomers.pa.yaml         Customer directory
    ├── scrCustomerOverview.pa.yaml  One customer's solutions
    ├── scrCatalogue.pa.yaml         Product catalogue and universal documents
    ├── scrSolution.pa.yaml          One solution's version, units and documents
    └── scrUnit.pa.yaml              One unit's version and documents
```

## Data

Four SharePoint lists back the app: `TB_Customers`, `TB_Products`, `TB_Installations`,
`TB_References`. They must exist and be connected as data sources before pasting.

`seed/` holds sample CSVs, numbered in paste order, that exercise every state the app renders.
Run `python3 scripts/verify_seed.py seed` before pasting any of them — it catches a lookup
value that would otherwise fail to resolve silently. See `seed/README.md` for the full paste
procedure.

`scripts/verify_yaml.py app/screens` checks the screen files parse and reference only real
schema columns; run it before pasting any `.pa.yaml` file into Studio.

## archive/

The previous generation of this app — a different schema (seven lists instead of four) and a
different screen set. Kept as a record of what came before and of its own defects, not as
something to paste. See `archive/README.md`.
