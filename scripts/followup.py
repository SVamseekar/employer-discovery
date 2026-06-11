"""
Follow-Up Sender
================
Reads outreach_tracker.csv, finds Sent emails that are 5–10 days old
and have NOT received a reply, then sends a short follow-up.

WHY THIS MATTERS:
  ~80% of cold email replies come from follow-ups. A one-liner bump
  3x's response rate vs. a single email alone.

USAGE:
  python scripts/followup.py --dry-run         # Preview without sending
  python scripts/followup.py --limit 10        # Send up to 10 follow-ups
  python scripts/followup.py --days-min 5      # Only follow up after 5 days (default)
  python scripts/followup.py --days-max 14     # Give up after 14 days (default)
"""
import argparse
import base64
import csv
import os
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))
from candidate_profile import CANDIDATE, SIGNATURE

BASE = os.path.join(os.path.dirname(__file__), "..")
TRACKER_PATH = os.path.join(BASE, "data", "outreach_tracker.csv")
CREDS_PATH   = os.path.join(BASE, "config", "gmail_credentials.json")
TOKEN_PATH   = os.path.join(BASE, "config", "gmail_token.json")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

TRACKER_FIELDS = [
    "Company", "To_Email", "Subject", "Status",
    "Sent_At", "Replied_At", "Score", "Sector", "Country",
    "Careers_URL", "Notes",
]

# Follow-up window
DEFAULT_DAYS_MIN = 5    # don't follow up sooner than this
DEFAULT_DAYS_MAX = 14   # give up after this many days
DEFAULT_LIMIT    = 10


# ---------------------------------------------------------------------------
# Gmail Auth (shared with send_outreach.py)
# ---------------------------------------------------------------------------

def get_gmail_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\nERROR: Gmail API libraries not installed.")
        print("Fix: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client\n")
        sys.exit(1)

    if not os.path.exists(CREDS_PATH):
        print(f"\nERROR: {CREDS_PATH} not found. Run send_outreach.py --dry-run first to set up auth.\n")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_PATH):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ---------------------------------------------------------------------------
# Follow-up logic
# ---------------------------------------------------------------------------

def parse_sent_at(sent_at_str: str):
    """Parse 'YYYY-MM-DD HH:MM UTC' → datetime. Returns None on failure."""
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(sent_at_str.replace(" UTC", ""), fmt.replace(" UTC", ""))
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def days_since(sent_at_str: str) -> int:
    """Return days since the email was sent. Returns -1 on parse failure."""
    dt = parse_sent_at(sent_at_str)
    if not dt:
        return -1
    delta = datetime.now(timezone.utc) - dt
    return delta.days


def build_followup_email(company: str, original_subject: str) -> str:
    """
    Short, non-needy follow-up. References the original subject.
    Intentionally brief — 3 sentences max.
    """
    return f"""Hi {company} Team,

Following up on my note from last week — just wanted to make sure it didn't get buried.

I'm a Hyderabad-based AI/Data Engineer with production experience in Databricks, dbt, GCP, and LLM pipelines. Happy to share my CV or jump on a quick call if there's a fit.

{SIGNATURE}"""


