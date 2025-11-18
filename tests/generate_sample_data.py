"""
Sample Data Generator for Testing
Creates realistic test data without requiring actual CAFRs
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.db_setup import DatabaseConfig, get_connection
import uuid
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleDataGenerator:
    """Generate realistic sample data for testing"""

    def __init__(self, db_connection):
        self.conn = db_connection

    def generate_sample_utilities(self, count: int = 10) -> list:
        """Generate sample utility records"""

        states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']
        utility_types = ['municipal', 'special_district', 'investor_owned', 'regional']

        sample_names = [
            "Metro Water District",
            "City Water and Sewer",
            "Regional Water Authority",
            "Municipal Utility District",
            "Water and Power Department",
            "Public Utilities Commission",
            "Water Resources Authority",
            "Metropolitan Water Works",
            "County Water District",
            "Water Conservation District"
        ]

        utilities = []
        cursor = self.conn.cursor()

        for i in range(count):
            utility_id = str(uuid.uuid4())
            state = random.choice(states)

            utility = {
                'utility_id': utility_id,
                'name': f"{random.choice(['North', 'South', 'East', 'West', 'Central'])} {state} {random.choice(sample_names)}",
                'legal_name': f"The {state} {random.choice(sample_names)}",
                'utility_type': random.choice(utility_types),
                'city': f"City_{i}",
                'state_code': state,
                'zip_code': f"{random.randint(10000, 99999)}",
                'population_served': random.randint(50000, 2000000),
                'connections': random.randint(20000, 800000),
                'ownership_structure': 'public' if random.random() > 0.3 else 'private',
                'year_established': random.randint(1950, 2000),
            }

            cursor.execute("""
                INSERT INTO utilities (
                    utility_id, name, legal_name, utility_type,
                    city, state_code, zip_code,
                    population_served, connections, ownership_structure, year_established
                ) VALUES (
                    %(utility_id)s, %(name)s, %(legal_name)s, %(utility_type)s,
                    %(city)s, %(state_code)s, %(zip_code)s,
                    %(population_served)s, %(connections)s, %(ownership_structure)s, %(year_established)s
                )
                ON CONFLICT (name, state_code) DO NOTHING
            """, utility)

            utilities.append(utility)

        self.conn.commit()
        cursor.close()

        logger.info(f"✓ Generated {count} sample utilities")
        return utilities

    def generate_financial_data(self, utility_id: str, years: int = 10):
        """Generate realistic financial data for a utility"""

        cursor = self.conn.cursor()

        # Base financial metrics (scaled by population)
        cursor.execute("SELECT population_served FROM utilities WHERE utility_id = %s", (utility_id,))
        result = cursor.fetchone()
        population = result[0] if result else 100000

        # Scale revenue by population (rough: $500-800 per capita annually)
        base_revenue = population * random.uniform(500, 800)

        current_year = datetime.now().year - 1

        for year_offset in range(years):
            fiscal_year = current_year - year_offset

            # Apply random growth (2-4% annually)
            growth_factor = (1 + random.uniform(0.02, 0.04)) ** (years - year_offset)
            year_revenue = base_revenue * growth_factor
            year_expenses = year_revenue * random.uniform(0.75, 0.85)  # 75-85% expense ratio

            # Create financial report
            report_id = str(uuid.uuid4())

            cursor.execute("""
                INSERT INTO financial_reports (
                    report_id, utility_id, fiscal_year, fiscal_year_end_date,
                    report_type, report_title, processing_status,
                    has_balance_sheet, has_income_statement, has_cash_flow
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (utility_id, fiscal_year, report_type) DO NOTHING
                RETURNING report_id
            """, (
                report_id, utility_id, fiscal_year,
                datetime(fiscal_year, 6, 30),
                'CAFR', f'FY{fiscal_year} Comprehensive Annual Financial Report',
                'completed', True, True, True
            ))

            if cursor.fetchone() is None:
                continue  # Already exists

            # Create income statement
            income_stmt_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO financial_statements (
                    statement_id, report_id, utility_id, statement_type,
                    fiscal_year, period_start_date, period_end_date,
                    fund_type, extraction_method
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                income_stmt_id, report_id, utility_id, 'income_statement',
                fiscal_year, datetime(fiscal_year-1, 7, 1), datetime(fiscal_year, 6, 30),
                'enterprise_fund', 'sample_data'
            ))

            # Create balance sheet
            balance_stmt_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO financial_statements (
                    statement_id, report_id, utility_id, statement_type,
                    fiscal_year, period_start_date, period_end_date,
                    fund_type, extraction_method
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                balance_stmt_id, report_id, utility_id, 'balance_sheet',
                fiscal_year, datetime(fiscal_year-1, 7, 1), datetime(fiscal_year, 6, 30),
                'enterprise_fund', 'sample_data'
            ))

            # Generate line items for income statement
            self._generate_income_statement_items(income_stmt_id, utility_id, fiscal_year, year_revenue, year_expenses)

            # Generate line items for balance sheet
            self._generate_balance_sheet_items(balance_stmt_id, utility_id, fiscal_year, year_revenue)

        self.conn.commit()
        cursor.close()

        logger.info(f"✓ Generated {years} years of financial data")

    def _generate_income_statement_items(self, statement_id, utility_id, fiscal_year, revenue, expenses):
        """Generate income statement line items"""
        cursor = self.conn.cursor()

        # Get standardized accounts
        cursor.execute("""
            SELECT account_id, account_code, account_name, account_category
            FROM standardized_accounts
            WHERE statement_type = 'income_statement'
        """)
        accounts = cursor.fetchall()

        revenue_accounts = [a for a in accounts if a[3] == 'revenue']
        expense_accounts = [a for a in accounts if a[3] == 'expense']

        # Allocate revenue
        water_sales = revenue * random.uniform(0.70, 0.80)
        sewer_sales = revenue * random.uniform(0.15, 0.20)
        other_revenue = revenue - water_sales - sewer_sales

        revenue_items = [
            ('REV-001', 'Operating Revenue - Water Sales', water_sales),
            ('REV-002', 'Operating Revenue - Sewer Service', sewer_sales),
            ('REV-004', 'Non-Operating Revenue', other_revenue),
        ]

        for code, name, amount in revenue_items:
            account_id = next((a[0] for a in revenue_accounts if a[1] == code), None)
            if account_id:
                cursor.execute("""
                    INSERT INTO line_items (
                        line_item_id, statement_id, utility_id, fiscal_year,
                        line_item_name, line_item_category, amount,
                        standardized_account_id, standardized_account_name,
                        account_code, confidence_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    str(uuid.uuid4()), statement_id, utility_id, fiscal_year,
                    name, 'revenue', amount,
                    account_id, name, code, 1.0
                ))

        # Allocate expenses
        personnel = expenses * random.uniform(0.35, 0.45)
        utilities = expenses * random.uniform(0.15, 0.25)
        depreciation = expenses * random.uniform(0.15, 0.20)
        other_expenses = expenses - personnel - utilities - depreciation

        expense_items = [
            ('EXP-001', 'Personnel Services', personnel),
            ('EXP-003', 'Utilities and Fuel', utilities),
            ('EXP-005', 'Depreciation and Amortization', depreciation),
            ('EXP-002', 'Contractual Services', other_expenses * 0.5),
            ('EXP-004', 'Repairs and Maintenance', other_expenses * 0.5),
        ]

        for code, name, amount in expense_items:
            account_id = next((a[0] for a in expense_accounts if a[1] == code), None)
            if account_id:
                cursor.execute("""
                    INSERT INTO line_items (
                        line_item_id, statement_id, utility_id, fiscal_year,
                        line_item_name, line_item_category, amount,
                        standardized_account_id, standardized_account_name,
                        account_code, confidence_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    str(uuid.uuid4()), statement_id, utility_id, fiscal_year,
                    name, 'expense', amount,
                    account_id, name, code, 1.0
                ))

    def _generate_balance_sheet_items(self, statement_id, utility_id, fiscal_year, revenue):
        """Generate balance sheet line items"""
        cursor = self.conn.cursor()

        # Get standardized accounts
        cursor.execute("""
            SELECT account_id, account_code, account_name, account_category
            FROM standardized_accounts
            WHERE statement_type = 'balance_sheet'
        """)
        accounts = cursor.fetchall()

        # Typical water utility balance sheet (multiples of revenue)
        total_assets = revenue * random.uniform(8, 12)  # 8-12x revenue in assets

        # Assets
        cash = total_assets * random.uniform(0.05, 0.10)
        receivables = revenue * random.uniform(0.08, 0.12)  # ~1 month revenue
        infrastructure = total_assets * random.uniform(0.75, 0.85)

        asset_items = [
            ('AST-001', 'Cash and Cash Equivalents', cash, 'asset'),
            ('AST-003', 'Accounts Receivable', receivables, 'asset'),
            ('AST-004', 'Capital Assets - Infrastructure', infrastructure, 'asset'),
        ]

        # Liabilities
        total_liabilities = total_assets * random.uniform(0.45, 0.55)
        bonds = total_liabilities * random.uniform(0.75, 0.85)
        current_liab = total_liabilities - bonds

        liability_items = [
            ('LIA-001', 'Accounts Payable', current_liab, 'liability'),
            ('LIA-004', 'Bonds Payable', bonds, 'liability'),
        ]

        # Equity/Net Position
        total_equity = total_assets - total_liabilities

        equity_items = [
            ('EQT-001', 'Net Investment in Capital Assets', total_equity * 0.7, 'equity'),
            ('EQT-003', 'Unrestricted Net Position', total_equity * 0.3, 'equity'),
        ]

        all_items = asset_items + liability_items + equity_items

        for code, name, amount, category in all_items:
            account_id = next((a[0] for a in accounts if a[1] == code), None)
            if account_id:
                cursor.execute("""
                    INSERT INTO line_items (
                        line_item_id, statement_id, utility_id, fiscal_year,
                        line_item_name, line_item_category, amount,
                        standardized_account_id, standardized_account_name,
                        account_code, confidence_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    str(uuid.uuid4()), statement_id, utility_id, fiscal_year,
                    name, category, amount,
                    account_id, name, code, 1.0
                ))

    def generate_complete_dataset(self, utility_count: int = 10, years: int = 10):
        """Generate complete test dataset"""
        logger.info(f"Generating test dataset: {utility_count} utilities × {years} years")

        # Generate utilities
        utilities = self.generate_sample_utilities(utility_count)

        # Generate financial data for each
        for i, utility in enumerate(utilities, 1):
            logger.info(f"Generating data for utility {i}/{utility_count}: {utility['name']}")
            self.generate_financial_data(utility['utility_id'], years)

        logger.info("✓ Complete test dataset generated")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print dataset summary"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM utilities")
        util_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM financial_reports")
        report_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM line_items")
        item_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT MIN(fiscal_year), MAX(fiscal_year)
            FROM financial_reports
        """)
        year_range = cursor.fetchone()

        print("\n" + "="*60)
        print("TEST DATASET SUMMARY")
        print("="*60)
        print(f"Utilities: {util_count}")
        print(f"Financial Reports: {report_count}")
        print(f"Line Items: {item_count}")
        print(f"Year Range: {year_range[0]} - {year_range[1]}")
        print("="*60)

        cursor.close()


def main():
    """Generate sample data for testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate sample data for testing')
    parser.add_argument('--utilities', type=int, default=10, help='Number of utilities to generate')
    parser.add_argument('--years', type=int, default=10, help='Number of years of data per utility')
    parser.add_argument('--reset', action='store_true', help='Reset database before generating')

    args = parser.parse_args()

    config = DatabaseConfig()

    if args.reset:
        from database.db_setup import reset_database
        print("⚠️  Resetting database...")
        reset_database(config)

    conn = get_connection(config)
    generator = SampleDataGenerator(conn)

    generator.generate_complete_dataset(args.utilities, args.years)

    conn.close()


if __name__ == '__main__':
    main()
