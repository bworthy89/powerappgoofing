# Technician Toolbox

A Power Apps canvas app for Glory Global field technicians: look up a customer site, see what
machines are installed, check installed software against the current standard, open the right
manual or firmware download. Backed by SharePoint lists. No Dataverse, no premium connectors.

## The one thing to read first

**`app/00_Setup.md`** — 36 rules, each earned from a real failure, each recording the symptom
as well as the cause. Most of them describe behaviour that compiles cleanly and fails
silently, which is the characteristic failure mode of this platform.

Consult it *before* writing Power Fx, not after a bug. Rules written down and then violated
anyway have cost more time on this project than rules never discovered.

## How the app is built

Every screen is generated. **Never hand-edit `app/screens/*.pa.yaml`** — it is build output
and the next build overwrites it. Edit `scripts/gen_<screen>.py` instead.

```
python scripts/build_screens.py
```

runs, in order:

```
generators  →  migrate_dark  →  fix_dark_defaults  →  verify_yaml  →  check_overlaps
```

- **generators** — one per screen, plus `screen_parts.py` for fragments shared between them
  (brand band, version hero, config panel, reference lists)
- **migrate_dark** — adds the 3px brand rule to screens with no full band; its token maps are
  now no-ops and it is kept for that one job
- **fix_dark_defaults** — gives controls an explicit `Color`/`Fill`. **A non-zero count is a
  finding, not noise**: it means new controls shipped depending on the theme default, which is
  light, on an app whose ground is dark. A count that **drops** is a different
  finding: controls that were being counted have stopped existing, which usually means a
  generator failed and its stale screen is still on disk
- **verify_yaml** — a bespoke linter, ~10 checks, every one added after the corresponding bug
  reached the app
- **check_overlaps** — fails the build when two text-bearing siblings intersect, at both a
  desktop and a phone width. Three overlaps shipped in one week before this ran
  automatically, and each read as a *missing* label rather than a covered one. It also
  prints how many controls it could not resolve — that number going up means it is seeing
  less, not that the screens got better

A generator that crashes leaves the previous screen in place, so the build looks like it
succeeded and the stale screen is what gets pasted. `build_screens.py` prints a `FAILED:` line
at the end naming any that did not run. **Do not pipe the build through `tail`** — that is how
a crashing generator went unnoticed for several runs.

## How changes reach the app

There is no automated deploy. The user pastes YAML into Power Apps Studio by hand, so every
change costs them real work:

- **Say exactly which files changed**, not "paste everything". `git diff --stat <ref> -- app/`
- **Delete the screen in Studio before pasting.** Pasting over an existing screen leaves old
  controls with their old formulas, so a fix that is correct in the repo never reaches the app
  and looks like it did not work
- **Screens are cyclic** — every screen navigates to another, so no paste order avoids
  forward-reference errors. They resolve once the last screen lands
- A **component** and the screens using it must be pasted together; a stale screen looks
  identical to a missing component property

## SharePoint

Six lists, defined once in `scripts/sharepoint/ToolboxSchema.ps1`, which
`Create-ToolboxLists.ps1` and `Test-ToolboxSchema.ps1` both read.

Schema changes are made **by hand** in SharePoint by the user, so `deploy/SCHEMA-CHANGES.md`
must carry any new column or list before the app needs it. A column the script can create is
not necessarily one a person can create by hand — see the `Version` rule in `00_Setup.md`.

## Verifying

There are no unit tests, and the compile proves almost nothing: Power Apps validates formulas
in isolation, so a clean compile is compatible with a screen that renders blank. What has
actually worked on this project:

- **Instrumented labels** printing intermediate values into the running app
- **Querying SharePoint directly** rather than trusting what the screen shows
- **Checking generated output against intent**, not just exit codes — a generator writing to
  the wrong directory succeeded every time while changing nothing

When a change to a generator produces no change in the app, check where the generator writes
and whether the screen was deleted before pasting, before concluding the change was wrong.
