"""
Gmail Cold Outreach Sender
==========================
Sends personalized cold emails to companies in data/enriched_shortlist.csv
via your Gmail account (OAuth2 — no password stored).

ONE-TIME SETUP (takes ~5 minutes):
  1. Go to https://console.cloud.google.com/
  2. Create a new project (or use an existing one)
  3. APIs & Services → Library → search "Gmail API" → Enable
  4. APIs & Services → Credentials → Create Credentials → OAuth client ID
     - Application type: Desktop app
     - Name: employer-discovery
  5. Download JSON → save as: config/gmail_credentials.json
  6. Run once: python scripts/send_outreach.py --dry-run
     A browser will open for one-time auth. Token saved to config/gmail_token.json.

DAILY USAGE:
  python scripts/send_outreach.py --dry-run          # Preview emails without sending
  python scripts/send_outreach.py --limit 20         # Send up to 20 emails today
  python scripts/send_outreach.py --limit 5          # Send just 5 (start small)
  python scripts/send_outreach.py --company "Stripe" # Send to one company only
  python scripts/send_outreach.py --show-tracker     # See what's been sent + replies

MARK A REPLY:
  python scripts/tracker.py mark-replied "CompanyName"

RATE LIMITS:
  Gmail allows ~500 emails/day on personal accounts (2000 on Google Workspace).
  Default limit here is 20/day. A 2–5 second delay is added between sends
  to avoid triggering spam filters.
"""
import argparse
import base64
import csv
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.dirname(__file__))
from candidate_profile import CANDIDATE, SIGNATURE, get_best_project, get_skill_overlap, get_visa_line, get_language_line

BASE = os.path.join(os.path.dirname(__file__), "..")
ENRICHED_PATH  = os.path.join(BASE, "data", "enriched_shortlist.csv")
TRACKER_PATH   = os.path.join(BASE, "data", "outreach_tracker.csv")
CREDS_PATH     = os.path.join(BASE, "config", "gmail_credentials.json")
TOKEN_PATH     = os.path.join(BASE, "config", "gmail_token.json")

TRACKER_FIELDS = [
    "Company", "To_Email", "Subject", "Status",
    "Sent_At", "Replied_At", "Score", "Sector", "Country",
    "Careers_URL", "Notes",
]

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


# ---------------------------------------------------------------------------
# Gmail Authentication
# ---------------------------------------------------------------------------

