# Expected version — design

The app currently compares a machine's recorded version against its model's current standard
and reports the result: *on standard*, *update available*, *not recorded*. This removes that
comparison everywhere and reports two things instead — the version we expect, and when it was
last verified.

Status: design agreed 2026-08-23, open questions resolved. Implementing.

## Why

The app does not read machines. Every version it holds is a record of what someone last
entered, and the comparison presented that record as a finding: *"update available"* reads as
an instruction derived from knowledge the app does not have.

The failure mode is quiet and expensive. A technician arrives expecting a machine to need
updating, finds it already on the current build, and stops trusting the number — and once
trust in the number is gone, the app has nothing else to offer.

Reporting the record and its age is a claim the app can actually support. A version verified
three weeks ago is worth acting on; the same version verified fourteen months ago is worth
checking. That distinction is more useful than a comparison against a standard, and it is
true.

## What changes

**The version panel** (`cmpVersionChip`)

```
EXPECTED VERSION
3.4.1
verified 14 months ago
```

No arrow, no standard version, no verdict line. The rail is coloured by **verification age**,
not by version currency.

**Unit rows** on `scrSolution` show the unit's expected version and its age. No arrow.

**Solution cards** on `scrCustomerOverview` show the same. The `N behind` count goes.

**The customer list** loses `N behind`. See the open question below for what replaces it.

**The catalogue** keeps `Current Standard Version` on a model. It is a real fact about the
product line and the right place to publish it — it simply stops being used to judge any
particular machine.

## New state model

Two states where there were four, plus age as a separate axis.

| Version | Reads |
|---|---|
| Recorded | the version |
| Not recorded | `not recorded` |

| Verified | Reads | Colour |
|---|---|---|
| Within 12 months | `verified 3 weeks ago` | muted |
| Over 12 months | `verified 14 months ago` | amber |
| Never | `never verified` | muted |

Twelve months matches the existing threshold on document *last checked*, so the app has one
rule for staleness rather than two.

The distinction that survives from the old model is the one worth keeping: **a version nobody
recorded is different from a version that is old**, and neither is shown as if it were fine.

## Schema

A `Last Verified` date column on two lists:

| List | Why |
|---|---|
| `TB_Installations` | when this machine's own version was last confirmed |
| `TB_SoftwareVersions` | when the site default was last confirmed |

Both, because the expected version can come from either, and a date that did not track its
source would misreport. The existing precedence is unchanged — a machine's own version wins
over the site default — and the displayed date follows whichever supplied the version.

Manual step in SharePoint. **Do not name the column `Last Verified` if the UI derives an
internal name that collides**; use display `Last Verified`, internal `TBLastVerified`, and see
the `Version` collision recorded in `app/00_Setup.md`.

## Not automatic

Editing a version does **not** set the date. Convenient, but wrong when an admin is
correcting a typo in an old record — that is not a verification, and stamping it as one
launders a guess into a fact. The field sits beside the version on the form so it is hard to
miss.

## Wording

`verified` is a stronger claim than `updated`. It is used here on the understanding that the
date means *someone confirmed this against the machine*. If in practice it will mean *when we
last typed something*, the honest word is `updated` and the design should change to match.

## Resolved

**What replaces `N behind` on the customer list:** staleness. A row reads
*"3 not verified in over a year"* in amber, counting machines at that site whose expected
version was last verified more than twelve months ago **or never**. It preserves the reason
to scan the screen, is derived from data the app holds, and points at a real action.

As before, a row stays quiet when there is nothing to say. The app never renders a green
"all good", because a site nobody has surveyed and a site genuinely up to date are still
indistinguishable — that reasoning is unchanged by this design.

**"Verified" is the honest word.** The date means someone confirmed the version against the
machine, not merely that a record was touched. The form must therefore not stamp it on an
ordinary edit; see *Not automatic* above.

## Consequences beyond the app

The published pitch and user guide both sell the comparison — *"expected to be behind"*,
*"three states, never two"* — and the three-state key is a section of the guide. Both are to
be rewritten **once the app changes are complete**, so the documentation is updated against
what actually shipped rather than against this design. `app/00_Setup.md` also records the four-state logic in several rules.

## Files

- `scripts/sharepoint/ToolboxSchema.ps1` — two date columns
- `app/components/cmpVersionChip.pa.yaml` — label, remove comparison, add `VerifiedOn`
- `scripts/screen_parts.py` — pass the date from whichever source supplied the version
- `scripts/gen_solution.py`, `gen_customer_overview.py`, `gen_customers.py` — remove the
  comparison and the counts
- `scripts/gen_admin.py` — the date field on both lists
- `deploy/SCHEMA-CHANGES.md` — the manual step

Paste: the component, `scrSolution`, `scrUnit`, `scrCustomerOverview`, `scrCustomers`,
`scrAdmin`, `scrEditForm`.
