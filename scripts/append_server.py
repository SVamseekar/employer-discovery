"""
Tiny HTTP server that receives POST /append with JSON body
and appends rows to master_employers.csv.
Run: python scripts/append_server.py
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, csv, os

MASTER = os.path.join(os.path.dirname(__file__), "..", "data", "master_employers.csv")
FIELDS = ['Company','Website','Careers_URL','Country','City','Sector','Subsector',
          'Company_Stage','Company_Scale','Employer_Category','Remote','Visa_Sponsorship',
          'EOR','Hiring_Geography','Target_Roles','Tech_Stack','Region_Eligibility',
          'Portfolio_Theme_Match','Language_Requirement','Hiring_Confidence','Reason_Match',
          'Source','Cold_Outreach_Candidate','Visa_Sponsor_Register']

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def do_POST(self):
        if self.path != "/append":
            self.send_response(404); self.end_headers(); return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            rows = json.loads(body)
            if not isinstance(rows, list):
                rows = [rows]

            master = os.path.normpath(MASTER)
            added = 0
            with open(master, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                for row in rows:
                    if not row.get("Company") or row.get("Company") == "Unknown":
                        continue
                    writer.writerow({k: str(row.get(k, "Unknown"))[:500] for k in FIELDS})
                    added += 1

            print(f"Appended {added} rows from {rows[0].get('Source','?') if rows else '?'}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"appended": added}).encode())
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500); self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9876), Handler)
    print("Append server running on port 9876...")
    server.serve_forever()
