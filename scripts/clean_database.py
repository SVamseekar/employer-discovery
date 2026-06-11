import csv
import os
import re
import html

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MASTER_CSV = os.path.join(BASE_DIR, "data", "master_employers.csv")
SHORTLIST_CSV = os.path.join(BASE_DIR, "data", "cold_outreach_shortlist.csv")
ENRICHED_CSV = os.path.join(BASE_DIR, "data", "enriched_shortlist.csv")

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
    name = name.strip("'\"` \t\n\r")
    
    # Basic sanity checks
    if len(name) < 2 or len(name) > 50:
        return ""
        
    # Must start with letter or digit
    if not re.match(r'^[a-zA-Z0-9]', name):
        return ""
        
    # Conversational junk check
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
        return ""
        
    # Sentence check: if there are more than 4 words and contains common lowercase english connector words
    words = name.split()
    if len(words) > 4:
        connectors = {"to", "for", "the", "and", "our", "you", "your", "with", "from", "is", "a", "of", "in", "on", "at", "by", "that", "this", "it", "us"}
        connector_count = sum(1 for w in words if w.lower() in connectors)
        if connector_count >= 2 or connector_count / len(words) > 0.3:
            return ""
            
    return name

def clean_file(path: str, name_field: str = "Company"):
    if not os.path.exists(path):
        print(f"File {path} does not exist. Skipping.")
        return
        
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    
    if not rows:
        print(f"File {path} is empty.")
        return
        
    fields = list(rows[0].keys())
    cleaned_rows = []
    removed_count = 0
    cleaned_count = 0
    
    for row in rows:
        orig = row.get(name_field, "")
        cleaned = clean_company_name(orig)
        if not cleaned:
            removed_count += 1
            continue
            
        if cleaned != orig:
            cleaned_count += 1
            row[name_field] = cleaned
            
        cleaned_rows.append(row)
        
    # Save back
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cleaned_rows)
        
    print(f"Cleaned {path}:")
    print(f"  - Total before: {len(rows)}")
    print(f"  - Total after:  {len(cleaned_rows)}")
    print(f"  - Cleaned:      {cleaned_count}")
    print(f"  - Removed junk: {removed_count}")

if __name__ == "__main__":
    print("Starting database cleanup...")
    clean_file(MASTER_CSV, "Company")
    clean_file(SHORTLIST_CSV, "Company")
    clean_file(ENRICHED_CSV, "Company")
    print("Cleanup completed successfully!")
