"""
Financial Analysis Module
Analyzes utility financial data for trends, comparisons, and key metrics
"""

import psycopg2
from typing import List, Dict, Optional
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialAnalyzer:
    """Analyze financial data for water utilities"""

    def __init__(self, db_connection):
        """
        Initialize analyzer with database connection

        Args:
            db_connection: psycopg2 connection object
        """
        self.conn = db_connection

    def get_utility_summary(self, utility_id: str) -> Dict:
        """
        Get financial summary for a utility

        Args:
            utility_id: UUID of utility

        Returns:
            Dictionary with summary statistics
        """
        cursor = self.conn.cursor()

        # Get utility info
        cursor.execute("""
            SELECT name, state_code, utility_type, population_served
            FROM utilities
            WHERE utility_id = %s
        """, (utility_id,))

        utility_info = cursor.fetchone()

        if not utility_info:
            return {}

        # Get financial data
        cursor.execute("""
            SELECT
                fiscal_year,
                SUM(CASE WHEN line_item_category = 'revenue' THEN amount ELSE 0 END) as total_revenue,
                SUM(CASE WHEN line_item_category = 'expense' THEN amount ELSE 0 END) as total_expenses,
                SUM(CASE WHEN line_item_category = 'asset' THEN amount ELSE 0 END) as total_assets,
                SUM(CASE WHEN line_item_category = 'liability' THEN amount ELSE 0 END) as total_liabilities
            FROM line_items
            WHERE utility_id = %s
            GROUP BY fiscal_year
            ORDER BY fiscal_year DESC
        """, (utility_id,))

        financials = cursor.fetchall()

        cursor.close()

        return {
            'utility_name': utility_info[0],
            'state': utility_info[1],
            'utility_type': utility_info[2],
            'population_served': utility_info[3],
            'financials': [
                {
                    'fiscal_year': row[0],
                    'total_revenue': float(row[1]) if row[1] else 0,
                    'total_expenses': float(row[2]) if row[2] else 0,
                    'total_assets': float(row[3]) if row[3] else 0,
                    'total_liabilities': float(row[4]) if row[4] else 0,
                    'operating_margin': float((row[1] - row[2]) / row[1] * 100) if row[1] and row[1] != 0 else 0,
                    'debt_to_assets': float(row[4] / row[3] * 100) if row[3] and row[3] != 0 else 0,
                }
                for row in financials
            ]
        }

    def get_revenue_trends(self, utility_id: str, years: int = 10) -> pd.DataFrame:
        """
        Get revenue trends over time

        Args:
            utility_id: UUID of utility
            years: Number of years to analyze

        Returns:
            DataFrame with revenue trends
        """
        query = """
            SELECT
                fiscal_year,
                standardized_account_name,
                SUM(amount) as total_amount
            FROM line_items
            WHERE utility_id = %s
                AND line_item_category = 'revenue'
                AND fiscal_year >= (SELECT MAX(fiscal_year) FROM line_items WHERE utility_id = %s) - %s
            GROUP BY fiscal_year, standardized_account_name
            ORDER BY fiscal_year, standardized_account_name
        """

        return pd.read_sql_query(query, self.conn, params=(utility_id, utility_id, years))

    def calculate_key_metrics(self, utility_id: str, fiscal_year: int) -> Dict:
        """
        Calculate key financial metrics for a utility

        Args:
            utility_id: UUID of utility
            fiscal_year: Fiscal year

        Returns:
            Dictionary with calculated metrics
        """
        cursor = self.conn.cursor()

        # Get line items for this year
        cursor.execute("""
            SELECT line_item_category, SUM(amount) as total
            FROM line_items
            WHERE utility_id = %s AND fiscal_year = %s
            GROUP BY line_item_category
        """, (utility_id, fiscal_year))

        totals = {row[0]: float(row[1]) for row in cursor.fetchall()}

        # Calculate metrics
        revenue = totals.get('revenue', 0)
        expenses = totals.get('expense', 0)
        assets = totals.get('asset', 0)
        liabilities = totals.get('liability', 0)
        equity = totals.get('equity', 0)

        metrics = {
            'fiscal_year': fiscal_year,
            'total_revenue': revenue,
            'total_expenses': expenses,
            'total_assets': assets,
            'total_liabilities': liabilities,
            'total_equity': equity,
        }

        # Operating Margin
        if revenue > 0:
            metrics['operating_margin'] = (revenue - expenses) / revenue * 100
        else:
            metrics['operating_margin'] = 0

        # Debt to Assets Ratio
        if assets > 0:
            metrics['debt_to_assets_ratio'] = liabilities / assets * 100
        else:
            metrics['debt_to_assets_ratio'] = 0

        # Current Ratio (would need current assets/liabilities)
        # For now, we'll calculate total assets / total liabilities
        if liabilities > 0:
            metrics['asset_to_liability_ratio'] = assets / liabilities
        else:
            metrics['asset_to_liability_ratio'] = 0

        # Revenue per Connection (if available)
        cursor.execute("""
            SELECT connections FROM utilities WHERE utility_id = %s
        """, (utility_id,))

        connections = cursor.fetchone()
        if connections and connections[0] and revenue > 0:
            metrics['revenue_per_connection'] = revenue / connections[0]

        cursor.close()

        return metrics

    def compare_utilities(
        self,
        utility_ids: List[str],
        fiscal_year: int,
        metrics: List[str] = None
    ) -> pd.DataFrame:
        """
        Compare multiple utilities

        Args:
            utility_ids: List of utility UUIDs
            fiscal_year: Year to compare
            metrics: List of metrics to include

        Returns:
            DataFrame with comparison
        """
        if metrics is None:
            metrics = ['total_revenue', 'total_expenses', 'operating_margin', 'debt_to_assets_ratio']

        comparison_data = []

        for utility_id in utility_ids:
            # Get utility name
            cursor = self.conn.cursor()
            cursor.execute("SELECT name, state_code FROM utilities WHERE utility_id = %s", (utility_id,))
            utility_info = cursor.fetchone()
            cursor.close()

            if not utility_info:
                continue

            # Calculate metrics
            utility_metrics = self.calculate_key_metrics(utility_id, fiscal_year)
            utility_metrics['utility_name'] = utility_info[0]
            utility_metrics['state'] = utility_info[1]

            comparison_data.append(utility_metrics)

        return pd.DataFrame(comparison_data)

    def get_peer_comparison(
        self,
        utility_id: str,
        fiscal_year: int,
        peer_count: int = 10
    ) -> pd.DataFrame:
        """
        Compare utility to peers (similar size utilities in same state)

        Args:
            utility_id: UUID of utility
            fiscal_year: Year to compare
            peer_count: Number of peers to include

        Returns:
            DataFrame with peer comparison
        """
        cursor = self.conn.cursor()

        # Get target utility's state and size
        cursor.execute("""
            SELECT state_code, population_served
            FROM utilities
            WHERE utility_id = %s
        """, (utility_id,))

        target = cursor.fetchone()

        if not target:
            return pd.DataFrame()

        state, population = target

        # Find similar utilities
        cursor.execute("""
            SELECT DISTINCT u.utility_id
            FROM utilities u
            JOIN line_items li ON u.utility_id = li.utility_id
            WHERE u.state_code = %s
                AND u.utility_id != %s
                AND li.fiscal_year = %s
                AND u.population_served BETWEEN %s * 0.5 AND %s * 2
            LIMIT %s
        """, (state, utility_id, fiscal_year, population or 100000, population or 100000, peer_count))

        peer_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()

        # Add target utility
        all_ids = [utility_id] + peer_ids

        return self.compare_utilities(all_ids, fiscal_year)

    def calculate_growth_rates(
        self,
        utility_id: str,
        years: int = 5
    ) -> Dict:
        """
        Calculate year-over-year growth rates

        Args:
            utility_id: UUID of utility
            years: Number of years to analyze

        Returns:
            Dictionary with growth rates
        """
        cursor = self.conn.cursor()

        # Get historical data
        cursor.execute("""
            SELECT
                fiscal_year,
                SUM(CASE WHEN line_item_category = 'revenue' THEN amount ELSE 0 END) as revenue,
                SUM(CASE WHEN line_item_category = 'expense' THEN amount ELSE 0 END) as expenses
            FROM line_items
            WHERE utility_id = %s
                AND fiscal_year >= (SELECT MAX(fiscal_year) FROM line_items WHERE utility_id = %s) - %s
            GROUP BY fiscal_year
            ORDER BY fiscal_year
        """, (utility_id, utility_id, years))

        data = cursor.fetchall()
        cursor.close()

        if len(data) < 2:
            return {}

        # Calculate CAGR (Compound Annual Growth Rate)
        def calculate_cagr(start_value, end_value, periods):
            if start_value <= 0 or end_value <= 0:
                return 0
            return (pow(end_value / start_value, 1 / periods) - 1) * 100

        years_count = len(data) - 1
        revenue_cagr = calculate_cagr(data[0][1], data[-1][1], years_count)
        expense_cagr = calculate_cagr(data[0][2], data[-1][2], years_count)

        # Calculate year-over-year changes
        yoy_changes = []
        for i in range(1, len(data)):
            year = data[i][0]
            revenue_growth = ((data[i][1] - data[i-1][1]) / data[i-1][1] * 100) if data[i-1][1] else 0
            expense_growth = ((data[i][2] - data[i-1][2]) / data[i-1][2] * 100) if data[i-1][2] else 0

            yoy_changes.append({
                'fiscal_year': year,
                'revenue_growth': revenue_growth,
                'expense_growth': expense_growth
            })

        return {
            'revenue_cagr': revenue_cagr,
            'expense_cagr': expense_cagr,
            'year_over_year': yoy_changes
        }

    def export_to_excel(
        self,
        utility_id: str,
        output_file: str,
        years: int = 10
    ):
        """
        Export utility financial data to Excel

        Args:
            utility_id: UUID of utility
            output_file: Path to output Excel file
            years: Number of years to export
        """
        try:
            import openpyxl
        except ImportError:
            logger.error("openpyxl not installed. Run: pip install openpyxl")
            return

        # Get summary
        summary = self.get_utility_summary(utility_id)

        # Create Excel writer
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([{
                'Utility Name': summary['utility_name'],
                'State': summary['state'],
                'Type': summary['utility_type'],
                'Population Served': summary['population_served']
            }])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Financials sheet
            financials_df = pd.DataFrame(summary['financials'])
            financials_df.to_excel(writer, sheet_name='Financials', index=False)

            # Revenue trends
            revenue_df = self.get_revenue_trends(utility_id, years)
            revenue_df.to_excel(writer, sheet_name='Revenue Trends', index=False)

            # Growth rates
            growth = self.calculate_growth_rates(utility_id, years)
            if growth:
                growth_df = pd.DataFrame(growth['year_over_year'])
                growth_df.to_excel(writer, sheet_name='Growth Rates', index=False)

        logger.info(f"Exported to {output_file}")


