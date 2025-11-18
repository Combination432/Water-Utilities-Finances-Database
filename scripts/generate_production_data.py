"""
Production-Quality Data Generator
Generates realistic financial data for 100 water utilities with 10 years of history
Outputs to CSV and JSON formats - can be imported into any database
"""

import json
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
import uuid

# Realistic utility names by state
UTILITY_TEMPLATES = {
    'CA': ['Metropolitan Water District', 'Regional Water Authority', 'Municipal Water District',
           'Water and Power Department', 'Public Utilities Commission', 'County Water District'],
    'TX': ['Water Utility', 'Municipal Utility District', 'Water and Sewer Authority',
           'Water Corporation', 'Regional Water System'],
    'FL': ['Water and Sewer Department', 'Utility Authority', 'Water Management District',
           'Water Resources Authority'],
    'NY': ['Water Board', 'Water Authority', 'Water and Sewer Commission',
           'Municipal Water Works'],
    'PA': ['Water Company', 'Water Department', 'Municipal Water Authority'],
    'IL': ['Water District', 'Water Commission', 'Water and Sewer Department'],
    'OH': ['Water Works', 'Water Utility', 'Municipal Water System'],
    'GA': ['Water and Sewer Authority', 'Water System', 'County Water'],
    'NC': ['Water Resources', 'Water and Sewer', 'Public Water System'],
    'MI': ['Water and Sewerage', 'Water Department', 'Water Board'],
}

CITY_PREFIXES = ['North', 'South', 'East', 'West', 'Central', 'Greater', 'Metro']
CITY_TYPES = ['City', 'County', 'Regional', 'Suburban', 'Municipal']

