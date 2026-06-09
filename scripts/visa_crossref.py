"""
Phase 3: Cross-reference master_employers.csv against visa sponsor registers.
Countries covered:
- UK: Skilled Worker sponsor register (141k companies, monthly CSV)
- Ireland: Companies that issued employment permits (annual Excel)
- Netherlands: IND recognised sponsors (HTML scrape)
- Germany/France/Switzerland: EU Blue Card - no pre-registration needed, flag instead
"""
import csv, os, re, requests, difflib, io
from datetime import datetime

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

BASE = os.path.join(os.path.dirname(__file__), "..")
MASTER = os.path.join(BASE, "data", "master_employers.csv")

UK_SPONSOR_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"
IRELAND_PERMIT_URL = "https://enterprise.gov.ie/en/publications/publication-files/permits-issued-to-companies-2024.xlsx"

EU_BLUE_CARD_COUNTRIES = {
    "Germany", "Netherlands", "France", "Sweden", "Denmark", "Finland",
    "Austria", "Belgium", "Luxembourg", "Spain", "Portugal", "Italy",
    "Switzerland", "Norway", "Czech Republic", "Poland", "Estonia",
    "Latvia", "Lithuania", "Slovenia", "Croatia", "Slovakia", "Hungary",
    "Romania", "Bulgaria", "Greece", "Malta", "Cyprus"
}


def normalize(name):
    name = name.lower().strip().strip('"\'')
    for suffix in [" ltd", " limited", " plc", " llp", " llc", " inc", " corp",
                   " gmbh", " bv", " nv", " ag", " sa", " sas", " sl", " oy",
                   " ab", " as", " aps", " a/s", " spa", " srl"]:
        name = name.replace(suffix, "")
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def is_match(company_norm, sponsor_dict):
    if company_norm in sponsor_dict:
        return True, sponsor_dict[company_norm]
    matches = difflib.get_close_matches(company_norm, sponsor_dict.keys(), n=1, cutoff=0.92)
    if matches:
        return True, sponsor_dict[matches[0]]
    return False, None


# --- UK Sponsor Register ---
def fetch_uk_sponsors():
    print("  Fetching UK sponsor register...")
    cache = "/tmp/uk_sponsors.csv"
    try:
        r = requests.get(UK_SPONSOR_URL, timeout=15)
        match = re.search(
            r'href="(https://assets\.publishing\.service\.gov\.uk[^"]*Worker[^"]*\.csv)"', r.text
        )
        if match:
            r2 = requests.get(match.group(1), timeout=60)
            with open(cache, "wb") as f:
                f.write(r2.content)
    except Exception as e:
        print(f"  UK fetch error: {e}")

    sponsors = {}
    try:
        with open(cache, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("Organisation Name", "").strip().strip('"')
                if name:
                    sponsors[normalize(name)] = name
        print(f"  UK: {len(sponsors)} sponsors loaded")
    except Exception as e:
        print(f"  UK parse error: {e}")
    return sponsors


# --- Ireland Employment Permit Companies ---
def fetch_ireland_sponsors():
    print("  Fetching Ireland permit companies...")
    sponsors = {}
    if not HAS_OPENPYXL:
        print("  Skipping Ireland (openpyxl not installed)")
        return sponsors
    try:
        r = requests.get(IRELAND_PERMIT_URL, timeout=30)
        wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for cell in row:
                    if isinstance(cell, str) and len(cell) > 2:
                        sponsors[normalize(cell)] = cell
        print(f"  Ireland: {len(sponsors)} companies loaded")
    except Exception as e:
        print(f"  Ireland fetch error: {e}")
    return sponsors


# --- Netherlands IND Register (HTML scrape - top companies only) ---
def fetch_netherlands_sponsors():
    print("  Fetching Netherlands IND sponsors (HTML)...")
    sponsors = {}
    try:
        r = requests.get(
            "https://ind.nl/en/public-register-recognised-sponsors/public-register-work",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        # Extract company names from table rows
        names = re.findall(r'<th scope="row">(.*?)</th>', r.text)
        for name in names:
            name = re.sub(r'<[^>]+>', '', name).strip()
            if name and len(name) > 2:
                sponsors[normalize(name)] = name
        print(f"  Netherlands: {len(sponsors)} sponsors loaded")
    except Exception as e:
        print(f"  Netherlands fetch error: {e}")
    return sponsors


def run():
    # Load all sponsor lists
    uk_sponsors = fetch_uk_sponsors()
    ireland_sponsors = fetch_ireland_sponsors()
    nl_sponsors = fetch_netherlands_sponsors()

    rows = []
    with open(MASTER, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        for row in reader:
            rows.append(row)

    uk_matched = 0
    ireland_matched = 0
    nl_matched = 0
    eu_blue_card = 0

    for row in rows:
        company_norm = normalize(row.get("Company", ""))
        country = row.get("Country", "")

        # UK check
        found_uk, _ = is_match(company_norm, uk_sponsors)
        if found_uk:
            row["Visa_Sponsor_Register"] = "UK Skilled Worker"
            row["Visa_Sponsorship"] = "Yes"
            uk_matched += 1
            continue

        # Ireland check
        found_ie, _ = is_match(company_norm, ireland_sponsors)
        if found_ie:
            row["Visa_Sponsor_Register"] = "Ireland Employment Permit"
            row["Visa_Sponsorship"] = "Yes"
            ireland_matched += 1
            continue

        # Netherlands check
        found_nl, _ = is_match(company_norm, nl_sponsors)
        if found_nl:
            row["Visa_Sponsor_Register"] = "Netherlands IND"
            row["Visa_Sponsorship"] = "Yes"
            nl_matched += 1
            continue

        # EU Blue Card countries - no employer pre-registration needed
        # Flag as "Possible" if company is based in an EU Blue Card country
        if country in EU_BLUE_CARD_COUNTRIES:
            if row.get("Visa_Sponsor_Register", "Unknown") in ("Unknown", "Not Found"):
                row["Visa_Sponsor_Register"] = "EU Blue Card Eligible Country"
                row["Visa_Sponsorship"] = "Possible"
                eu_blue_card += 1
            continue

        # Not found anywhere
        if row.get("Visa_Sponsor_Register", "Unknown") == "Unknown":
            row["Visa_Sponsor_Register"] = "Not Found"

    # Write back
    with open(MASTER, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    total = uk_matched + ireland_matched + nl_matched + eu_blue_card
    print(f"\nVisa cross-reference complete:")
    print(f"  UK Skilled Worker:          {uk_matched}")
    print(f"  Ireland Employment Permit:  {ireland_matched}")
    print(f"  Netherlands IND:            {nl_matched}")
    print(f"  EU Blue Card (possible):    {eu_blue_card}")
    print(f"  Total flagged:              {total}/{len(rows)}")


if __name__ == "__main__":
    run()
