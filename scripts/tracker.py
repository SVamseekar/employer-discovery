"""
Application & Outreach Tracker
===============================
Tracks every application and outreach email. Your source of truth for
what's been sent, what's progressing, and what needs follow-up.

USAGE:
  python scripts/tracker.py list                        # All applications
  python scripts/tracker.py list --status Interview     # Filter by status
  python scripts/tracker.py add "Stripe" "Data Eng" "https://stripe.com/jobs/123"
  python scripts/tracker.py update "Stripe" --status "Phone Screen"
  python scripts/tracker.py update "Stripe" --notes "Spoke with recruiter Sarah"
  python scripts/tracker.py update "Stripe" --follow-up "2026-06-16"
  python scripts/tracker.py mark-replied "Stripe"       # Mark outreach reply received
  python scripts/tracker.py stats                       # Pipeline funnel stats
  python scripts/tracker.py follow-ups                  # Companies needing follow-up today
"""
import argparse
import csv
import os
import sys
from collections import Counter
from datetime import datetime, date, timezone

BASE         = os.path.join(os.path.dirname(__file__), "..")
APP_PATH     = os.path.join(BASE, "data", "applications.csv")
TRACKER_PATH = os.path.join(BASE, "data", "outreach_tracker.csv")

APP_FIELDS = [
    "Company", "Role", "Job_URL", "Source", "Status",
    "Applied_Date", "Follow_Up_Date", "Last_Action", "Notes",
]

