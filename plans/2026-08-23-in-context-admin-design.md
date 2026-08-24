# In-context admin — design

Admin currently exposes the SharePoint schema: six tabs named after six lists. Before an
admin can add anything they must work out which list it belongs in, which means learning the
data model first. This replaces that with editing in place — the same screens technicians
already use, with edit powers switched on.

Status: first half built 2026-08-23. See *What is built* below.

## Problem

Measured cost of the four common tasks today:

| Task | Steps | Lookups to fill |
|---|---|---|
| Correct a version on a machine | 7 | — |
| Add a machine to an existing site | 10 | 3 |
| Set a site's software version | 9 | 2 |
| Stand up a new customer | 5 | — (wizard) |

No individual form is badly built. The problem is that **every task begins
`Home → Admin`, away from whatever you were looking at.** You are on a machine's screen, you
want to record that it is now on 3.6.0, and the app makes you leave, choose a tab named after
a database table, and find the same machine again by typing its name.

Asked which part is hard, the answer was all four offered: which tab a thing belongs in, the
form once you are in it, the concepts behind it, and knowing what must exist before what.
That rules out optimising one flow. All four describe one cause — **Admin exposes the data
model instead of the work.** Tabs are tables, the ordering problem is foreign keys, and the
confusing vocabulary is schema names.

The original admin design predicted this and deferred the fix:

> *Corrections have the opposite problem: the edit itself is trivial (a version moved from
> K36 to K38), but finding the row costs more than changing it.*

> *Later: edit affordances on `scrSolution`, `scrUnit` and `scrCatalogue` … it modifies three
> working screens, so it should land only once the forms themselves are proven.*

Those screens are now generated rather than hand-written, so modifying them costs a generator
edit. Note the condition as stated was that the forms are *proven* — they function, but
their design is precisely what is being changed here, so this is not simply cashing in that
deferral.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Who can write | **Admins only** | Technician-suggest was considered and deferred; see `plans/DEFERRED.md` |
| Organising principle | **Object-first** — edit where you stand | Removes a mental model rather than adding a better one; admins already know this navigation from the read-only side |
| Creation rule | **Add a thing from the list of its siblings, one level up** | Every creation point is a screen you were already on, so the parent cannot be answered wrongly |
| The six tabs | **Kept, demoted** to an "All records" fallback | Still needed for orphans and oddities; no longer the front door |
| Guided setup | **Retired** once this lands | The same path works for the first machine and the hundredth; two ways to do one thing is its own confusion |
| Role rendering | One set of screens, affordances gated on `varIsAdmin` | Avoids a parallel set of admin screens that would drift |

## Two hierarchies

The app answers two different kinds of question, and they need different trees.

| | Sites | Catalogue |
|---|---|---|
| Answers | what does *this site* have | what models exist, and what goes with what |
| Root | Customers list | Catalogue (the screen technicians already browse) |
| Add at root | `+ Add a customer` | `+ Add a model` |
| Inside one | `+ Add a machine here` | `+ Add a unit this can take` |
| Inside that | `+ Add a unit`, `+ Add a document` | `+ Add a document` |

A customer has no page until it exists, which is why that one starts from the list of its
siblings. Everything else is added from the thing above it.

**Peripherals are not a special case.** A printer, scanner, palm vein reader or PC is a model
with a different Product Type, added like any other, then attached to whichever solution
models can take it.

## Screens

Each gains affordances visible only when `varIsAdmin`. Nothing about the technician view
changes.

**`scrCustomers`** — `+ Add a customer` below the list. Asks: name, description, support
notes.

**`scrCustomerOverview`** — an edit affordance on the title and on the support-notes panel;
one per solution card; `+ Add a machine here` below the list.

**`scrSolution`** — edit on the title and on the version hero; one per unit row; `+ Add a
unit` below the Units tab; `+ Add a document` below the Documents and Firmware tabs.

**`scrUnit`** — edit on the title and the version hero; `+ Add a document` on each tab.

**`scrCatalogue`** — `+ Add a model`. Selecting a model shows, for admins, a **Can take**
list (its `TB_SolutionUnits` rows, marked standard or optional) with edit affordances and
`+ Add a unit this can take`.

**`scrAdmin`** — unchanged in function, demoted in prominence. Reached from Home as now, and
described as "All records".

