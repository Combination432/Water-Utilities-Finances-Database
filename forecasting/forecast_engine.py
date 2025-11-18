"""
Financial Forecasting Engine
Creates 3-statement projections with customizable assumptions
"""

import psycopg2
from typing import Dict, List, Optional
from datetime import datetime
import json
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForecastEngine:
    """Generate financial forecasts for water utilities"""

    def __init__(self, db_connection):
        """
        Initialize forecast engine

        Args:
            db_connection: psycopg2 connection object
        """
        self.conn = db_connection

    def create_forecast(
        self,
        utility_id: str,
        forecast_name: str,
        base_year: int,
        forecast_years: int = 5,
        assumptions: Optional[Dict] = None
    ) -> str:
        """
        Create a new forecast scenario

        Args:
            utility_id: UUID of utility
            forecast_name: Name for this forecast
            base_year: Last historical year to base forecast on
            forecast_years: Number of years to forecast
            assumptions: Dictionary of forecast assumptions

        Returns:
            UUID of created forecast
        """
        if assumptions is None:
            assumptions = self._get_default_assumptions()

        forecast_id = str(uuid.uuid4())
        cursor = self.conn.cursor()

        try:
            # Create forecast record
            cursor.execute("""
                INSERT INTO forecasts (
                    forecast_id,
                    utility_id,
                    forecast_name,
                    forecast_type,
                    base_year,
                    forecast_start_year,
                    forecast_end_year,
                    assumptions,
                    model_version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                forecast_id,
                utility_id,
                forecast_name,
                assumptions.get('forecast_type', 'base_case'),
                base_year,
                base_year + 1,
                base_year + forecast_years,
                json.dumps(assumptions),
                'v1.0'
            ))

            self.conn.commit()
            logger.info(f"Created forecast: {forecast_id}")

            # Generate projections
            self._generate_projections(forecast_id, utility_id, base_year, forecast_years, assumptions)

            return forecast_id

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating forecast: {e}")
            raise

        finally:
            cursor.close()

    def _get_default_assumptions(self) -> Dict:
        """Get default forecast assumptions"""
        return {
            'forecast_type': 'base_case',
            'revenue_growth_rate': 0.025,  # 2.5% annual growth
            'expense_inflation_rate': 0.03,  # 3% annual inflation
            'depreciation_pct_of_assets': 0.03,  # 3% of capital assets
            'capex_pct_of_revenue': 0.15,  # 15% of revenue for capital expenditures
            'debt_service_coverage_target': 1.25,  # Target debt service coverage ratio
            'working_capital_days': 60,  # Days of working capital to maintain
        }

    def _generate_projections(
        self,
        forecast_id: str,
        utility_id: str,
        base_year: int,
        forecast_years: int,
        assumptions: Dict
    ):
        """
        Generate line item projections

        Args:
            forecast_id: UUID of forecast
            utility_id: UUID of utility
            base_year: Base year for forecast
            forecast_years: Number of years to project
            assumptions: Forecast assumptions
        """
        cursor = self.conn.cursor()

        # Get base year data
        cursor.execute("""
            SELECT
                standardized_account_id,
                standardized_account_name,
                line_item_category,
                SUM(amount) as base_amount
            FROM line_items
            WHERE utility_id = %s
                AND fiscal_year = %s
                AND standardized_account_id IS NOT NULL
            GROUP BY standardized_account_id, standardized_account_name, line_item_category
        """, (utility_id, base_year))

        base_data = cursor.fetchall()

        if not base_data:
            logger.warning(f"No base year data found for {base_year}")
            return

        # Project each account for each year
        for year_offset in range(1, forecast_years + 1):
            forecast_year = base_year + year_offset

            for account_id, account_name, category, base_amount in base_data:
                projected_amount = self._project_line_item(
                    category,
                    account_name,
                    base_amount,
                    year_offset,
                    assumptions
                )

                # Insert projection
                cursor.execute("""
                    INSERT INTO forecast_line_items (
                        forecast_line_item_id,
                        forecast_id,
                        fiscal_year,
                        standardized_account_id,
                        line_item_category,
                        projected_amount,
                        calculation_method,
                        calculation_inputs
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(uuid.uuid4()),
                    forecast_id,
                    forecast_year,
                    account_id,
                    category,
                    projected_amount,
                    self._get_calculation_method(category, account_name),
                    json.dumps({
                        'base_amount': float(base_amount),
                        'year_offset': year_offset,
                        'assumptions_used': assumptions
                    })
                ))

        self.conn.commit()
        cursor.close()

        logger.info(f"Generated projections for {forecast_years} years")

    def _project_line_item(
        self,
        category: str,
        account_name: str,
        base_amount: float,
        year_offset: int,
        assumptions: Dict
    ) -> float:
        """
        Project a single line item

        Args:
            category: Line item category
            account_name: Account name
            base_amount: Base year amount
            year_offset: Years from base year
            assumptions: Forecast assumptions

        Returns:
            Projected amount
        """
        # Revenue projections
        if category == 'revenue':
            growth_rate = assumptions.get('revenue_growth_rate', 0.025)
            return base_amount * pow(1 + growth_rate, year_offset)

        # Expense projections
        elif category == 'expense':
            # Depreciation is handled separately
            if 'depreciation' in account_name.lower():
                # Project based on capital assets growth
                return base_amount * pow(1 + assumptions.get('revenue_growth_rate', 0.025), year_offset)
            else:
                # Regular expenses grow with inflation
                inflation_rate = assumptions.get('expense_inflation_rate', 0.03)
                return base_amount * pow(1 + inflation_rate, year_offset)

        # Asset projections
        elif category == 'asset':
            if 'capital' in account_name.lower() or 'infrastructure' in account_name.lower():
                # Capital assets grow with CapEx
                capex_rate = assumptions.get('capex_pct_of_revenue', 0.15)
                growth_rate = assumptions.get('revenue_growth_rate', 0.025)
                # Simplified: assets grow at revenue growth rate
                return base_amount * pow(1 + growth_rate, year_offset)
            else:
                # Current assets grow with revenue
                growth_rate = assumptions.get('revenue_growth_rate', 0.025)
                return base_amount * pow(1 + growth_rate, year_offset)

        # Liability projections
        elif category == 'liability':
            # Debt stays relatively stable (simplified assumption)
            # In reality, would model debt service and new issuances
            return base_amount

        # Equity/Net Position
        elif category == 'equity':
            # Grows with retained earnings
            return base_amount * pow(1 + assumptions.get('revenue_growth_rate', 0.025) * 0.5, year_offset)

        # Default: no growth
        return base_amount

    def _get_calculation_method(self, category: str, account_name: str) -> str:
        """Get calculation method description"""
        if category == 'revenue':
            return 'growth_rate'
        elif category == 'expense':
            if 'depreciation' in account_name.lower():
                return 'percentage_of_assets'
            return 'inflation_rate'
        elif category == 'asset':
            return 'growth_rate'
        elif category == 'liability':
            return 'fixed'
        elif category == 'equity':
            return 'retained_earnings'
        return 'fixed'

    def get_forecast_summary(self, forecast_id: str) -> Dict:
        """
        Get summary of forecast projections

        Args:
            forecast_id: UUID of forecast

        Returns:
            Dictionary with forecast summary
        """
        cursor = self.conn.cursor()

        # Get forecast metadata
        cursor.execute("""
            SELECT
                f.forecast_name,
                f.forecast_type,
                f.base_year,
                f.forecast_start_year,
                f.forecast_end_year,
                f.assumptions,
                u.name as utility_name
            FROM forecasts f
            JOIN utilities u ON f.utility_id = u.utility_id
            WHERE f.forecast_id = %s
        """, (forecast_id,))

        metadata = cursor.fetchone()

        if not metadata:
            return {}

        # Get projected financials by year
        cursor.execute("""
            SELECT
                fiscal_year,
                SUM(CASE WHEN line_item_category = 'revenue' THEN projected_amount ELSE 0 END) as revenue,
                SUM(CASE WHEN line_item_category = 'expense' THEN projected_amount ELSE 0 END) as expenses,
                SUM(CASE WHEN line_item_category = 'asset' THEN projected_amount ELSE 0 END) as assets,
                SUM(CASE WHEN line_item_category = 'liability' THEN projected_amount ELSE 0 END) as liabilities
            FROM forecast_line_items
            WHERE forecast_id = %s
            GROUP BY fiscal_year
            ORDER BY fiscal_year
        """, (forecast_id,))

        projections = cursor.fetchall()
        cursor.close()

        return {
            'forecast_id': forecast_id,
            'forecast_name': metadata[0],
            'forecast_type': metadata[1],
            'base_year': metadata[2],
            'forecast_start_year': metadata[3],
            'forecast_end_year': metadata[4],
            'assumptions': metadata[5],
            'utility_name': metadata[6],
            'projections': [
                {
                    'fiscal_year': row[0],
                    'revenue': float(row[1]),
                    'expenses': float(row[2]),
                    'assets': float(row[3]),
                    'liabilities': float(row[4]),
                    'operating_income': float(row[1] - row[2]),
                    'operating_margin': float((row[1] - row[2]) / row[1] * 100) if row[1] else 0,
                }
                for row in projections
            ]
        }

    def create_scenario_comparison(
        self,
        utility_id: str,
        base_year: int,
        forecast_years: int = 5
    ) -> Dict[str, str]:
        """
        Create multiple forecast scenarios for comparison

        Args:
            utility_id: UUID of utility
            base_year: Base year
            forecast_years: Years to forecast

        Returns:
            Dictionary mapping scenario name to forecast_id
        """
        scenarios = {
            'Base Case': {
                'revenue_growth_rate': 0.025,
                'expense_inflation_rate': 0.03,
            },
            'Optimistic': {
                'revenue_growth_rate': 0.04,
                'expense_inflation_rate': 0.025,
            },
            'Pessimistic': {
                'revenue_growth_rate': 0.01,
                'expense_inflation_rate': 0.04,
            }
        }

        forecast_ids = {}

        for scenario_name, assumptions in scenarios.items():
            full_assumptions = self._get_default_assumptions()
            full_assumptions.update(assumptions)
            full_assumptions['forecast_type'] = scenario_name.lower().replace(' ', '_')

            forecast_id = self.create_forecast(
                utility_id,
                scenario_name,
                base_year,
                forecast_years,
                full_assumptions
            )

            forecast_ids[scenario_name] = forecast_id

        return forecast_ids

    def export_forecast_to_excel(self, forecast_id: str, output_file: str):
        """
        Export forecast to Excel file

        Args:
            forecast_id: UUID of forecast
            output_file: Path to output file
        """
        try:
            import pandas as pd
            import openpyxl
        except ImportError:
            logger.error("pandas or openpyxl not installed")
            return

        summary = self.get_forecast_summary(forecast_id)

        if not summary:
            logger.error(f"Forecast {forecast_id} not found")
            return

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([{
                'Forecast Name': summary['forecast_name'],
                'Utility': summary['utility_name'],
                'Base Year': summary['base_year'],
                'Forecast Period': f"{summary['forecast_start_year']}-{summary['forecast_end_year']}"
            }])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Projections sheet
            proj_df = pd.DataFrame(summary['projections'])
            proj_df.to_excel(writer, sheet_name='Projections', index=False)

            # Assumptions sheet
            assumptions = summary['assumptions']
            if isinstance(assumptions, str):
                assumptions = json.loads(assumptions)

            assumptions_df = pd.DataFrame([
                {'Parameter': k, 'Value': v}
                for k, v in assumptions.items()
            ])
            assumptions_df.to_excel(writer, sheet_name='Assumptions', index=False)

        logger.info(f"Exported forecast to {output_file}")


