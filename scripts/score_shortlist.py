"""
Phase 4: Score all employers and produce top-500 cold outreach shortlist.
Scoring based on Marti's profile: AI/Data Engineer, based in Hyderabad, EU Blue Card eligible.

GEOGRAPHY LOGIC:
  India  → +15 (Marti is LOCAL — zero visa/relocation friction, highest accessibility)
  EU     → +15 (Blue Card eligible, clear relocation path)
  AU/NZ  → +10 (lower competition, English market)
  Remote → +8  (works from Hyderabad)

LANGUAGE PENALTY:
  (Learning) language required → -8 (deprioritise unless specifically targeted)
"""
import csv, os, re

BASE = os.path.join(os.path.dirname(__file__), "..")
MASTER = os.path.join(BASE, "data", "master_employers.csv")
SHORTLIST = os.path.join(BASE, "data", "cold_outreach_shortlist.csv")

AI_KEYWORDS = {"ai", "ml", "machine learning", "deep learning", "llm", "nlp", "data",
               "analytics", "platform", "infrastructure", "cloud", "mlops", "databricks",
               "spark", "kafka", "dbt", "pipeline", "warehouse", "lakehouse", "rag",
               "fastapi", "spring boot", "azure", "gcp", "geospatial", "compliance",
               "event-driven", "distributed", "backend"}

EU_COUNTRIES = {"germany", "netherlands", "france", "sweden", "spain", "portugal",
                "denmark", "finland", "austria", "belgium", "poland", "czech", "ireland",
                "switzerland", "norway", "estonia", "latvia", "lithuania", "europe", "eu"}

INDIA_TERMS = {"india", "hyderabad", "bangalore", "bengaluru", "mumbai", "pune",
               "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata"}

# Your 11 portfolio themes
PORTFOLIO_THEMES = {
    "ai assurance": ["ai assurance", "ai safety", "ai audit", "model governance"],
    "ai governance": ["ai governance", "ai policy", "responsible ai", "ai regulation"],
    "eu policy": ["eu policy", "eu regulation", "gdpr", "ai act", "european"],
    "workforce analytics": ["workforce", "hr analytics", "people analytics", "talent analytics"],
    "transport analytics": ["transport", "mobility", "logistics", "fleet", "transit", "rail"],
    "smart cities": ["smart city", "smart cities", "urban", "city data", "municipal"],
    "geospatial": ["geospatial", "gis", "mapping", "location", "spatial", "satellite"],
    "fintech infrastructure": ["fintech", "payments", "banking", "financial infrastructure"],
    "compliance systems": ["compliance", "regtech", "regulatory", "aml", "kyc", "audit"],
    "public sector analytics": ["govtech", "public sector", "government", "civic"],
    "enterprise data platforms": ["data platform", "data warehouse", "lakehouse", "enterprise data"]
}

HIGH_VALUE_STAGES = {"startup", "series a", "series b", "series c", "scale", "growth", "scaleup"}

# All India category variants included — static_companies.py uses gcc/data/fintech/ai/product
HIGH_VALUE_CATEGORIES = {"yc", "remote-first", "eu startup", "eu remote", "eu tech",
                          "github signal", "remotive", "hn hiring",
                          "australia tech", "new zealand tech",
                          "india tech", "india gcc", "india data", "india fintech",
                          "india product", "india ai", "india mnc"}


