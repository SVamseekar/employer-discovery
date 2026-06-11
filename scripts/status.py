"""
Pipeline Status Dashboard
=========================
Shows exactly where you are vs. your original plan targets.
Run this whenever you want a snapshot of the pipeline.

Usage: python scripts/status.py
"""
import csv
import os
import sys
from collections import Counter
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), "..")
MASTER   = os.path.join(BASE, "data", "master_employers.csv")
SHORTLIST = os.path.join(BASE, "data", "cold_outreach_shortlist.csv")
TRACKER  = os.path.join(BASE, "data", "outreach_tracker.csv")
APPS     = os.path.join(BASE, "data", "applications.csv")
LOG      = os.path.join(BASE, "data", "pipeline_log.csv")

# ---- Targets from your original plan ----
PLAN_MIN = 5_000
PLAN_MAX = 20_000

REGION_TARGETS = {
    "Europe":       0.20,
    "USA":          0.20,
    "Australia/NZ": 0.20,
    "India":        0.20,
    "Remote/Global":0.20,
}
STAGE_TARGETS = {
    "Startup":         0.30,
    "Scaleup":         0.30,
    "Mid-market":      0.20,
    "Enterprise":      0.10,
    "Hidden Champion": 0.10,
}


# ---------------------------------------------------------------------------
# Classifiers
# ---------------------------------------------------------------------------

EU = ["germany", "netherlands", "france", "sweden", "ireland", "spain", "portugal",
      "denmark", "finland", "austria", "belgium", "poland", "czech", "norway",
      "switzerland", "europe", " eu", "estonia", "latvia", "lithuania", "greece",
      "hungary", "romania", "bulgaria", "croatia", "slovakia", "slovenia"]

INDIA_TERMS = ["india", "hyderabad", "bangalore", "bengaluru", "mumbai",
               "pune", "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata"]

def classify_region(row):
    geo = (row.get("Country","") + " " + row.get("Hiring_Geography","") + " " + row.get("City","")).lower()
    if any(c in geo for c in EU):
        return "Europe"
    if any(c in geo for c in ["usa", "united states", "u.s."]):
        return "USA"
    if any(c in geo for c in ["australia", "new zealand"]):
        return "Australia/NZ"
    if any(c in geo for c in INDIA_TERMS):
        return "India"
    return "Remote/Global"


def classify_stage(row):
    stage    = row.get("Company_Stage","").lower()
    category = row.get("Employer_Category","").lower()
    scale    = row.get("Company_Scale","").lower()
    if "enterprise" in stage or "1000+" in scale or "h1b sponsor" in category:
        return "Enterprise"
    if any(s in stage for s in ["scaleup","scale-up","series b","series c","series d","growth"]):
        return "Scaleup"
    if any(s in stage for s in ["series a","startup","seed","yc"]) or "yc" in category:
        return "Startup"
    if "mid" in stage or "smb" in stage:
        return "Mid-market"
    return "Startup"   # safest default for unclassified


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def progress_bar(value, total, width=25, target_pct=None):
    pct   = value / total if total > 0 else 0
    filled = int(pct * width)
    bar   = "█" * filled + "░" * (width - filled)
    line  = f"[{bar}] {pct:>5.1%}  ({value:>5,})"
    if target_pct is not None:
        diff = pct - target_pct
        arrow = "▲ over" if diff > 0.05 else ("▼ under" if diff < -0.05 else "✓ on target")
        line += f"   {arrow} ({target_pct:.0%} target)"
    return line


def mini_bar(value, total, width=20):
    pct    = value / total if total > 0 else 0
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


