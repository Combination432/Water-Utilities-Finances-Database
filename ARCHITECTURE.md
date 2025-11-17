# Water Utilities Financial Analysis Platform - Architecture Design

## Executive Summary

This document outlines the full-stack architecture for a web application that analyzes the financial performance of the top 1,000 US water utilities. The system automatically discovers, extracts, and analyzes 10 years of 3-statement financial data from annual reports (CAFRs/10-Ks).

---

## 1. Tech Stack

### Frontend
- **Framework:** React 18+ with TypeScript
- **State Management:** Zustand or Redux Toolkit
- **UI Components:** shadcn/ui + Tailwind CSS
- **Data Visualization:** Recharts or D3.js
- **Data Grid:** AG Grid (for complex financial tables)
- **API Client:** TanStack Query (React Query)
- **Build Tool:** Vite

**Rationale:** React ecosystem provides robust tooling for complex data visualization. TypeScript ensures type safety for financial data. AG Grid excels at rendering large financial datasets.

### Backend
- **API Framework:** FastAPI (Python 3.11+)
- **Web Server:** Uvicorn with Gunicorn workers
- **Task Queue:** Celery with Redis broker
- **Async Processing:** asyncio for concurrent API calls
- **Authentication:** Auth0 or Firebase Auth + custom JWT
- **API Documentation:** Auto-generated OpenAPI/Swagger

**Rationale:** FastAPI provides async capabilities crucial for I/O-heavy PDF processing. Celery handles long-running extraction jobs. Python's ML/data ecosystem (pandas, numpy) is essential for financial analysis.

### Database & Storage
- **Primary Database:** PostgreSQL 15+ with TimescaleDB extension
- **Document Store:** AWS S3 or Google Cloud Storage (for PDF storage)
- **Cache Layer:** Redis 7+
- **Search Engine:** Elasticsearch (optional, for full-text search of reports)
- **Vector Database:** Pinecone or pgvector (for semantic search of financial disclosures)

**Rationale:** PostgreSQL handles complex relational financial data. TimescaleDB optimizes time-series queries for multi-year analysis. S3 provides cost-effective PDF storage. Vector DB enables intelligent document search.

### Data Pipeline & ML
- **Document Processing:**
  - Apache Tika (metadata extraction)
  - PyPDF2/pdfplumber (structure parsing)
  - Tesseract OCR (for scanned documents)
  - Claude 3.5 Sonnet or GPT-4 (structured data extraction via API)
- **Web Scraping:**
  - Scrapy (large-scale crawling)
  - Playwright (JavaScript-heavy sites)
  - BeautifulSoup4 (HTML parsing)
- **Data Processing:**
  - pandas (data manipulation)
  - numpy (numerical computation)
  - Apache Airflow (workflow orchestration)
- **Financial Modeling:**
  - Custom Python modules
  - scikit-learn (for predictive models)

**Rationale:** Modern LLMs (Claude/GPT-4) dramatically improve structured extraction accuracy from unstructured financial reports. Airflow provides robust pipeline orchestration with retry logic and monitoring.

### Infrastructure & DevOps
- **Container Orchestration:** Docker + Kubernetes or AWS ECS
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **Cloud Provider:** AWS or GCP
- **Infrastructure as Code:** Terraform

---

## 2. Database Schema

### 2.1 Core Tables

#### `utilities`
Stores information about each water utility organization.

```sql
CREATE TABLE utilities (
    utility_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(500),
    utility_type VARCHAR(50) NOT NULL, -- 'municipal', 'special_district', 'investor_owned', 'regional'

    -- Location
    city VARCHAR(100),
    county VARCHAR(100),
    state_code CHAR(2) NOT NULL,
    zip_code VARCHAR(10),
    service_area_description TEXT,

    -- Identifiers
    ein VARCHAR(20), -- Employer Identification Number
    cusip VARCHAR(9), -- For investor-owned utilities
    gfoa_id VARCHAR(50), -- Government Finance Officers Association ID

    -- Contact & Website
    website_url VARCHAR(500),
    investor_relations_url VARCHAR(500),
    contact_email VARCHAR(255),
    phone VARCHAR(20),

    -- Characteristics
    population_served INTEGER,
    connections INTEGER,
    ownership_structure VARCHAR(50), -- 'public', 'private', 'cooperative'
    year_established INTEGER,

    -- Data Quality
    data_quality_score DECIMAL(3,2), -- 0.00 to 1.00
    last_verified_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    CONSTRAINT utilities_name_state_unique UNIQUE (name, state_code)
);

CREATE INDEX idx_utilities_state ON utilities(state_code);
CREATE INDEX idx_utilities_type ON utilities(utility_type);
CREATE INDEX idx_utilities_population ON utilities(population_served DESC);
```

#### `financial_reports`
Tracks annual financial report documents (CAFRs, 10-Ks, etc.).

