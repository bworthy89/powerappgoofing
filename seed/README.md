# Seeding

Four CSV files, numbered in the order they must be pasted. This is sample data — invented
customers, invented URLs — built to exercise every state the app can render, not a record of a
real deployment.

## Paste order

**Order matters.** Lookups resolve on the parent's exact `Title` text, and the parent row must
already exist:

1. `1_TB_Customers.csv` and `2_TB_Products.csv` — no lookups, these are the roots
2. `3_TB_Installations.csv` — needs both `TB_Customers` (`Customer`) and `TB_Products`
   (`Product`); some rows also need `TB_Installations` itself (`Parent`, for units nested
   under a solution), so paste this file in one pass rather than a few rows at a time
3. `4_TB_References.csv` — needs `TB_Products` (`Product`), and `TB_Customers` (`Customer`) for
   the customer-specific exceptions only

For each file: open the list, **Edit in grid view**, paste the block under the matching headers.
Headers in each CSV are the list's display names exactly — they should already match the
column headers in grid view.

## The one rule that matters

A lookup column (`Customer`, `Parent`, `Product`) resolves by matching the parent's `Title`
column **exactly** — character for character, including spacing. There is no fuzzy match and no
error message. If a lookup value doesn't match any parent `Title` byte for byte, SharePoint
leaves that cell **blank** and moves on silently. A trailing space, a curly vs. straight
apostrophe, a title that was retyped instead of copied — any of these produces a silent blank,
not a paste failure.

Before pasting, run the checker:

```bash
python3 scripts/verify_seed.py seed
```

It reads all four CSVs and fails if any lookup value has no byte-for-byte match in the parent
list's `Title` column, or if any Choice-column value isn't one of the values the list actually
offers. Run it again on your own copy any time you hand-edit a seed file — the failure mode it
guards against produces no symptom until someone notices a gallery is quietly missing a row.

## Spotting a silently failed lookup after pasting

The checker only protects the files as committed; a `Title` retyped instead of copied straight
out of grid view can still slip through review by eye. After pasting `TB_Installations`, switch
to grid view and:

- Sort by `Product` and scan for blank cells — a blank `Product` means that row's Product value
  didn't match any `TB_Products` Title.
- Do the same sorting by `Customer`.
- For any row that should be nested under a solution, check `Parent` is not blank.

Do the equivalent for `TB_References`: sort by `Product` (required on every row) and by
`Customer` (blank is valid there — only rows meant to be customer-specific should have it set).

A blank lookup cell after paste looks identical to a lookup that was correctly left blank (e.g.
a universal reference's `Customer`, or a top-level installation's `Parent`). The only way to
tell them apart is to already know which rows were supposed to have a value — which is exactly
why the checker runs against the source CSVs before paste, rather than trying to audit
SharePoint after the fact.

## What this seed set covers

Run `python3 scripts/verify_seed.py seed` for the full breakdown; each state named in the task
appears at least once:

- an installation on standard, one off standard, and one with a blank `Installed Version`
- a product (`BIO 50`) with a blank `Current Standard Version`, so its currency badge suppresses
- a retired installation (`Coastway Fuel - UPS 1500`)
- an upgrade-planned installation (`Harbour Savings Bank - BV 300`), status alongside the chip
- a customer with no installations at all (`Riverside Self Service Ltd`)
- a reference with a blank `URL`, one with a blank `Last Checked`, and one over 12 months old
- a customer-specific reference (`Customer` set) sitting alongside universal references for the
  same product, for two different products
- a solution (`Northgate Retail Group - CI 300X`) with two units nested beneath it via `Parent`
