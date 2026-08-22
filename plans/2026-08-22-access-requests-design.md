# Requesting admin access

**Date:** 2026-08-22
**Status:** built

## What it does

Someone who is not an admin sees **Request access** in the header slot where an admin sees
**Admin**. It leads to a screen that explains what admin covers and, if they have not asked
before, offers a button. That writes a `Pending` row into `TB_Admins` carrying their
signed-in identity.

An admin sees a sixth tab on the Admin screen, **Access**, carrying the pending count.
Each row has Approve and Deny in the row itself.

## Decisions

| question | answer |
| --- | --- |
| What roles? | Admin, or not. Everyone with app access is a technician - that is what access means. |
| How is an admin told? | In the app only. The tab shows a count. |
| Who is an admin before setup? | Nobody. The first one is seeded in SharePoint. |

Email was considered and rejected: it needs the Office365Outlook connector, which is another
connection to establish at import and the kind of thing a DLP policy blocks outright. The
count on the tab is the substitute, and its weakness is honest - nobody is told, an admin has
to open the app.

## Closed by default, and the trap that was nearly shipped

Nobody has admin until a row says so:

```powerfx
Set(varIsAdmin,
    !IsBlank(LookUp(TB_Admins,
        Lower(Person.Email) = Lower(User().Email)
        && Status.Value = "Approved")))
```

**The first admin is seeded directly in SharePoint** - a row with Status `Approved` - before
anyone opens the app. Everyone after that goes through the request flow. That is one manual
step at install, and it has to be right or the first person is locked out of a screen only
that screen can grant.

The first version instead read *an empty list means everyone is an admin*, so nobody could be
locked out before setup. That is defensible for a solo test and wrong for a rollout: during
the window before the first approval, any technician who opened the app had Admin - which now
contains delete.

Worse, it very nearly shipped in a broken form. `TB_Admins` carries requests as well as
approvals, so "empty list" had to become "no *approved* rows" - otherwise a single pending
request would make the list non-empty and lock out everybody, including whoever should
approve it. That was caught, fixed, and then removed entirely when the posture changed.
Closed-by-default has no such clause to get wrong.

A lockout is recoverable: the SharePoint list is editable outside the app.

## Why Access is not in the LISTS spec

The other five tabs generate from one specification: a browse gallery, an Add new, and an
edit form. Access has none of those. Approving is a single decision, and routing it through
open-the-record-change-a-dropdown-save would be worse than the thing it replaces.

It is a separate `ACCESS` entry that joins `LISTS` only where tabs are drawn. Putting it in
the list proper would mean excepting it from every loop that reads them.

Denying does not delete. A denied row records that the question was asked, and answered.

## Still to do

Nothing warns an admin outside the app. If requests turn out to sit unnoticed, the smallest
fix is a Power Automate flow on the SharePoint list rather than a connector in the app -
it keeps the app's connection list unchanged, which is what makes it importable without
negotiation.
