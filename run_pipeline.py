"""
Main Pipeline Runner
Simple command-line interface to run the complete pipeline
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_setup import DatabaseConfig, get_connection, initialize_schema, create_database
from tests.generate_sample_data import SampleDataGenerator
from tests.run_all_tests import run_all_tests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database():
    """Initialize database"""
    print("\n" + "="*60)
    print("DATABASE SETUP")
    print("="*60)

    config = DatabaseConfig()

    print(f"Host: {config.host}:{config.port}")
    print(f"Database: {config.database}")

    # Create database
    if create_database(config):
        print("✓ Database created/verified")

    # Initialize schema
    if initialize_schema(config):
        print("✓ Schema initialized")

    print("="*60)


def generate_test_data(utilities=10, years=10):
    """Generate sample data"""
    print("\n" + "="*60)
    print("GENERATING TEST DATA")
    print("="*60)

    config = DatabaseConfig()
    conn = get_connection(config)

    generator = SampleDataGenerator(conn)
    generator.generate_complete_dataset(utilities, years)

    conn.close()


def run_tests():
    """Run test suite"""
    print("\n" + "="*60)
    print("RUNNING TESTS")
    print("="*60)

    success = run_all_tests()

    return success


def analyze_utility(utility_name=None):
    """Run analysis on a utility"""
    from analysis.financial_analysis import FinancialAnalyzer

    config = DatabaseConfig()
    conn = get_connection(config)
    analyzer = FinancialAnalyzer(conn)

    cursor = conn.cursor()

    if utility_name:
        cursor.execute("""
            SELECT utility_id, name FROM utilities
            WHERE name ILIKE %s
            LIMIT 1
        """, (f"%{utility_name}%",))
    else:
        cursor.execute("SELECT utility_id, name FROM utilities LIMIT 1")

    result = cursor.fetchone()

    if not result:
        print("No utilities found")
        conn.close()
        return

    utility_id, name = result

    print("\n" + "="*60)
    print(f"ANALYZING: {name}")
    print("="*60)

    # Get summary
    summary = analyzer.get_utility_summary(utility_id)

    if summary.get('financials'):
        print(f"\nUtility: {summary['utility_name']}")
        print(f"State: {summary['state']}")
        print(f"Type: {summary['utility_type']}")
        if summary.get('population_served'):
            print(f"Population Served: {summary['population_served']:,}")

        print("\nFinancial Summary:")

        for year_data in summary['financials'][:5]:
            print(f"\n  FY {year_data['fiscal_year']}:")
            print(f"    Revenue: ${year_data['total_revenue']:,.0f}")
            print(f"    Expenses: ${year_data['total_expenses']:,.0f}")
            print(f"    Operating Margin: {year_data['operating_margin']:.1f}%")
            print(f"    Debt-to-Assets: {year_data['debt_to_assets']:.1f}%")

        # Growth rates
        growth = analyzer.calculate_growth_rates(utility_id)

        if growth:
            print(f"\nGrowth Rates ({len(growth['year_over_year'])} years):")
            print(f"  Revenue CAGR: {growth['revenue_cagr']:.2f}%")
            print(f"  Expense CAGR: {growth['expense_cagr']:.2f}%")

    cursor.close()
    conn.close()


def create_forecast(utility_name=None, years=5):
    """Create financial forecast"""
    from forecasting.forecast_engine import ForecastEngine

    config = DatabaseConfig()
    conn = get_connection(config)
    engine = ForecastEngine(conn)

    cursor = conn.cursor()

    # Get utility with data
    if utility_name:
        cursor.execute("""
            SELECT u.utility_id, u.name, MAX(li.fiscal_year) as latest_year
            FROM utilities u
            JOIN line_items li ON u.utility_id = li.utility_id
            WHERE u.name ILIKE %s
            GROUP BY u.utility_id, u.name
            LIMIT 1
        """, (f"%{utility_name}%",))
    else:
        cursor.execute("""
            SELECT u.utility_id, u.name, MAX(li.fiscal_year) as latest_year
            FROM utilities u
            JOIN line_items li ON u.utility_id = li.utility_id
            GROUP BY u.utility_id, u.name
            LIMIT 1
        """)

    result = cursor.fetchone()

    if not result:
        print("No utilities with financial data found")
        conn.close()
        return

    utility_id, name, latest_year = result

    print("\n" + "="*60)
    print(f"CREATING FORECAST: {name}")
    print("="*60)

    print(f"Base Year: {latest_year}")
    print(f"Forecast Period: {latest_year+1} - {latest_year+years}")

    # Create scenarios
    print("\nGenerating scenario forecasts...")
    scenarios = engine.create_scenario_comparison(
        utility_id=utility_id,
        base_year=latest_year,
        forecast_years=years
    )

    print(f"\n✓ Created {len(scenarios)} scenarios")

    # Show results
    for scenario_name, forecast_id in scenarios.items():
        summary = engine.get_forecast_summary(forecast_id)

        print(f"\n{scenario_name}:")
        for proj in summary['projections']:
            print(f"  FY{proj['fiscal_year']}: "
                  f"Revenue=${proj['revenue']:,.0f}, "
                  f"Margin={proj['operating_margin']:.1f}%")

    cursor.close()
    conn.close()


def list_utilities():
    """List all utilities in database"""
    config = DatabaseConfig()
    conn = get_connection(config)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.name,
            u.state_code,
            u.population_served,
            COUNT(DISTINCT fr.fiscal_year) as years_of_data
        FROM utilities u
        LEFT JOIN financial_reports fr ON u.utility_id = fr.utility_id
        WHERE fr.processing_status = 'completed'
        GROUP BY u.utility_id, u.name, u.state_code, u.population_served
        ORDER BY years_of_data DESC, u.name
    """)

    results = cursor.fetchall()

    print("\n" + "="*60)
    print("UTILITIES IN DATABASE")
    print("="*60)

    print(f"\n{'Utility':<40} {'State':<6} {'Pop.':<12} {'Years':<6}")
    print("-"*60)

    for name, state, pop, years in results:
        pop_str = f"{pop:,}" if pop else "N/A"
        print(f"{name[:38]:<40} {state:<6} {pop_str:<12} {years:<6}")

    print(f"\nTotal: {len(results)} utilities")

    cursor.close()
    conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Water Utilities Financial Analysis Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup database and generate test data
  python run_pipeline.py --setup --generate-data

  # Run tests
  python run_pipeline.py --test

  # List all utilities
  python run_pipeline.py --list

  # Analyze a utility
  python run_pipeline.py --analyze "San Francisco"

  # Create forecast
  python run_pipeline.py --forecast "Los Angeles" --years 5

  # Complete workflow
  python run_pipeline.py --setup --generate-data --test --analyze
        """
    )

    # Setup options
    parser.add_argument('--setup', action='store_true', help='Initialize database')
    parser.add_argument('--generate-data', action='store_true', help='Generate sample data')
    parser.add_argument('--utilities', type=int, default=10, help='Number of utilities to generate')
    parser.add_argument('--years', type=int, default=10, help='Years of data to generate')

    # Operation options
    parser.add_argument('--test', action='store_true', help='Run test suite')
    parser.add_argument('--list', action='store_true', help='List utilities')
    parser.add_argument('--analyze', type=str, metavar='NAME', help='Analyze utility (partial name match)')
    parser.add_argument('--forecast', type=str, metavar='NAME', help='Create forecast for utility')

    args = parser.parse_args()

    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # Execute commands in order
    try:
        if args.setup:
            setup_database()

        if args.generate_data:
            generate_test_data(args.utilities, args.years)

        if args.test:
            run_tests()

        if args.list:
            list_utilities()

        if args.analyze:
            analyze_utility(args.analyze)

        if args.forecast:
            create_forecast(args.forecast, args.years)

        print("\n✓ All operations completed successfully")

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