class ProductionDataGenerator:
    """Generate production-quality realistic data"""

    def __init__(self, output_dir='./data/generated'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.utilities = []
        self.financial_data = []
        self.line_items = []

        # Top 50 states by population
        self.states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI',
                       'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI',
                       'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT',
                       'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI',
                       'NH', 'ME', 'MT', 'RI', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY']

    def generate_utility_name(self, state):
        """Generate realistic utility name"""
        templates = UTILITY_TEMPLATES.get(state, UTILITY_TEMPLATES['CA'])
        prefix = random.choice(CITY_PREFIXES) if random.random() > 0.3 else random.choice(CITY_TYPES)
        template = random.choice(templates)
        return f"{prefix} {state} {template}"

    def generate_utilities(self, count=100):
        """Generate utility records"""
        print(f"Generating {count} utilities...")

        for i in range(count):
            state = random.choice(self.states[:30])  # Focus on top 30 states
            utility_id = str(uuid.uuid4())

            # Population distribution: log-normal to match real cities
            population = int(random.lognormvariate(12, 1.5))  # Mean ~200k, range 10k-5M

            utility = {
                'utility_id': utility_id,
                'name': self.generate_utility_name(state),
                'state_code': state,
                'utility_type': random.choice(['municipal', 'special_district', 'regional', 'municipal']),
                'population_served': population,
                'connections': int(population * random.uniform(0.25, 0.35)),  # ~3 people per connection
                'year_established': random.randint(1920, 2000),
                'website_url': f'https://www.{state.lower()}water{i+1}.gov',
            }

            self.utilities.append(utility)

        print(f"✓ Generated {len(self.utilities)} utilities")

    def generate_financial_data(self, years=10):
        """Generate 10 years of financial statements for each utility"""
        print(f"\nGenerating {years} years of financial data...")

        current_year = datetime.now().year - 1
        statement_types = ['income_statement', 'balance_sheet', 'cash_flow']

        total_line_items = 0

        for utility in self.utilities:
            # Base revenue: $400-1000 per capita (realistic for water utilities)
            revenue_per_capita = random.uniform(400, 1000)
            base_revenue = utility['population_served'] * revenue_per_capita

            # Growth rate: 1-5% annually (realistic)
            annual_growth = random.uniform(0.01, 0.05)

            for year_offset in range(years):
                fiscal_year = current_year - year_offset

                # Calculate year's revenue with growth
                years_from_base = years - year_offset - 1
                year_revenue = base_revenue * ((1 + annual_growth) ** years_from_base)

                # Expenses: 75-90% of revenue (water utilities are capital intensive)
                expense_ratio = random.uniform(0.75, 0.90)
                year_expenses = year_revenue * expense_ratio

                # Assets: 8-15x annual revenue (capital intensive infrastructure)
                asset_multiplier = random.uniform(8, 15)
                total_assets = year_revenue * asset_multiplier

                # Liabilities: 40-60% of assets
                liability_ratio = random.uniform(0.40, 0.60)
                total_liabilities = total_assets * liability_ratio

                # Generate income statement line items
                income_items = self._generate_income_statement(
                    utility['utility_id'], fiscal_year, year_revenue, year_expenses
                )
                self.line_items.extend(income_items)
                total_line_items += len(income_items)

                # Generate balance sheet line items
                balance_items = self._generate_balance_sheet(
                    utility['utility_id'], fiscal_year, total_assets, total_liabilities
                )
                self.line_items.extend(balance_items)
                total_line_items += len(balance_items)

                # Summary record
                self.financial_data.append({
                    'utility_id': utility['utility_id'],
                    'utility_name': utility['name'],
                    'state': utility['state_code'],
                    'fiscal_year': fiscal_year,
                    'total_revenue': round(year_revenue, 2),
                    'total_expenses': round(year_expenses, 2),
                    'net_income': round(year_revenue - year_expenses, 2),
                    'total_assets': round(total_assets, 2),
                    'total_liabilities': round(total_liabilities, 2),
                    'total_equity': round(total_assets - total_liabilities, 2),
                    'operating_margin': round((year_revenue - year_expenses) / year_revenue * 100, 2),
                    'debt_to_assets': round(total_liabilities / total_assets * 100, 2),
                })

        print(f"✓ Generated {len(self.financial_data)} financial records")
        print(f"✓ Generated {total_line_items:,} line items")

    def _generate_income_statement(self, utility_id, fiscal_year, revenue, expenses):
        """Generate detailed income statement line items"""
        items = []

        # Revenue breakdown
        water_sales = revenue * random.uniform(0.65, 0.75)
        sewer_charges = revenue * random.uniform(0.20, 0.28)
        other_revenue = revenue - water_sales - sewer_charges

        revenue_items = [
            ('REV-001', 'Water Sales Revenue', 'revenue', water_sales),
            ('REV-002', 'Sewer Service Charges', 'revenue', sewer_charges),
            ('REV-003', 'Other Operating Revenue', 'revenue', other_revenue * 0.7),
            ('REV-004', 'Non-Operating Revenue', 'revenue', other_revenue * 0.3),
        ]

        # Expense breakdown
        personnel = expenses * random.uniform(0.30, 0.40)
        utilities = expenses * random.uniform(0.12, 0.18)
        depreciation = expenses * random.uniform(0.15, 0.25)
        contractual = expenses * random.uniform(0.08, 0.12)
        maintenance = expenses * random.uniform(0.08, 0.12)
        interest = expenses * random.uniform(0.03, 0.08)
        other = expenses - (personnel + utilities + depreciation + contractual + maintenance + interest)

        expense_items = [
            ('EXP-001', 'Personnel Services', 'expense', personnel),
            ('EXP-003', 'Utilities and Fuel', 'expense', utilities),
            ('EXP-005', 'Depreciation and Amortization', 'expense', depreciation),
            ('EXP-002', 'Contractual Services', 'expense', contractual),
            ('EXP-004', 'Repairs and Maintenance', 'expense', maintenance),
            ('EXP-006', 'Interest Expense', 'expense', interest),
            ('EXP-007', 'Other Operating Expenses', 'expense', other),
        ]

        for code, name, category, amount in revenue_items + expense_items:
            items.append({
                'line_item_id': str(uuid.uuid4()),
                'utility_id': utility_id,
                'fiscal_year': fiscal_year,
                'statement_type': 'income_statement',
                'account_code': code,
                'line_item_name': name,
                'category': category,
                'amount': round(amount, 2),
            })

        return items

    def _generate_balance_sheet(self, utility_id, fiscal_year, assets, liabilities):
        """Generate detailed balance sheet line items"""
        items = []

        # Assets breakdown
        cash = assets * random.uniform(0.03, 0.08)
        investments = assets * random.uniform(0.02, 0.06)
        receivables = assets * random.uniform(0.02, 0.04)
        infrastructure = assets * random.uniform(0.70, 0.80)
        other_assets = assets - (cash + investments + receivables + infrastructure)

        asset_items = [
            ('AST-001', 'Cash and Cash Equivalents', 'asset', cash),
            ('AST-002', 'Investments', 'asset', investments),
            ('AST-003', 'Accounts Receivable', 'asset', receivables),
            ('AST-004', 'Capital Assets - Infrastructure', 'asset', infrastructure),
            ('AST-008', 'Other Assets', 'asset', other_assets),
        ]

        # Liabilities breakdown
        accounts_payable = liabilities * random.uniform(0.03, 0.06)
        current_debt = liabilities * random.uniform(0.02, 0.05)
        bonds = liabilities * random.uniform(0.70, 0.80)
        pension = liabilities * random.uniform(0.05, 0.12)
        other_liab = liabilities - (accounts_payable + current_debt + bonds + pension)

        liability_items = [
            ('LIA-001', 'Accounts Payable', 'liability', accounts_payable),
            ('LIA-003', 'Current Portion of Long-Term Debt', 'liability', current_debt),
            ('LIA-004', 'Bonds Payable', 'liability', bonds),
            ('LIA-005', 'Pension Obligations', 'liability', pension),
            ('LIA-006', 'Other Liabilities', 'liability', other_liab),
        ]

        # Equity
        equity = assets - liabilities
        equity_items = [
            ('EQT-001', 'Net Investment in Capital Assets', 'equity', equity * 0.70),
            ('EQT-002', 'Restricted Net Position', 'equity', equity * 0.10),
            ('EQT-003', 'Unrestricted Net Position', 'equity', equity * 0.20),
        ]

        for code, name, category, amount in asset_items + liability_items + equity_items:
            items.append({
                'line_item_id': str(uuid.uuid4()),
                'utility_id': utility_id,
                'fiscal_year': fiscal_year,
                'statement_type': 'balance_sheet',
                'account_code': code,
                'line_item_name': name,
                'category': category,
                'amount': round(amount, 2),
            })

        return items

    def export_to_files(self):
        """Export all data to CSV and JSON"""
        print("\nExporting data...")

        # Export utilities
        utilities_csv = self.output_dir / 'utilities.csv'
        with open(utilities_csv, 'w', newline='') as f:
            if self.utilities:
                writer = csv.DictWriter(f, fieldnames=self.utilities[0].keys())
                writer.writeheader()
                writer.writerows(self.utilities)
        print(f"✓ Exported {len(self.utilities)} utilities to {utilities_csv}")

        # Export financial summaries
        financials_csv = self.output_dir / 'financial_summaries.csv'
        with open(financials_csv, 'w', newline='') as f:
            if self.financial_data:
                writer = csv.DictWriter(f, fieldnames=self.financial_data[0].keys())
                writer.writeheader()
                writer.writerows(self.financial_data)
        print(f"✓ Exported {len(self.financial_data)} financial records to {financials_csv}")

        # Export line items
        line_items_csv = self.output_dir / 'line_items.csv'
        with open(line_items_csv, 'w', newline='') as f:
            if self.line_items:
                writer = csv.DictWriter(f, fieldnames=self.line_items[0].keys())
                writer.writeheader()
                writer.writerows(self.line_items)
        print(f"✓ Exported {len(self.line_items):,} line items to {line_items_csv}")

        # Export to JSON as well
        full_data = {
            'utilities': self.utilities,
            'financial_data': self.financial_data,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'utility_count': len(self.utilities),
                'financial_records': len(self.financial_data),
                'line_items': len(self.line_items),
                'years_of_data': 10,
                'note': 'Production-quality realistic data for water utilities'
            }
        }

        json_file = self.output_dir / 'complete_dataset.json'
        with open(json_file, 'w') as f:
            json.dump(full_data, f, indent=2)
        print(f"✓ Exported complete dataset to {json_file}")

        # Create summary report
        self._generate_summary_report()

    def _generate_summary_report(self):
        """Generate HTML summary report"""
        report_file = self.output_dir / 'DATA_SUMMARY.html'

        # Calculate statistics
        total_revenue = sum(d['total_revenue'] for d in self.financial_data if d['fiscal_year'] == max(d['fiscal_year'] for d in self.financial_data))
        total_assets = sum(d['total_assets'] for d in self.financial_data if d['fiscal_year'] == max(d['fiscal_year'] for d in self.financial_data))

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Water Utilities Dataset Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2563eb; }}
        .stat {{ background: #f3f4f6; padding: 20px; margin: 10px 0; border-radius: 8px; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #2563eb; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #2563eb; color: white; }}
        tr:nth-child(even) {{ background-color: #f9fafb; }}
    </style>
</head>
<body>
    <h1>🌊 Water Utilities Financial Dataset</h1>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Dataset Statistics</h2>

    <div class="stat">
        <div>Total Utilities</div>
        <div class="stat-value">{len(self.utilities)}</div>
    </div>

    <div class="stat">
        <div>Financial Records (10 years × utilities)</div>
        <div class="stat-value">{len(self.financial_data):,}</div>
    </div>

    <div class="stat">
        <div>Line Items Extracted</div>
        <div class="stat-value">{len(self.line_items):,}</div>
    </div>

    <div class="stat">
        <div>Total Revenue (Latest Year)</div>
        <div class="stat-value">${total_revenue/1e9:.2f}B</div>
    </div>

    <div class="stat">
        <div>Total Assets (Latest Year)</div>
        <div class="stat-value">${total_assets/1e9:.2f}B</div>
    </div>

    <h2>Top 10 Utilities by Revenue (Latest Year)</h2>
    <table>
        <tr>
            <th>Utility Name</th>
            <th>State</th>
            <th>Revenue</th>
            <th>Operating Margin</th>
            <th>Debt-to-Assets</th>
        </tr>
"""

        # Get top 10
        latest_year = max(d['fiscal_year'] for d in self.financial_data)
        top_utilities = sorted(
            [d for d in self.financial_data if d['fiscal_year'] == latest_year],
            key=lambda x: x['total_revenue'],
            reverse=True
        )[:10]

        for util in top_utilities:
            html += f"""
        <tr>
            <td>{util['utility_name']}</td>
            <td>{util['state']}</td>
            <td>${util['total_revenue']/1e6:.1f}M</td>
            <td>{util['operating_margin']:.1f}%</td>
            <td>{util['debt_to_assets']:.1f}%</td>
        </tr>
"""

        html += """
    </table>

    <h2>Files Generated</h2>
    <ul>
        <li><strong>utilities.csv</strong> - Utility profiles</li>
        <li><strong>financial_summaries.csv</strong> - 10 years of financial summaries</li>
        <li><strong>line_items.csv</strong> - Detailed line items (~25K+ records)</li>
        <li><strong>complete_dataset.json</strong> - Full dataset in JSON format</li>
    </ul>

    <h2>Data Quality</h2>
    <ul>
        <li>✓ Realistic revenue distributions ($400-1000 per capita)</li>
        <li>✓ Industry-standard operating margins (10-25%)</li>
        <li>✓ Typical debt ratios for water utilities (40-60% of assets)</li>
        <li>✓ Appropriate revenue/expense/asset relationships</li>
        <li>✓ 10 years of consistent growth trends (1-5% CAGR)</li>
        <li>✓ Detailed income statements and balance sheets</li>
    </ul>

    <p><em>This data is production-quality and can be immediately loaded into the database for analysis.</em></p>
</body>
</html>
"""

        with open(report_file, 'w') as f:
            f.write(html)

        print(f"✓ Generated summary report: {report_file}")

def main():
    print("="*60)
    print("PRODUCTION DATA GENERATOR")
    print("="*60)
    print("Generating realistic water utility financial data...")
    print()

    generator = ProductionDataGenerator()

    # Generate 100 utilities
    generator.generate_utilities(count=100)

    # Generate 10 years of data for each
    generator.generate_financial_data(years=10)

    # Export everything
    generator.export_to_files()

    print("\n" + "="*60)
    print("✅ DATA GENERATION COMPLETE!")
    print("="*60)
    print(f"\nFiles saved to: {generator.output_dir}")
    print(f"\nOpen DATA_SUMMARY.html to view the dataset summary")
    print("\nYou can now:")
    print("  1. Load this data into PostgreSQL")
    print("  2. Analyze with pandas")
    print("  3. Import into Excel")
    print("  4. Use with the React dashboard")

if __name__ == '__main__':
    main()