# Example usage
if __name__ == '__main__':
    from database.db_setup import DatabaseConfig, get_connection

    config = DatabaseConfig()

    try:
        conn = get_connection(config)
        analyzer = FinancialAnalyzer(conn)

        print("="*60)
        print("Financial Analysis Module")
        print("="*60)

        # Get first utility for testing
        cursor = conn.cursor()
        cursor.execute("SELECT utility_id, name FROM utilities LIMIT 1")
        result = cursor.fetchone()

        if result:
            utility_id, name = result
            print(f"\nAnalyzing: {name}")
            print(f"Utility ID: {utility_id}")

            # Get summary
            summary = analyzer.get_utility_summary(utility_id)

            if summary.get('financials'):
                print(f"\nFinancial Summary:")
                for year_data in summary['financials'][:3]:
                    print(f"\n  FY {year_data['fiscal_year']}:")
                    print(f"    Revenue: ${year_data['total_revenue']:,.0f}")
                    print(f"    Expenses: ${year_data['total_expenses']:,.0f}")
                    print(f"    Operating Margin: {year_data['operating_margin']:.1f}%")

            # Calculate growth rates
            growth = analyzer.calculate_growth_rates(utility_id)

            if growth:
                print(f"\n  Revenue CAGR: {growth['revenue_cagr']:.2f}%")
                print(f"  Expense CAGR: {growth['expense_cagr']:.2f}%")

        else:
            print("\nNo utilities found in database")
            print("Run the data collection pipeline first")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\nMake sure PostgreSQL is running and database is initialized")
        print("Run: python database/db_setup.py init")