**`scrEditForm`** — remains the write surface. It is reached with more of its context already
supplied, and shows only the fields that context has not answered.

## What each form asks

Context supplies the rest. The generated Title replaces a field that only ever duplicated
what the lookups already said.

| Action | Asks | Supplied by context | Title |
|---|---|---|---|
| Add a customer | name, description, support notes | — | typed name |
| Add a machine to a site | model, status | customer | `<customer> - <model>` |
| Add a unit to a machine | model, version, status | customer, parent | `<customer> - <model>` |
| Add a document | title, reference type, URL | product, section, customer | typed title |
| Add a model | name, product type, family, standard version | — | typed name |
| Add a unit a model can take | unit model, standard or optional | solution model | `<solution> - <unit>` |
| Record a version | version | the installation | unchanged |

## Adding a machine offers its standard build

When a solution is added to a site, the form lists the model's `TB_SolutionUnits` rows with
the standard ones already ticked, and creates the ticked units in the same action. This is
what the guided setup does at step three; here it stops being a separate flow and becomes the
ordinary path.

## The ordering problem

A dropdown that cannot offer what you need ends the task. Each model dropdown therefore ends
with **"Not in the list — add a new model"**, which creates the model and returns to the form
in progress with it selected.

This is the only place the design allows creating something outside its own hierarchy, and it
is deliberate: without it, an admin adding a palm vein reader must abandon the task, navigate
to the catalogue, add the model, and find their way back.

## Out of scope

- **Technicians writing anything.** Recorded with its costs in `plans/DEFERRED.md`.
- **Bulk operations.** Copying one site's setup to another, or updating many machines at
  once, is a different problem and not evidenced as a need yet.
- **Deleting from in-context screens.** Delete stays on the form, behind the existing
  dependency guard. A delete affordance beside an edit one on a browse screen is too easy to
  hit by accident.

## Resolved

Both were open because neither is common and both are unpleasant if the design has no
answer. Decided before implementation, as this spec required.

**Moving a machine between customers — change it on the edit form.** The browse hierarchy
gets no gesture for it, because a machine is reached *through* the customer that owns it and
a drag-between-sites affordance on a screen people mostly read would be easy to hit by
accident. The Installations form already has a Customer field; that is the move. It costs no
new work and keeps the rare operation in the place where rare operations live.

**Retiring a model that sites still have installed — honour `Active` in the model
dropdowns.** `TB_Products` already carries the flag and only the catalogue reads it. The
delete guard correctly refuses while installations reference a model, so the need is to stop
*offering* it, not to remove it.

`Choices()` returns only `{Id, Value}`, so `Active` cannot be filtered on directly — but
`00_Setup.md` documents the idiom for exactly this, asking per option whether a qualifying
row exists:

```powerfx
Filter(Choices(TB_Installations.Product) As Opt,
       CountRows(Filter(TB_Products, ID = Opt.Id, Active = true)) > 0
       || Opt.Id = varRecInst.Product.Id)
```

The second clause is the part that is easy to miss and expensive to omit. Without it, opening
an existing machine whose model was since retired finds no matching item, the dropdown renders
blank, and saving any unrelated edit writes that blank back — a silent data loss triggered by
an unrelated action. With it, a retired model stays visible on the records that already use it
and disappears only from new ones.

Cost is a non-delegable `CountRows` per option, client-side. `TB_Products` holds models rather
than machines, so it is small, and the Parent dropdown already pays exactly this price.

## What is built

Editing in place works end to end: every browse screen offers the edit and the creation its
level owns, the form arrives with the context already filled in, and it returns to where it
was opened from rather than to the admin list.

| Built | Where |
|---|---|
| `+ Add a customer` | scrCustomers |
| `Edit` the customer, `+ Add a machine` | scrCustomerOverview |
| `Edit` the machine, `+ Add a unit` | scrSolution |
| `Edit` the unit | scrUnit |
| `+ Add a model` | scrCatalogue |
| Context arrives pre-filled | scrEditForm |
| The form returns to its caller | scrEditForm |
| `Active` honoured by model dropdowns | scrEditForm |
| `Last verified` / `Last checked` date fields | scrEditForm |

Two deliberate departures from the design above:

