import os
import sys
import csv
import subprocess
from datetime import datetime, timezone
from typing import Optional, List
from collections import Counter
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add the scripts directory to the path so we can import our pipeline modules
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS_DIR)

# Import existing modules
import candidate_profile
try:
    import send_outreach
except ImportError:
    send_outreach = None

try:
    import tracker
except ImportError:
    tracker = None

try:
    import score_shortlist
except ImportError:
    score_shortlist = None

# Base path for the project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
MASTER_CSV = os.path.join(DATA_DIR, "master_employers.csv")
SHORTLIST_CSV = os.path.join(DATA_DIR, "cold_outreach_shortlist.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "enriched_shortlist.csv")
TRACKER_CSV = os.path.join(DATA_DIR, "outreach_tracker.csv")
APPS_CSV = os.path.join(DATA_DIR, "applications.csv")
LOG_CSV = os.path.join(DATA_DIR, "pipeline_log.csv")

app = FastAPI(title="Employer Discovery & CRM Portal")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active pipeline tasks status tracking
pipeline_tasks = {
    "run_scrapers": {"status": "Idle", "last_run": None, "output": ""},
    "score_shortlist": {"status": "Idle", "last_run": None, "output": ""},
    "enrich_shortlist": {"status": "Idle", "last_run": None, "output": ""},
    "visa_crossref": {"status": "Idle", "last_run": None, "output": ""}
}

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class EmailUpdateSchema(BaseModel):
    to_email: str
    email_draft: str
    job_url: Optional[str] = ""

class ApplicationCreateUpdateSchema(BaseModel):
    company: str
    role: str
    url: Optional[str] = ""
    status: str
    notes: Optional[str] = ""
    follow_up: Optional[str] = ""  # YYYY-MM-DD format

class EmailSendSchema(BaseModel):
    company: str
    to_email: str
    subject: str
    body: str

# ---------------------------------------------------------------------------
# Helper functions for calculations (derived from status.py & tracker.py)
# ---------------------------------------------------------------------------

EU_COUNTRIES = [
    "germany", "netherlands", "france", "sweden", "ireland", "spain", "portugal",
    "denmark", "finland", "austria", "belgium", "poland", "czech", "norway",
    "switzerland", "europe", " eu", "estonia", "latvia", "lithuania", "greece",
    "hungary", "romania", "bulgaria", "croatia", "slovakia", "slovenia"
]

INDIA_TERMS = [
    "india", "hyderabad", "bangalore", "bengaluru", "mumbai",
    "pune", "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata"
]

def classify_region(row):
    geo = (row.get("Country","") + " " + row.get("Hiring_Geography","") + " " + row.get("City","")).lower()
    if any(c in geo for c in EU_COUNTRIES):
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
    return "Startup"

import html
import re

def clean_company_name(name: str) -> str:
    if not name:
        return ""
    # Decode html entities like &#x27; or &amp; or &lt;
    name = html.unescape(name)
    # Strip quotes and whitespace
    name = name.strip("'\"` \t\n\r")
    
    # Remove text inside parentheses or brackets like "(YC S21)" or "[Remote]"
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'\[.*?\]', '', name)
    return name.strip("'\"` \t\n\r")

