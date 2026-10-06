"""Unit tests for src/genai_insights.py."""

from src.genai_insights import (
    generate_deterministic_executive_briefing,
    generate_executive_insights,
)


def test_deterministic_executive_briefing():
    """Verify that deterministic briefing renders comprehensive C-suite analysis."""
    payload = {
        "date_range_label": "Jan 2024 to Dec 2025",
        "departments_count": 6,
        "regions_label": "Global",
        "total_gross_mt": 12500.5,
        "total_offsets_mt": 2500.0,
        "total_net_mt": 10000.5,
        "offset_coverage_pct": 20.0,
        "mom_change_pct": -4.2,
        "scope1_mt": 1200.0,
        "scope2_mt": 3500.0,
        "scope3_mt": 7800.5,
        "scope1_pct": 9.6,
        "scope2_pct": 28.0,
        "scope3_pct": 62.4,
        "flight_mt": 4200.0,
        "cloud_mt": 1800.0,
        "top_department": "Global Technology & Infrastructure",
        "top_dept_mt": 4500.0,
        "top_region": "North America (NAM)",
    }

    briefing = generate_deterministic_executive_briefing(payload, scenario="Mandate 20% SAF on flights")
    assert "Executive Summary & Velocity Scorecard" in briefing
    assert "12,500.50 MT CO2e" in briefing
    assert "Scope 3 (Value Chain)" in briefing
    assert "Global Technology & Infrastructure" in briefing
    assert "What-If Scenario Evaluation" in briefing
    assert "Mandate 20% SAF on flights" in briefing


def test_generate_executive_insights_no_key():
    """Verify generate_executive_insights falls back cleanly when no key is set."""
    payload = {
        "date_range_label": "Active Period",
        "total_gross_mt": 500.0,
        "total_offsets_mt": 100.0,
        "total_net_mt": 400.0,
        "offset_coverage_pct": 20.0,
        "mom_change_pct": 1.5,
        "scope1_pct": 10.0,
        "scope2_pct": 30.0,
        "scope3_pct": 60.0,
    }
    # Pass api_key_override="" or None with no env var
    result = generate_executive_insights(payload, api_key_override=None)
    assert "Executive Summary" in result
    assert "500.00 MT CO2e" in result