def section(title):
    print(f"\n{'─' * 65}")
    print(f"  {title}")
    print(f"{'─' * 65}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    print()
    print("╔" + "═" * 63 + "╗")
    print("║   EMPLOYER DISCOVERY PIPELINE — STATUS DASHBOARD" + " " * 13 + "║")
    print(f"║   {datetime.now().strftime('%Y-%m-%d %H:%M')}" + " " * 47 + "║")
    print("╚" + "═" * 63 + "╝")

    # ---- 1. Master database ----
    section("1 / EMPLOYER DATABASE")
    if not os.path.exists(MASTER):
        print("  Master file not found. Run: python scripts/import_h1b.py")
        return

    with open(MASTER, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    total = len(rows)

    pct_min = min(total / PLAN_MIN * 100, 100)
    pct_max = total / PLAN_MAX * 100
    bar_min = mini_bar(min(total, PLAN_MIN), PLAN_MIN, 30)
    bar_max = mini_bar(total, PLAN_MAX, 30)

    print(f"\n  Total companies:  {total:,}")
    print(f"  Plan target:      {PLAN_MIN:,} – {PLAN_MAX:,}")
    print(f"\n  vs minimum  [{bar_min}] {pct_min:.0f}%")
    print(f"  vs maximum  [{bar_max}] {pct_max:.0f}%")

    needed = max(0, PLAN_MIN - total)
    if needed > 0:
        print(f"\n  ⚠  Need {needed:,} more to reach the 5k minimum.")
        print(f"     Run: python scripts/run_scrapers.py")
    else:
        print(f"\n  ✓  Minimum target reached!")

    # ---- 2. Regional breakdown ----
    section("2 / REGIONAL BREAKDOWN  (plan: 20% each across 5 regions)")
    region_counts = Counter(classify_region(r) for r in rows)
    for region, target in REGION_TARGETS.items():
        count = region_counts.get(region, 0)
        print(f"  {region:<18} {progress_bar(count, total, 22, target)}")

    # ---- 3. Company stage ----
    section("3 / COMPANY STAGE")
    stage_counts = Counter(classify_stage(r) for r in rows)
    for stage, target in STAGE_TARGETS.items():
        count = stage_counts.get(stage, 0)
        print(f"  {stage:<18} {progress_bar(count, total, 22, target)}")

    # ---- 4. Visa signals ----
    section("4 / VISA & REMOTE SIGNALS")
    visa_yes      = sum(1 for r in rows if r.get("Visa_Sponsorship","").lower() == "yes")
    visa_possible = sum(1 for r in rows if r.get("Visa_Sponsorship","").lower() == "possible")
    eor_yes       = sum(1 for r in rows if r.get("EOR","").lower() == "yes")
    remote_yes    = sum(1 for r in rows if r.get("Remote","").lower() == "yes")
    not_found     = sum(1 for r in rows if r.get("Visa_Sponsor_Register","").lower() in ("not found","unknown",""))

    print(f"\n  ✓  Confirmed visa sponsor:  {visa_yes:>5,}  ({visa_yes/total:.0%})")
    print(f"  ~  EU Blue Card possible:   {visa_possible:>5,}  ({visa_possible/total:.0%})")
    print(f"  ✓  EOR available:           {eor_yes:>5,}  ({eor_yes/total:.0%})")
    print(f"  ✓  Remote friendly:         {remote_yes:>5,}  ({remote_yes/total:.0%})")
    print(f"  ✗  Visa signal unknown:     {not_found:>5,}  ({not_found/total:.0%})")

    # ---- 5. Top sectors ----
    section("5 / TOP SECTORS (by company count)")
    sector_counts = Counter(r.get("Sector","Unknown") for r in rows)
    for sector, count in sector_counts.most_common(12):
        bar = mini_bar(count, sector_counts.most_common(1)[0][1], 18)
        print(f"  {sector[:35]:<35} [{bar}] {count:,}")

    # ---- 6. Shortlist ----
    section("6 / COLD OUTREACH SHORTLIST")
    if os.path.exists(SHORTLIST):
        with open(SHORTLIST, newline="", encoding="utf-8") as f:
            shortlist = list(csv.DictReader(f))
        print(f"\n  Companies in shortlist:  {len(shortlist)}")
        if shortlist:
            scores = [int(r.get("Score", 0)) for r in shortlist]
            print(f"  Score range:  {min(scores)} – {max(scores)}  (avg {sum(scores)//len(scores)})")
            print(f"\n  Top 10:")
            for r in shortlist[:10]:
                score   = r.get("Score","?")
                company = r.get("Company","")[:36]
                country = r.get("Country","")[:14]
                notes   = r.get("Match_Notes","")[:40]
                print(f"    [{score:>3}] {company:<36} {country:<14} {notes}")
    else:
        print("  Not generated yet. Run: python scripts/score_shortlist.py")

    # ---- 7. Outreach ----
    section("7 / OUTREACH STATUS")
    if os.path.exists(TRACKER):
        with open(TRACKER, newline="", encoding="utf-8") as f:
            tracker = list(csv.DictReader(f))
        counts  = Counter(r["Status"] for r in tracker)
        total_t = len(tracker)
        print(f"\n  Total contacted:  {total_t}")
        for status in ("Sent","FollowedUp","Replied","Failed","Bounced"):
            n = counts.get(status, 0)
            print(f"  {status:<12} {mini_bar(n, max(total_t,1), 15)}  {n}")
        replies = counts.get("Replied",0)
        if total_t > 0:
            print(f"\n  Reply rate:  {replies/total_t:.1%}  ({replies}/{total_t})")
    else:
        print("  Not started yet. Run: python scripts/send_outreach.py --dry-run")

    # ---- 8. Application tracker ----
    section("8 / APPLICATION PIPELINE")
    if os.path.exists(APPS):
        with open(APPS, newline="", encoding="utf-8") as f:
            apps = list(csv.DictReader(f))
        app_counts = Counter(r["Status"] for r in apps)
        for status in ["Applied","Phone Screen","Interview","Technical Test",
                        "Final Round","Offer","Rejected"]:
            n = app_counts.get(status, 0)
            if n:
                print(f"  {status:<18} {'█'*n}  {n}")
        total_apps = len(apps)
        print(f"\n  Total tracked:  {total_apps}")
    else:
        print("  No applications tracked yet.")
        print("  Add one: python scripts/tracker.py add \"Company\" \"Role\" \"URL\"")

    # ---- 9. Recent pipeline runs ----
    section("9 / RECENT PIPELINE RUNS")
    if os.path.exists(LOG):
        with open(LOG, newline="", encoding="utf-8") as f:
            log_rows = list(csv.DictReader(f))
        print()
        for r in log_rows[-8:]:
            dt     = r.get("Run_Date","")[:16]
            source = r.get("Source","")[:38]
            added  = r.get("Companies_Added","0")
            print(f"  {dt}  {source:<38} +{int(added):>5,}")
    else:
        print("  No pipeline runs logged yet.")

    # ---- 10. What to do next ----
    section("WHAT TO DO NEXT")
    steps = []
    if total < PLAN_MIN:
        steps.append(f"Run scrapers  →  python scripts/run_scrapers.py  (need {PLAN_MIN-total:,} more)")
    steps.append("Re-score      →  python scripts/score_shortlist.py")
    steps.append("Re-enrich     →  python scripts/enrich_shortlist.py")
    if os.path.exists(SHORTLIST):
        steps.append("Preview emails →  python scripts/send_outreach.py --dry-run")
        steps.append("Send 20 emails →  python scripts/send_outreach.py --limit 20")
    steps.append("Track replies  →  python scripts/tracker.py list")
    steps.append("Full status    →  python scripts/status.py")
    print()
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print()


if __name__ == "__main__":
    run()