def is_valid_company(name: str) -> bool:
    if not name:
        return False
        
    # Must start with letter or digit
    if not re.match(r'^[a-zA-Z0-9]', name):
        return False
        
    lower_name = name.lower()
    junk_patterns = [
        r'\bwe\'re\b', r'\bwe are\b', r'\bi am\b', r'\blooking for\b',
        r'\bposition\b', r'\brole\b', r'\bjob\b', r'\bhiring\b',
        r'\bapply\b', r'\bcareers?\b', r'\bcv\b', r'\bresume\b',
        r'\bhttp\b', r'\bwww\b', r'\bclick\b', r'\blink\b',
        r'\bemail\b', r'\bcontact\b', r'\bsentence\b', r'\bpoint by\b',
        r'\bago\b', r'\bupvote\b', r'\bdownvote\b', r'\bthanks\b',
        r'\bappreciate\b', r'\bblog\b', r'\bpost\b', r'\beligible\b',
        r'\bsponsor\b', r'\bvisa\b', r'\bwork in\b', r'\bcomment\b',
        r'\bthread\b', r'\bposted by\b'
    ]
    if any(re.search(p, lower_name) for p in junk_patterns):
        return False
        
    # Sentence check: if there are more than 4 words and contains common lowercase english connector words
    words = name.split()
    if len(words) > 4:
        connectors = {"to", "for", "the", "and", "our", "you", "your", "with", "from", "is", "a", "of", "in", "on", "at", "by", "that", "this", "it", "us"}
        connector_count = sum(1 for w in words if w.lower() in connectors)
        if connector_count >= 2 or connector_count / len(words) > 0.3:
            return False
            
    # Avoid general job titles like "Software Engineer" if they leak
    job_titles = [r'\bsoftware engineer\b', r'\bfrontend engineer\b', r'\bbackend engineer\b', 
                  r'\bdata engineer\b', r'\bfull stack engineer\b', r'\bfrontend developer\b', 
                  r'\bbackend developer\b', r'\bdata scientist\b', r'\bproduct manager\b']
    if any(re.search(title, lower_name) for title in job_titles):
         return False
            
    # Length check
    if len(name) < 2 or len(name) > 50:
        return False
        
    return True

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/config-status")
def get_config_status():
    """Check configuration and API credentials status."""
    creds_exist = os.path.exists(os.path.join(BASE_DIR, "config", "gmail_credentials.json"))
    token_exist = os.path.exists(os.path.join(BASE_DIR, "config", "gmail_token.json"))
    return {
        "gmail_credentials_exists": creds_exist,
        "gmail_token_exists": token_exist,
        "candidate": candidate_profile.CANDIDATE
    }

