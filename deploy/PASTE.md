# Building the app by pasting, instead of importing

An alternative to `deploy/README.md` steps 2 and 3. You create a blank app in the target
environment, add that environment's data sources, and paste each screen in.

It is more steps than an import, and it has one real advantage: nothing ever points at the
development SharePoint site, so there is no re-pointing to get wrong and no silent empty
gallery afterwards. The formulas bind to the lists you add, in the tenant you are in.

**Do step 1 of `deploy/README.md` first.** The lists must exist, and
`Test-ToolboxSchema.ps1` must pass, before any of this. Every formula addresses those
columns by display name, and pasting against lists that do not exist yet produces hundreds
of errors that all disappear again once the data is connected - which makes it impossible to
tell a real mistake from a missing connection.

---

## Order matters, for one specific reason

The nine screens navigate to each other in cycles: home to customers and back, solution to
unit and back, admin to the edit form and back. There is no order that avoids referring to a
screen that does not exist yet.

So create all nine **empty** screens first, with their exact names, before pasting anything
into any of them. Then no `Navigate` is ever dangling and no error is ever spurious.

| create these nine, exactly |
| --- |
| `scrHome` |
| `scrCustomers` |
| `scrCustomerOverview` |
| `scrSolution` |
| `scrUnit` |
| `scrCatalogue` |
| `scrAdmin` |
| `scrEditForm` |
| `scrOnboard` |

Names are case-sensitive and are referenced by formula throughout. A typo here surfaces much
later as a navigation that silently does nothing.

---

## 1. New app, data first

1. make.powerapps.com, work environment, **Create** > **Blank app** > **Blank canvas app**
2. Name it *Technician Toolbox*, tablet format
3. **Settings** > **Updates** > **New** > turn on **Modern controls and themes**
4. **Data** > **Add data** > SharePoint > your work site
5. Tick **all four** lists - `TB_Customers`, `TB_Products`, `TB_Installations`,
   `TB_References` - and add them together

Step 3 is not optional. Most of the app is `ModernText`, `ModernButton`, `ModernDropdown`,
`ModernToggle` and `ModernIcon`; without that setting they will not render.

Step 5: add all four at once. `TB_Installations` has lookups into `TB_Customers` and
`TB_Products`, and adding it on its own can leave those columns unresolved.

## 2. App-level configuration

This part is not a control and cannot be pasted with the screens. Nothing works without it -
every screen refers to `AppTheme`, `AppFont`, `AppType`, `Gutter` and `ContentWidth`.

Select **App** at the top of the tree, then set each property from the formula bar.

**`App.Formulas`** - paste the whole block from `app/App.pa.yaml`, from `AppTheme = {` to
the closing line of `ContentWidth`. Omit the leading `=`; the formula bar supplies it.

**`App.OnStart`**

```
Set(varCustomer, Defaults(TB_Customers));
Set(varInstallation, Defaults(TB_Installations));
Set(varExpandedModel, 0)
```

`Defaults(<table>)` rather than `Blank()` is deliberate: it yields an empty record that still
carries a schema, so the screens' `varCustomer.Title` and similar type-check before anyone
has selected anything.

**`App.StartScreen`** - `scrHome`

## 3. Create the nine screens

**Insert** > **New screen** > **Blank**, nine times, renaming each in the tree to match the
table above. Leave them empty.

Delete the default `Screen1` once `scrHome` exists and `StartScreen` points at it.

## 4. Paste each screen

For each screen, open `app/screens/<name>.pa.yaml`, and copy everything **below** the
`Children:` line - that is, the list of controls, starting at `- conRoot...`. Select the
screen in the tree and paste onto the canvas.

Do not paste the first four lines (`Screens:`, the screen name, `Properties:`, `Fill:`).
Those describe the screen itself rather than its contents.

Then set the screen's own properties by hand, from the same file:

- every screen: `Fill` = `AppTheme.Bg`
- `scrOnboard` only: `OnVisible`, the five-line block from its `Properties`. Miss this and
  the wizard opens completely blank, because every step-1 control tests `varWizStep = 1` and
  nothing would ever set it.

Suggested order - dependencies resolve soonest, so genuine errors stand out:

```
scrCatalogue   scrUnit      scrSolution   scrCustomerOverview   scrCustomers
scrEditForm    scrAdmin     scrOnboard    scrHome
```

## 5. Check it

`app/screens/*.pa.yaml` is a mirror of a working app, so anything that errors after a paste
is a paste problem, not a code problem. Look first at:

- **Unknown name `AppTheme` / `Gutter`** - step 2 was skipped or has a typo
- **Unknown name `TB_...`** - the data source was not added, or was added under a different
  name
- **A whole screen blank** - check `Fill`, and for `scrOnboard` check `OnVisible`
- **Navigation does nothing** - a screen name is misspelled; compare against the table above

Then walk step 3 of `deploy/README.md` and confirm the rows reach SharePoint rather than
trusting the screens.

---

## Honest caveat

Every screen in `app/screens/` was deployed and tested through the Canvas Authoring MCP
against a live coauthoring session, not by hand-pasting into Studio. The YAML is proven; this
particular route into Studio is not, on this app.

If Studio rejects a paste outright, that is worth reporting rather than working around: the
likeliest cause is pasting the screen-level wrapper instead of the control list, and the
second likeliest is modern controls being off.

If Claude Code and the Canvas Authoring MCP are available on the work machine, connecting it
to the new app and running `compile_canvas` over `app/screens/` is the route that is actually
proven - it deployed all nine screens repeatedly today. See `app/00_Setup.md` for the rules
that route follows, particularly that a compile mirrors the directory and that screens must
never be pushed over existing ones.
