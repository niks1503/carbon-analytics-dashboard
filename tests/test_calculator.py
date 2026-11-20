"""Unit tests for src/calculator.py carbon conversion functions."""

import pytest

from src.calculator import (
    calculate_carbon_intensity,
    calculate_gross_emissions_mt,
    calculate_mom_change,
    calculate_net_emissions_mt,
    calculate_scope_breakdown,
    cloud_compute_hours_to_kg_co2e,
    flight_km_to_kg_co2e,
    fuel_liters_to_kg_co2e,
    kwh_to_kg_co2e,
)


def test_kwh_to_kg_co2e_standard():
    """Test standard electricity calculations across regions."""
    # 1,000 kWh in North America (0.385 kg/kWh)
    res_nam = kwh_to_kg_co2e(1000.0, region="North America (NAM)", renewable_pct=0.0)
    assert res_nam == 385.0

    # 1,000 kWh in EMEA (0.255 kg/kWh)
    res_emea = kwh_to_kg_co2e(1000.0, region="Europe, Middle East & Africa (EMEA)", renewable_pct=0.0)
    assert res_emea == 255.0


def test_kwh_to_kg_co2e_renewable_discount():
    """Test renewable PPA percentage reduction."""
    # 50% renewable contract should halve emissions
    res_50 = kwh_to_kg_co2e(1000.0, region="North America (NAM)", renewable_pct=50.0)
    assert res_50 == 192.5

    # 100% renewable should be 0 emissions
    res_100 = kwh_to_kg_co2e(1000.0, region="North America (NAM)", renewable_pct=100.0)
    assert res_100 == 0.0


def test_kwh_to_kg_co2e_negative_input():
    """Ensure negative kWh raises ValueError."""
    with pytest.raises(ValueError):
        kwh_to_kg_co2e(-100.0)


def test_flight_km_to_kg_co2e_hauls():
    """Test flight emissions across haul distances and cabin classes."""
    # Medium haul economy with RFI
    res_med = flight_km_to_kg_co2e(1000.0, haul_type="medium", cabin_class="economy", include_radiative_forcing=True)
    assert res_med == 155.0

    # Long haul economy with RFI
    res_long = flight_km_to_kg_co2e(1000.0, haul_type="long", cabin_class="economy", include_radiative_forcing=True)
    assert res_long == 180.0

    # Business class multiplier (2.9x)
    res_biz = flight_km_to_kg_co2e(1000.0, haul_type="medium", cabin_class="business", include_radiative_forcing=True)
    assert res_biz == round(1000.0 * 0.155 * 2.9, 4)


def test_cloud_compute_hours_to_kg_co2e():
    """Test cloud computing energy and emission calculations."""
    # 10,000 vCPU hours on GCP (PUE 1.10) in North America (0.385 kg/kWh)
    # Energy = 10000 * 0.045 * 1.10 = 495 kWh
    # Emissions = 495 * 0.385 = 190.575 kg
    res = cloud_compute_hours_to_kg_co2e(10000.0, instance_type="standard_vcpu", provider="gcp", region="North America (NAM)")
    assert res == 190.575


def test_fuel_liters_to_kg_co2e():
    """Test Scope 1 direct combustion calculations."""
    res_gas = fuel_liters_to_kg_co2e(100.0, fuel_type="gasoline_liter")
    assert res_gas == 231.0

    res_diesel = fuel_liters_to_kg_co2e(100.0, fuel_type="diesel_liter")
    assert res_diesel == 268.0


def test_gross_and_net_emissions():
    """Test gross conversion to metric tons and net offset abating."""
    # 100,000 kg S1 + 200,000 kg S2 + 700,000 kg S3 = 1,000,000 kg = 1,000 MT
    gross_mt = calculate_gross_emissions_mt(100000.0, 200000.0, 700000.0)
    assert gross_mt == 1000.0

    # 1,000 MT gross minus 300 MT offsets = 700 MT net
    net_mt = calculate_net_emissions_mt(gross_mt, 300.0)
    assert net_mt == 700.0

    # Offsets exceeding gross clamps to 0.0 (cannot be negative)
    net_clamped = calculate_net_emissions_mt(gross_mt, 1500.0)
    assert net_clamped == 0.0


def test_mom_change_calculations():
    """Test month-over-month velocity calculations."""
    # 10% decrease
    assert calculate_mom_change(90.0, 100.0) == -10.0
    # 15% increase
    assert calculate_mom_change(115.0, 100.0) == 15.0
    # Zero previous value returns 0.0 without DivisionByZero
    assert calculate_mom_change(100.0, 0.0) == 0.0


def test_carbon_intensity_ratios():
    """Test carbon intensity per employee and operational spend."""
    kpis = calculate_carbon_intensity(1000.0, fte_count=500, spend_million_usd=50.0)
    assert kpis["mt_per_fte"] == 2.0
    assert kpis["mt_per_million_usd"] == 20.0


def test_scope_breakdown():
    """Test percentage distribution across Scopes 1, 2, and 3."""
    breakdown = calculate_scope_breakdown(100.0, 300.0, 600.0)
    assert breakdown["Scope 1"] == 10.0
    assert breakdown["Scope 2"] == 30.0
    assert breakdown["Scope 3"] == 60.0