@app.get("/api/status")
def get_dashboard_status():
    """Returns aggregated pipeline status data similar to status.py."""
    if not os.path.exists(MASTER_CSV):
        return {"error": "Master database file not found. Run a scraper or import task first."}

    # Load master employers
    with open(MASTER_CSV, newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))
    
    rows = []
    for r in raw_rows:
        cleaned = clean_company_name(r.get("Company", ""))
        if is_valid_company(cleaned):
            r["Company"] = cleaned
            rows.append(r)
    total_employers = len(rows)

    # Calculate regional counts
    region_counts = Counter(classify_region(r) for r in rows)
    regions = []
    region_targets = {"Europe": 0.20, "USA": 0.20, "Australia/NZ": 0.20, "India": 0.20, "Remote/Global": 0.20}
    for r_name, target in region_targets.items():
        cnt = region_counts.get(r_name, 0)
        regions.append({
            "name": r_name,
            "count": cnt,
            "percentage": round(cnt / total_employers * 100, 1) if total_employers > 0 else 0,
            "target": target * 100
        })

    # Calculate stage counts
    stage_counts = Counter(classify_stage(r) for r in rows)
    stages = []
    stage_targets = {"Startup": 0.30, "Scaleup": 0.30, "Mid-market": 0.20, "Enterprise": 0.10, "Hidden Champion": 0.10}
    for s_name, target in stage_targets.items():
        cnt = stage_counts.get(s_name, 0)
        stages.append({
            "name": s_name,
            "count": cnt,
            "percentage": round(cnt / total_employers * 100, 1) if total_employers > 0 else 0,
            "target": target * 100
        })

    # Visa and remote signals
    visa_yes = sum(1 for r in rows if r.get("Visa_Sponsorship","").lower() == "yes")
    visa_possible = sum(1 for r in rows if r.get("Visa_Sponsorship","").lower() == "possible")
    eor_yes = sum(1 for r in rows if r.get("EOR","").lower() == "yes")
    remote_yes = sum(1 for r in rows if r.get("Remote","").lower() == "yes")
    not_found = sum(1 for r in rows if r.get("Visa_Sponsor_Register","").lower() in ("not found","unknown",""))

    visa_signals = {
        "confirmed": visa_yes,
        "possible": visa_possible,
        "eor": eor_yes,
        "remote": remote_yes,
        "unknown": not_found
    }

    # Top sectors
    sector_counts = Counter(r.get("Sector","Unknown") for r in rows)
    top_sectors = [{"sector": sect, "count": cnt} for sect, cnt in sector_counts.most_common(12)]

    # Shortlist info
    shortlist_info = {"total": 0, "min_score": 0, "max_score": 0, "avg_score": 0}
    if os.path.exists(SHORTLIST_CSV):
        with open(SHORTLIST_CSV, newline="", encoding="utf-8") as f:
            shortlist_rows = list(csv.DictReader(f))
        shortlist_info["total"] = len(shortlist_rows)
        if shortlist_rows:
            scores = [int(r.get("Score", 0)) for r in shortlist_rows]
            shortlist_info["min_score"] = min(scores)
            shortlist_info["max_score"] = max(scores)
            shortlist_info["avg_score"] = sum(scores) // len(shortlist_rows)

    # Outreach status
    outreach_info = {"total_contacted": 0, "reply_rate": 0, "breakdown": {}}
    if os.path.exists(TRACKER_CSV):
        with open(TRACKER_CSV, newline="", encoding="utf-8") as f:
            tracker_rows = list(csv.DictReader(f))
        outreach_info["total_contacted"] = len(tracker_rows)
        counts = Counter(r["Status"] for r in tracker_rows)
        outreach_info["breakdown"] = dict(counts)
        replies = counts.get("Replied", 0)
        outreach_info["reply_rate"] = round(replies / len(tracker_rows) * 100, 1) if len(tracker_rows) > 0 else 0

    # Applications pipeline
    app_pipeline = {}
    if os.path.exists(APPS_CSV):
        with open(APPS_CSV, newline="", encoding="utf-8") as f:
            app_rows = list(csv.DictReader(f))
        app_counts = Counter(r["Status"] for r in app_rows)
        app_pipeline = dict(app_counts)

    # Recent runs
    recent_runs = []
    if os.path.exists(LOG_CSV):
        with open(LOG_CSV, newline="", encoding="utf-8") as f:
            log_rows = list(csv.DictReader(f))
        for r in log_rows[-8:]:
            recent_runs.append({
                "run_date": r.get("Run_Date","")[:16],
                "source": r.get("Source",""),
                "added": int(r.get("Companies_Added","0"))
            })
        recent_runs.reverse()

    # Generate next steps list
    plan_min = 5000
    next_steps = []
    if total_employers < plan_min:
        next_steps.append(f"Scrape more companies to reach the 5,000 minimum target (need {plan_min - total_employers:,} more).")
    
    if shortlist_info["total"] == 0:
        next_steps.append("Run the scoring script to shortlist top companies matching your CV.")
    
    if not os.path.exists(ENRICHED_CSV):
        next_steps.append("Enrich your shortlist to automatically search for open jobs and generate cold emails.")
    elif outreach_info["total_contacted"] == 0:
        next_steps.append("Set up your Gmail credentials and trigger your first cold emails.")
    
    overdue_count = 0
    if os.path.exists(APPS_CSV):
        today_str = datetime.now().strftime("%Y-%m-%d")
        overdue_count = sum(1 for r in app_rows if r.get("Follow_Up_Date","") and r["Follow_Up_Date"] <= today_str and r["Status"] not in ("Offer","Rejected","Withdrawn"))
        if overdue_count > 0:
            next_steps.append(f"Follow up with the {overdue_count} overdue application(s) marked in your CRM pipeline.")
    
    next_steps.append("Review company shortlist drafts before initiating automated bulk cold emails.")

    return {
        "database": {
            "total": total_employers,
            "plan_min": plan_min,
            "plan_max": 20000,
            "percentage": round(min(total_employers / plan_min * 100, 100), 1)
        },
        "regions": regions,
        "stages": stages,
        "visa_signals": visa_signals,
        "top_sectors": top_sectors,
        "shortlist": shortlist_info,
        "outreach": outreach_info,
        "applications": app_pipeline,
        "recent_runs": recent_runs,
        "next_steps": next_steps
    }

