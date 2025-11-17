# Getting Started - Zero-Cost Water Utility Data Collection

This guide shows you how to build a water utility financial database with **$0 in costs**.

## What You Have

This repository contains:

1. **Full Architecture Design** (`ARCHITECTURE.md`)
   - Complete tech stack for production application
   - Database schema with 12+ tables
   - 5-stage data pipeline design
   - Includes both free and paid options

2. **EMMA Pipeline** (`emma-pipeline/` + `EMMA_DATA_SOURCE_GUIDE.md`)
   - **100% FREE** data collection system
   - Access to 700-900 water utility financial reports
   - 10+ years of historical data
   - No API keys, no authentication, zero cost

## Quick Start (30 Minutes)

### Step 1: Set Up Environment

```bash
# Clone this repository (if not already done)
cd Water-Utilities-Finances-Database

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd emma-pipeline
pip install -r requirements.txt
```

### Step 2: Test EMMA Access

```bash
# Run test suite
python test_emma.py
```

This will:
- ✓ Test connection to EMMA
- ⚠ Show that API needs reverse-engineering
- 📋 Give you manual testing instructions

### Step 3: Reverse-Engineer EMMA API (1 Hour)

EMMA doesn't have official API docs, so you need to discover the endpoints:

1. **Open EMMA in browser:**
   - Go to https://emma.msrb.org/

2. **Open Developer Tools:**
   - Press F12
   - Click "Network" tab

3. **Perform a search:**
   - Click "Advanced Search"
   - Enter: Issuer Name = "water"
   - Select: State = "California"
   - Document Type = "Annual Financial Information"
   - Click "Search"

4. **Observe the network request:**
   - Look for XHR/Fetch requests in Network tab
   - Find the search endpoint URL
   - Note the request parameters
   - Copy the response format

5. **Update the code:**
   - Edit `emma-pipeline/emma_client.py`
   - Update the search URL and parameters
   - Test again with `python test_emma.py`

**Alternative:** If EMMA only returns HTML (not JSON):
- Install BeautifulSoup: `pip install beautifulsoup4`
- Parse the HTML search results
- Extract document IDs from result tables

### Step 4: Start Collecting Data

Once the client works, start small:

```python
from emma_client import EmmaClient

client = EmmaClient()

# Test with one utility
results = client.search_by_issuer(
    issuer_name="San Francisco Public Utilities",
    state="CA"
)

print(f"Found {results['total']} documents")

# Download one report
if results['results']:
    doc = results['results'][0]
    client.download_document(doc['documentId'], 'test_report.pdf')
    print("✓ Downloaded test report!")
```

### Step 5: Scale to 1,000 Utilities

See examples in `EMMA_DATA_SOURCE_GUIDE.md` section 4-5 for:
- Searching all states
- Building utility database
- Downloading 10 years per utility
- Rate limiting (be respectful!)

## Free vs Paid Options

| Component | Free Option | Paid Option | Recommendation |
|-----------|-------------|-------------|----------------|
| **Data Discovery** | EMMA (700-900 utilities) | Data vendors | **Start with EMMA** |
| **PDF Storage** | Local disk (60-100 GB) | AWS S3 (~$2/mo) | **Local for MVP** |
| **Database** | PostgreSQL (local) | AWS RDS (~$200/mo) | **Local for MVP** |
| **PDF Parsing** | pdfplumber (free) | AWS Textract ($) | **Use pdfplumber** |
| **Data Extraction** | Rule-based (free) | LLM API ($450 one-time) | **Rules first** |
| **Web Hosting** | Not needed (local) | AWS/Vercel ($50-500/mo) | **Local for MVP** |
| **TOTAL** | **$0** | **$700+ initial** | **Start free!** |

## Roadmap: Free MVP to Production

### Phase 1: Proof of Concept (Free - 2 weeks)

**Goal:** Get 10 utilities with 3 years of data each

- [ ] Reverse-engineer EMMA API
- [ ] Download 30 CAFRs (10 utilities × 3 years)
- [ ] Parse PDFs with pdfplumber (free)
- [ ] Build simple rule-based extraction for 1-2 line items
- [ ] Store in SQLite database (free, local)
- [ ] Verify you can extract revenue/expenses

**Cost: $0**

### Phase 2: Scale to 100 Utilities (Free - 1 month)

**Goal:** Prove the approach works at scale

- [ ] Set up PostgreSQL locally (free)
- [ ] Build utilities table
- [ ] Automated EMMA discovery for 100 utilities
- [ ] Download 800 reports (100 × 8 years average)
- [ ] Improve rule-based extraction
- [ ] Extract full 3-statement data for clean PDFs
- [ ] Calculate basic metrics (debt service coverage, etc.)

**Cost: $0**
**Time: 1-2 hours to download 800 PDFs (with rate limiting)**
**Storage: ~6 GB**

### Phase 3: Decision Point

Now you have real data and can decide:

**Option A: Keep It Free**
- Continue with local setup
- Build simple Python/Pandas analysis scripts
- Export to Excel for viewing
- **Good for:** Personal project, research, learning

