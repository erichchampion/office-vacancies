# Identifying Vacant Local Offices: Implementation Guide

During election nomination windows, local elections offices routinely deal with "unapportioned" or empty contests—seats on school boards, fire districts, and special utility districts where either no candidates file or fewer candidates run than open seats.

This guide provides a professional technical framework for automating the detection of these vacancies for a registered voter resident of the incorporated City of Scotts Valley in Santa Cruz County.

---

## 1. Eligibility Matrix & Scope

To accurately filter vacancies, the system uses a tiered eligibility model. This distinguishes between offices any resident of Scotts Valley can seek and those requiring a specific parcel address.

| Tier | Scope | Eligible Offices | Logic |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **County-Wide** | Board of Supervisors (Dist 5), County Clerk, Treasurer-Tax Collector, District Attorney, Sheriff | `Resident == True` $\implies$ Eligible |
| **Tier 2** | **City/Agency** | Scotts Valley City Council, SVUSD Board, Cabrillo Trustee (Area 1), SV Fire, SV Water | `Resident == True` $\implies$ Eligible |
| **Tier 3** | **Parcel-Specific** | San Lorenzo Valley Water, Small Special Districts | `Address $\in$ DistrictBoundary` $\implies$ Eligible |

---

## 2. Technical Implementation Guide

### Recommended Technology Stack

While NodeJS is a viable option for browser automation, **Python 3.11+** is recommended for this project. Government data sources frequently mix HTML tables with legacy PDFs; Python's `pdfplumber` is significantly more robust for extracting tabular data from PDFs than available NodeJS alternatives.

- **Language:** Python 3.11
- **Browser Automation:** `playwright` (to handle JS-heavy government portals)
- **Parsing:** `beautifulsoup4` (HTML) and `pdfplumber` (PDFs)
- **Scheduler:** GitHub Actions (Free, built-in cron, zero-infrastructure)
- **Notifications:** Discord Webhooks or SendGrid (Email)

### Implementation Roadmap

#### Phase 1: Data Acquisition (The Collectors)
The system implements two distinct collector modules:

1. **Nomination Collector (`collector_nominations.py`)**
   - **Target:** [votescount.santacruzcountyca.gov](https://votescount.santacruzcountyca.gov)
   - **Process:** Navigates to the "Candidate Watch" section. If the target is a PDF, it uses `pdfplumber` to locate and extract the candidate table. If HTML, it uses `BeautifulSoup`.
   - **Extraction:** Captures `(Office Name, Seats Open, Candidates Filed)`.

2. **Notice Collector (`collector_notices.py`)**
   - **Target:** A curated list of "Public Notices" or "Agendas" URLs (e.g., `scottsvalley.gov/notices`).
   - **Process:** Performs a scheduled crawl of target pages and scans text using regex for triggers like `(Notice of Vacancy|Filling Vacancy|Appointment to the Board)`.
   - **Extraction:** Captures the direct URL to the notice for the alert.

#### Phase 2: Filtering & State Management (The Brain)
- **Eligibility Mapping:** Maps the scraped `Office Name` against the **Eligibility Matrix**.
- **Vacancy Calculation:** Triggers an alert if `candidates_filed < seats_open` during the nomination window.
- **Deduplication:** Maintains a `state.json` file to track which vacancies have already been alerted, preventing notification spam.

#### Phase 3: Alerting (The Notifier)
- **Payload Construction:** Formats a priority-based message:
  - **High Priority:** Nomination deadlines (Time-sensitive).
  - **Medium Priority:** Off-cycle appointments (Less urgent).
  - **Details:** [Office Name] | [Eligibility Tier] | [Action Link] | [Deadline].

---

## 3. Refined Implementation Example

The following modular approach separates the eligibility logic from the data collection process.

```python
import pdfplumber
from bs4 import BeautifulSoup

# Configuration Mapping
ELIGIBILITY_MATRIX = {
    "Scotts Valley City Council": "Tier 2",
    "SVUSD Board": "Tier 2",
    "County Supervisor, 5th District": "Tier 1",
    "San Lorenzo Valley Water": "Tier 3",
}

class VacancyEngine:
    def __init__(self, state_file="state.json"):
        self.state_file = state_file

    def check_eligibility(self, office_name):
        """Returns the Tier if eligible, otherwise None."""
        for key, tier in ELIGIBILITY_MATRIX.items():
            if key.lower() in office_name.lower():
                return tier
        return None

    def process_candidate_data(self, rows):
        """
        rows: List of (office_name, seats_open, candidates_filed)
        """
        alerts = []
        for office, open_seats, filed in rows:
            tier = self.check_eligibility(office)
            if tier and filed < open_seats:
                alerts.append({
                    "office": office,
                    "vacancies": open_seats - filed,
                    "tier": tier,
                    "urgency": "HIGH"
                })
        return alerts

    def parse_pdf_table(self, pdf_path):
        """Extracts candidates from the Candidate Watch PDF."""
        with pdfplumber.open(pdf_path) as pdf:
            # Extract table from first page
            table = pdf.pages[0].extract_table()
            # Convert table to (office, seats, candidates) tuples, skipping header
            return [tuple(row) for row in table[1:]]

# Example usage
if __name__ == "__main__":
    engine = VacancyEngine()
    # Mock data from a PDF/HTML scrap
    scraped_data = [
        ("Scotts Valley City Council", 3, 1), 
        ("Other District", 1, 0)
    ]
    vacancies = engine.process_candidate_data(scraped_data)
    print(f"Found {len(vacancies)} eligible vacancies: {vacancies}")
```

---

## 4. Deployment Strategy

**GitHub Actions Workflow**
- **Schedule:** 
  - **Daily** during nomination windows (July–August and January–February).
  - **Weekly** for off-cycle notices.
- **Execution:**
  - Runs in a `ubuntu-latest` container.
  - Uses `playwright install` for browser dependencies.
  - Commits `state.json` updates back to the repository to persist memory across runs.
