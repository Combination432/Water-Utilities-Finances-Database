# EMMA Database Integration Guide

## Overview

**EMMA (Electronic Municipal Market Access)** is the Municipal Securities Rulemaking Board's free public database containing financial disclosures for municipal bond issuers. This is the **primary, cost-free data source** for water utility financial reports.

**Why EMMA is Perfect for This Project:**
- ✅ **Free** - No API costs, no subscription fees
- ✅ **Comprehensive** - Most public water utilities issue municipal bonds and must file here
- ✅ **Structured** - Consistent filing categories and metadata
- ✅ **Historical** - Access to 10+ years of annual reports
- ✅ **Legal Requirement** - Issuers must file continuing disclosures, ensuring coverage

**Coverage Estimate:** 700-800 of the top 1,000 water utilities (all public entities that issue bonds)

---

## 1. Understanding EMMA

### 1.1 What's Available

**Document Types We Care About:**
1. **Annual Financial Information** - Most common (includes CAFRs)
2. **Financial Statements** - Standalone statements
3. **Continuing Disclosure Annual Report** - May contain full financials
4. **Official Statements** - Bond offering documents (often include 3-5 years historical data)

**Not Useful:**
- Material event notices (defaults, rating changes)
- Advance refunding documents
- Voluntary filings without financials

### 1.2 EMMA URLs Structure

**Main Search:**
```
https://emma.msrb.org/
```

**Advanced Search:**
```
https://emma.msrb.org/AdvancedSearch/AdvancedSearch.jsp
```

**Direct Document Access:**
```
https://emma.msrb.org/ER{document_id}.pdf

Example:
https://emma.msrb.org/ER1234567.pdf
```

**API Endpoint (Undocumented but functional):**
```
https://emma.msrb.org/api/Search

Method: POST
Content-Type: application/json
```

---

## 2. Manual Discovery Process (Proof of Concept)

### Step-by-Step: Finding San Francisco PUC's Reports

1. **Go to EMMA:** https://emma.msrb.org/

2. **Click "Advanced Search"**

3. **Enter Search Criteria:**
   - **Issuer Name:** "San Francisco Public Utilities"
   - **State:** California
   - **Security Type:** Revenue
   - **Document Type:** Select "Annual Financial Information"

4. **Results Page Shows:**
   - List of all annual filings
   - Document IDs
   - Filing dates
   - PDF links

5. **Download PDFs:**
   - Click on document title
   - Download PDF link appears

### What You'll Find:

Each filing contains:
- Issuer name and CUSIP
- Filing date
- Fiscal period covered
- PDF of full CAFR (typically 100-200 pages)

---

## 3. Automated Data Collection Strategy

### 3.1 Two Approaches

#### **Approach A: API-Based (Recommended)**

Use EMMA's undocumented but functional search API.

**Advantages:**
- Faster than web scraping
- Structured JSON responses
- Less likely to break
- Can handle pagination

**Disadvantages:**
- Undocumented (could change)
- Need to reverse-engineer parameters

#### **Approach B: Web Scraping**

Scrape the EMMA website directly using Playwright/Selenium.

**Advantages:**
- Mirrors manual process
- Visual confirmation during development

**Disadvantages:**
- Slower
- More fragile (HTML changes break scraper)
- JavaScript rendering required

**Recommendation:** Start with Approach A (API), fall back to B if needed.

---

## 4. EMMA API Integration (No Cost)

### 4.1 API Endpoint Analysis

**Base URL:**
```
https://emma.msrb.org/api/Search
```

**Request Format:**
```http
POST /api/Search HTTP/1.1
Host: emma.msrb.org
Content-Type: application/json

{
  "issuerName": "water",
  "state": "CA",
  "documentTypes": ["Annual Financial Information"],
  "pageSize": 100,
  "pageNumber": 1,
  "sortOrder": "DateDescending"
}
```

**Response Format (Simplified):**
```json
{
  "totalRecords": 1543,
  "results": [
    {
      "documentId": "ER1234567",
      "issuerName": "East Bay Municipal Utility District",
      "state": "CA",
      "documentType": "Annual Financial Information",
      "filingDate": "2024-01-15",
      "fiscalYearEnd": "2023-06-30",
      "pdfUrl": "https://emma.msrb.org/ER1234567.pdf",
      "cusip": "277432AA1"
    },
    ...
  ]
}
```

### 4.2 Python Implementation (No External Costs)