**Affordances sit on each object's own screen, not on every gallery row.** A row already
navigates to the object it describes, so a per-row edit button duplicates the destination it
sits beside — and it would put the most clutter on the busiest screens, which is exactly the
risk this design names. The task the spec measured, correcting a version, is unaffected: you
are on the machine, you tap Edit.

**Context pre-fills fields rather than hiding them.** The form lays its fields out at fixed
positions computed when it is generated, so hiding one at runtime leaves a hole rather than
closing a gap; showing them filled needs no runtime layout arithmetic. It is also the better
behaviour — the admin can see what the screen assumed and correct it, which is what makes
*moving a machine between customers* work with no special gesture, as resolved above.

## A side effect worth knowing about

Letting the form's defaults read the record directly - which is what makes context arrive
pre-filled - also lets a column's **SharePoint default** through to a new record. The old
`If(varAdminNew, ...)` wrapper suppressed it for every field, everywhere.

Four columns declare a default. Three now honour it and one is held back:

| Column | Default | Now |
|---|---|---|
| `TB_Customers.Active` | true | honoured — **this fixes a bug** |
| `TB_Products.Active` | true | honoured — **same bug** |
| `TB_Installations.Status` | In Service | honoured |
| `TB_SolutionUnits.Standard` | true | **held at false** |

**The bug it fixes.** The wizard's Active toggle defaults to true; the admin form forced
false. So a customer or model created through *Admin → Add new* was written inactive — and
every browse list filters on `Active = true`, so it was invisible on the customer list, in
the catalogue and in search, until somebody reopened the record and flipped a toggle they had
no reason to look at. Two paths that create the same row disagreed about it, which is why
nobody noticed: whichever one you used, the behaviour looked consistent.

**Why `Standard` is the exception.** A unit a model *can* take is more often optional than
standard, a pre-ticked toggle looks identical to one somebody set deliberately, and the error
propagates: the standard build is what the guided setup pre-ticks when a machine is added to
a site. That is a schema default which is right for the column and wrong for a new record, so
`gen_admin` overrides it there and says why.

Worth confirming when the schema change is made: this assumes the live SharePoint columns
were actually created with those defaults. If `Active` has no default in SharePoint, a new
customer is written inactive again and the old bug is back, silently.

## Not yet built

- **`+ Add a document`** on the reference tabs of scrSolution, scrUnit and scrCatalogue, and
  the **Can take** list on a catalogue model.
- **Retiring guided setup.** Now unblocked — the ordinary path offers the standard build, so
  the wizard no longer does anything the normal route cannot. Worth doing once the in-context
  path has been used in anger.

## Departures from the design, and why

**The standard build creates itself rather than being ticked.** The design called for the
model's units listed with the standard ones pre-ticked. `scrEditForm` has no room: its
deepest list already reaches 754px against a Save button pinned to the bottom of the screen,
so a picker would land behind it on any laptop. The standard build is the usual case by
definition, the units appear on the machine's own screen immediately, and removing one costs
a tap — so it creates them and says how many, rather than asking.

That is a workaround for a real layout bug, not a preference. See below.

## A bug this uncovered

**`scrEditForm` cannot scroll, and two of its lists no longer fit.** The root container is a
`ManualLayout` group sized to the screen, and nothing in a canvas app scrolls by default.
References reaches 754px and Installations 710px, while Save sits at
`Parent.Height - Gutter - 44`. On anything shorter than about 800px the last fields are
behind the button.

Fixing it means a scrollable container: an auto-layout group with `Overflow: Scroll` wrapping
a `ManualLayout` group taller than the screen, so the absolute positions every field depends
on are preserved. It is its own change — the auto-layout property names are not yet proven
against this compiler — and it should land before anything else is added to that form.

## Risks

- **Two rendering states per screen.** Every screen must be correct for both roles, and a
  technician must never see an editable field. This is a new class of bug the app has not had
  before, and it is invisible to a compile.
- **Visual noise.** Edit affordances land on screens deliberately decluttered. They should be
  outlined and muted, never filled buttons, and only ever visible to admins.
- **Four generated screens change**, so a full paste cycle and a re-test on both roles.
- **`scrEditForm` grows conditional logic** for which fields to show given the supplied
  context. It is already the largest generated screen.

## Deployment note

Delete every screen in Studio, paste the complete set. See the deployment section of
`app/00_Setup.md`, and check both roles after pasting — a screen correct for an admin can be
wrong for a technician and vice versa.
