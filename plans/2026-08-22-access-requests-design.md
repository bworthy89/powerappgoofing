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

Email was considered and rejected: it needs the Office365Outlook connector, which is another
connection to establish at import and the kind of thing a DLP policy blocks outright. The
count on the tab is the substitute, and its weakness is honest - nobody is told, an admin has
to open the app.

## The bootstrap trap

`TB_Admins` previously meant "the admins", and the rule was *an empty list means everyone is
an admin*, so nobody could be locked out before the first row existed.

That list now carries requests as well as approvals, which breaks the rule in a way that is
easy to miss and impossible to recover from inside the app: **one pending request makes the
list non-empty and locks out everybody**, including whoever should approve it.

So the check counts approved rows, not rows:

```powerfx
Set(varIsAdmin,
    CountRows(Filter(TB_Admins, Status.Value = "Approved")) = 0
    || !IsBlank(LookUp(TB_Admins,
         Lower(Person.Email) = Lower(User().Email)
         && Status.Value = "Approved")))
```

The property worth keeping is that the app is open until somebody is approved, and closes
itself the moment the first admin exists. The first person to install it approves their own
request, and from then on it is shut.

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