```sql
CREATE TABLE financial_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Report Metadata
    fiscal_year INTEGER NOT NULL,
    fiscal_year_end_date DATE NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- 'CAFR', '10-K', '10-Q', 'Annual_Report', 'Budget'
    report_title VARCHAR(500),

    -- Document Information
    document_url VARCHAR(1000),
    document_storage_path VARCHAR(1000), -- S3/GCS path
    file_hash VARCHAR(64), -- SHA-256 for deduplication
    file_size_bytes BIGINT,
    page_count INTEGER,

    -- Processing Status
    processing_status VARCHAR(50) DEFAULT 'pending',
    -- 'pending', 'downloading', 'downloaded', 'parsing', 'extracting', 'completed', 'failed'
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Quality Metrics
    extraction_confidence_score DECIMAL(3,2), -- AI confidence in extraction
    ocr_required BOOLEAN DEFAULT FALSE,
    ocr_quality_score DECIMAL(3,2),

    -- Metadata
    discovered_date DATE DEFAULT CURRENT_DATE,
    publication_date DATE,
    auditor_name VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT financial_reports_utility_year_unique UNIQUE (utility_id, fiscal_year, report_type)
);

CREATE INDEX idx_financial_reports_utility ON financial_reports(utility_id);
CREATE INDEX idx_financial_reports_year ON financial_reports(fiscal_year DESC);
CREATE INDEX idx_financial_reports_status ON financial_reports(processing_status);
```

#### `financial_statements`
Represents a specific financial statement within a report.

```sql
CREATE TABLE financial_statements (
    statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES financial_reports(report_id) ON DELETE CASCADE,
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Statement Metadata
    statement_type VARCHAR(50) NOT NULL,
    -- 'income_statement', 'balance_sheet', 'cash_flow', 'statement_of_net_position',
    -- 'statement_of_revenues_expenses_changes', 'statement_of_cash_flows'
    fiscal_year INTEGER NOT NULL,
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,

    -- Classification
    fund_type VARCHAR(100), -- 'enterprise_fund', 'general_fund', 'water_fund', 'consolidated'
    basis_of_accounting VARCHAR(50), -- 'accrual', 'modified_accrual', 'cash'

    -- Source Information
    page_numbers VARCHAR(100), -- "12-14" or "23"
    extraction_method VARCHAR(50), -- 'llm_extraction', 'ocr', 'structured_pdf', 'manual'

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT financial_statements_unique UNIQUE (report_id, statement_type, fund_type)
);

CREATE INDEX idx_financial_statements_utility_year ON financial_statements(utility_id, fiscal_year);
CREATE INDEX idx_financial_statements_type ON financial_statements(statement_type);
```

#### `line_items`
Granular financial data - individual line items from statements.

```sql
CREATE TABLE line_items (
    line_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id UUID NOT NULL REFERENCES financial_statements(statement_id) ON DELETE CASCADE,
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,

    -- Line Item Details
    account_code VARCHAR(50), -- Chart of accounts code if available
    line_item_name VARCHAR(500) NOT NULL,
    line_item_category VARCHAR(100), -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    parent_line_item_id UUID REFERENCES line_items(line_item_id), -- For hierarchical relationships

    -- Financial Values
    amount DECIMAL(18,2) NOT NULL, -- In dollars
    currency_code CHAR(3) DEFAULT 'USD',

    -- Normalization
    standardized_account_name VARCHAR(255),
    -- Maps to standard chart of accounts (e.g., "Operating Revenue - Water Sales")
    account_hierarchy_level INTEGER, -- 1 = top level, 2 = sub-category, etc.

    -- Context
    notes TEXT, -- Any footnotes or context
    is_calculated BOOLEAN DEFAULT FALSE, -- True if this is a sum/total
    calculation_formula TEXT, -- e.g., "line_item_1 + line_item_2"

    -- Quality
    confidence_score DECIMAL(3,2), -- AI extraction confidence
    manually_verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_line_items_statement ON line_items(statement_id);
CREATE INDEX idx_line_items_utility_year ON line_items(utility_id, fiscal_year);
CREATE INDEX idx_line_items_category ON line_items(line_item_category);
CREATE INDEX idx_line_items_standardized ON line_items(standardized_account_name);

-- Enable TimescaleDB hypertable for time-series queries
SELECT create_hypertable('line_items', 'fiscal_year', chunk_time_interval => 1,
    migrate_data => true, if_not_exists => true);
```

#### `standardized_accounts`
Master chart of accounts for normalization across utilities.

```sql
CREATE TABLE standardized_accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_category VARCHAR(100) NOT NULL, -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    statement_type VARCHAR(50) NOT NULL,
    parent_account_id UUID REFERENCES standardized_accounts(account_id),
    hierarchy_level INTEGER NOT NULL,

    -- Description & Mapping
    description TEXT,
    common_variations TEXT[], -- Array of common naming variations
    keywords TEXT[], -- Keywords for ML-based matching

    -- Industry Standards
    gasb_reference VARCHAR(100), -- Government Accounting Standards Board reference
    fasb_reference VARCHAR(100), -- Financial Accounting Standards Board (for IOUs)

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standardized_accounts_category ON standardized_accounts(account_category);
CREATE INDEX idx_standardized_accounts_statement ON standardized_accounts(statement_type);
```

