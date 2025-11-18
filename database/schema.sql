-- Water Utilities Financial Database Schema
-- PostgreSQL 12+
-- Zero-cost implementation for 700-900 water utilities

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Utilities: Master table of water utilities
CREATE TABLE IF NOT EXISTS utilities (
    utility_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Basic Information
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
    cusip VARCHAR(9), -- For investor-owned utilities (EMMA uses this)
    gfoa_id VARCHAR(50), -- Government Finance Officers Association ID
    emma_issuer_id VARCHAR(50), -- EMMA internal ID

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
    data_quality_score DECIMAL(3,2) DEFAULT 0.00, -- 0.00 to 1.00
    last_verified_date DATE,
    has_complete_data BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT utilities_name_state_unique UNIQUE (name, state_code)
);

CREATE INDEX idx_utilities_state ON utilities(state_code);
CREATE INDEX idx_utilities_type ON utilities(utility_type);
CREATE INDEX idx_utilities_population ON utilities(population_served DESC NULLS LAST);
CREATE INDEX idx_utilities_data_quality ON utilities(data_quality_score DESC);

-- Financial Reports: Annual report documents
CREATE TABLE IF NOT EXISTS financial_reports (
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Report Metadata
    fiscal_year INTEGER NOT NULL,
    fiscal_year_end_date DATE NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- 'CAFR', '10-K', 'Annual_Report', 'Official_Statement'
    report_title VARCHAR(500),

    -- Document Information
    document_url VARCHAR(1000),
    document_storage_path VARCHAR(1000), -- Local file path
    emma_document_id VARCHAR(50), -- EMMA ID (e.g., "ER1234567")
    file_hash VARCHAR(64), -- SHA-256 for deduplication
    file_size_bytes BIGINT,
    page_count INTEGER,

    -- Processing Status
    processing_status VARCHAR(50) DEFAULT 'pending',
    -- 'pending', 'downloading', 'downloaded', 'parsing', 'parsed', 'extracting', 'completed', 'failed'
    processing_started_at TIMESTAMP,
    processing_completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Quality Metrics
    extraction_confidence_score DECIMAL(3,2), -- AI confidence in extraction
    has_balance_sheet BOOLEAN DEFAULT FALSE,
    has_income_statement BOOLEAN DEFAULT FALSE,
    has_cash_flow BOOLEAN DEFAULT FALSE,
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
CREATE INDEX idx_financial_reports_emma_id ON financial_reports(emma_document_id);

-- Financial Statements: Individual statements within reports
CREATE TABLE IF NOT EXISTS financial_statements (
    statement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES financial_reports(report_id) ON DELETE CASCADE,
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Statement Metadata
    statement_type VARCHAR(50) NOT NULL,
    -- 'income_statement', 'balance_sheet', 'cash_flow', 'statement_of_net_position'
    fiscal_year INTEGER NOT NULL,
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,

    -- Classification
    fund_type VARCHAR(100) DEFAULT 'enterprise_fund', -- 'enterprise_fund', 'water_fund', 'consolidated'
    basis_of_accounting VARCHAR(50) DEFAULT 'accrual', -- 'accrual', 'modified_accrual', 'cash'

    -- Source Information
    page_numbers VARCHAR(100), -- "12-14" or "23"
    extraction_method VARCHAR(50), -- 'rule_based', 'llm_extraction', 'manual'

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT financial_statements_unique UNIQUE (report_id, statement_type, fund_type)
);

CREATE INDEX idx_financial_statements_utility_year ON financial_statements(utility_id, fiscal_year);
CREATE INDEX idx_financial_statements_type ON financial_statements(statement_type);
CREATE INDEX idx_financial_statements_report ON financial_statements(report_id);

-- Standardized Chart of Accounts
CREATE TABLE IF NOT EXISTS standardized_accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_category VARCHAR(100) NOT NULL, -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    statement_type VARCHAR(50) NOT NULL, -- 'income_statement', 'balance_sheet', 'cash_flow'
    parent_account_id UUID REFERENCES standardized_accounts(account_id),
    hierarchy_level INTEGER NOT NULL,

    -- Description & Mapping
    description TEXT,
    common_variations TEXT[], -- Array of common naming variations
    keywords TEXT[], -- Keywords for matching

    -- Industry Standards
    gasb_reference VARCHAR(100), -- Government Accounting Standards Board reference

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standardized_accounts_category ON standardized_accounts(account_category);
CREATE INDEX idx_standardized_accounts_statement ON standardized_accounts(statement_type);
CREATE INDEX idx_standardized_accounts_code ON standardized_accounts(account_code);

-- Line Items: Granular financial data
CREATE TABLE IF NOT EXISTS line_items (
    line_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statement_id UUID NOT NULL REFERENCES financial_statements(statement_id) ON DELETE CASCADE,
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,
    fiscal_year INTEGER NOT NULL,

    -- Line Item Details
    account_code VARCHAR(50),
    line_item_name VARCHAR(500) NOT NULL,
    line_item_category VARCHAR(100) NOT NULL, -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    parent_line_item_id UUID REFERENCES line_items(line_item_id),

    -- Financial Values
    amount DECIMAL(18,2) NOT NULL, -- In dollars
    currency_code CHAR(3) DEFAULT 'USD',

    -- Normalization
    standardized_account_id UUID REFERENCES standardized_accounts(account_id),
    standardized_account_name VARCHAR(255),
    account_hierarchy_level INTEGER, -- 1 = top level, 2 = sub-category, etc.

    -- Context
    notes TEXT,
    is_calculated BOOLEAN DEFAULT FALSE, -- True if this is a sum/total
    calculation_formula TEXT,

    -- Quality
    confidence_score DECIMAL(3,2), -- Extraction confidence
    manually_verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_line_items_statement ON line_items(statement_id);
CREATE INDEX idx_line_items_utility_year ON line_items(utility_id, fiscal_year);
CREATE INDEX idx_line_items_category ON line_items(line_item_category);
CREATE INDEX idx_line_items_standardized ON line_items(standardized_account_id);
CREATE INDEX idx_line_items_year ON line_items(fiscal_year DESC);

-- =============================================================================
-- SUPPORTING TABLES
-- =============================================================================

-- Data Sources: Where we find reports
CREATE TABLE IF NOT EXISTS data_sources (
    source_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    -- 'emma', 'sec_edgar', 'utility_website', 'state_repository'
    base_url VARCHAR(1000),

    -- Reliability
    last_successful_crawl TIMESTAMP,
    success_rate DECIMAL(5,2), -- Percentage

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Utility Data Sources: Maps utilities to sources
CREATE TABLE IF NOT EXISTS utility_data_sources (
    utility_id UUID REFERENCES utilities(utility_id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(source_id) ON DELETE CASCADE,

    specific_url VARCHAR(1000),
    last_checked TIMESTAMP,
    last_found_report_date DATE,

    PRIMARY KEY (utility_id, source_id)
);

-- =============================================================================
-- FORECASTING TABLES
-- =============================================================================

-- Forecasts: Financial projection scenarios
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    utility_id UUID NOT NULL REFERENCES utilities(utility_id) ON DELETE CASCADE,

    -- Forecast Metadata
    forecast_name VARCHAR(255) NOT NULL,
    forecast_type VARCHAR(50) DEFAULT 'base_case', -- 'base_case', 'optimistic', 'pessimistic', 'custom'

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
        "capital_expenditure_annual": 5000000
    }
    */

    -- Methodology
    model_version VARCHAR(50) DEFAULT 'v1.0',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_forecasts_utility ON forecasts(utility_id);
CREATE INDEX idx_forecasts_base_year ON forecasts(base_year);

-- Forecast Line Items: Projected financial data
CREATE TABLE IF NOT EXISTS forecast_line_items (
    forecast_line_item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_id UUID NOT NULL REFERENCES forecasts(forecast_id) ON DELETE CASCADE,

    fiscal_year INTEGER NOT NULL,
    standardized_account_id UUID REFERENCES standardized_accounts(account_id),
    line_item_category VARCHAR(100) NOT NULL,

    projected_amount DECIMAL(18,2) NOT NULL,

    -- Calculation details
    calculation_method VARCHAR(100), -- 'growth_rate', 'percentage_of_revenue', 'fixed'
    calculation_inputs JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_forecast_line_items_forecast ON forecast_line_items(forecast_id);
CREATE INDEX idx_forecast_line_items_year ON forecast_line_items(fiscal_year);

-- =============================================================================
-- AUDIT & LOGGING
-- =============================================================================

-- Audit Log: Track data modifications
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'

    old_values JSONB,
    new_values JSONB,

    changed_at TIMESTAMP DEFAULT NOW(),
    changed_by VARCHAR(100) DEFAULT 'system'
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(changed_at DESC);

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View: Latest financial data for each utility
CREATE OR REPLACE VIEW v_latest_financials AS
SELECT
    u.utility_id,
    u.name,
    u.state_code,
    MAX(li.fiscal_year) as latest_year,
    SUM(CASE WHEN li.line_item_category = 'revenue' THEN li.amount ELSE 0 END) as total_revenue,
    SUM(CASE WHEN li.line_item_category = 'expense' THEN li.amount ELSE 0 END) as total_expenses,
    SUM(CASE WHEN li.line_item_category = 'asset' THEN li.amount ELSE 0 END) as total_assets,
    SUM(CASE WHEN li.line_item_category = 'liability' THEN li.amount ELSE 0 END) as total_liabilities
FROM utilities u
JOIN line_items li ON u.utility_id = li.utility_id
GROUP BY u.utility_id, u.name, u.state_code;

-- View: Data coverage by utility
CREATE OR REPLACE VIEW v_data_coverage AS
SELECT
    u.utility_id,
    u.name,
    u.state_code,
    COUNT(DISTINCT fr.fiscal_year) as years_covered,
    MIN(fr.fiscal_year) as earliest_year,
    MAX(fr.fiscal_year) as latest_year,
    COUNT(DISTINCT CASE WHEN fr.processing_status = 'completed' THEN fr.report_id END) as completed_reports,
    COUNT(DISTINCT fr.report_id) as total_reports
FROM utilities u
LEFT JOIN financial_reports fr ON u.utility_id = fr.utility_id
GROUP BY u.utility_id, u.name, u.state_code;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_utilities_updated_at BEFORE UPDATE ON utilities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_financial_reports_updated_at BEFORE UPDATE ON financial_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_financial_statements_updated_at BEFORE UPDATE ON financial_statements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_line_items_updated_at BEFORE UPDATE ON line_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_forecasts_updated_at BEFORE UPDATE ON forecasts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- SEED DATA: Standardized Chart of Accounts
-- =============================================================================

-- Insert standardized accounts for water utilities
INSERT INTO standardized_accounts (account_code, account_name, account_category, statement_type, hierarchy_level, common_variations, keywords) VALUES
-- REVENUES
('REV-001', 'Operating Revenue - Water Sales', 'revenue', 'income_statement', 1, ARRAY['Water Sales', 'Water Service Revenue', 'Revenue from Water Sales'], ARRAY['water', 'sales', 'service revenue']),
('REV-002', 'Operating Revenue - Sewer Service', 'revenue', 'income_statement', 1, ARRAY['Sewer Service Charges', 'Wastewater Revenue', 'Sewer Revenue'], ARRAY['sewer', 'wastewater', 'service charges']),
('REV-003', 'Other Operating Revenue', 'revenue', 'income_statement', 1, ARRAY['Other Service Charges', 'Miscellaneous Revenue'], ARRAY['other', 'miscellaneous']),
('REV-004', 'Non-Operating Revenue', 'revenue', 'income_statement', 1, ARRAY['Investment Income', 'Interest Income', 'Grant Revenue'], ARRAY['interest', 'investment', 'grant']),

-- EXPENSES
('EXP-001', 'Personnel Services', 'expense', 'income_statement', 1, ARRAY['Salaries and Wages', 'Labor Costs', 'Employee Compensation'], ARRAY['salary', 'wage', 'personnel', 'labor']),
('EXP-002', 'Contractual Services', 'expense', 'income_statement', 1, ARRAY['Professional Services', 'Contracted Services'], ARRAY['contract', 'professional', 'consultant']),
('EXP-003', 'Utilities and Fuel', 'expense', 'income_statement', 1, ARRAY['Energy Costs', 'Power Costs'], ARRAY['utilities', 'fuel', 'energy', 'power']),
('EXP-004', 'Repairs and Maintenance', 'expense', 'income_statement', 1, ARRAY['Maintenance Expense', 'Repairs'], ARRAY['repair', 'maintenance']),
('EXP-005', 'Depreciation and Amortization', 'expense', 'income_statement', 1, ARRAY['Depreciation', 'Amortization'], ARRAY['depreciation', 'amortization']),
('EXP-006', 'Interest Expense', 'expense', 'income_statement', 1, ARRAY['Interest on Debt', 'Debt Service Interest'], ARRAY['interest', 'debt service']),

-- ASSETS
('AST-001', 'Cash and Cash Equivalents', 'asset', 'balance_sheet', 1, ARRAY['Cash', 'Cash Equivalents'], ARRAY['cash']),
('AST-002', 'Investments', 'asset', 'balance_sheet', 1, ARRAY['Investment Securities'], ARRAY['investment', 'securities']),
('AST-003', 'Accounts Receivable', 'asset', 'balance_sheet', 1, ARRAY['Receivables', 'Customer Receivables'], ARRAY['receivable', 'accounts receivable']),
('AST-004', 'Capital Assets - Infrastructure', 'asset', 'balance_sheet', 1, ARRAY['Water System', 'Sewer System', 'Infrastructure Assets'], ARRAY['infrastructure', 'capital assets', 'water system']),
('AST-005', 'Capital Assets - Buildings', 'asset', 'balance_sheet', 1, ARRAY['Buildings and Improvements'], ARRAY['building', 'structure']),
('AST-006', 'Capital Assets - Equipment', 'asset', 'balance_sheet', 1, ARRAY['Equipment', 'Machinery'], ARRAY['equipment', 'machinery']),
('AST-007', 'Accumulated Depreciation', 'asset', 'balance_sheet', 1, ARRAY['Accumulated Depreciation'], ARRAY['accumulated depreciation']),

-- LIABILITIES
('LIA-001', 'Accounts Payable', 'liability', 'balance_sheet', 1, ARRAY['Payables', 'Accounts Payable'], ARRAY['payable', 'accounts payable']),
('LIA-002', 'Accrued Liabilities', 'liability', 'balance_sheet', 1, ARRAY['Accrued Expenses'], ARRAY['accrued', 'accrual']),
('LIA-003', 'Current Portion of Long-Term Debt', 'liability', 'balance_sheet', 1, ARRAY['Current Debt', 'Short-Term Debt'], ARRAY['current debt', 'short-term']),
('LIA-004', 'Bonds Payable', 'liability', 'balance_sheet', 1, ARRAY['Revenue Bonds', 'Municipal Bonds', 'Long-Term Debt'], ARRAY['bonds', 'long-term debt']),
('LIA-005', 'Pension Obligations', 'liability', 'balance_sheet', 1, ARRAY['Pension Liability', 'Retirement Obligations'], ARRAY['pension', 'retirement']),

-- NET POSITION / EQUITY
('EQT-001', 'Net Investment in Capital Assets', 'equity', 'balance_sheet', 1, ARRAY['Net Investment in Capital Assets'], ARRAY['net investment', 'capital']),
('EQT-002', 'Restricted Net Position', 'equity', 'balance_sheet', 1, ARRAY['Restricted Assets', 'Restricted Funds'], ARRAY['restricted']),
('EQT-003', 'Unrestricted Net Position', 'equity', 'balance_sheet', 1, ARRAY['Unrestricted', 'Unrestricted Funds'], ARRAY['unrestricted'])
ON CONFLICT (account_code) DO NOTHING;

-- =============================================================================
-- INITIAL DATA SOURCE: EMMA
-- =============================================================================

INSERT INTO data_sources (source_id, source_name, source_type, base_url, is_active) VALUES
(uuid_generate_v4(), 'EMMA - Municipal Securities Rulemaking Board', 'emma', 'https://emma.msrb.org/', true)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE utilities IS 'Master table of water utilities in the United States';
COMMENT ON TABLE financial_reports IS 'Annual financial report documents (CAFRs, 10-Ks)';
COMMENT ON TABLE financial_statements IS 'Individual financial statements within reports';
COMMENT ON TABLE line_items IS 'Granular line-item level financial data';
COMMENT ON TABLE standardized_accounts IS 'Standardized chart of accounts for normalization';
COMMENT ON TABLE forecasts IS 'Financial forecast scenarios';
COMMENT ON TABLE forecast_line_items IS 'Projected line items for forecasts';

-- Done!
SELECT 'Database schema created successfully!' AS status;
