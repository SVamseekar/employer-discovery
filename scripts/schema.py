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

def empty_row():
    """Return a dict with all 24 fields set to Unknown."""
    return {f: UNKNOWN for f in FIELDS}