@app.get("/api/employers")
def get_employers(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    region: Optional[str] = None,
    stage: Optional[str] = None,
    visa: Optional[str] = None,
    sort_by: str = "Company",
    sort_dir: str = "asc"
):
    """Retrieve filtered, paginated list of employers in master_employers.csv."""
    if not os.path.exists(MASTER_CSV):
        return {"total": 0, "data": []}

    with open(MASTER_CSV, newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))

    rows = []
    for r in raw_rows:
        cleaned = clean_company_name(r.get("Company", ""))
        if is_valid_company(cleaned):
            r["Company"] = cleaned
            if score_shortlist:
                s, _ = score_shortlist.score(r)
                r["Score"] = str(s)
            else:
                r["Score"] = "0"
            rows.append(r)

    # Add calculated fields for filtering
    for r in rows:
        r["_Region"] = classify_region(r)
        r["_Stage"] = classify_stage(r)

    # Filter
    filtered_rows = rows
    if search:
        search_lower = search.lower()
        filtered_rows = [
            r for r in filtered_rows
            if search_lower in r.get("Company","").lower()
            or search_lower in r.get("Domain","").lower()
            or search_lower in r.get("Sector","").lower()
            or search_lower in r.get("Tech_Stack","").lower()
            or search_lower in r.get("Country","").lower()
            or search_lower in r.get("City","").lower()
        ]

    if region:
        filtered_rows = [r for r in filtered_rows if r["_Region"].lower() == region.lower()]

    if stage:
        filtered_rows = [r for r in filtered_rows if r["_Stage"].lower() == stage.lower()]

    if visa:
        if visa.lower() == "confirmed":
            filtered_rows = [r for r in filtered_rows if r.get("Visa_Sponsorship","").lower() == "yes"]
        elif visa.lower() == "possible":
            filtered_rows = [r for r in filtered_rows if r.get("Visa_Sponsorship","").lower() == "possible"]
        elif visa.lower() == "remote":
            filtered_rows = [r for r in filtered_rows if r.get("Remote","").lower() == "yes"]

    # Sort
    reverse = True if sort_dir.lower() == "desc" else False
    
    # Custom sort helpers
    def get_sort_val(row):
        val = row.get(sort_by, "")
        if sort_by == "Score":
            try:
                return int(val) if val else 0
            except ValueError:
                return 0
        return val.lower()

    if sort_by in ["Company", "Sector", "Country", "Score", "Visa_Sponsorship"]:
        filtered_rows = sorted(filtered_rows, key=get_sort_val, reverse=reverse)

    # Paginate
    total = len(filtered_rows)
    start = (page - 1) * limit
    end = start + limit
    paginated_data = filtered_rows[start:end]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": paginated_data
    }

