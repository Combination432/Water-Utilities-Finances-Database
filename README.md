# Water Utilities Financial Analysis Platform

A comprehensive system for collecting, analyzing, and forecasting financial data for the top 1,000 US water utilities.

## 🎯 Project Overview

This platform provides:
- **Automated data collection** from public sources (EMMA, SEC EDGAR)
- **Financial statement extraction** from annual reports (CAFRs/10-Ks)
- **10 years of historical data** for 3-statement analysis
- **Financial forecasting** with customizable assumptions
- **Web interface** for visualization and analysis

**Key Innovation:** Uses EMMA (Municipal Securities Rulemaking Board) as a free data source, covering 700-900 water utilities at zero cost.

## 💰 Cost: $0 for MVP

The complete proof of concept can be built with **zero costs**:

- ✅ **EMMA Database** - Free public access to CAFRs
- ✅ **Python/PostgreSQL** - Free open-source tools
- ✅ **Local Development** - Run on your laptop
- ✅ **PDF Parsing** - Free pdfplumber library
- ✅ **Rule-Based Extraction** - No LLM API costs

See [`GETTING_STARTED.md`](GETTING_STARTED.md) for the zero-cost roadmap.

## 📚 Documentation

| Document | Description | Size |
|----------|-------------|------|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Zero-cost MVP roadmap and quick start guide | Start here! |
| **[EMMA_DATA_SOURCE_GUIDE.md](EMMA_DATA_SOURCE_GUIDE.md)** | Complete EMMA database integration guide (20KB) | Primary data source |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Full production architecture design (29KB) | Advanced/production |

## 🚀 Quick Start

### 1. Set Up EMMA Pipeline (30 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd Water-Utilities-Finances-Database

# Install dependencies
cd emma-pipeline
pip install -r requirements.txt

# Test EMMA access
python test_emma.py
```

### 2. Reverse-Engineer EMMA API (1 hour)

EMMA doesn't publish API docs, so you need to:
1. Visit https://emma.msrb.org/
2. Open browser DevTools (F12 → Network)
3. Perform a search for water utilities
4. Observe the API calls
5. Update `emma_client.py` with real endpoints

See detailed instructions in [`EMMA_DATA_SOURCE_GUIDE.md`](EMMA_DATA_SOURCE_GUIDE.md).

### 3. Start Collecting Data

```python
from emma_client import EmmaClient

client = EmmaClient()

# Search for utilities
results = client.search_by_issuer("water", state="CA")
print(f"Found {results['total']} documents")

# Download a report
client.download_document("ER1234567", "report.pdf")
```

### 4. Build Your Database

See Phase 1-4 roadmap in [`GETTING_STARTED.md`](GETTING_STARTED.md):
- Phase 1: 10 utilities (free)
- Phase 2: 100 utilities (free)
- Phase 3: Decide on cloud vs local
- Phase 4: Add advanced features

## 📁 Repository Structure

```
Water-Utilities-Finances-Database/
├── GETTING_STARTED.md              # Start here - zero-cost MVP guide
├── EMMA_DATA_SOURCE_GUIDE.md       # EMMA database deep dive
├── ARCHITECTURE.md                  # Full production architecture
│
├── emma-pipeline/                   # EMMA data collection (FREE)
│   ├── emma_client.py              # API client for EMMA
│   ├── test_emma.py                # Test suite
│   ├── requirements.txt            # Dependencies (all free)
│   └── README.md                   # EMMA pipeline docs
│
└── (future directories)
    ├── database/                   # PostgreSQL schemas and migrations
    ├── parsers/                    # PDF parsing tools
    ├── extractors/                 # Financial data extraction
    ├── api/                        # FastAPI backend
    └── frontend/                   # React web interface
```

## 🏗️ Architecture Highlights

### Data Pipeline (5 Stages)

```
1. DISCOVERY          2. ACQUISITION       3. PARSING
   (EMMA API)    →    (PDF Download)   →   (pdfplumber)
                                              ↓
                                         4. EXTRACTION
                                            (Rules/LLM)
                                              ↓
                                         5. NORMALIZATION
                                            (Account mapping)