def get_gmail_service():
    """Authenticate with Gmail API. Opens browser on first run."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("\nERROR: Gmail API libraries are not installed.")
        print("Fix: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client\n")
        sys.exit(1)

    os.makedirs(os.path.join(BASE, "config"), exist_ok=True)

    if not os.path.exists(CREDS_PATH):
        print(f"\nERROR: Gmail credentials file not found.")
        print(f"Expected at: {CREDS_PATH}")
        print("\nSetup steps:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. APIs & Services → Enable 'Gmail API'")
        print("  3. Credentials → Create OAuth client ID (Desktop app)")
        print(f"  4. Download JSON → save as config/gmail_credentials.json\n")
        sys.exit(1)

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = _load_creds(TOKEN_PATH)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"  Auth saved to {TOKEN_PATH}")

    return build("gmail", "v1", credentials=creds)


def _load_creds(token_path):
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_file(token_path, GMAIL_SCOPES)


# ---------------------------------------------------------------------------
# Outreach Tracker
# ---------------------------------------------------------------------------

def load_tracker() -> list:
    if not os.path.exists(TRACKER_PATH):
        return []
    with open(TRACKER_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_tracker(rows: list):
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def already_contacted(company: str, tracker: list) -> bool:
    return any(
        r["Company"].lower().strip() == company.lower().strip()
        and r["Status"] in ("Sent", "Replied", "Bounced")
        for r in tracker
    )


# ---------------------------------------------------------------------------
# Email Helpers
# ---------------------------------------------------------------------------

def domain_from_url(url: str) -> str:
    if not url or url in ("Unknown", ""):
        return ""
    url = url.lower().strip()
    for prefix in ("https://", "http://", "www."):
        url = url.replace(prefix, "")
    return url.split("/")[0].strip()


def guess_to_email(company: str, website: str, careers_url: str) -> str:
    """
    Best-guess the careers email. Tries careers@ first, then jobs@.
    Falls back to 'careers@{slug}.com' if no domain is available.
    """
    domain = domain_from_url(website) or domain_from_url(careers_url)
    if domain and "." in domain:
        return f"careers@{domain}"
    # Last resort: slug the company name
    slug = company.lower().replace(" ", "").replace(".", "")[:30]
    return f"careers@{slug}.com"


def build_subject(company: str) -> str:
    return f"AI/Data Engineer — {company} | EU Blue Card Eligible"


def build_body(company: str, sector: str, tech_stack: str, match_notes: str,
               country: str, remote: str, open_role: str = "",
               language_req: str = "") -> str:
    """Generate a CV-personalized cold email body."""
    project      = get_best_project(sector, match_notes, tech_stack)
    overlaps     = get_skill_overlap(tech_stack)
    visa_line    = get_visa_line(country, remote=remote)
    lang_line    = get_language_line(language_req)

    role_ref = f"the {open_role} role" if open_role else "potential AI/Data Engineering opportunities"

    if overlaps:
        tech_line = (
            f"I noticed your stack includes {', '.join(overlaps[:3])} — "
            "tools I use in production daily."
        )
    elif sector and sector not in ("Tech", "Unknown"):
        tech_line = f"Your focus on {sector} maps closely to what I've been building."
    else:
        tech_line = "Your engineering culture and product direction caught my attention."

    lang_block = f"\n{lang_line}\n" if lang_line else ""

    body = f"""Hi {company} Team,

I came across {company} while researching {sector} companies and wanted to reach out directly about {role_ref}.

{tech_line}

A recent example of my work: {project['one_liner']}.

My production stack: Python · Java 17/Spring Boot 3 · Databricks · dbt · GCP · Azure Data Factory · Kubernetes · RAG/LLM pipelines. Currently delivering an institutional equity research AI platform at a London fintech.

{visa_line}
{lang_block}
Would you be open to a 20-minute call to explore fit?