def score(row):
    s = 0
    notes = []

    sector = (row.get("Sector", "") + " " + row.get("Tech_Stack", "")).lower()
    category = row.get("Employer_Category", "").lower()
    stage = row.get("Company_Stage", "").lower()
    visa = row.get("Visa_Sponsorship", "").lower()
    sponsor = row.get("Visa_Sponsor_Register", "").lower()
    remote = row.get("Remote", "").lower()
    geo = (row.get("Hiring_Geography", "") + " " + row.get("Country", "") + " " + row.get("City", "")).lower()
    confidence = row.get("Hiring_Confidence", "").lower()
    reason = row.get("Reason_Match", "").lower()
    source = row.get("Source", "").lower()
    language_req = row.get("Language_Requirement", "").lower()

    # AI/Data stack match (+30 max)
    matched_kw = [kw for kw in AI_KEYWORDS if kw in sector or kw in reason]
    kw_score = min(len(matched_kw) * 6, 30)
    s += kw_score
    if matched_kw:
        notes.append(f"Tech: {', '.join(matched_kw[:3])}")

    # Portfolio theme match (+25 max)
    all_text = f"{sector} {reason} {row.get('Tech_Stack','')} {row.get('Subsector','')}".lower()
    matched_themes = []
    for theme, keywords in PORTFOLIO_THEMES.items():
        if any(kw in all_text for kw in keywords):
            matched_themes.append(theme)
    theme_score = min(len(matched_themes) * 8, 25)
    s += theme_score
    if matched_themes:
        notes.append(f"Portfolio: {', '.join(matched_themes[:2])}")

    # Visa/relocation signal (+25)
    # India companies skip this — Marti is local, no visa needed
    is_india = any(c in geo for c in INDIA_TERMS)
    if not is_india:
        if visa == "yes" or "uk skilled worker" in sponsor or "ireland" in sponsor or "netherlands" in sponsor:
            s += 25
            notes.append("Confirmed visa sponsor")
        elif "eu blue card" in sponsor or "possible" in visa:
            s += 15
            notes.append("EU Blue Card country")
        elif sponsor not in ("not found", "unknown", ""):
            s += 8

    # EOR signal (+10)
    eor = row.get("EOR", "").lower()
    if eor == "yes":
        s += 10
        notes.append("EOR available")

    # India geography (+15) — Marti is LOCAL, zero friction, highest accessibility
    if is_india:
        s += 15
        notes.append("India (local, no visa)")
    # EU geography (+15) — Blue Card eligible, clear relocation path
    elif any(c in geo for c in EU_COUNTRIES):
        s += 15
        notes.append("EU based")
    # Remote (+8) — works from Hyderabad
    elif remote == "yes":
        s += 8
        notes.append("Remote")

    # Australia/NZ (+10 - lower competition, English market)
    if any(c in geo for c in ["australia", "new zealand"]):
        s += 10
        notes.append("AU/NZ - lower competition")

    # High-signal source category (+8)
    if any(c in category for c in HIGH_VALUE_CATEGORIES):
        s += 8

    # Startup/growth stage (+5)
    if any(st in stage for st in HIGH_VALUE_STAGES):
        s += 5
        notes.append("Growth stage")

    # Language penalty (-8) — (Learning) language slows response rate; deprioritise
    # Companies explicitly English or Unknown get no penalty
    if "(learning)" in language_req and language_req not in ("unknown", "english", "none", ""):
        s -= 8
        notes.append("Lang barrier")

    # Target_Roles match (+15) — role is explicitly data/AI/engineering
    target_roles = row.get("Target_Roles", "").lower()
    if any(kw in target_roles for kw in ["data", "ai", "machine learning", "ml", "engineer", "analytics", "platform"]):
        s += 15
        notes.append("Target role match")

    # Region_Eligibility match (+10) — explicitly eligible/open
    region_elig = row.get("Region_Eligibility", "").lower()
    if any(x in region_elig for x in ["eligible", "open", "global", "worldwide", "india", "yes"]):
        s += 10
        notes.append("Region eligible")

    # Hiring confidence (+5)
    if confidence == "high":
        s += 5
    elif confidence == "medium":
        s += 2

    # YC bonus (+5)
    if "yc" in category or "yc" in source:
        s += 5
        notes.append("YC backed")

    return s, "; ".join(notes)


def run():
    rows = []
    with open(MASTER, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Score all
    scored = []
    for row in rows:
        s, notes = score(row)
        scored.append((s, notes, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Top 500 with score >= 20
    shortlist = [(s, notes, row) for s, notes, row in scored if s >= 20][:500]

    # Mark in master CSV
    shortlist_names = {row["Company"] for _, _, row in shortlist}
    for row in rows:
        if row["Company"] in shortlist_names:
            row["Cold_Outreach_Candidate"] = "Yes"

    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # Write shortlist
    shortlist_fields = ["Score", "Match_Notes", "Company", "Website", "Careers_URL",
                        "Country", "City", "Sector", "Company_Stage", "Employer_Category",
                        "Remote", "Visa_Sponsorship", "Visa_Sponsor_Register",
                        "Hiring_Geography", "Tech_Stack", "Language_Requirement",
                        "Target_Roles", "Region_Eligibility", "Reason_Match", "Source"]

    with open(SHORTLIST, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=shortlist_fields)
        writer.writeheader()
        for s, notes, row in shortlist:
            out = {k: row.get(k, "") for k in shortlist_fields}
            out["Score"] = s
            out["Match_Notes"] = notes
            writer.writerow(out)

    print(f"Scored {len(rows)} employers")
    print(f"Shortlist: {len(shortlist)} companies written to {SHORTLIST}")
    print(f"\nTop 10:")
    for s, notes, row in shortlist[:10]:
        print(f"  [{s:3d}] {row['Company'][:35]:<35} | {notes[:60]}")


if __name__ == "__main__":
    run()