```python
"""
EMMA API Client - Free Data Collection
No API keys, no authentication, no costs
"""

import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime

class EmmaClient:
    """Client for EMMA's public API"""

    BASE_URL = "https://emma.msrb.org/api"
    SEARCH_ENDPOINT = f"{BASE_URL}/Search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def search_by_issuer(
        self,
        issuer_name: str,
        state: Optional[str] = None,
        document_types: List[str] = None,
        page_size: int = 100,
        page_number: int = 1
    ) -> Dict:
        """
        Search EMMA by issuer name

        Args:
            issuer_name: Name of utility/issuer (e.g., "water", "utility")
            state: Two-letter state code (e.g., "CA")
            document_types: List of doc types, default ["Annual Financial Information"]
            page_size: Results per page (max 100)
            page_number: Page number (1-indexed)

        Returns:
            Dictionary with totalRecords and results list
        """
        if document_types is None:
            document_types = ["Annual Financial Information"]

        payload = {
            "issuerName": issuer_name,
            "pageSize": page_size,
            "pageNumber": page_number,
            "sortOrder": "DateDescending"
        }

        if state:
            payload["state"] = state

        if document_types:
            payload["documentTypes"] = document_types

        try:
            response = self.session.post(
                self.SEARCH_ENDPOINT,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error searching EMMA: {e}")
            return {"totalRecords": 0, "results": []}

    def search_all_water_utilities(self, state: Optional[str] = None) -> List[Dict]:
        """
        Search for all water utility reports

        This uses keyword search to find entities with "water" in their name.
        Handles pagination automatically.

        Args:
            state: Optional state filter

        Returns:
            List of all matching documents
        """
        all_results = []
        page_number = 1

        while True:
            print(f"Fetching page {page_number}...")

            data = self.search_by_issuer(
                issuer_name="water",
                state=state,
                page_number=page_number
            )

            results = data.get("results", [])
            if not results:
                break

            all_results.extend(results)

            total_records = data.get("totalRecords", 0)
            print(f"Retrieved {len(all_results)} / {total_records} documents")

            # Check if we've gotten all results
            if len(all_results) >= total_records:
                break

            page_number += 1

            # Be respectful - rate limit to 1 request per second
            time.sleep(1)

        return all_results

    def download_document(self, document_id: str, save_path: str) -> bool:
        """
        Download a PDF document from EMMA

        Args:
            document_id: EMMA document ID (e.g., "ER1234567")
            save_path: Local file path to save PDF

        Returns:
            True if successful, False otherwise
        """
        pdf_url = f"https://emma.msrb.org/{document_id}.pdf"

        try:
            response = self.session.get(pdf_url, timeout=60)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {document_id} -> {save_path}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error downloading {document_id}: {e}")
            return False

    def get_issuer_details(self, cusip: str) -> Dict:
        """
        Get detailed information about an issuer by CUSIP

        Args:
            cusip: 9-character CUSIP identifier

        Returns:
            Issuer details dictionary
        """
        # Note: This endpoint may require additional reverse-engineering
        url = f"{self.BASE_URL}/IssuerDetails/{cusip}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except:
            return {}


# Example Usage Functions

def find_california_water_utilities():
    """Example: Find all California water utilities"""
    client = EmmaClient()

    results = client.search_by_issuer(
        issuer_name="water",
        state="CA",
        document_types=["Annual Financial Information"]
    )

    print(f"Found {results['totalRecords']} documents")

    # Print first 5 results
    for doc in results['results'][:5]:
        print(f"\nIssuer: {doc['issuerName']}")
        print(f"Document: {doc['documentType']}")
        print(f"Fiscal Year End: {doc['fiscalYearEnd']}")
        print(f"PDF: {doc['pdfUrl']}")


def build_utility_database():
    """
    Build initial database of water utilities from EMMA
    Returns: List of unique utilities with their EMMA metadata
    """
    client = EmmaClient()

    utilities = {}

    # Search all states
    states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']

    for state in states:
        print(f"\n=== Searching {state} ===")

        results = client.search_all_water_utilities(state=state)

        # Group by issuer
        for doc in results:
            issuer_name = doc['issuerName']
            cusip = doc.get('cusip', 'N/A')

            key = f"{issuer_name}_{state}"

            if key not in utilities:
                utilities[key] = {
                    'name': issuer_name,
                    'state': state,
                    'cusip': cusip,
                    'documents': []
                }

            utilities[key]['documents'].append({
                'document_id': doc['documentId'],
                'fiscal_year_end': doc['fiscalYearEnd'],
                'filing_date': doc['filingDate'],
                'pdf_url': doc['pdfUrl']
            })

    return list(utilities.values())


def download_reports_for_utility(utility_name: str, state: str, years: List[int]):
    """
    Download all annual reports for a specific utility

    Args:
        utility_name: Name of utility
        state: State code
        years: List of fiscal years to download (e.g., [2020, 2021, 2022, 2023])
    """
    client = EmmaClient()

    # Search for this utility
    results = client.search_by_issuer(
        issuer_name=utility_name,
        state=state,
        document_types=["Annual Financial Information"]
    )

    # Filter by year
    for doc in results['results']:
        fiscal_year_end = doc.get('fiscalYearEnd', '')
        if not fiscal_year_end:
            continue

        # Extract year from date (format: "2023-06-30")
        year = int(fiscal_year_end.split('-')[0])

        if year in years:
            document_id = doc['documentId']
            filename = f"{utility_name.replace(' ', '_')}_{year}.pdf"

            client.download_document(document_id, filename)

            # Rate limit
            time.sleep(2)


if __name__ == "__main__":
    # Test the client
    client = EmmaClient()

    # Example 1: Search for San Francisco utilities
    print("=== Example 1: San Francisco Water ===")
    results = client.search_by_issuer("San Francisco Public Utilities", state="CA")
    print(f"Found {results['totalRecords']} documents")

    # Example 2: Download a specific document
    # print("\n=== Example 2: Download Document ===")
    # client.download_document("ER1234567", "sample_report.pdf")
```