```

### Tech Stack

| Layer | Technology | Cost |
|-------|------------|------|
| **Data Source** | EMMA Database | Free |
| **Backend** | Python + FastAPI | Free |
| **Database** | PostgreSQL + TimescaleDB | Free (local) |
| **PDF Parsing** | pdfplumber | Free |
| **Data Extraction** | Rule-based → LLM fallback | Free → $450 |
| **Frontend** | React + TypeScript | Free |
| **Hosting** | Local → Cloud | Free → $50-500/mo |

### Database Schema

12 core tables:
- `utilities` - 1,000 water utility profiles
- `financial_reports` - CAFR/10-K documents
- `financial_statements` - Individual statements
- `line_items` - Granular financial data
- `standardized_accounts` - Chart of accounts
- `forecasts` - Financial projections
- And more...

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for full schema.

## 🎓 Expected Results

### Coverage

| Source | Utilities | Cost | Reports/Utility |
|--------|-----------|------|-----------------|
| **EMMA** | 700-900 | $0 | 8-10 years |
| SEC EDGAR | 50-100 | $0 | 10+ years |
| Direct Scraping | 100-200 | $0* | Variable |
| **TOTAL** | **~1,000** | **$0** | **~8 avg** |

*Free but requires more development effort

### Time Estimates

- **Discovery (all utilities):** 1 hour
- **Download (8,000 PDFs):** 13 hours
- **Parsing:** 10-20 hours (parallelized)
- **Extraction:** 20-40 hours
- **Total MVP:** 2-4 weeks part-time

### Storage

- **PDFs:** 60-100 GB
- **Database:** 5-10 GB
- **Total:** ~100 GB (easily fits on laptop)

## 💡 Key Features

### 1. EMMA Integration (Free)
- Access to 700-900 municipal water utilities
- 10+ years of audited financial statements
- Automated discovery and download
- No API keys or authentication required

### 2. Intelligent Extraction
- **Rule-based:** Fast, free, 80-90% accuracy for clean PDFs
- **LLM-based:** Fallback for complex documents (optional, costs $)
- **Hybrid approach:** Best of both worlds

### 3. Financial Analysis
- 3-statement modeling (Income, Balance, Cash Flow)
- 10-year trend analysis
- Peer comparison across utilities
- Key metrics: Debt service coverage, operating margin, etc.

### 4. Forecasting Module
- Build custom scenarios
- Adjustable assumptions (growth rates, CapEx, etc.)
- Sensitivity analysis
- Export pro forma statements

## 🔍 Use Cases

1. **Investment Research** - Analyze municipal bonds
2. **Regulatory Analysis** - Compare utility performance
3. **Academic Research** - Study water utility finances
4. **Consulting** - Benchmark clients against peers
5. **Policy Making** - Inform rate-setting decisions

## 📊 Sample Analysis

```sql
-- Top 10 utilities by revenue (2023)
SELECT u.name, u.state_code,
       SUM(li.amount) as total_revenue
FROM utilities u
JOIN line_items li ON u.utility_id = li.utility_id
WHERE li.line_item_category = 'revenue'
  AND li.fiscal_year = 2023
GROUP BY u.name, u.state_code
ORDER BY total_revenue DESC
LIMIT 10;
```

Output: Revenue rankings, year-over-year growth, operating margins, and more.

## 🛠️ Development Roadmap

### ✅ Phase 0: Design (Complete)
- [x] Architecture design
- [x] Database schema
- [x] EMMA integration strategy
- [x] Documentation

### 🔄 Phase 1: MVP (In Progress)
- [ ] EMMA API reverse-engineering
- [ ] Download 10 utilities × 3 years
- [ ] Basic PDF parsing
- [ ] Simple extraction (1-2 line items)
- [ ] SQLite storage

### 📋 Phase 2: Scale (Planned)
- [ ] PostgreSQL setup
- [ ] 100 utilities × 8 years
- [ ] Full 3-statement extraction
- [ ] Basic metrics calculation

### 🚀 Phase 3: Production (Future)
- [ ] Cloud deployment
- [ ] LLM extraction
- [ ] React frontend
- [ ] API endpoints
- [ ] User authentication

## 🤝 Contributing

This is a design/architecture project. To contribute:

1. **Test EMMA Access** - Verify the client works in your location
2. **Reverse-Engineer APIs** - Help document actual EMMA endpoints
3. **Add Utilities** - Contribute utility metadata
4. **Improve Extraction** - Build better parsing rules
5. **Add Features** - Implement forecasting, visualizations, etc.

## 📄 License

The architecture and code are open-source. Financial data from EMMA is public information.

Respect EMMA's terms of use and implement reasonable rate limiting.

## 🆘 Support

1. Read [`GETTING_STARTED.md`](GETTING_STARTED.md) for the quick start guide
2. Check [`EMMA_DATA_SOURCE_GUIDE.md`](EMMA_DATA_SOURCE_GUIDE.md) for EMMA details
3. Review [`ARCHITECTURE.md`](ARCHITECTURE.md) for production design
4. Run `python test_emma.py` for diagnostics

## 🎯 Success Metrics

After MVP (Phase 2), you'll have:
- ✅ 100 water utilities in database
- ✅ 800+ financial reports (CAFRs)
- ✅ 10 years of financial data
- ✅ 3-statement coverage (Income, Balance, Cash Flow)
- ✅ Basic trend analysis capability
- ✅ All for $0 in costs

## 🔗 Resources

- **EMMA:** https://emma.msrb.org/
- **PostgreSQL:** https://www.postgresql.org/
- **pdfplumber:** https://github.com/jsvine/pdfplumber
- **FastAPI:** https://fastapi.tiangolo.com/
- **React:** https://react.dev/

---

**Start building:**
```bash
cd emma-pipeline
python test_emma.py
```

**Current cost: $0** ✅