{SIGNATURE}"""
    return body.strip()


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
# Main Send Flow
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, daily_limit: int = 20, company_filter: str = None):
    if not os.path.exists(ENRICHED_PATH):
        print(f"ERROR: {ENRICHED_PATH} not found.")
        print("Run: python scripts/enrich_shortlist.py first.")
        sys.exit(1)

    with open(ENRICHED_PATH, newline="", encoding="utf-8") as f:
        companies = list(csv.DictReader(f))

    tracker       = load_tracker()
    already_sent  = {r["Company"].lower() for r in tracker if r["Status"] in ("Sent", "Replied", "Bounced")}
    sent_today    = sum(1 for r in tracker
                        if r.get("Sent_At", "")[:10] == datetime.now().strftime("%Y-%m-%d"))

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Cold Outreach Sender")
    print(f"  Enriched companies:  {len(companies)}")
    print(f"  Already contacted:   {len(already_sent)}")
    print(f"  Sent today:          {sent_today} / {daily_limit} daily limit")
    print(f"  Remaining today:     {max(0, daily_limit - sent_today)}\n")

    if sent_today >= daily_limit and not dry_run:
        print(f"Daily limit ({daily_limit}) already reached. Run again tomorrow.")
        print(f"To increase the limit: --limit 30")
        return

    service = None
    if not dry_run:
        print("  Authenticating with Gmail...")
        service = get_gmail_service()
        print("  ✓ Gmail ready\n")

    sent_count   = 0
    new_tracker  = []

    for row in companies:
        if sent_today + sent_count >= daily_limit:
            print(f"\n  Daily limit ({daily_limit}) reached. Run again tomorrow.")
            break

        company = row.get("Company", "").strip()
        if not company:
            continue
        if company_filter and company_filter.lower() not in company.lower():
            continue
        if company.lower() in already_sent:
            continue

        website     = row.get("Website", "")
        careers_url = row.get("Careers_URL", "Unknown")
        sector      = row.get("Sector", "Tech")
        tech_stack  = row.get("Tech_Stack", "")
        match_notes = row.get("Match_Notes", "")
        country     = row.get("Country", "")
        remote       = row.get("Remote", "")
        score        = row.get("Score", "0")
        open_role    = row.get("Open_Roles_Found", "")
        language_req = row.get("Language_Requirement", "")

        to_email = guess_to_email(company, website, careers_url)
        subject  = build_subject(company)
        body     = build_body(company, sector, tech_stack, match_notes,
                              country, remote, open_role, language_req)

        status_icon = "→" if dry_run else "✉"
        print(f"  [{int(score):>3}] {company[:38]:<38} {status_icon} {to_email}")

        if dry_run:
            print(f"         Subject : {subject}")
            print(f"         Preview : {body.split(chr(10))[2][:100]}...")
            print()
        else:
            success = gmail_send(service, to_email, subject, body)
            status  = "Sent" if success else "Failed"
            icon    = "✓" if success else "✗"
            print(f"         {icon} {status}")

            new_tracker.append({
                "Company":    company,
                "To_Email":   to_email,
                "Subject":    subject,
                "Status":     status,
                "Sent_At":    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "Replied_At": "",
                "Score":      score,
                "Sector":     sector,
                "Country":    country,
                "Careers_URL": careers_url,
                "Notes":      match_notes[:120] if match_notes else "",
            })

            if success:
                sent_count += 1
                time.sleep(random.uniform(2.0, 5.0))  # avoid spam flags

    # Persist tracker
    if not dry_run and new_tracker:
        tracker.extend(new_tracker)
        save_tracker(tracker)
        total_sent = len([r for r in tracker if r["Status"] == "Sent"])
        print(f"\n  Done. Sent {sent_count} emails this run.")
        print(f"  Total sent all-time: {total_sent}")
        print(f"  Tracker: {TRACKER_PATH}")
    elif dry_run:
        print(f"  [DRY RUN] Would send {len(new_tracker)} emails. No emails sent.")
        print(f"  Remove --dry-run to send for real.")


# ---------------------------------------------------------------------------
# Show Tracker Summary
# ---------------------------------------------------------------------------

def show_tracker():
    tracker = load_tracker()
    if not tracker:
        print("\nNo outreach sent yet.")
        print("Run: python scripts/send_outreach.py --dry-run")
        return

    counts = Counter(r["Status"] for r in tracker)
    replied = [r for r in tracker if r["Status"] == "Replied"]
    total   = len(tracker)

    print(f"\nOutreach Tracker — {total} total")
    print("-" * 55)
    for status in ("Sent", "Replied", "Failed", "Bounced"):
        n = counts.get(status, 0)
        if n:
            bar = "█" * min(n, 40)
            print(f"  {status:<10} {bar} {n}")
    if total > 0:
        reply_rate = len(replied) / total * 100
        print(f"\n  Reply rate:  {reply_rate:.1f}%  ({len(replied)}/{total})")

    if replied:
        print(f"\n  Replies received:")
        for r in replied:
            print(f"    ✓  {r['Company']:<35}  {r.get('Replied_At','')}")

    print(f"\n  To mark a reply: python scripts/tracker.py mark-replied \"Company\"")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send cold outreach emails via Gmail",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dry-run",      action="store_true", help="Preview emails without sending")
    parser.add_argument("--limit",        type=int, default=20, help="Max emails to send today (default 20)")
    parser.add_argument("--company",      type=str, default=None, help="Send to this company only (name match)")
    parser.add_argument("--show-tracker", action="store_true", help="Show outreach status and reply rate")
    args = parser.parse_args()

    if args.show_tracker:
        show_tracker()
    else:
        run(dry_run=args.dry_run, daily_limit=args.limit, company_filter=args.company)
