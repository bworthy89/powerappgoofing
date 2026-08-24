"""Regenerate every generated screen, then apply the passes that must follow.

WHY THIS EXISTS

gen_admin, gen_form and gen_onboard emitted the light palette long after their screens had
been migrated to dark, because migrate_dark.py and fix_dark_defaults.py were applied to the
OUTPUT rather than to the generators. Running any one of them would silently revert that
screen and drop every explicit colour added afterwards - a landmine, because nothing about
running a generator looks dangerous.

The generators now emit dark directly. This script exists so the follow-up passes cannot be
forgotten either, and so the order is written down once rather than remembered:

    generators  ->  migrate_dark  ->  fix_dark_defaults  ->  verify_yaml
                ->  check_overlaps

Both middle passes are idempotent. migrate_dark's token maps no-op now that the generators
emit AppDark; what it still contributes is the 3px brand rule on screens that have no full
band. fix_dark_defaults adds Color and Fill to controls that would otherwise inherit the
light theme's near-black default - a non-zero count from it is a real finding, meaning new
controls shipped depending on a default that is wrong for this app.
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent
GENERATORS = ["gen_home", "gen_solution", "gen_unit", "gen_customer_overview",
              "gen_customers", "gen_catalogue", "gen_request_access",
              "gen_admin", "gen_form", "gen_onboard"]
# check_overlaps runs last and every time. A screen whose controls sit on top of each
# other compiles clean, and the symptom is a label that looks MISSING rather than
# covered - so it reads as "you forgot one" and sends you looking in the wrong place.
# Three of those shipped in one week before this was automatic.
PASSES = ["migrate_dark", "fix_dark_defaults", "verify_yaml", "check_overlaps"]


ROOT = SCRIPTS.parent


def run(name):
    # verify_yaml resolves app/screens relative to the repo root; the generators write
    # absolute paths and do not care. Running everything from the root suits both.
    r = subprocess.run([sys.executable, str(SCRIPTS / f"{name}.py")],
                       capture_output=True, text=True, cwd=ROOT)
    ok = r.returncode == 0
    tail = (r.stdout or r.stderr).strip().splitlines()
    print(f"  {'ok  ' if ok else 'FAIL'} {name:22} {tail[-1][:70] if tail else ''}")
    if not ok:
        print((r.stderr or r.stdout)[-800:])
    return ok


print("generators")
good = all([run(g) for g in GENERATORS if (SCRIPTS / f"{g}.py").exists()])
print("\npasses")
good = all([run(p) for p in PASSES]) and good
sys.exit(0 if good else 1)