PIPELINE_ORDER = [
    "Shortlisted", "Applied", "Email Sent", "Phone Screen",
    "Interview", "Technical Test", "Final Round", "Offer",
    "Rejected", "Withdrawn", "On Hold",
]


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_apps() -> list:
    if not os.path.exists(APP_PATH):
        return []
    with open(APP_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_apps(rows: list):
    os.makedirs(os.path.dirname(APP_PATH), exist_ok=True)
    with open(APP_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=APP_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args):
    rows = load_apps()
    if not rows:
        print("\nNo applications tracked yet.")
        print("Add one: python scripts/tracker.py add \"Company\" \"Role\" \"URL\"")
        return

    if args.status:
        rows = [r for r in rows if r["Status"].lower() == args.status.lower()]
        if not rows:
            print(f"No applications with status '{args.status}'.")
            return

    rows = sorted(rows, key=lambda r: r.get("Applied_Date",""), reverse=True)

    header = f"{'#':<4} {'Company':<35} {'Role':<28} {'Status':<18} {'Applied':<12} {'Follow-up'}"
    print(f"\n{header}")
    print("─" * 115)
    for i, r in enumerate(rows, 1):
        fu   = r.get("Follow_Up_Date","")
        flag = " ⚑" if fu and fu <= today() and r["Status"] not in ("Offer","Rejected","Withdrawn") else ""
        print(f"{i:<4} {r['Company'][:34]:<35} {r['Role'][:27]:<28} "
              f"{r['Status']:<18} {r.get('Applied_Date',''):<12} {fu}{flag}")

    print(f"\n  Total: {len(rows)}")
    overdue = [r for r in rows if r.get("Follow_Up_Date","") and
               r["Follow_Up_Date"] <= today() and
               r["Status"] not in ("Offer","Rejected","Withdrawn")]
    if overdue:
        print(f"  ⚑  {len(overdue)} follow-up(s) due today or overdue.")


def cmd_add(args):
    rows = load_apps()
    existing = {r["Company"].lower().strip() for r in rows}

    if args.company.lower().strip() in existing:
        print(f"'{args.company}' is already tracked.")
        print(f"Use: python scripts/tracker.py update \"{args.company}\" --status \"Applied\"")
        return

    rows.append({
        "Company":       args.company,
        "Role":          args.role,
        "Job_URL":       args.url or "",
        "Source":        args.source or "Manual",
        "Status":        "Shortlisted",
        "Applied_Date":  today(),
        "Follow_Up_Date": "",
        "Last_Action":   today(),
        "Notes":         args.notes or "",
    })
    save_apps(rows)
    print(f"  ✓ Added: {args.company} — {args.role} (status: Shortlisted)")
    print(f"  Next step: python scripts/tracker.py update \"{args.company}\" --status Applied")


def cmd_update(args):
    rows = load_apps()
    found = False
    for r in rows:
        if r["Company"].lower().strip() == args.company.lower().strip():
            old_status = r["Status"]
            if args.status:
                r["Status"]      = args.status
            if args.notes:
                r["Notes"]       = args.notes
            if args.follow_up:
                r["Follow_Up_Date"] = args.follow_up
            r["Last_Action"]     = today()
            found = True
            print(f"  ✓ {r['Company']}: {old_status} → {r['Status']}")
            if r.get("Follow_Up_Date"):
                print(f"    Follow-up set: {r['Follow_Up_Date']}")
            break

    if not found:
        print(f"  '{args.company}' not found.")
        print(f"  Add it first: python scripts/tracker.py add \"{args.company}\" \"Role\"")
        return

    save_apps(rows)


def cmd_mark_replied(args):
    """Mark a company's outreach as replied in the outreach tracker."""
    if not os.path.exists(TRACKER_PATH):
        print("  No outreach tracker found. Send some emails first.")
        return

    with open(TRACKER_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows   = list(reader)

    found = False
    for r in rows:
        if r["Company"].lower().strip() == args.company.lower().strip():
            r["Status"]     = "Replied"
            r["Replied_At"] = today()
            found           = True
            print(f"  ✓ Marked as replied: {r['Company']}")
            break

    if not found:
        print(f"  '{args.company}' not found in outreach tracker.")
        print(f"  Check: python scripts/send_outreach.py --show-tracker")
        return

    with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Also add to applications tracker automatically
    app_rows = load_apps()
    existing = {r["Company"].lower().strip() for r in app_rows}
    if args.company.lower().strip() not in existing:
        app_rows.append({
            "Company":        args.company,
            "Role":           "AI/Data Engineer",
            "Job_URL":        "",
            "Source":         "Cold Email Reply",
            "Status":         "Phone Screen",
            "Applied_Date":   today(),
            "Follow_Up_Date": "",
            "Last_Action":    today(),
            "Notes":          "Replied to cold email",
        })
        save_apps(app_rows)
        print(f"  ✓ Also added to application tracker (status: Phone Screen)")


def cmd_follow_ups(args):
    """Show applications that need follow-up today or are overdue."""
    rows = load_apps()
    due = [r for r in rows
           if r.get("Follow_Up_Date","") and
           r["Follow_Up_Date"] <= today() and
           r["Status"] not in ("Offer","Rejected","Withdrawn")]
    if not due:
        print("\n  No follow-ups due today. You're on top of it!")
        return

    print(f"\n  Follow-ups due ({len(due)}):")
    print("  " + "─" * 80)
    for r in sorted(due, key=lambda x: x.get("Follow_Up_Date","")):
        overdue = r["Follow_Up_Date"] < today()
        flag    = " ⚑ OVERDUE" if overdue else " → due today"
        print(f"  {r['Company'][:35]:<35} {r['Status']:<18} {r.get('Follow_Up_Date','')}{flag}")
        if r.get("Notes"):
            print(f"    Notes: {r['Notes'][:70]}")
    print()


def cmd_stats(args):
    rows = load_apps()
    if not rows:
        print("\n  No applications tracked yet.")
        return

    counts   = Counter(r["Status"] for r in rows)
    total    = len(rows)
    active   = sum(v for k, v in counts.items() if k not in ("Rejected","Withdrawn","On Hold"))
    rejected = counts.get("Rejected", 0)

    print(f"\n  Application Funnel — {total} total, {active} active")
    print("  " + "─" * 55)
    for status in PIPELINE_ORDER:
        n = counts.get(status, 0)
        if n == 0:
            continue
        bar = "█" * n + " " * max(0, 20 - n)
        pct = n / total * 100
        print(f"  {status:<18} {bar}  {n:>3}  ({pct:.0f}%)")

    print(f"\n  Active:    {active}")
    print(f"  Rejected:  {rejected}")

    # Conversion rates
    applied = counts.get("Applied", 0) + counts.get("Email Sent", 0)
    screens = counts.get("Phone Screen", 0)
    interviews = (counts.get("Interview",0) + counts.get("Technical Test",0) +
                  counts.get("Final Round",0))
    offers = counts.get("Offer", 0)

    if applied > 0:
        print(f"\n  Applied → Phone screen:  {screens}/{applied} = {screens/applied:.0%}")
    if screens > 0:
        print(f"  Screen  → Interview:     {interviews}/{screens} = {interviews/screens:.0%}")
    if interviews > 0:
        print(f"  Interview → Offer:       {offers}/{interviews} = {offers/interviews:.0%}")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Job application & outreach tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="List all applications")
    p_list.add_argument("--status", help="Filter by status (e.g. Interview)")

    # add
    p_add = sub.add_parser("add", help="Add a new application")
    p_add.add_argument("company")
    p_add.add_argument("role")
    p_add.add_argument("url", nargs="?", default="")
    p_add.add_argument("--source",  default="Manual")
    p_add.add_argument("--notes",   default="")

    # update
    p_upd = sub.add_parser("update", help="Update application status")
    p_upd.add_argument("company")
    p_upd.add_argument("--status",    choices=PIPELINE_ORDER)
    p_upd.add_argument("--notes",     help="Add a note")
    p_upd.add_argument("--follow-up", dest="follow_up", help="Follow-up date (YYYY-MM-DD)")

    # mark-replied
    p_rep = sub.add_parser("mark-replied", help="Mark an outreach email as replied")
    p_rep.add_argument("company")

    # follow-ups
    sub.add_parser("follow-ups", help="Show applications needing follow-up today")

    # stats
    sub.add_parser("stats", help="Show funnel conversion stats")

    args = parser.parse_args()

    dispatch = {
        "list":         cmd_list,
        "add":          cmd_add,
        "update":       cmd_update,
        "mark-replied": cmd_mark_replied,
        "follow-ups":   cmd_follow_ups,
        "stats":        cmd_stats,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()