@app.get("/api/shortlist")
def get_shortlist():
    """Retrieve shortlisted companies with their email drafts."""
    source_file = ENRICHED_CSV if os.path.exists(ENRICHED_CSV) else SHORTLIST_CSV
    if not os.path.exists(source_file):
        return []

    with open(source_file, newline="", encoding="utf-8") as f:
        raw_rows = list(csv.DictReader(f))

    rows = []
    for r in raw_rows:
        cleaned = clean_company_name(r.get("Company", ""))
        if is_valid_company(cleaned):
            r["Company"] = cleaned
            rows.append(r)

    # Check outreach status for each shortlisted company
    sent_map = {}
    if os.path.exists(TRACKER_CSV):
        with open(TRACKER_CSV, newline="", encoding="utf-8") as f:
            tracker_rows = list(csv.DictReader(f))
        for tr in tracker_rows:
            sent_map[tr["Company"].lower().strip()] = {
                "Status": tr.get("Status", "Unsent"),
                "Sent_At": tr.get("Sent_At", ""),
                "Replied_At": tr.get("Replied_At", ""),
                "To_Email": tr.get("To_Email", "")
            }

    for r in rows:
        company_key = r["Company"].lower().strip()
        if company_key in sent_map:
            r["Outreach_Status"] = sent_map[company_key]["Status"]
            r["Outreach_Sent_At"] = sent_map[company_key]["Sent_At"]
            r["Outreach_To_Email"] = sent_map[company_key]["To_Email"]
        else:
            r["Outreach_Status"] = "Unsent"
            r["Outreach_Sent_At"] = ""
            r["Outreach_To_Email"] = ""

        # Provide a default To_Email if missing
        if "To_Email" not in r or not r["To_Email"]:
            if send_outreach:
                r["To_Email"] = send_outreach.guess_to_email(r["Company"], r.get("Domain", ""), r.get("Careers_URL", ""))
            else:
                r["To_Email"] = f"careers@{r['Company'].lower().replace(' ', '')}.com"

        # Provide a default Cold_Email_Draft if missing
        if "Cold_Email_Draft" not in r or not r["Cold_Email_Draft"]:
            if send_outreach:
                r["Cold_Email_Draft"] = send_outreach.build_body(
                    company=r["Company"],
                    sector=r.get("Sector",""),
                    tech_stack=r.get("Tech_Stack",""),
                    match_notes=r.get("Match_Notes",""),
                    country=r.get("Country",""),
                    remote=r.get("Remote",""),
                    open_role=r.get("Open_Roles_Found",""),
                    language_req=r.get("Language_Requirement","")
                )
            else:
                r["Cold_Email_Draft"] = f"Hi {r['Company']} Team,\n\nI am interested in Data Engineering opportunities..."

    return rows

