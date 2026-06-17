# scripts/schema.py
FIELDS = [
    "Company",
    "Website",
    "Careers_URL",
    "Country",
    "City",
    "Sector",
    "Subsector",
    "Company_Stage",
    "Company_Scale",
    "Employer_Category",
    "Remote",
    "Visa_Sponsorship",
    "EOR",
    "Hiring_Geography",
    "Target_Roles",
    "Tech_Stack",
    "Region_Eligibility",
    "Portfolio_Theme_Match",
    "Language_Requirement",
    "Hiring_Confidence",
    "Reason_Match",
    "Source",
    "Cold_Outreach_Candidate",
    "Visa_Sponsor_Register",
]

UNKNOWN = "Unknown"

JOB_SIGNAL_FIELDS = [
    "Company",
    "Job_Title",
    "Job_URL",
    "Country",
    "City",
    "Sector",
    "Tech_Stack",
    "Source",
    "Reason_Match",
    "Hiring_Confidence",
    "Language_Requirement",
    "Scraped_At",
]

MASTER_PATH = "data/master_employers.csv"
JOB_SIGNALS_PATH = "data/job_signals.csv"


def empty_row():
    """Return a dict with all 24 fields set to Unknown."""
    return {f: UNKNOWN for f in FIELDS}


def empty_job_signal():
    return {f: UNKNOWN for f in JOB_SIGNAL_FIELDS}


def row_to_job_signal(row: dict) -> dict:
    from datetime import datetime, timezone
    return {
        "Company": row.get("Company", UNKNOWN),
        "Job_Title": row.get("Target_Roles", UNKNOWN),
        "Job_URL": row.get("Careers_URL", UNKNOWN),
        "Country": row.get("Country", UNKNOWN),
        "City": row.get("City", UNKNOWN),
        "Sector": row.get("Sector", UNKNOWN),
        "Tech_Stack": row.get("Tech_Stack", UNKNOWN),
        "Source": row.get("Source", UNKNOWN),
        "Reason_Match": row.get("Reason_Match", UNKNOWN),
        "Hiring_Confidence": row.get("Hiring_Confidence", UNKNOWN),
        "Language_Requirement": row.get("Language_Requirement", UNKNOWN),
        "Scraped_At": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