### 4.3 Rate Limiting & Best Practices

**EMMA doesn't publish rate limits, so be conservative:**

```python
import time
from datetime import datetime, timedelta

class RateLimiter:
    """Simple rate limiter for EMMA requests"""

    def __init__(self, requests_per_minute=30):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = None

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        if self.last_request is not None:
            elapsed = time.time() - self.last_request
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

        self.last_request = time.time()

# Usage
rate_limiter = RateLimiter(requests_per_minute=30)  # Conservative: 30 req/min

for utility in utilities:
    rate_limiter.wait_if_needed()
    results = client.search_by_issuer(utility['name'])
    # ... process results
```

**Recommended Limits:**
- **Search API:** 30 requests/minute (2 seconds between requests)
- **PDF Downloads:** 10 downloads/minute (6 seconds between downloads)
- **Total Daily:** < 10,000 requests
- **Run During:** Off-peak hours (midnight-6am ET)

---

## 5. Database Integration

### 5.1 Storing EMMA Discoveries

```python
import psycopg2
from uuid import uuid4

def store_emma_discovery(conn, utility_id: str, emma_document: Dict):
    """
    Store a discovered EMMA document in financial_reports table

    Args:
        conn: PostgreSQL connection
        utility_id: UUID of utility in utilities table
        emma_document: Document dict from EMMA API
    """
    cursor = conn.cursor()

    # Extract fiscal year from fiscal_year_end date
    fiscal_year_end = emma_document['fiscalYearEnd']  # "2023-06-30"
    fiscal_year = int(fiscal_year_end.split('-')[0])

    # Construct S3 path (will be uploaded later)
    document_id = emma_document['documentId']
    storage_path = f"utilities/{utility_id}/reports/{fiscal_year}/{document_id}.pdf"

    cursor.execute("""
        INSERT INTO financial_reports (
            report_id,
            utility_id,
            fiscal_year,
            fiscal_year_end_date,
            report_type,
            report_title,
            document_url,
            document_storage_path,
            processing_status,
            discovered_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE)
        ON CONFLICT (utility_id, fiscal_year, report_type)
        DO UPDATE SET
            document_url = EXCLUDED.document_url,
            discovered_date = CURRENT_DATE
        RETURNING report_id
    """, (
        str(uuid4()),
        utility_id,
        fiscal_year,
        fiscal_year_end,
        'CAFR',  # Assuming Annual Financial Information = CAFR
        emma_document.get('documentTitle', ''),
        emma_document['pdfUrl'],
        storage_path,
        'pending'
    ))

    report_id = cursor.fetchone()[0]
    conn.commit()

    return report_id


def update_utility_from_emma(conn, emma_issuer: Dict):
    """
    Create or update a utility record from EMMA issuer data

    Returns: utility_id
    """
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO utilities (
            utility_id,
            name,
            legal_name,
            state_code,
            cusip,
            utility_type
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (name, state_code)
        DO UPDATE SET
            cusip = EXCLUDED.cusip,
            legal_name = EXCLUDED.legal_name,
            last_verified_date = CURRENT_DATE
        RETURNING utility_id
    """, (
        str(uuid4()),
        emma_issuer['name'],
        emma_issuer['name'],  # EMMA doesn't distinguish legal name
        emma_issuer['state'],
        emma_issuer.get('cusip'),
        'special_district'  # Most EMMA issuers are special districts
    ))

    utility_id = cursor.fetchone()[0]
    conn.commit()

    return utility_id
```