# Example usage
if __name__ == '__main__':
    from database.db_setup import DatabaseConfig, get_connection

    config = DatabaseConfig()

    try:
        conn = get_connection(config)
        engine = ForecastEngine(conn)

        print("="*60)
        print("Financial Forecasting Engine")
        print("="*60)

        # Get first utility for testing
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.utility_id, u.name, MAX(li.fiscal_year) as latest_year
            FROM utilities u
            JOIN line_items li ON u.utility_id = li.utility_id
            GROUP BY u.utility_id, u.name
            LIMIT 1
        """)

        result = cursor.fetchone()

        if result:
            utility_id, name, latest_year = result

            print(f"\nCreating forecast for: {name}")
            print(f"Base Year: {latest_year}")

            # Create scenario comparison
            print("\nGenerating scenario forecasts...")
            scenarios = engine.create_scenario_comparison(
                utility_id,
                latest_year,
                forecast_years=5
            )

            print(f"\nCreated {len(scenarios)} scenarios:")
            for scenario_name, forecast_id in scenarios.items():
                print(f"  - {scenario_name}: {forecast_id}")

                # Get summary
                summary = engine.get_forecast_summary(forecast_id)

                print(f"\n    {scenario_name} Projections:")
                for proj in summary['projections'][:3]:
                    print(f"      FY{proj['fiscal_year']}: "
                          f"Revenue=${proj['revenue']:,.0f}, "
                          f"Margin={proj['operating_margin']:.1f}%")

        else:
            print("\nNo utilities with financial data found")
            print("Run the data collection pipeline first")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\nMake sure database is initialized with financial data")