**Option B: Add Cloud ($50-100/month)**
- Move to cloud database (AWS RDS or DigitalOcean)
- Use S3 for PDF storage
- Deploy FastAPI backend
- Keep frontend local (React dev server)
- **Good for:** Sharing with team, better performance

**Option C: Full Production ($500-1000/month)**
- Full cloud infrastructure
- Add LLM extraction for accuracy
- Deploy React frontend (Vercel/Netlify)
- Professional monitoring/logging
- **Good for:** Public launch, business use

### Phase 4: Add Advanced Features (Variable Cost)

Only after MVP is working:

- [ ] LLM-based extraction for complex PDFs (~$450 one-time)
- [ ] Financial forecasting module (free - just code)
- [ ] React web interface (free to develop, $ to host)
- [ ] API for external access (free to build, $ to host)

## What to Build First

**Week 1: EMMA Client**
```
Day 1-2: Reverse-engineer EMMA API
Day 3-4: Build search and download functions
Day 5: Test with 10 utilities
Day 6-7: Document findings and refine
```

**Week 2: PDF Processing**
```
Day 1-2: Install pdfplumber, parse 5 sample CAFRs
Day 3-4: Identify common table structures
Day 5: Write extraction rules for Balance Sheet
Day 6: Extract Income Statement
Day 7: Extract Cash Flow Statement
```

**Week 3: Database**
```
Day 1-2: Set up PostgreSQL locally
Day 3: Create utilities table
Day 4: Create financial_reports table
Day 5: Create line_items table
Day 6-7: Load data from Weeks 1-2
```

**Week 4: Analysis**
```
Day 1-3: Build queries for common metrics
Day 4-5: Create simple Python visualization scripts
Day 6: Calculate trends (revenue growth, etc.)
Day 7: Document results and plan next phase
```

## Zero-Cost Tech Stack

Here's what you can run entirely for free:

```
[Data Source]
EMMA Database (free)
    ↓
[Collection]
Python + requests (free)
Running on your laptop (free)
    ↓
[Storage]
PDFs on local disk (free)
PostgreSQL database (free, local)
    ↓
[Processing]
pdfplumber PDF parsing (free)
Rule-based extraction (free)
Python + pandas (free)
    ↓
[Analysis]
Jupyter notebooks (free)
matplotlib/seaborn (free)
Excel export (free)
```

**Total Cost: $0**

## When You Need to Spend Money

You only need to spend if you want:

1. **More utilities than EMMA has** → Need web scraping of utility websites
2. **Better extraction accuracy** → Need LLM API (Claude/GPT-4)
3. **Web interface for others** → Need cloud hosting
4. **Faster processing** → Need cloud compute
5. **Redundancy/backups** → Need cloud storage

For a personal project analyzing water utilities, **you can do everything for free**.

## Sample Output (What You'll Get)

After Phase 2, you'll have:

```sql
-- Query example: Top 10 utilities by revenue
SELECT
    u.name,
    u.state_code,
    li.fiscal_year,
    SUM(li.amount) as total_revenue
FROM utilities u
JOIN line_items li ON u.utility_id = li.utility_id
WHERE li.line_item_category = 'revenue'
    AND li.fiscal_year = 2023
GROUP BY u.name, u.state_code, li.fiscal_year
ORDER BY total_revenue DESC
LIMIT 10;
```

Result:
```
name                                    | state | year | total_revenue
----------------------------------------|-------|------|---------------
New York City Water Board               | NY    | 2023 | 4,234,567,890
Los Angeles Department of Water & Power| CA    | 2023 | 3,456,789,012
San Francisco Public Utilities          | CA    | 2023 | 1,234,567,890
...
```

You can then analyze:
- Revenue trends over 10 years
- Operating margins
- Debt levels
- Capital investment
- Rate structures
- Comparative performance

All for $0.

## Next Steps

1. **Read:** `EMMA_DATA_SOURCE_GUIDE.md` for detailed EMMA documentation
2. **Read:** `ARCHITECTURE.md` for full production design
3. **Run:** `emma-pipeline/test_emma.py` to test EMMA access
4. **Experiment:** Download 5-10 CAFRs and examine their structure
5. **Build:** Start with Phase 1 above

## Questions?

- **"Can I really do this for free?"** Yes! EMMA is public, Python is free, PostgreSQL is free.
- **"How accurate is rule-based extraction?"** 80-90% for clean PDFs, lower for scanned/complex ones.
- **"Do I need to know Python?"** Basic Python helps, but examples are provided.
- **"Can I sell access to this data?"** The data is public, but check EMMA terms for redistribution.
- **"How long does this take?"** MVP in 2-4 weeks part-time. Full 1,000 utilities in 2-3 months.

## Resources

- EMMA: https://emma.msrb.org/
- PostgreSQL: https://www.postgresql.org/
- pdfplumber: https://github.com/jsvine/pdfplumber
- Python requests: https://requests.readthedocs.io/

---

**Ready to start? Begin with:**
```bash
cd emma-pipeline
python test_emma.py
```

**Cost so far: $0** ✅