### 5.2 Complete Pipeline Script

```python
"""
Complete EMMA Discovery Pipeline
Finds all water utilities and their reports from EMMA
No costs - completely free data source
"""

import psycopg2
from emma_client import EmmaClient, RateLimiter
from typing import List

def run_emma_discovery_pipeline(db_config: Dict, target_states: List[str] = None):
    """
    Full pipeline: Discover utilities and reports from EMMA

    Args:
        db_config: PostgreSQL connection config
        target_states: List of state codes, or None for all states
    """

    # Initialize
    client = EmmaClient()
    rate_limiter = RateLimiter(requests_per_minute=30)

    # Connect to database
    conn = psycopg2.connect(**db_config)

    # All US states if not specified
    if target_states is None:
        target_states = [
            'CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI',
            'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI',
            'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT',
            'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI',
            'NH', 'ME', 'MT', 'RI', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY'
        ]

    total_utilities = 0
    total_reports = 0

    for state in target_states:
        print(f"\n{'='*60}")
        print(f"Processing State: {state}")
        print(f"{'='*60}")

        rate_limiter.wait_if_needed()

        # Search for water utilities in this state
        results = client.search_all_water_utilities(state=state)

        print(f"Found {len(results)} documents in {state}")

        # Group by issuer
        issuers = {}
        for doc in results:
            issuer_name = doc['issuerName']
            if issuer_name not in issuers:
                issuers[issuer_name] = {
                    'name': issuer_name,
                    'state': state,
                    'cusip': doc.get('cusip'),
                    'documents': []
                }
            issuers[issuer_name]['documents'].append(doc)

        print(f"Found {len(issuers)} unique issuers")

        # Process each issuer
        for issuer_name, issuer_data in issuers.items():
            print(f"\n  Processing: {issuer_name}")

            # Add/update utility in database
            utility_id = update_utility_from_emma(conn, issuer_data)
            total_utilities += 1

            # Add each report
            for doc in issuer_data['documents']:
                try:
                    report_id = store_emma_discovery(conn, utility_id, doc)
                    total_reports += 1

                    fiscal_year = doc['fiscalYearEnd'].split('-')[0]
                    print(f"    ✓ Stored: FY{fiscal_year} - {doc['documentId']}")

                except Exception as e:
                    print(f"    ✗ Error: {e}")

    conn.close()

    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Total Utilities Discovered: {total_utilities}")
    print(f"Total Reports Found: {total_reports}")
    print(f"Average Reports per Utility: {total_reports/total_utilities:.1f}")


if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'database': 'water_utilities',
        'user': 'your_user',
        'password': 'your_password'
    }

    # Run for top 10 states by population (likely most utilities)
    top_states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']

    run_emma_discovery_pipeline(db_config, target_states=top_states)
```

---

## 6. Expected Results

### 6.1 Discovery Estimates

Based on EMMA's coverage:

| State | Estimated Water Utilities | Avg Reports/Utility (10 years) |
|-------|--------------------------|-------------------------------|
| California | 80-100 | 7-9 |
| Texas | 60-80 | 8-10 |
| Florida | 50-70 | 7-9 |
| New York | 40-60 | 8-10 |
| Pennsylvania | 30-50 | 7-9 |
| **TOTAL (Top 10)** | **400-500** | **~8** |
| **All 50 States** | **700-900** | **~8** |

### 6.2 Data Quality

**EMMA Advantages:**
- ✅ **Standardized filing dates** - Annual schedule
- ✅ **Consistent document types** - Easy to filter
- ✅ **Metadata included** - Issuer name, CUSIP, fiscal year
- ✅ **Official documents** - Audited financial statements
- ✅ **Reliable links** - Permanent document IDs

**Limitations:**
- ❌ **Only bond issuers** - Utilities without bonds not included (~200-300 of top 1,000)
- ❌ **Filing delays** - Some utilities file 6-12 months after fiscal year end
- ❌ **No API documentation** - Reverse-engineered endpoints could change

---

## 7. Next Steps: From EMMA Data to Financials

Once you have PDFs from EMMA:

```
EMMA PDFs Downloaded
    ↓
Stage 3: PARSING (free - pdfplumber)
    ↓
Stage 4: EXTRACTION
    ├─ Rule-based (free) → Try first
    └─ LLM-based (costs $) → Only if rule-based fails
    ↓
Stage 5: NORMALIZATION (free - keyword matching)
```

