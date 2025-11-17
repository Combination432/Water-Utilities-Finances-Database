# EMMA Pipeline - Free Water Utility Data Collection

This directory contains tools to collect financial data from EMMA (Electronic Municipal Market Access), the MSRB's free public database of municipal securities disclosures.

## Why EMMA?

- ✅ **100% Free** - No API keys, no subscriptions, no costs
- ✅ **Comprehensive** - 700-900 of top 1,000 water utilities file here
- ✅ **Official Data** - Required filings for bond issuers
- ✅ **10+ Years** - Historical annual financial reports (CAFRs)
- ✅ **Legal Requirement** - Utilities must file, ensuring ongoing coverage

## What's Included

```
emma-pipeline/
├── emma_client.py      # Main API client for EMMA
├── test_emma.py        # Test suite to verify functionality
├── requirements.txt    # Python dependencies (all free)
└── README.md          # This file
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Run Tests

```bash
python test_emma.py
```

This will:
- Test connection to EMMA
- Verify search functionality
- Show manual testing instructions
- Help you reverse-engineer EMMA's API

### 3. Use the Client

```python
from emma_client import EmmaClient

# Initialize
client = EmmaClient()

# Search for a utility
results = client.search_by_issuer(
    issuer_name="San Francisco Public Utilities",
    state="CA"
)

print(f"Found {results['total']} documents")

# Download a document (need real document ID from EMMA)
client.download_document("ER1234567", "report.pdf")
```

## Important Notes

### EMMA API Structure

**EMMA does not have official public API documentation.** This client is based on:

1. **Observation** of EMMA website behavior
2. **Reverse-engineering** network requests
3. **Common patterns** in municipal finance APIs

You will likely need to:

1. Visit https://emma.msrb.org/ manually
2. Use browser Developer Tools (F12 → Network tab)
3. Observe actual API calls when searching
4. Update `emma_client.py` with real endpoints

### Two Possible Approaches

#### Approach A: EMMA Has JSON API
If EMMA exposes JSON endpoints:
- Update the search URLs in `emma_client.py`
- Parse JSON responses directly
- **Fastest and most reliable**

#### Approach B: EMMA Only Returns HTML
If EMMA only returns HTML search results:
- Install BeautifulSoup4: `pip install beautifulsoup4`
- Implement `_parse_search_html()` method
- Extract document IDs from HTML tables
- **More work, but still free**

### Document ID Format

EMMA document IDs typically:
- Are numeric (e.g., "1234567890")
- May have prefixes (e.g., "ER1234567")
- Are used in URLs: `https://emma.msrb.org/ER1234567.pdf`

You'll discover the exact format by examining actual EMMA URLs.

## Usage Examples

### Example 1: Find All California Water Utilities

```python
from emma_client import EmmaClient, search_water_utilities_by_state

# Get all CA water utilities
results = search_water_utilities_by_state("CA")

for doc in results:
    print(f"Issuer: {doc['issuerName']}")
    print(f"Fiscal Year: {doc['fiscalYear']}")
    print(f"Document: {doc['documentId']}")
    print()
```

### Example 2: Download 10 Years of Reports

```python
from emma_client import EmmaClient, download_utility_history

# Download reports for 2014-2023
years = list(range(2014, 2024))

downloaded = download_utility_history(
    utility_name="Los Angeles Department of Water and Power",
    state="CA",
    years=years,
    output_dir="./downloads"
)

print(f"Successfully downloaded {len(downloaded)} reports")
```

### Example 3: Build Utility Database

```python
from emma_client import EmmaClient, RateLimiter

client = EmmaClient()
rate_limiter = RateLimiter(requests_per_minute=30)

# Search all top 10 states
states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']

all_utilities = {}

for state in states:
    print(f"Searching {state}...")
    rate_limiter.wait_if_needed()

    results = client.search_by_issuer("water", state=state)

    for doc in results.get('results', []):
        issuer = doc['issuerName']
        if issuer not in all_utilities:
            all_utilities[issuer] = {
                'name': issuer,
                'state': state,
                'documents': []
            }
        all_utilities[issuer]['documents'].append(doc)

print(f"Found {len(all_utilities)} unique water utilities")
```

## Rate Limiting

Be respectful of EMMA's servers:

```python
from emma_client import RateLimiter

# Conservative: 30 requests per minute
limiter = RateLimiter(requests_per_minute=30)

for utility in utilities:
    limiter.wait_if_needed()  # Automatically adds delays
    results = client.search_by_issuer(utility['name'])
```

**Recommended Limits:**
- **Search requests:** 30/minute (2 seconds between requests)
- **PDF downloads:** 10/minute (6 seconds between downloads)
- **Total daily:** <10,000 requests
- **Best time:** Off-peak hours (midnight-6am ET)

## Integration with Database

Once you have the database set up (see `ARCHITECTURE.md`), you can store EMMA discoveries:

```python
import psycopg2
from emma_client import EmmaClient

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    database="water_utilities",
    user="your_user",
    password="your_password"
)

# Search EMMA
client = EmmaClient()
results = client.search_by_issuer("water", state="CA")

# Store in database
for doc in results['results']:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO financial_reports (utility_id, fiscal_year, document_url, ...)
        VALUES (%s, %s, %s, ...)
    """, (utility_id, fiscal_year, doc['pdfUrl'], ...))

conn.commit()
```

See full database integration code in the main guide: `EMMA_DATA_SOURCE_GUIDE.md`

## Troubleshooting

### "No results found"
- Try partial name searches (e.g., "Los Angeles" instead of full name)
- Some utilities file under parent entity names
- Check state code is correct (two letters, e.g., "CA")

### "Connection timeout"
- EMMA servers may be slow during business hours
- Try during off-peak times
- Increase timeout: `client.session.get(url, timeout=120)`

### "404 on document download"
- Document ID format may be incorrect
- Some documents may be temporarily unavailable
- Check EMMA website manually for correct URL pattern

### "Rate limited or blocked"
- Increase delay between requests
- Use RateLimiter with lower requests_per_minute
- Spread requests over multiple days
- Rotate User-Agent strings

## Next Steps

After collecting EMMA data:

1. **Parse PDFs** - Extract tables from downloaded CAFRs
2. **Extract Financial Data** - Pull out line items from statements
3. **Normalize Accounts** - Standardize account names across utilities
4. **Build Web Interface** - Display data in React frontend

See `ARCHITECTURE.md` for full pipeline design.

## Cost Estimate

**Total Cost: $0** 🎉

- EMMA access: Free
- Python/requests: Free
- Storage (local disk): Free
- Database (PostgreSQL): Free (open-source)

The only costs in the full pipeline come from:
- Cloud hosting (optional - can run locally)
- LLM extraction (optional - can use rule-based)

## Support

For issues:
1. Check `EMMA_DATA_SOURCE_GUIDE.md` for detailed documentation
2. Review `test_emma.py` output for diagnostics
3. Visit https://emma.msrb.org/ to verify current website structure
4. Open an issue in the repository

## License

This tool accesses public data from EMMA. All municipal securities disclosure data is public information. Respect EMMA's terms of use and rate limits.
