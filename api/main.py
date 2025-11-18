"""
FastAPI Backend for Water Utilities Dashboard
Provides REST API endpoints for the React frontend
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_setup import DatabaseConfig, get_connection
from analysis.financial_analysis import FinancialAnalyzer
from forecasting.forecast_engine import ForecastEngine

app = FastAPI(
    title="Water Utilities Financial Analysis API",
    description="API for analyzing water utility financial data",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
config = DatabaseConfig()


@app.get("/")
def read_root():
    """API root endpoint"""
    return {
        "message": "Water Utilities Financial Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "stats": "/api/stats",
            "utilities": "/api/utilities",
            "utility": "/api/utility/{id}",
            "forecasts": "/api/forecasts/{utility_id}"
        }
    }


@app.get("/api/stats")
def get_stats():
    """Get database statistics"""
    conn = get_connection(config)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM utilities")
    utilities = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM financial_reports WHERE processing_status = 'completed'")
    reports = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM line_items")
    line_items = cursor.fetchone()[0]

    cursor.execute("""
        SELECT MIN(fiscal_year), MAX(fiscal_year)
        FROM financial_reports
        WHERE processing_status = 'completed'
    """)
    year_range = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "utilities": utilities,
        "reports": reports,
        "line_items": line_items,
        "year_range": {
            "earliest": year_range[0] if year_range[0] else None,
            "latest": year_range[1] if year_range[1] else None
        }
    }


@app.get("/api/utilities")
def list_utilities(
    state: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    """List utilities with optional filtering"""
    conn = get_connection(config)
    cursor = conn.cursor()

    query = """
        SELECT
            u.utility_id,
            u.name,
            u.state_code,
            u.population_served,
            u.utility_type,
            COUNT(DISTINCT fr.fiscal_year) as years_of_data
        FROM utilities u
        LEFT JOIN financial_reports fr ON u.utility_id = fr.utility_id
            AND fr.processing_status = 'completed'
    """

    params = []

    if state:
        query += " WHERE u.state_code = %s"
        params.append(state)

    query += """
        GROUP BY u.utility_id, u.name, u.state_code, u.population_served, u.utility_type
        ORDER BY years_of_data DESC, u.name
        LIMIT %s OFFSET %s
    """

    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()

    utilities = []
    for row in results:
        utilities.append({
            "id": row[0],
            "name": row[1],
            "state": row[2],
            "population_served": row[3],
            "utility_type": row[4],
            "years_of_data": row[5]
        })

    cursor.close()
    conn.close()

    return utilities


@app.get("/api/utilities/top")
def get_top_utilities(limit: int = Query(10, le=100)):
    """Get top utilities by revenue"""
    conn = get_connection(config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.utility_id,
            u.name,
            u.state_code,
            SUM(CASE WHEN li.line_item_category = 'revenue' THEN li.amount ELSE 0 END) as total_revenue,
            SUM(CASE WHEN li.line_item_category = 'expense' THEN li.amount ELSE 0 END) as total_expenses,
            SUM(CASE WHEN li.line_item_category = 'asset' THEN li.amount ELSE 0 END) as total_assets,
            SUM(CASE WHEN li.line_item_category = 'liability' THEN li.amount ELSE 0 END) as total_liabilities
        FROM utilities u
        JOIN line_items li ON u.utility_id = li.utility_id
        WHERE li.fiscal_year = (SELECT MAX(fiscal_year) FROM line_items)
        GROUP BY u.utility_id, u.name, u.state_code
        HAVING SUM(CASE WHEN li.line_item_category = 'revenue' THEN li.amount ELSE 0 END) > 0
        ORDER BY total_revenue DESC
        LIMIT %s
    """, (limit,))

    results = cursor.fetchall()

    utilities = []
    for row in results:
        revenue = float(row[3]) if row[3] else 0
        expenses = float(row[4]) if row[4] else 0
        assets = float(row[5]) if row[5] else 0
        liabilities = float(row[6]) if row[6] else 0

        utilities.append({
            "id": row[0],
            "name": row[1],
            "state": row[2],
            "revenue": revenue,
            "operating_margin": ((revenue - expenses) / revenue * 100) if revenue > 0 else 0,
            "debt_ratio": (liabilities / assets * 100) if assets > 0 else 0
        })

    cursor.close()
    conn.close()

    return utilities


@app.get("/api/utility/{utility_id}")
def get_utility(utility_id: str):
    """Get detailed information for a utility"""
    conn = get_connection(config)
    analyzer = FinancialAnalyzer(conn)

    try:
        summary = analyzer.get_utility_summary(utility_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Utility not found")

        # Get growth rates
        growth = analyzer.calculate_growth_rates(utility_id, years=5)

        conn.close()

        return {
            **summary,
            "growth_rates": growth
        }

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/revenue-trend")
def get_revenue_trend():
    """Get aggregate revenue trend across all utilities"""
    conn = get_connection(config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            fiscal_year as year,
            SUM(amount) as total_revenue
        FROM line_items
        WHERE line_item_category = 'revenue'
        GROUP BY fiscal_year
        ORDER BY fiscal_year
    """)

    results = cursor.fetchall()

    data = [
        {"year": row[0], "total_revenue": float(row[1])}
        for row in results
    ]

    cursor.close()
    conn.close()

    return data


@app.get("/api/analytics/by-state")
def get_state_distribution():
    """Get number of utilities by state"""
    conn = get_connection(config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT state_code as state, COUNT(*) as count
        FROM utilities
        GROUP BY state_code
        ORDER BY count DESC
        LIMIT 10
    """)

    results = cursor.fetchall()

    data = [
        {"state": row[0], "count": row[1]}
        for row in results
    ]

    cursor.close()
    conn.close()

    return data


@app.get("/api/forecasts/{utility_id}")
def get_forecasts(utility_id: str):
    """Get all forecasts for a utility"""
    conn = get_connection(config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT forecast_id, forecast_name, forecast_type, base_year, forecast_start_year, forecast_end_year
        FROM forecasts
        WHERE utility_id = %s
        ORDER BY created_at DESC
    """, (utility_id,))

    results = cursor.fetchall()

    forecasts = [
        {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "base_year": row[3],
            "forecast_start_year": row[4],
            "forecast_end_year": row[5]
        }
        for row in results
    ]

    cursor.close()
    conn.close()

    return forecasts


@app.get("/api/forecast/{forecast_id}")
def get_forecast(forecast_id: str):
    """Get detailed forecast data"""
    conn = get_connection(config)
    engine = ForecastEngine(conn)

    try:
        summary = engine.get_forecast_summary(forecast_id)

        if not summary:
            raise HTTPException(status_code=404, detail="Forecast not found")

        conn.close()
        return summary

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forecast/create")
def create_forecast(
    utility_id: str,
    forecast_name: str,
    base_year: int,
    forecast_years: int = 5,
    assumptions: Optional[dict] = None
):
    """Create a new forecast"""
    conn = get_connection(config)
    engine = ForecastEngine(conn)

    try:
        forecast_id = engine.create_forecast(
            utility_id=utility_id,
            forecast_name=forecast_name,
            base_year=base_year,
            forecast_years=forecast_years,
            assumptions=assumptions
        )

        conn.close()

        return {
            "forecast_id": forecast_id,
            "message": "Forecast created successfully"
        }

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