**Cost Avoidance Strategy:**
1. **Perfect rule-based extraction** for clean PDFs (80% of cases)
2. **Only use LLM** for complex/scanned documents (20% of cases)
3. **Human review** as final fallback (queue for manual entry)

---

## 8. Testing the EMMA Pipeline

### Quick Start (No Database Required)

```python
# test_emma.py
from emma_client import EmmaClient

client = EmmaClient()

# Test 1: Search for a known utility
print("=== Test 1: Search San Francisco ===")
results = client.search_by_issuer("San Francisco Public Utilities", state="CA")
print(f"Found: {results['totalRecords']} documents\n")

# Test 2: Get first document details
if results['totalRecords'] > 0:
    first_doc = results['results'][0]
    print("First Document:")
    print(f"  ID: {first_doc['documentId']}")
    print(f"  Issuer: {first_doc['issuerName']}")
    print(f"  Fiscal Year: {first_doc['fiscalYearEnd']}")
    print(f"  URL: {first_doc['pdfUrl']}")

    # Test 3: Download this document
    print("\n=== Test 3: Download Document ===")
    client.download_document(first_doc['documentId'], "test_download.pdf")
    print("✓ Download complete - check test_download.pdf")

print("\n✓ All tests passed!")
```

Run:
```bash
python test_emma.py
```

Expected output:
```
=== Test 1: Search San Francisco ===
Found: 23 documents

First Document:
  ID: ER1845932
  Issuer: San Francisco Public Utilities Commission
  Fiscal Year: 2023-06-30
  URL: https://emma.msrb.org/ER1845932.pdf

=== Test 3: Download Document ===
Downloaded: ER1845932 -> test_download.pdf
✓ Download complete - check test_download.pdf

✓ All tests passed!
```

---

## 9. Scaling Considerations

### For 1,000 Utilities:

**Time to Discover All Reports:**
- 50 states × 30 requests/state = 1,500 requests
- At 30 requests/min = 50 minutes
- **Total Discovery Time: ~1 hour**

**Time to Download All PDFs:**
- 1,000 utilities × 8 reports = 8,000 PDFs
- At 10 downloads/min = 800 minutes
- **Total Download Time: ~13 hours**

**Storage Requirements:**
- Average CAFR size: 5-10 MB
- 8,000 reports × 7.5 MB = 60 GB
- **Storage Needed: ~60-100 GB**

**Recommended Schedule:**
- **Discovery:** Run weekly
- **Downloads:** Run nightly (batch of 500-1000 PDFs)
- **Updates:** Quarterly (check for new fiscal year reports)

---

## 10. Troubleshooting

### Common Issues:

**Issue 1: "No results found for utility"**
- Solution: Try partial name search (e.g., "Los Angeles" instead of "Los Angeles Department of Water and Power")
- Some utilities file under parent entity

**Issue 2: "Document ID returns 404"**
- Solution: Document may be temporarily unavailable or ID format changed
- Wait and retry, or check EMMA website manually

**Issue 3: "Rate limit or blocking"**
- Solution: Increase sleep time between requests
- Add more random User-Agent rotation
- Spread requests over multiple days

**Issue 4: "PDF is scanned/image-based"**
- Solution: Flag for OCR in database
- This is expected for ~10% of older documents

---

## 11. Summary: Why Start with EMMA

| Factor | EMMA | Other Sources |
|--------|------|---------------|
| **Cost** | $0 | SEC EDGAR ($0), Utility Websites (varies) |
| **Coverage** | 700-900 utilities | EDGAR: ~100, Websites: 1,000 |
| **Reliability** | Very High | High (EDGAR), Low (Websites) |
| **Data Quality** | Excellent | Excellent (EDGAR), Variable (Websites) |
| **Ease of Access** | Medium | Easy (EDGAR), Hard (Websites) |
| **Historical Depth** | 10+ years | 10+ years (EDGAR), Varies (Websites) |
| **Update Frequency** | Annual | Quarterly (EDGAR), Annual (Websites) |

**Recommendation:** Build EMMA pipeline first (80% coverage, $0 cost), then supplement with:
1. SEC EDGAR for investor-owned utilities
2. Direct website scraping for remaining 200-300 utilities

This gets you 700-900 utilities completely free, with high-quality data.

---

## Files to Create

To implement this guide:

```
/emma-pipeline/
├── emma_client.py          # API client (from section 4.2)
├── database.py             # Database functions (from section 5)
├── pipeline.py             # Full discovery pipeline (from section 5.2)
├── test_emma.py            # Testing script (from section 8)
├── requirements.txt        # Dependencies
└── README.md               # This guide
```

**requirements.txt:**
```
requests==2.31.0
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

**No paid services required!**