@app.put("/api/shortlist/{company}")
def update_shortlist_company(company: str, payload: EmailUpdateSchema):
    """Updates contact email, job URL, or cold email draft in enriched_shortlist.csv."""
    target_file = ENRICHED_CSV if os.path.exists(ENRICHED_CSV) else SHORTLIST_CSV
    if not os.path.exists(target_file):
        raise HTTPException(status_code=404, detail="Shortlist file not found.")

    with open(target_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    fields = list(rows[0].keys()) if rows else []
    # Make sure all fields exist
    for extra in ["To_Email", "Cold_Email_Draft", "Best_Job_URL"]:
        if extra not in fields:
            fields.append(extra)

    updated = False
    for r in rows:
        if r["Company"].lower().strip() == company.lower().strip():
            r["To_Email"] = payload.to_email
            r["Cold_Email_Draft"] = payload.email_draft
            r["Best_Job_URL"] = payload.job_url
            updated = True
            break

    if not updated:
        # Create a new record in enriched if it existed in master but not shortlist
        raise HTTPException(status_code=404, detail=f"Company '{company}' not found in the shortlist.")

    # Save back to CSV
    with open(target_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # If this is shortlist.csv, let's copy/rename to enriched_shortlist.csv to promote it
    if target_file == SHORTLIST_CSV:
        os.rename(SHORTLIST_CSV, ENRICHED_CSV)

    return {"message": f"Successfully updated draft for {company}."}

@app.post("/api/outreach/send")
def send_email_api(payload: EmailSendSchema):
    """Sends a cold email to the target company using Gmail API and updates tracker."""
    if not send_outreach:
        raise HTTPException(status_code=500, detail="Outreach module (send_outreach.py) not available.")

    # 1. Fetch credentials check
    creds_exist = os.path.exists(os.path.join(BASE_DIR, "config", "gmail_credentials.json"))
    if not creds_exist:
        raise HTTPException(status_code=400, detail="Gmail credentials.json is missing in config/ folder. Complete console setup first.")

    # 2. Trigger OAuth & Gmail Service
    try:
        service = send_outreach.get_gmail_service()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail Authentication failed: {str(e)}. Please authenticate in the terminal once.")

    # 3. Send email
    subject = payload.subject or send_outreach.build_subject(payload.company)
    success = send_outreach.gmail_send(service, payload.to_email, subject, payload.body)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email via Gmail API.")

    # 4. Update outreach tracker CSV
    tracker_rows = []
    if os.path.exists(TRACKER_CSV):
        with open(TRACKER_CSV, newline="", encoding="utf-8") as f:
            tracker_rows = list(csv.DictReader(f))

    sent_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Read company details from enriched shortlist
    company_details = {}
    if os.path.exists(ENRICHED_CSV):
        with open(ENRICHED_CSV, newline="", encoding="utf-8") as f:
            erows = list(csv.DictReader(f))
            for er in erows:
                if er["Company"].lower().strip() == payload.company.lower().strip():
                    company_details = er
                    break

    # Add or update tracker row
    existing_idx = next((i for i, r in enumerate(tracker_rows) if r["Company"].lower().strip() == payload.company.lower().strip()), None)
    
    new_tr = {
        "Company": payload.company,
        "To_Email": payload.to_email,
        "Subject": subject,
        "Status": "Sent",
        "Sent_At": sent_time_str,
        "Replied_At": "",
        "Score": company_details.get("Score", "0"),
        "Sector": company_details.get("Sector", "Unknown"),
        "Country": company_details.get("Country", "Unknown"),
        "Careers_URL": company_details.get("Best_Job_URL") or company_details.get("Careers_URL", ""),
        "Notes": "Sent via Web Portal Review Station"
    }

    if existing_idx is not None:
        tracker_rows[existing_idx] = new_tr
    else:
        tracker_rows.append(new_tr)

    send_outreach.save_tracker(tracker_rows)

    # 5. Auto-update CRM tracking
    if tracker:
        apps = tracker.load_apps()
        app_exists = next((a for a in apps if a["Company"].lower().strip() == payload.company.lower().strip()), None)
        
        # Calculate 7-day follow-up date
        from datetime import timedelta
        follow_up_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        if app_exists:
            app_exists["Status"] = "Email Sent"
            app_exists["Last_Action"] = f"Email sent to {payload.to_email}"
            app_exists["Follow_Up_Date"] = follow_up_date
        else:
            apps.append({
                "Company": payload.company,
                "Role": "AI/Data Engineer",
                "Job_URL": company_details.get("Best_Job_URL") or company_details.get("Careers_URL", ""),
                "Source": "Cold Outreach",
                "Status": "Email Sent",
                "Applied_Date": datetime.now().strftime("%Y-%m-%d"),
                "Follow_Up_Date": follow_up_date,
                "Last_Action": "Sent initial cold email via Web UI",
                "Notes": "Auto-added from Cold Outreach Review"
            })
        tracker.save_apps(apps)

    return {"message": f"Successfully sent outreach email to {payload.company}."}

@app.get("/api/applications")
def get_applications():
    """Returns application tracking pipeline (Kanban board layout)."""
    if not os.path.exists(APPS_CSV):
        return []
    with open(APPS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

@app.post("/api/applications")
def add_update_application(payload: ApplicationCreateUpdateSchema):
    """Add or update application in the CRM pipeline."""
    if not tracker:
        raise HTTPException(status_code=500, detail="Tracker module (tracker.py) not available.")

    apps = tracker.load_apps()
    today_str = datetime.now().strftime("%Y-%m-%d")

    existing_idx = next((i for i, a in enumerate(apps) if a["Company"].lower().strip() == payload.company.lower().strip()), None)

    app_data = {
        "Company": payload.company,
        "Role": payload.role,
        "Job_URL": payload.url,
        "Source": "Web Portal CRM" if existing_idx is None else apps[existing_idx].get("Source", "Outreach"),
        "Status": payload.status,
        "Applied_Date": apps[existing_idx].get("Applied_Date", today_str) if existing_idx is not None else today_str,
        "Follow_Up_Date": payload.follow_up or (apps[existing_idx].get("Follow_Up_Date", "") if existing_idx is not None else ""),
        "Last_Action": f"Stage updated to {payload.status} via Web Portal CRM",
        "Notes": payload.notes or (apps[existing_idx].get("Notes", "") if existing_idx is not None else "")
    }

    if existing_idx is not None:
        # Update keep applied date
        app_data["Source"] = apps[existing_idx].get("Source", "Outreach")
        app_data["Applied_Date"] = apps[existing_idx].get("Applied_Date", today_str)
        apps[existing_idx] = app_data
    else:
        apps.append(app_data)

    tracker.save_apps(apps)

    # If application is marked as Replied, sync back to outreach_tracker
    if payload.status.lower() == "phone screen" and os.path.exists(TRACKER_CSV):
        with open(TRACKER_CSV, newline="", encoding="utf-8") as f:
            trows = list(csv.DictReader(f))
        
        t_idx = next((i for i, r in enumerate(trows) if r["Company"].lower().strip() == payload.company.lower().strip()), None)
        if t_idx is not None and trows[t_idx]["Status"] != "Replied":
            trows[t_idx]["Status"] = "Replied"
            trows[t_idx]["Replied_At"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            send_outreach.save_tracker(trows)

    return {"message": f"Successfully updated application for {payload.company}."}

# ---------------------------------------------------------------------------
# Background Script Execution Handler
# ---------------------------------------------------------------------------

def run_script_task(script_name: str, args: List[str] = []):
    """Executes a pipeline script inside a background thread/process."""
    script_path = os.path.join(SCRIPTS_DIR, f"{script_name}.py")
    python_exec = sys.executable

    pipeline_tasks[script_name]["status"] = "Running"
    pipeline_tasks[script_name]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pipeline_tasks[script_name]["output"] = f"Starting run of {script_name}.py...\n"

    try:
        process = subprocess.Popen(
            [python_exec, script_path] + args,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Stream logs
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                pipeline_tasks[script_name]["output"] += line
        
        rc = process.poll()
        if rc == 0:
            pipeline_tasks[script_name]["status"] = "Completed"
            pipeline_tasks[script_name]["output"] += f"\n[SUCCESS] Completed run of {script_name}.py"
        else:
            pipeline_tasks[script_name]["status"] = f"Failed (code {rc})"
            pipeline_tasks[script_name]["output"] += f"\n[ERROR] Script returned non-zero code {rc}"
    except Exception as e:
        pipeline_tasks[script_name]["status"] = "Failed"
        pipeline_tasks[script_name]["output"] += f"\n[CRITICAL ERROR] Execution failed: {str(e)}"

@app.post("/api/pipeline/run/{script}")
def run_pipeline_script(script: str, background_tasks: BackgroundTasks):
    """Trigger the execution of a Python pipeline script in the background."""
    if script not in pipeline_tasks:
        raise HTTPException(status_code=400, detail="Invalid script. Available scripts: run_scrapers, score_shortlist, enrich_shortlist, visa_crossref")
    
    if pipeline_tasks[script]["status"] == "Running":
        return {"message": "Script is already running.", "task": pipeline_tasks[script]}

    background_tasks.add_task(run_script_task, script)
    return {"message": f"Triggered {script}.py execution in the background.", "task": pipeline_tasks[script]}

@app.get("/api/pipeline/status")
def get_pipeline_tasks_status():
    """Retrieve running status of pipeline background scripts."""
    return pipeline_tasks

# Serve static HTML site
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9800)
