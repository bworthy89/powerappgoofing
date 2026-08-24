# In-context admin — design

Admin currently exposes the SharePoint schema: six tabs named after six lists. Before an
admin can add anything they must work out which list it belongs in, which means learning the
data model first. This replaces that with editing in place — the same screens technicians
already use, with edit powers switched on.

Status: design agreed 2026-08-23. Not yet built. Implementation deliberately not started —
other improvements to be discussed first.

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

## Open questions

Neither is common, and both are unpleasant if the design has no answer. Both need deciding
before implementation, not during.

- **Moving a machine between customers.** The sites hierarchy has no gesture for it, because
  a machine is reached *through* the customer that owns it. Options: allow the customer to be
  changed on the edit form (leaving the browse hierarchy alone), or leave it to the All
  records fallback.
- **Retiring a model that sites still have installed.** The delete guard already refuses
  while installations reference it, which is correct but leaves no way to stop offering a
  model to new sites. Likely wants an Active flag on the model honoured by the dropdowns —
  `TB_Products` already has one, currently only honoured by the catalogue.

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