### 2.2 Supporting Tables

#### `data_sources`
Tracks where we find financial reports.

```sql
CREATE TABLE data_sources (
    source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    -- 'utility_website', 'sec_edgar', 'municipal_bonds_site', 'gfoa', 'state_repository'
    base_url VARCHAR(1000),

    -- Scraping Configuration
    scraping_strategy VARCHAR(50), -- 'static_html', 'javascript_rendered', 'api', 'ftp'
    css_selectors JSONB, -- For HTML scraping
    api_endpoint VARCHAR(500),
    requires_authentication BOOLEAN DEFAULT FALSE,

    -- Reliability
    last_successful_crawl TIMESTAMP,
    success_rate DECIMAL(5,2), -- Percentage
    average_response_time_ms INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `utility_data_sources`
Maps utilities to their data sources.

```sql
CREATE TABLE utility_data_sources (
    utility_id UUID REFERENCES utilities(utility_id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(source_id) ON DELETE CASCADE,

    specific_url VARCHAR(1000), -- Specific page for this utility
    url_pattern VARCHAR(500), -- Pattern for generating URLs
    last_checked TIMESTAMP,
    last_found_report_date DATE,

    PRIMARY KEY (utility_id, source_id)
);
```

#### `forecasts`
Stores financial forecast scenarios.

```sql
CREATE TABLE forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Forecast Metadata
    forecast_name VARCHAR(255) NOT NULL,
    forecast_type VARCHAR(50), -- 'base_case', 'optimistic', 'pessimistic', 'custom'
    created_by UUID, -- User ID reference

    -- Time Horizon
    base_year INTEGER NOT NULL, -- Last historical year
    forecast_start_year INTEGER NOT NULL,
    forecast_end_year INTEGER NOT NULL,

    -- Assumptions (stored as JSONB for flexibility)
    assumptions JSONB,
    /* Example:
    {
        "revenue_growth_rate": 0.025,
        "operating_expense_inflation": 0.03,
        "capital_expenditure_annual": 5000000,
        "debt_service_coverage_target": 1.25
    }
    */

    -- Methodology
    model_version VARCHAR(50),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_forecasts_utility ON forecasts(utility_id);
```

#### `forecast_line_items`
Projected financial line items.

```sql
CREATE TABLE forecast_line_items (
    forecast_line_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forecast_id UUID NOT NULL REFERENCES forecasts(forecast_id) ON DELETE CASCADE,

    fiscal_year INTEGER NOT NULL,
    standardized_account_id UUID REFERENCES standardized_accounts(account_id),
    line_item_category VARCHAR(100) NOT NULL,

    projected_amount DECIMAL(18,2) NOT NULL,

    -- Calculation details
    calculation_method VARCHAR(100), -- 'growth_rate', 'percentage_of_revenue', 'fixed', 'regression'
    calculation_inputs JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_forecast_line_items_forecast ON forecast_line_items(forecast_id);
CREATE INDEX idx_forecast_line_items_year ON forecast_line_items(fiscal_year);
```

#### `audit_log`
Track all data modifications.

```sql
CREATE TABLE audit_log (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'

    old_values JSONB,
    new_values JSONB,

    changed_by UUID, -- User ID
    changed_at TIMESTAMP DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(changed_at DESC);
```

---

## 3. Data Pipeline Architecture

### 3.1 Pipeline Overview

The data pipeline consists of 5 main stages:

```
1. DISCOVERY → 2. ACQUISITION → 3. PARSING → 4. EXTRACTION → 5. NORMALIZATION
```

Each stage is orchestrated by Apache Airflow as a separate DAG (Directed Acyclic Graph).

### 3.2 Stage 1: Document Discovery

**Objective:** Find URLs for financial reports for all 1,000 utilities.

#### Discovery Strategies (in order of preference):

##### A. SEC EDGAR Database (for Investor-Owned Utilities)
```python
# Workflow:
1. Query SEC EDGAR API with utility CIK (Central Index Key)
2. Filter for 10-K and 10-Q filings
3. Parse index files to get document URLs
4. Store in financial_reports table

# Data Source:
- Base URL: https://www.sec.gov/cgi-bin/browse-edgar
- API: https://data.sec.gov/submissions/CIK{CIK}.json
- Coverage: ~50-100 investor-owned water utilities
```

##### B. Municipal Securities Rulemaking Board (MSRB EMMA)
```python
# Workflow:
1. Search EMMA database by utility name or CUSIP
2. Filter for "Annual Financial Information" documents
3. Extract document URLs from search results
4. Download metadata and filing dates

# Data Source:
- Base URL: https://emma.msrb.org
- Search endpoint: https://emma.msrb.org/Search/Search
- Coverage: Most public water utilities issuing municipal bonds
- Document types: CAFRs, Annual Reports, Official Statements
```

##### C. Government Finance Officers Association (GFOA)
```python
# Workflow:
1. Query GFOA Certificate of Achievement database
2. Identify utilities receiving awards for financial reporting excellence
3. Extract links to awarded CAFRs
4. Cross-reference with utility database

# Data Source:
- Base URL: https://www.gfoa.org/coa
- Coverage: ~3,000 government entities (subset are water utilities)
- Quality: High - these are exemplary reports
```

##### D. State-Level Repositories
```python
# Many states maintain centralized repositories:
# Examples:
- California: State Controller's Office (cities-ca.gov)
- Texas: Texas Municipal Reports (tmrs.com)
- Florida: Department of Financial Services

# Workflow per state:
1. Identify repository structure
2. Build state-specific scrapers
3. Map state entity IDs to our utility_id
4. Extract annual report links
```

##### E. Direct Utility Website Scraping
```python
# Workflow:
1. Start with utility.website_url from utilities table
2. Use ML model to identify "Finance", "Reports", "Investor Relations" links
3. Crawl these sections with depth limit = 3
4. Pattern matching for PDF links containing:
   - Keywords: "CAFR", "comprehensive annual", "financial report", "10-K"
   - Year patterns: "2023", "FY23", "fiscal year 2023"
5. Verify PDFs contain financial tables (check for keywords)

# Technologies:
- Scrapy: Main crawling framework
- Playwright: For JavaScript-heavy sites
- URL pattern matching with regex
- Content-type verification
```

##### F. Google Search API (Fallback)
```python
# Workflow:
1. For utilities without discovered reports, use search queries:
   "{utility_name} {state} CAFR {year}"
   "{utility_name} annual financial report {year}"
2. Filter results to .gov domains or official sites
3. Verify PDF content
4. Manual review queue for low-confidence matches

# Limitations:
- API quota limits
- May find non-official sources
- Requires validation
```

#### Discovery Orchestration (Airflow DAG)

```python
# DAG: utility_report_discovery
# Schedule: Weekly

Task 1: Load utilities without recent reports (last_checked > 30 days)
    ↓
Task 2: [Parallel] Run discovery strategies A-F
    ↓
Task 3: Deduplicate discovered URLs (by file hash)
    ↓
Task 4: Insert into financial_reports with status='pending'
    ↓
Task 5: Update utility_data_sources.last_checked
    ↓
Task 6: Send alert if discovery rate < 80% for any year
```

### 3.3 Stage 2: Document Acquisition

**Objective:** Download PDFs and store them reliably.

```python
# DAG: document_download
# Schedule: Continuous (triggered by discoveries)

Task 1: Query financial_reports WHERE processing_status='pending'
    ↓
Task 2: [Celery Workers - Parallel] For each report:
    2a. Download PDF from document_url
    2b. Calculate SHA-256 hash
    2c. Check for duplicate (same hash = same document)
    2d. Upload to S3: s3://bucket/utilities/{utility_id}/reports/{fiscal_year}/{filename}
    2e. Update financial_reports:
        - document_storage_path
        - file_hash
        - file_size_bytes
        - processing_status = 'downloaded'
    ↓
Task 3: Run virus scan on downloaded files
    ↓
Task 4: Extract basic metadata:
    - Page count (PyPDF2)
    - PDF version
    - Check if OCR needed (text extraction test)
    ↓
Task 5: Update report.ocr_required flag
```

**Retry Logic:**
- Max retries: 3
- Exponential backoff: 2s, 4s, 8s
- Handle HTTP errors: 404 (mark as unavailable), 429 (rate limit), 5xx (retry)

### 3.4 Stage 3: Document Parsing

**Objective:** Convert PDF to structured format ready for extraction.

#### Parsing Strategy Decision Tree:

```
PDF Downloaded
    ↓
Check: Is text extractable?
    ├─ YES (90% of PDFs) → Extract text with structure
    │   ↓
    │   Tools: pdfplumber (preserves layout)
    │   Output: JSON with pages, tables, text blocks, coordinates
    │
    └─ NO (10% - scanned PDFs) → OCR Pipeline
        ↓
        Tools: Tesseract or AWS Textract
        Output: Same JSON structure with OCR confidence scores
```

#### Detailed Parsing Process:

```python
# DAG: document_parsing
# Triggered when: processing_status = 'downloaded'

Task 1: Load PDF from S3
    ↓
Task 2: Determine parsing strategy
    if ocr_required:
        strategy = 'ocr'
    else:
        strategy = 'text_extraction'
    ↓
Task 3: Execute strategy

    # TEXT EXTRACTION PATH
    if strategy == 'text_extraction':
        1. Extract with pdfplumber:
            - Get all pages
            - Identify tables using .extract_tables()
            - Get text with coordinates
            - Detect headers/footers

        2. Identify financial statement pages:
            - Search for keywords:
              "Statement of Net Position", "Balance Sheet",
              "Statement of Revenues", "Income Statement",
              "Statement of Cash Flows"
            - Track page numbers

        3. Extract tables from those pages:
            - Parse table structure (rows/columns)
            - Preserve numeric formatting
            - Capture column headers
            - Handle multi-line headers
            - Detect subtotals and totals

        4. Save structured JSON:
        {
            "report_id": "uuid",
            "total_pages": 150,
            "financial_statement_pages": [
                {
                    "page_number": 12,
                    "statement_type": "balance_sheet",
                    "tables": [
                        {
                            "table_id": 1,
                            "headers": ["", "2023", "2022"],
                            "rows": [
                                ["Current Assets:", "", ""],
                                ["Cash and Cash Equivalents", "5,234,123", "4,987,654"],
                                ...
                            ]
                        }
                    ]
                }
            ]
        }

    # OCR PATH
    elif strategy == 'ocr':
        1. Convert PDF pages to images (pdf2image)
        2. For each financial statement page:
            - Run Tesseract OCR or AWS Textract
            - Get text + bounding boxes
            - Reconstruct table structure
        3. Save same JSON structure with ocr_confidence scores
    ↓
Task 4: Upload structured JSON to S3:
    s3://bucket/utilities/{utility_id}/parsed/{report_id}.json
    ↓
Task 5: Update financial_reports:
    - processing_status = 'parsing_complete'
    - page_count
    - ocr_quality_score (if applicable)
```

**Key Libraries:**
- **pdfplumber**: Best for layout-preserving extraction
- **PyPDF2**: Fallback for basic text extraction
- **Tabula-py**: Alternative for table extraction
- **pdf2image**: Convert to images for OCR
- **pytesseract**: OCR engine
- **AWS Textract**: Premium OCR with table detection (for critical documents)

### 3.5 Stage 4: Financial Data Extraction

**Objective:** Convert parsed tables into structured financial data.

This is the **MOST CRITICAL** stage. We use a hybrid approach:

#### Extraction Methods:

##### Method 1: Rule-Based Extraction (for well-structured PDFs)
```python
# Use when: Table structure is clean and consistent

Process:
1. Identify statement type from page headers
2. Parse column headers to determine fiscal years
3. Map row labels to standardized accounts using keyword matching
4. Extract numeric values
5. Validate sums/totals

Accuracy: 85-90% for clean PDFs
Speed: Very fast (seconds per document)
Cost: Low
```

##### Method 2: LLM-Based Extraction (Claude 3.5 Sonnet or GPT-4)
```python
# Use when: Complex formatting, inconsistent structure, or rule-based fails

Process:
1. For each financial statement page:

    a. Prepare prompt with context:
    """
    Extract the Balance Sheet data from this water utility's annual report.

    Fiscal Year: 2023
    Utility Name: [name]

    Return a JSON object with the following structure:
    {
        "statement_type": "balance_sheet",
        "fiscal_year": 2023,
        "line_items": [
            {
                "category": "asset",
                "name": "Cash and Cash Equivalents",
                "amount": 5234123,
                "parent": "Current Assets"
            },
            ...
        ]
    }

    Rules:
    - Extract ALL line items, including subtotals
    - Preserve the hierarchy (parent-child relationships)
    - Convert all amounts to numeric values (remove $ and commas)
    - If comparative year columns exist, extract those as separate records
    """

    b. Send to LLM:
        - Image input: Page screenshot (via Claude Vision) OR
        - Text input: Parsed table JSON

    c. Parse LLM response (JSON)

    d. Validate extraction:
        - Check totals match
        - Verify numeric fields are numbers
        - Ensure required fields present

    e. Confidence scoring:
        - Ask LLM to rate confidence (0-100) for each line item
        - If confidence < 80%, flag for manual review

2. Store extracted data in line_items table

Accuracy: 95-98% with GPT-4/Claude 3.5
Speed: Slower (10-30 seconds per page)
Cost: Higher ($0.01-0.05 per page estimate)
```

##### Method 3: Hybrid Approach (RECOMMENDED)
```python
# Workflow Decision Logic:

For each financial statement page:

    1. Attempt rule-based extraction
    2. Run validation checks:
        - Do subtotals sum correctly?
        - Are >90% of line items matched to standardized accounts?
        - Are there any missing critical accounts (e.g., Total Assets)?

    3. If validation passes:
        → Use rule-based extraction
        → Mark confidence = 'high'

    4. If validation fails:
        → Fall back to LLM extraction
        → Compare LLM results with rule-based
        → Use LLM results
        → Mark confidence = 'medium'

    5. If LLM confidence < 80%:
        → Queue for human review
        → Mark confidence = 'low'

Benefits:
- Cost-effective: Use cheap rule-based when possible
- Accurate: LLM handles edge cases
- Scalable: Automated with quality gates
```

#### Extraction Orchestration:

```python
# DAG: financial_data_extraction
# Triggered when: processing_status = 'parsing_complete'

Task 1: Load parsed JSON from S3
    ↓
Task 2: For each statement page, [Celery Queue]:
    2a. Identify statement type
    2b. Create financial_statements record
    2c. Run extraction (hybrid method)
    2d. Insert line_items
    2e. Calculate extraction_confidence_score
    ↓
Task 3: Validation Checks:
    - Three statements present? (Balance Sheet, Income, Cash Flow)
    - Accounting equation holds? (Assets = Liabilities + Equity)
    - Year-over-year changes reasonable? (<50% change flags review)
    ↓
Task 4: Update financial_reports:
    - processing_status = 'completed'
    - extraction_confidence_score
    ↓
Task 5: If confidence < 80% → Add to manual_review_queue
```

**LLM Provider Selection:**
- **Primary:** Claude 3.5 Sonnet via Anthropic API
  - Excellent at structured data extraction
  - Vision capabilities for table understanding
  - 200K context window (can handle full reports)
- **Backup:** GPT-4 Turbo via OpenAI API
  - Very accurate
  - Good JSON mode
- **Budget Option:** GPT-3.5 Turbo for simple extractions

**Cost Estimation:**
- 1,000 utilities × 10 years × 3 statements per year = 30,000 statements
- LLM usage (50% hybrid rate): 15,000 statements
- At $0.03 per statement = $450 one-time + incremental updates

### 3.6 Stage 5: Data Normalization

**Objective:** Standardize account names across different utilities for comparability.

#### Challenge:
Different utilities use different terminology:
- "Water Sales Revenue" vs "Revenue from Water Sales" vs "Water Service Charges"
- "Depreciation and Amortization" vs "Depreciation Expense"

#### Solution: ML-Based Account Mapping

```python
# DAG: account_normalization
# Runs after: Extraction complete

Task 1: Load unmapped line_items (standardized_account_id IS NULL)
    ↓
Task 2: For each line_item:

    # Method A: Keyword Matching
    - Compare line_item_name to standardized_accounts.common_variations
    - Use fuzzy matching (fuzzywuzzy library)
    - If match confidence > 90% → Assign standardized_account_id

    # Method B: Embedding-Based Similarity (for no exact match)
    - Generate embedding for line_item_name (OpenAI text-embedding-3-small)
    - Compare to embeddings of standardized_accounts.account_name
    - Find nearest neighbor using cosine similarity
    - If similarity > 0.85 → Assign standardized_account_id

    # Method C: LLM Classification (for ambiguous cases)
    - Prompt: "Which standard account does '{line_item_name}' belong to?"
    - Provide list of possible standardized_accounts
    - Get LLM classification
    - If confidence > 75% → Assign

    # Method D: Human Review
    - Queue items with confidence < 75%
    - Admin interface for manual mapping
    - Learn from human decisions to improve ML model
    ↓
Task 3: Update line_items.standardized_account_name
    ↓
Task 4: Update account_hierarchy_level based on parent relationships
    ↓
Task 5: Retrain embedding model monthly with new mappings
```

**Standardized Chart of Accounts:**

Based on GASB (Governmental Accounting Standards Board) and NARUC (National Association of Regulatory Utility Commissioners) guidelines:

```
REVENUES
├── Operating Revenues
│   ├── Water Sales - Residential
│   ├── Water Sales - Commercial
│   ├── Water Sales - Industrial
│   ├── Sewer Service Charges
│   └── Other Service Charges
├── Non-Operating Revenues
│   ├── Interest Income
│   ├── Grant Revenue
│   └── Other Non-Operating Revenue
└── Capital Contributions

EXPENSES
├── Operating Expenses
│   ├── Personnel Services
│   ├── Contractual Services
│   ├── Utilities and Fuel
│   ├── Repairs and Maintenance
│   ├── Depreciation and Amortization
│   └── Other Operating Expenses
├── Non-Operating Expenses
│   ├── Interest Expense
│   └── Other Non-Operating Expenses
└── Capital Outlays

ASSETS
├── Current Assets
│   ├── Cash and Cash Equivalents
│   ├── Investments
│   ├── Accounts Receivable
│   └── Inventory
├── Capital Assets
│   ├── Land
│   ├── Buildings
│   ├── Infrastructure (Water/Sewer Systems)
│   ├── Equipment
│   └── Accumulated Depreciation
└── Other Assets

LIABILITIES
├── Current Liabilities
│   ├── Accounts Payable
│   ├── Accrued Liabilities
│   └── Current Portion of Long-Term Debt
└── Long-Term Liabilities
    ├── Bonds Payable
    ├── Pension Obligations
    └── Other Long-Term Liabilities

NET POSITION / EQUITY
├── Net Investment in Capital Assets
├── Restricted Net Position
└── Unrestricted Net Position
```

---

## 4. API Design

### 4.1 RESTful Endpoints

```
BASE_URL: https://api.waterfinance.com/v1

# Utilities
GET    /utilities                    # List all utilities (paginated)
GET    /utilities/{id}               # Get utility details
GET    /utilities/{id}/reports       # Get all reports for a utility
GET    /utilities/{id}/financials    # Get financial summary

# Financial Data
GET    /financials/statements        # Query statements (filters: utility_id, year, type)
GET    /financials/line-items        # Query line items (filters: utility_id, year, account)
GET    /financials/compare           # Compare multiple utilities
GET    /financials/trends            # Time-series analysis

# Forecasting
POST   /forecasts                    # Create new forecast
GET    /forecasts/{id}               # Get forecast details
PUT    /forecasts/{id}               # Update forecast
GET    /forecasts/{id}/statements    # Get projected statements

# Admin
POST   /admin/reports/trigger-discovery    # Manually trigger discovery
GET    /admin/reports/queue                # View processing queue
POST   /admin/line-items/{id}/verify       # Manually verify/correct data

# Search
GET    /search/utilities             # Full-text search utilities
GET    /search/reports               # Search within reports (Elasticsearch)
```

### 4.2 Example Response

```json
GET /utilities/550e8400-e29b-41d4-a716-446655440000/financials?year=2023

{
  "utility": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "San Francisco Public Utilities Commission",
    "state": "CA"
  },
  "fiscal_year": 2023,
  "statements": {
    "balance_sheet": {
      "statement_id": "...",
      "period_end": "2023-06-30",
      "assets": {
        "current_assets": {
          "cash_and_equivalents": 523412300,
          "accounts_receivable": 145234100,
          "total": 715234500
        },
        "capital_assets": {
          "infrastructure_net": 8234123400,
          "total": 8534123400
        },
        "total_assets": 9249357900
      },
      "liabilities": {
        "current_liabilities": 234123400,
        "long_term_debt": 4123234100,
        "total_liabilities": 4357357500
      },
      "net_position": {
        "net_investment_in_capital_assets": 4234123400,
        "restricted": 123423400,
        "unrestricted": 534453600,
        "total": 4892000400
      }
    },
    "income_statement": { ... },
    "cash_flow": { ... }
  },
  "metadata": {
    "report_id": "...",
    "report_type": "CAFR",
    "extraction_confidence": 0.96,
    "last_updated": "2024-03-15T10:30:00Z"
  }
}
```

---

## 5. Frontend Architecture

### 5.1 Application Structure

```
src/
├── components/
│   ├── common/
│   │   ├── DataTable.tsx
│   │   ├── FinancialChart.tsx
│   │   └── UtilitySearchBar.tsx
│   ├── utilities/
│   │   ├── UtilityList.tsx
│   │   ├── UtilityDetail.tsx
│   │   └── UtilityMap.tsx
│   ├── financials/
│   │   ├── BalanceSheet.tsx
│   │   ├── IncomeStatement.tsx
│   │   ├── CashFlowStatement.tsx
│   │   ├── TrendAnalysis.tsx
│   │   └── ComparativeView.tsx
│   └── forecasts/
│       ├── ForecastBuilder.tsx
│       ├── AssumptionsEditor.tsx
│       └── ScenarioComparison.tsx
├── pages/
│   ├── Dashboard.tsx
│   ├── UtilitiesPage.tsx
│   ├── FinancialsPage.tsx
│   └── ForecastsPage.tsx
├── hooks/
│   ├── useUtilities.ts
│   ├── useFinancials.ts
│   └── useForecasts.ts
├── services/
│   ├── api.ts
│   └── authService.ts
├── store/
│   ├── utilitiesStore.ts
│   └── financialsStore.ts
└── utils/
    ├── formatters.ts
    └── calculations.ts
```

### 5.2 Key Features

#### A. Dashboard
- Executive summary: Total utilities, coverage by state, data quality metrics
- Recent updates feed
- Quick search
- Top utilities by revenue/assets

#### B. Utility Browser
- Filterable table: by state, type, size
- Interactive map view (D3.js or Mapbox)
- Utility detail page with 10-year financial summary

#### C. Financial Analysis
- Side-by-side statement comparison (multiple years, multiple utilities)
- Interactive charts: Revenue trends, expense breakdown, cash flow waterfall
- Downloadable Excel exports
- Ratio analysis: Debt service coverage, operating margin, current ratio

#### D. Forecast Module
- Drag-and-drop assumption builder
- Real-time recalculation
- Sensitivity analysis (what-if scenarios)
- Export pro forma statements

---

## 6. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CloudFlare                           │
│                     (CDN + DDoS Protection)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴────────────────┐
         │                                │
         ▼                                ▼
┌─────────────────┐            ┌──────────────────┐
│  React Frontend │            │   FastAPI        │
│  (S3 + CloudFr) │            │   Application    │
│                 │            │   (ECS/Kubernetes)│
└─────────────────┘            │   - API Servers  │
                               │   - Auth Service │
                               └────────┬─────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
          ┌──────────────────┐  ┌─────────────┐   ┌──────────────┐
          │   PostgreSQL     │  │   Redis     │   │   Celery     │
          │   (RDS/Cloud SQL)│  │   (Cache)   │   │   Workers    │
          │   - TimescaleDB  │  │             │   │   - Scrapers │
          └──────────────────┘  └─────────────┘   │   - Parsers  │
                    │                              │   - Extractors│
                    │                              └───────┬──────┘
                    │                                      │
                    ▼                                      ▼
          ┌──────────────────┐              ┌──────────────────────┐
          │  Elasticsearch   │              │   S3 / GCS Storage   │
          │  (Search Index)  │              │   - PDFs             │
          └──────────────────┘              │   - Parsed JSON      │
                                            └──────────────────────┘
                    │
                    ▼
          ┌──────────────────┐
          │  Apache Airflow  │
          │  (Orchestration) │
          │  - Discovery DAG │
          │  - Extraction DAG│
          └──────────────────┘
```

---

## 7. Data Quality & Monitoring

### 7.1 Quality Metrics Dashboard

Track:
- **Coverage:** % of utilities with reports for each year (target: >95% for recent 3 years)
- **Extraction Confidence:** Average confidence score (target: >0.90)
- **Data Freshness:** Days since last report update
- **Pipeline Health:** Success rate of each DAG stage

### 7.2 Alerting

Trigger alerts when:
- Extraction confidence < 0.80 for any report
- Accounting equation doesn't balance (Assets ≠ Liabilities + Equity)
- Year-over-year change > 50% for major line items
- Pipeline failure for >10 utilities
- Discovery rate < 80% for any target year

### 7.3 Human Review Queue

Admin interface to:
- View low-confidence extractions
- Correct/verify line items
- Re-run extraction with corrected parameters
- Add utility-specific parsing rules

---

## 8. Security & Compliance

### 8.1 Data Security
- All data encrypted at rest (S3/database encryption)
- TLS 1.3 for all data in transit
- API authentication via JWT with refresh tokens
- Role-based access control (RBAC)

### 8.2 Compliance
- Financial data is public information (no PII concerns)
- Maintain attribution to original source documents
- Respect robots.txt for web scraping
- Rate limiting to avoid overwhelming source servers

### 8.3 Backup Strategy
- Automated daily PostgreSQL backups (7-day retention)
- S3 versioning for all PDFs
- Point-in-time recovery capability
- Disaster recovery RTO: 4 hours, RPO: 1 hour

---

## 9. Scalability Considerations

### 9.1 Current Scale
- 1,000 utilities × 10 years × ~200 pages/report = ~2 million pages
- Storage: ~50 GB PDFs + 10 GB database
- API traffic: <1000 requests/day initially

### 9.2 Future Scale (5,000 utilities)
- 10 million pages
- Storage: 250 GB PDFs + 50 GB database
- Optimize:
  - PostgreSQL read replicas for queries
  - ElastiCache for frequently accessed data
  - CDN for PDF serving
  - Horizontal scaling of API servers

---

## 10. Development Phases

### Phase 1: MVP (3 months)
- [ ] Database schema setup
- [ ] Discovery pipeline for 100 utilities (EDGAR + EMMA only)
- [ ] Basic extraction (rule-based + manual fallback)
- [ ] Simple React frontend (list + detail view)
- [ ] Deployment on AWS/GCP

### Phase 2: Scale (2 months)
- [ ] Expand to 1,000 utilities
- [ ] Implement LLM-based extraction
- [ ] Add forecasting module
- [ ] Advanced visualizations

### Phase 3: Enhance (2 months)
- [ ] ML-based normalization
- [ ] Real-time updates
- [ ] API for third-party integrations
- [ ] Mobile-responsive design

---

## 11. Cost Estimate

**Infrastructure (Monthly):**
- AWS/GCP compute (API + workers): $500
- PostgreSQL RDS: $200
- S3 storage: $50
- Elasticsearch: $150
- Airflow hosting: $100
- **Total Infrastructure:** ~$1,000/month

**API Costs (One-time + ongoing):**
- LLM extraction (initial 30K statements @ 50% usage): $450
- LLM extraction (updates, ~500/year): $15/month
- Embedding generation: $50 one-time
- **Total API:** ~$450 one-time + $15/month

**Total First Year:** ~$12,450

---

## 12. Key Technical Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Backend Language** | Python | Best ecosystem for ML/data processing |
| **API Framework** | FastAPI | Async, fast, auto-docs |
| **Database** | PostgreSQL + TimescaleDB | Relational + time-series optimization |
| **Frontend** | React + TypeScript | Industry standard, strong typing |
| **Extraction Method** | Hybrid (Rules + LLM) | Balance cost and accuracy |
| **LLM Provider** | Claude 3.5 Sonnet | Best structured extraction |
| **Orchestration** | Apache Airflow | Robust workflow management |
| **Storage** | S3 | Scalable, cheap |
| **Deployment** | Docker + K8s/ECS | Containerized, scalable |

---

## Conclusion

This architecture provides a robust, scalable foundation for analyzing 1,000+ water utilities. The **data pipeline** leverages modern LLMs to solve the historically difficult problem of extracting structured data from unstructured financial reports, while maintaining cost-effectiveness through a hybrid approach.

**Critical Success Factors:**
1. **Discovery coverage:** Finding reports for >95% of utilities
2. **Extraction accuracy:** Achieving >95% accuracy through LLM + validation
3. **Normalization:** Building a comprehensive standardized chart of accounts
4. **Data quality:** Automated validation + human review queues

**Next Steps:**
1. Set up development environment
2. Initialize database schema
3. Build discovery pipeline for 10 test utilities
4. Validate extraction approach with real CAFRs
5. Iterate based on results

---

*Document Version: 1.0*
*Last Updated: 2025-11-17*
*Author: Principal Solutions Architect*
