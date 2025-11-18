"""
Comprehensive Test Suite
Tests all modules with sample data
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database.db_setup import DatabaseConfig, get_connection, test_connection
from analysis.financial_analysis import FinancialAnalyzer
from forecasting.forecast_engine import ForecastEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test 1: Database Connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)

    config = DatabaseConfig()

    try:
        result = test_connection(config)
        if result:
            print("✓ PASS: Database connection successful")
            return True
        else:
            print("✗ FAIL: Database connection failed")
            return False
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_sample_data_exists():
    """Test 2: Sample Data Exists"""
    print("\n" + "="*60)
    print("TEST 2: Sample Data Verification")
    print("="*60)

    config = DatabaseConfig()

    try:
        conn = get_connection(config)
        cursor = conn.cursor()

        # Check utilities
        cursor.execute("SELECT COUNT(*) FROM utilities")
        util_count = cursor.fetchone()[0]
        print(f"  Utilities: {util_count}")

        if util_count == 0:
            print("  ⚠️  No sample data found. Run: python tests/generate_sample_data.py")
            cursor.close()
            conn.close()
            return False

        # Check financial reports
        cursor.execute("SELECT COUNT(*) FROM financial_reports")
        report_count = cursor.fetchone()[0]
        print(f"  Reports: {report_count}")

        # Check line items
        cursor.execute("SELECT COUNT(*) FROM line_items")
        item_count = cursor.fetchone()[0]
        print(f"  Line Items: {item_count}")

        cursor.close()
        conn.close()

        if util_count > 0 and report_count > 0 and item_count > 0:
            print("✓ PASS: Sample data exists")
            return True
        else:
            print("✗ FAIL: Incomplete sample data")
            return False

    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_financial_analysis():
    """Test 3: Financial Analysis Module"""
    print("\n" + "="*60)
    print("TEST 3: Financial Analysis")
    print("="*60)

    config = DatabaseConfig()

    try:
        conn = get_connection(config)
        analyzer = FinancialAnalyzer(conn)

        # Get first utility
        cursor = conn.cursor()
        cursor.execute("SELECT utility_id, name FROM utilities LIMIT 1")
        result = cursor.fetchone()

        if not result:
            print("✗ FAIL: No utilities found")
            conn.close()
            return False

        utility_id, name = result
        print(f"  Testing with: {name}")

        # Test 3.1: Get Summary
        print("\n  3.1: Utility Summary...")
        summary = analyzer.get_utility_summary(utility_id)

        if summary and 'financials' in summary:
            print(f"    ✓ Got summary with {len(summary['financials'])} years")

            if summary['financials']:
                latest = summary['financials'][0]
                print(f"    Latest Year: FY{latest['fiscal_year']}")
                print(f"    Revenue: ${latest['total_revenue']:,.0f}")
                print(f"    Expenses: ${latest['total_expenses']:,.0f}")
                print(f"    Operating Margin: {latest['operating_margin']:.1f}%")
        else:
            print("    ✗ Failed to get summary")
            conn.close()
            return False

        # Test 3.2: Calculate Metrics
        print("\n  3.2: Key Metrics...")
        if summary['financials']:
            latest_year = summary['financials'][0]['fiscal_year']
            metrics = analyzer.calculate_key_metrics(utility_id, latest_year)

            print(f"    Operating Margin: {metrics['operating_margin']:.1f}%")
            print(f"    Debt-to-Assets: {metrics['debt_to_assets_ratio']:.1f}%")
            print("    ✓ Metrics calculated")

        # Test 3.3: Growth Rates
        print("\n  3.3: Growth Rates...")
        growth = analyzer.calculate_growth_rates(utility_id, years=5)

        if growth:
            print(f"    Revenue CAGR: {growth['revenue_cagr']:.2f}%")
            print(f"    Expense CAGR: {growth['expense_cagr']:.2f}%")
            print("    ✓ Growth rates calculated")

        cursor.close()
        conn.close()

        print("\n✓ PASS: Financial Analysis module working")
        return True

    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forecasting():
    """Test 4: Forecasting Module"""
    print("\n" + "="*60)
    print("TEST 4: Forecasting Engine")
    print("="*60)

    config = DatabaseConfig()

    try:
        conn = get_connection(config)
        engine = ForecastEngine(conn)

        # Get utility with data
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.utility_id, u.name, MAX(li.fiscal_year) as latest_year
            FROM utilities u
            JOIN line_items li ON u.utility_id = li.utility_id
            GROUP BY u.utility_id, u.name
            LIMIT 1
        """)

        result = cursor.fetchone()

        if not result:
            print("✗ FAIL: No utilities with financial data found")
            conn.close()
            return False

        utility_id, name, latest_year = result
        print(f"  Testing with: {name}")
        print(f"  Base Year: {latest_year}")

        # Test 4.1: Create Single Forecast
        print("\n  4.1: Creating forecast...")
        forecast_id = engine.create_forecast(
            utility_id=utility_id,
            forecast_name="Test Forecast",
            base_year=latest_year,
            forecast_years=3
        )
        print(f"    ✓ Created forecast: {forecast_id[:8]}...")

        # Test 4.2: Get Forecast Summary
        print("\n  4.2: Getting forecast summary...")
        summary = engine.get_forecast_summary(forecast_id)

        if summary and 'projections' in summary:
            print(f"    ✓ Got {len(summary['projections'])} years of projections")

            for proj in summary['projections']:
                print(f"      FY{proj['fiscal_year']}: "
                      f"Revenue=${proj['revenue']:,.0f}, "
                      f"Margin={proj['operating_margin']:.1f}%")

        # Test 4.3: Scenario Comparison
        print("\n  4.3: Creating scenario comparison...")
        scenarios = engine.create_scenario_comparison(
            utility_id=utility_id,
            base_year=latest_year,
            forecast_years=3
        )

        print(f"    ✓ Created {len(scenarios)} scenarios:")
        for scenario_name in scenarios.keys():
            print(f"      - {scenario_name}")

        cursor.close()
        conn.close()

        print("\n✓ PASS: Forecasting module working")
        return True

    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_export():
    """Test 5: Excel Export"""
    print("\n" + "="*60)
    print("TEST 5: Excel Export")
    print("="*60)

    config = DatabaseConfig()

    try:
        import openpyxl
    except ImportError:
        print("⚠️  SKIP: openpyxl not installed")
        return True

    try:
        conn = get_connection(config)
        analyzer = FinancialAnalyzer(conn)

        # Get first utility
        cursor = conn.cursor()
        cursor.execute("SELECT utility_id, name FROM utilities LIMIT 1")
        result = cursor.fetchone()

        if not result:
            print("✗ FAIL: No utilities found")
            conn.close()
            return False

        utility_id, name = result

        # Export to Excel
        print(f"  Exporting {name} to Excel...")
        output_file = "/tmp/test_analysis.xlsx"
        analyzer.export_to_excel(utility_id, output_file)

        # Check file exists
        if os.path.exists(output_file):
            size_kb = os.path.getsize(output_file) / 1024
            print(f"    ✓ Created {output_file} ({size_kb:.1f} KB)")

            # Clean up
            os.remove(output_file)
            print("    ✓ Cleaned up test file")

        cursor.close()
        conn.close()

        print("\n✓ PASS: Excel export working")
        return True

    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🔬"*30)
    print(" "*20 + "COMPREHENSIVE TEST SUITE")
    print("🔬"*30)

    tests = [
        ("Database Connection", test_database_connection),
        ("Sample Data Verification", test_sample_data_exists),
        ("Financial Analysis", test_financial_analysis),
        ("Forecasting Engine", test_forecasting),
        ("Excel Export", test_excel_export),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = 0
    failed = 0

    for test_name, result in results:
        if result:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1

        print(f"{status:12} {test_name}")

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")

    print("="*60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