def encode_message(to: str, subject: str, body: str) -> dict:
    msg = MIMEMultipart("alternative")
    msg["to"]      = to
    msg["from"]    = CANDIDATE["email"]
    msg["subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


def gmail_send(service, to: str, subject: str, body: str) -> bool:
    try:
        service.users().messages().send(
            userId="me", body=encode_message(to, subject, body)
        ).execute()
        return True
    except Exception as e:
        print(f"    ✗ Send error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_tracker():
    if not os.path.exists(TRACKER_PATH):
        return []
    with open(TRACKER_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_tracker(rows: list):
    with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as f:
        # preserve original fields + add FollowUp_Sent_At if not there
        all_fields = TRACKER_FIELDS + ["FollowUp_Sent_At"]
        # but only write fields that exist in the data
        actual_fields = list(rows[0].keys()) if rows else TRACKER_FIELDS
        if "FollowUp_Sent_At" not in actual_fields:
            actual_fields.append("FollowUp_Sent_At")
        writer = csv.DictWriter(f, fieldnames=actual_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run(dry_run=False, limit=DEFAULT_LIMIT,
        days_min=DEFAULT_DAYS_MIN, days_max=DEFAULT_DAYS_MAX):

    tracker = load_tracker()
    if not tracker:
        print("No tracker found. Send some outreach first: python scripts/send_outreach.py --limit 20")
        return

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Find candidates for follow-up
    candidates = []
    for row in tracker:
        status = row.get("Status", "")
        if status != "Sent":
            continue  # skip Replied, Failed, Bounced, FollowedUp
        if row.get("FollowUp_Sent_At", ""):
            continue  # already followed up once
        sent_at = row.get("Sent_At", "")
        age = days_since(sent_at)
        if age < days_min or age > days_max:
            continue
        candidates.append((age, row))

    # Sort by oldest first (most overdue)
    candidates.sort(key=lambda x: x[0], reverse=True)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Follow-Up Sender")
    print(f"  Tracker entries:        {len(tracker)}")
    print(f"  Follow-up candidates:   {len(candidates)}")
    print(f"  Window:                 {days_min}–{days_max} days since send")
    print(f"  Limit this run:         {limit}\n")

    if not candidates:
        print("  Nothing to follow up on right now.")
        print(f"  (Looking for 'Sent' emails that are {days_min}–{days_max} days old with no follow-up yet.)")
        return

    service = None
    if not dry_run:
        print("  Authenticating with Gmail...")
        service = get_gmail_service()
        print("  ✓ Gmail ready\n")

    sent_count = 0
    company_map = {row.get("Company", "").lower(): row for row in tracker}

    for age, row in candidates[:limit]:
        company    = row.get("Company", "").strip()
        to_email   = row.get("To_Email", "")
        orig_subj  = row.get("Subject", "")

        # Follow-up subject: prepend "Re: " to original
        followup_subject = f"Re: {orig_subj}" if not orig_subj.startswith("Re:") else orig_subj
        body = build_followup_email(company, orig_subj)

        icon = "→" if dry_run else "✉"
        print(f"  [{age:>2}d] {company[:40]:<40} {icon} {to_email}")

        if dry_run:
            print(f"         Subject : {followup_subject}")
            print(f"         Preview : {body.split(chr(10))[2][:100]}...")
            print()
        else:
            success = gmail_send(service, to_email, followup_subject, body)
            icon    = "✓" if success else "✗"
            print(f"         {icon} {'Sent' if success else 'Failed'}")

            if success:
                # Update tracker row
                row["FollowUp_Sent_At"] = now_str
                row["Status"] = "FollowedUp"
                sent_count += 1
                time.sleep(random.uniform(2.0, 4.0))

    if not dry_run:
        save_tracker(tracker)
        print(f"\n  Done. Sent {sent_count} follow-ups.")
        print(f"  Tracker updated: {TRACKER_PATH}")
    else:
        print(f"  [DRY RUN] Would send {min(len(candidates), limit)} follow-ups.")
        print(f"  Remove --dry-run to send for real.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send follow-up emails for unreplied outreach")
    parser.add_argument("--dry-run",   action="store_true", help="Preview without sending")
    parser.add_argument("--limit",     type=int, default=DEFAULT_LIMIT,    help=f"Max follow-ups to send (default {DEFAULT_LIMIT})")
    parser.add_argument("--days-min",  type=int, default=DEFAULT_DAYS_MIN, help=f"Min days since original send (default {DEFAULT_DAYS_MIN})")
    parser.add_argument("--days-max",  type=int, default=DEFAULT_DAYS_MAX, help=f"Max days since original send (default {DEFAULT_DAYS_MAX})")
    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        limit=args.limit,
        days_min=args.days_min,
        days_max=args.days_max,
    )
