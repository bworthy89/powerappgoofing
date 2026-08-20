#!/usr/bin/env python3
"""Verify seed/*.csv before pasting into SharePoint grid view.

SharePoint's grid-view paste resolves a lookup column by matching the parent
row's Title *exactly*. A mismatch does not error — it fails silently and
leaves the cell empty. There is no way to catch that after the fact by
looking at the app, because a blank lookup cell looks identical to a blank
lookup value that was never populated. So this has to be caught before
pasting, by a script that compares every lookup value against the parent
list's Title column character for character.

Three kinds of check:

  1. Referential integrity — every value in a lookup column (Customer,
     Parent, Product) must appear verbatim as a Title in the parent CSV.
  2. Choice-column integrity — every value in a Choice column must be one
     of the values the list will actually offer, so a typo does not become
     a silent new choice value SharePoint quietly accepts.
  3. Title uniqueness — no CSV may contain the same Title twice. A
     duplicate Title makes lookup resolution ambiguous: SharePoint's paste
     still succeeds, silently, bound to whichever matching row it finds
     first, so this is the same silent-failure family as (1) and cannot be
     caught by looking at the app either.

Usage:
    python3 scripts/verify_seed.py [seed_dir]

Exits 1 and prints every finding if anything is wrong; exits 0 and prints a
per-file state-coverage summary if everything checks out.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

CHOICES = {
    "TB_Products": {
        "Product Type": {"Solution", "Note Recycler", "Coin Recycler", "Drop Vault",
                          "Printer", "Scanner", "Biometric", "PC", "UPS"},
        "Family": {"CashInfinity", "Retail", "Banking", "Self Service"},
        "Active": {"Yes", "No"},
    },
    "TB_Installations": {
        "Status": {"In Service", "Upgrade Planned", "Retired"},
    },
    "TB_References": {
        "Section": {"Documentation", "Firmware & Downloads"},
        "Reference Type": {
            "Service Manual", "Installation Manual", "Error Code Manual",
            "Technical Bulletin", "Technical Alert", "Product Specification",
            "Customer Specific", "Machine Firmware", "BV Firmware",
            "Software Download", "Driver", "Support Tool",
        },
        "Featured": {"Yes", "No"},
    },
    "TB_Customers": {
        "Active": {"Yes", "No"},
    },
}

REQUIRED_HEADERS = {
    "TB_Customers": ["Title", "Description", "Support Notes", "Active"],
    "TB_Products": ["Title", "Product Type", "Family",
                    "Current Standard Version", "Description", "Active"],
    "TB_Installations": ["Title", "Customer", "Parent", "Product",
                          "Installed Version", "Status", "Config Notes"],
    "TB_References": ["Title", "Product", "Customer", "Section",
                       "Reference Type", "URL", "Version", "Featured",
                       "Last Checked"],
}

FILES = {
    "TB_Customers": "1_TB_Customers.csv",
    "TB_Products": "2_TB_Products.csv",
    "TB_Installations": "3_TB_Installations.csv",
    "TB_References": "4_TB_References.csv",
}


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows


def main():
    seed_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "seed")
    findings = []
    tables = {}

    for name, filename in FILES.items():
        path = seed_dir / filename
        if not path.exists():
            findings.append(f"{filename}: file not found")
            continue
        rows = load(path)
        header = rows[0].keys() if rows else []
        missing = [h for h in REQUIRED_HEADERS[name] if h not in header]
        if missing:
            findings.append(f"{filename}: missing header(s) {missing}")
        tables[name] = rows

    if len(tables) < 4:
        for f in findings:
            print(f"FAIL: {f}")
        sys.exit(1)

    customer_titles = {r["Title"] for r in tables["TB_Customers"]}
    product_titles = {r["Title"] for r in tables["TB_Products"]}
    installation_titles = {r["Title"] for r in tables["TB_Installations"]}

    # --- Title uniqueness --------------------------------------------------
    for name, filename in FILES.items():
        counts = Counter(r.get("Title", "") for r in tables.get(name, []))
        for title, n in sorted(counts.items()):
            if n > 1:
                findings.append(
                    f"{filename}: Title {title!r} appears {n} times — duplicate Titles make "
                    f"lookup resolution ambiguous")

    # --- referential integrity -------------------------------------------
    for i, row in enumerate(tables["TB_Installations"], start=2):
        title = row.get("Title", "")
        customer = row.get("Customer", "")
        parent = row.get("Parent", "")
        product = row.get("Product", "")
        if not customer:
            findings.append(f"3_TB_Installations.csv row {i} ({title!r}): Customer is blank")
        elif customer not in customer_titles:
            findings.append(
                f"3_TB_Installations.csv row {i} ({title!r}): Customer {customer!r} "
                f"has no matching Title in TB_Customers")
        if not product:
            findings.append(f"3_TB_Installations.csv row {i} ({title!r}): Product is blank")
        elif product not in product_titles:
            findings.append(
                f"3_TB_Installations.csv row {i} ({title!r}): Product {product!r} "
                f"has no matching Title in TB_Products")
        if parent and parent not in installation_titles:
            findings.append(
                f"3_TB_Installations.csv row {i} ({title!r}): Parent {parent!r} "
                f"has no matching Title in TB_Installations")
        if parent == title:
            findings.append(
                f"3_TB_Installations.csv row {i} ({title!r}): Parent is its own Title "
                f"(self-reference)")

    for i, row in enumerate(tables["TB_References"], start=2):
        title = row.get("Title", "")
        product = row.get("Product", "")
        customer = row.get("Customer", "")
        reftype = row.get("Reference Type", "")
        if not product:
            findings.append(f"4_TB_References.csv row {i} ({title!r}): Product is blank")
        elif product not in product_titles:
            findings.append(
                f"4_TB_References.csv row {i} ({title!r}): Product {product!r} "
                f"has no matching Title in TB_Products")
        if customer and customer not in customer_titles:
            findings.append(
                f"4_TB_References.csv row {i} ({title!r}): Customer {customer!r} "
                f"has no matching Title in TB_Customers")
        # Product spec: "Customer Specific is only for documents with no
        # other kind, so a row of that type with no customer set is a data
        # error the app surfaces." Catch that error here instead.
        if reftype == "Customer Specific" and not customer:
            findings.append(
                f"4_TB_References.csv row {i} ({title!r}): Reference Type is "
                f"'Customer Specific' but Customer is blank")

    # --- choice-column integrity ------------------------------------------
    for name, filename in FILES.items():
        rows = tables.get(name, [])
        for col, allowed in CHOICES.get(name, {}).items():
            for i, row in enumerate(rows, start=2):
                val = row.get(col, "")
                if not val:
                    continue  # blank is a separate concern, not a bad choice value
                if val not in allowed:
                    findings.append(
                        f"{filename} row {i} ({row.get('Title', '')!r}): "
                        f"{col}={val!r} is not one of {sorted(allowed)}")

    if findings:
        print(f"FAIL: {len(findings)} finding(s)\n")
        for f in findings:
            print(f"  - {f}")
        sys.exit(1)

    print("PASS: all lookups resolve, all choice values are valid.\n")

    # --- state coverage summary --------------------------------------------
    inst = tables["TB_Installations"]
    prod = tables["TB_Products"]
    cust = tables["TB_Customers"]
    refs = tables["TB_References"]

    def installed_state(row):
        installed = row.get("Installed Version", "").strip()
        p = next((p for p in prod if p["Title"].strip() == row["Product"].strip()), None)
        standard = (p or {}).get("Current Standard Version", "").strip()
        if not installed:
            return "blank"
        if not standard:
            return "no-standard"
        return "on" if installed == standard else "off"

    # Retired rows never reach a currency-comparing screen (no screen queries
    # them for it — they vanish from every gallery), so they are excluded
    # from the on/off/blank currency counts below to avoid implying a state
    # that is never actually rendered.
    non_retired = [r for r in inst if r.get("Status", "") != "Retired"]
    on_standard = sum(1 for r in non_retired if installed_state(r) == "on")
    off_standard = sum(1 for r in non_retired if installed_state(r) == "off")
    blank_installed = sum(1 for r in non_retired if installed_state(r) == "blank")
    blank_standard_product = sum(
        1 for p in prod if not p.get("Current Standard Version", "").strip())
    retired = sum(1 for r in inst if r.get("Status", "").strip() == "Retired")
    upgrade_planned = sum(1 for r in inst if r.get("Status", "").strip() == "Upgrade Planned")
    nested_units = sum(1 for r in inst if r.get("Parent", "").strip())
    solutions = sum(1 for r in inst if not r.get("Parent", "").strip())
    customers_with_no_installs = sum(
        1 for c in cust
        if c["Title"].strip() not in {r["Customer"].strip() for r in inst})
    blank_url_refs = sum(1 for r in refs if not r.get("URL", "").strip())
    blank_last_checked = sum(1 for r in refs if not r.get("Last Checked", "").strip())
    customer_specific_refs = sum(1 for r in refs if r.get("Customer", "").strip())

    product_customers = defaultdict(set)
    for r in inst:
        product_customers[r.get("Product", "")].add(r.get("Customer", ""))
    shared_products = sorted(p for p, custs in product_customers.items() if len(custs) > 1)

    import datetime
    today = datetime.date.today()
    older_than_12mo = 0
    for r in refs:
        lc = r.get("Last Checked", "").strip()
        if not lc:
            continue
        try:
            d = datetime.date.fromisoformat(lc)
        except ValueError:
            continue
        months = (today.year - d.year) * 12 + (today.month - d.month)
        if months >= 12:
            older_than_12mo += 1

    print("State coverage:")
    print(f"  installation on standard, excl. retired (installed == standard) : {on_standard}")
    print(f"  installation off standard, excl. retired (installed != standard): {off_standard}")
    print(f"  installation with blank Installed Version, excl. retired ('not recorded'): {blank_installed}")
    print(f"  product with blank Current Standard Version (badge hidden): {blank_standard_product}")
    print(f"  retired installation                                      : {retired}")
    print(f"  upgrade-planned installation                              : {upgrade_planned}")
    print(f"  solution rows (blank Parent)                              : {solutions}")
    print(f"  unit rows nested under a solution (Parent set)            : {nested_units}")
    print(f"  customers with zero installations                        : {customers_with_no_installs}")
    print(f"  references with blank URL ('visible but inert')          : {blank_url_refs}")
    print(f"  references with blank Last Checked ('never checked')     : {blank_last_checked}")
    print(f"  references older than 12 months (age display)            : {older_than_12mo}")
    print(f"  customer-specific references (Customer set)               : {customer_specific_refs}")
    print(f"  products installed at 2+ customers (disclosure filter demonstrable): "
          f"{len(shared_products)} ({', '.join(shared_products) or 'none'})")
    sys.exit(0)


if __name__ == "__main__":
    main()
