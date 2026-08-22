# Solution units: what actually attaches to what

**Date:** 2026-08-22
**Status:** built

## Why

The guided setup suggested units by product `Family`: every non-Solution product in the
same family as the machine you picked. A CI 300X therefore proposed every CashInfinity
component ever catalogued, whether it fits one or not.

The real relationship is specific. A CI 300X carries an SDRB250 note recycler and an SDRC200
coin recycler as standard, and can also take an RCW-200 coin recycler or a PWC-10 coin
dispenser. Family cannot express that, because it is not a property of either product - it is
a fact about the pair.

Separately, a financial recycler on its own floor belongs to no solution at all, and the
wizard should not imply it needs one.

## What was established by asking

| question | answer |
| --- | --- |
| Is a CI 300X always the same two units? | No - it can also take an RCW-200 or a PWC-10 |
| Can the same model appear twice on one machine? | No, one of each at most |
| How should a standalone recycler be handled? | The same flow, with the word "solution" dropped |

The second answer is why this stays a tick list rather than growing quantities, and the third
is why no data model change was needed for standalone machines: `TB_Installations` already
allows a top-level row with no children.

## The data

One new list.

**`TB_SolutionUnits`** - which unit models attach to which solution model:

| column | type | |
| --- | --- | --- |
| Title | Text | a readable label, e.g. `CI 300X - SDRB250` |
| Solution | Lookup to `TB_Products` | required |
| Unit | Lookup to `TB_Products` | required |
| Standard | Yes/No | default **Yes** |

A CI 300X is four rows:

```
CI 300X -> SDRB250    Standard  yes
CI 300X -> SDRC200    Standard  yes
CI 300X -> RCW-200    Standard  no
CI 300X -> PWC-10     Standard  no
```

`Standard` is what makes the common case one click: the usual build arrives ticked, the
options sit beside it, offered rather than assumed.

A standalone machine has **no rows**, and that is how the app knows it is standalone.

### What this does not change

`Family` and `Product Type` both stay. They are read on the customer overview, the catalogue,
the unit screen and the admin form. They simply stop deciding what attaches to what -
`'Product Type' = "Solution"` is no longer how the app works out whether something can host
units. A model hosts units because rows say so.

## The wizard

Step 2 stops saying "solution". It is *the machines on site*, and `+ Add machine`. A CI 300X
and a lone recycler are both machines; only one of them turns out to have anything attached.

Step 3 reads the new list:

```powerfx
Filter(TB_SolutionUnits As S,
       S.Solution.Id = varWizParent.Product.Id,
       CountRows(Filter(colWizFitted, Product.Id = S.Unit.Id)) = 0)
```

with the checkbox defaulting to `ThisItem.Standard`.

`As S` is not optional. Without it, `Unit.Id` inside the inner `Filter` is ambiguous between
the two record scopes - the trap already recorded in `app/00_Setup.md`.

### Why the fitted collection exists

Pre-ticking introduced a duplicate risk that ticking-from-nothing did not have. `Reset`
returns a checkbox to its `Default`, which is now *ticked*, so a second press of Add would
attach the standard build twice.

So picking a machine reads what is already under it into a local collection:

```powerfx
ClearCollect(colWizFitted, Filter(TB_Installations, 'Parent'.Id = varWizParent.ID))
```

and the Add button refreshes it. Units disappear from the list as they are added, which also
makes progress visible. A collection rather than a live query because it is local: the
comparison happens in memory, with no delegation warning and no round trip per row.

## Three empty states

The list can be empty for three different reasons, and two of them mean opposite things:

| when | what it says |
| --- | --- |
| no machine picked | *Pick a machine above and its units appear here.* |
| the model has no units on file | *A SDRB250 has no attached units on file.* |
| all of them are already added | *Everything on file for a CI 300X is already added.* |

Conflating the last two would be the mistake. One means "this machine stands alone", the
other means "you are finished". They look identical if you only test for an empty list, which
is the same error that made the wizard's step 3 look broken when it was merely waiting for a
selection.

## Naming

The list was nearly called `TB_SolutionParts`. "Parts" implies spare parts - a bill of
materials for a machine - when an SDRB250 is a machine in its own right that happens to sit
inside another one. `Unit` is the word the app already uses everywhere: `scrUnit`, "Add ticked
units", "units under each machine".

## Setting it up

`TB_SolutionUnits` has to be populated before the wizard can suggest anything. Until it has
rows, every machine looks standalone - which is a safe failure, but a silent one.

Rows are maintained in SharePoint directly. There is no admin screen for this list, on the
grounds that a model catalogue changes when products are launched, not during a site visit.
