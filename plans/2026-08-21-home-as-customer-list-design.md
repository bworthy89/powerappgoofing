# Home as the customer list

**Date:** 2026-08-21
**Status:** agreed, not yet built

## Why

The home screen opened with a `BACKLOG` card - a count of installations whose installed
version differs from the product's current standard, with a proportion bar - flanked by
`active customers` and `active models` figures. Those are management-reporting idioms:
numbers to look at rather than things to do.

They are also the wrong genre for this app. Technicians open the Toolbox to **find
information**, not to discover what is out of date or to work a queue. A tech already knows
there are four customers.

The data underneath the backlog card is not the problem, and it has not been deleted from
the lists. What was wrong was presenting it as a scoreboard on the screen that should be
getting someone to a record.

## What technicians actually arrive with

Established by asking, not assumed:

| question | answer |
| --- | --- |
| What is in their head on opening? | A customer or site name |
| How many customers, realistically? | 20 to 100 |
| Do they revisit the same sites? | No - genuinely varied |

Two consequences fall straight out. The customer is the way in, so home should be the
customer list rather than a menu that stands in front of it. And because sites vary, the
recently-viewed row cannot predict the next one wanted, so it is dead weight.

## Shape

`scrHome` becomes the customer list. `scrCustomers` is deleted; nine screens become eight.

```
Technician Toolbox         Catalogue    + New customer    Admin

  search customers, models, documents

  +----------------+ +----------------+ +----------------+
  | Coastway Fuel  | | Harbour Savings| | Northgate      |
  | Forecourt      | | Retail banking | | Regional super |
  | operator...    | | and one cash...| | market group...|
  +----------------+ +----------------+ +----------------+
```

Empty search box: browse customers. Two characters or more: the cards are replaced by
grouped Customers / Models / Documents results, exactly as the screen already behaves.

### Removed

| | |
| --- | --- |
| `conDashboard` and three KPI cards | 13 controls, including the proportion bar |
| `lblRecentHeading`, `btnRecent1`-`3` | 4 controls |
| `colRecent` machinery | `App.OnStart`'s `ClearCollect` / `Clear` / `LoadData`, and the `RemoveIf` / `Collect` / `SaveData` block in the gallery's `OnSelect` |
| `rectChip`, `lblChip` | the per-customer status chip |
| `lblAccent` and `IsSelected` styling | selection state has nothing to show when tapping navigates away |
| `btnTileCustomers` | home *is* the customer list |
| `scrCustomers` | whole screen |

Dropping the chips removes the two heaviest formulas in the app - each ran four nested
`CountRows` / `LookUp` passes per row - and with them about eight delegation warnings.

## Cards

Name and description only. The template shrinks from 130px to about 96px, so more
customers fit above the fold, which matters at 20-100 in a way it did not at 4.

Hover and pressed feedback stay on the transparent hit target, so a card still responds to
touch without carrying a selected state.

Only `Active = true` customers are listed. An inactive customer is one nobody should be
visiting.

## Navigation

Three destinations remain: Catalogue, New customer, Admin. They sit right-aligned in the
header as `ModernButton` with `Appearance.Subtle` and an icon, collapsing to
`ButtonLayout.IconOnly` when `IsNarrow`.

A bottom nav bar was considered and rejected: it would give Admin equal billing with the
customer list, and Admin is not an everyday technician destination.

## Search

No new mechanism. The customer list takes `conDashboard`'s slot and inherits its
visibility rule.

| control | visible when |
| --- | --- |
| customer list | `Len(Trim(txtSearchHome.Text)) < 2` |
| the three result galleries | `>= 2 && CountRows(Self.AllItems) > 0` |
| each result heading | follows its own gallery's `Visible` |
| `lblNoSearchResults` | `>= 2` and all three galleries empty |

The two-character threshold stays. One letter matches nearly everything and runs three
queries per keystroke.

Two empty states, kept distinct - conflating them is what made the wizard's step 3 look
broken when it was merely unpicked:

- no customers at all: *"No customers yet. Add one from New customer."*
- search found nothing: *"No matches for this search."*

## Build order

1. Move `galCustomers` and its template into `scrHome`, dropping the chip, accent and
   `IsSelected` conditionals. Names stay unique app-wide because `scrCustomers` goes in the
   same push.
2. Delete `conDashboard` and its children, and the recents controls.
3. Rebuild the header with the three navigation buttons.
4. `scrCustomers.Size` becomes `scrHome.Size` in the `WrapCount` switch.
5. `scrCustomerOverview`'s back link points at `scrHome`, relabelled `Home`.
6. `App.OnStart` loses the three `colRecent` lines.
7. Delete `scrCustomers.pa.yaml` from the push directory. `compile_canvas` mirrors, so its
   absence removes the screen - the one occasion that behaviour helps.

## Risks

`scrHome` is hand-written rather than generated, so there is no regeneration to fall back
on: check `verify_yaml.py` and control counts before pushing. `App.pa.yaml` changes, which
has broken this app before.

## Verification

Compile clean, then: home lists active customers only; two characters swaps to grouped
results; tapping a customer opens the overview and the back link returns home; Catalogue,
New customer and Admin are all reachable; narrow width collapses the navigation to icons.
Warning count should fall from 93 to roughly 85.

---

## Revision: action-led, not a list

**Built, deployed, and judged wrong.** Making home the customer list removed the KPI
numbers but left a grid of cards, which still read as a dashboard: *"we need a home page
that guides the user on what to do."*

The mistake was treating "not a dashboard" as a subtraction problem. Stripping the screen
to a bare list is efficient for someone who already knows the app and says nothing to
anyone who does not. A home screen has to answer *what is this, and where do I start*.

Home now shows no data at all. It names three things a technician can do, each with a line
explaining it:

| card | goes to | line |
| --- | --- | --- |
| Find a customer | `scrCustomers` | See what a site runs, and its documents |
| Browse the catalogue | `scrCatalogue` | Manuals, guides and standard versions |
| Add a customer | `scrOnboard` | Set up a new site and its equipment |

Admin stays a subtle header button - it is not a technician task, and a card would say it
was.

`scrCustomers` comes back, keeping the improvements made while it was merged: no status
chips, no selected-state styling, no `colRecent`. Nine screens again. Finding a site costs
one extra tap, which is the deliberate trade for a home that explains itself.

### One deviation from the agreed sketch

The sketch put the search box *below* the action cards. It is above them instead. The
results have to appear somewhere, and they reuse the slot the cards occupy - that is what
makes the swap free. With the box underneath, results would have rendered above the thing
being typed into, in roughly 300px of space that three 170px galleries cannot fit. Above
the cards, the box never moves and results get the full remaining height.
