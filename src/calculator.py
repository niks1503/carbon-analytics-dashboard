"""Carbon and ESG Footprint Conversion Calculator.

Provides modular, mathematically validated functions for greenhouse gas (GHG)
footprint calculations under the GHG Protocol Corporate Standard (Scopes 1, 2, and 3).
Factors reference standard EPA eGRID 2024, UK DEFRA 2024, and Cloud Carbon Footprint models.
"""

from __future__ import annotations

from typing import Final, Literal

# ==============================================================================
# Emission Factor Constants
# ==============================================================================

# Electricity Grid Emission Factors (kgCO2e per kWh)
# Sources: EPA eGRID 2024 (US), European Environment Agency, IEA regional benchmarks
GRID_EMISSION_FACTORS: Final[dict[str, float]] = {
    "North America (NAM)": 0.385,
    "Europe, Middle East & Africa (EMEA)": 0.255,
    "Asia-Pacific (APAC)": 0.550,
    "Latin America (LATAM)": 0.210,
    "Global Average": 0.390,
}

# Flight Emission Factors (kgCO2e per passenger-kilometer)
# Short-haul (< 500 km), Medium-haul (500 - 3700 km), Long-haul (> 3700 km)
# Includes radiative forcing index (RFI ~1.9x for high altitude NOX/contrail impacts)
FLIGHT_EMISSION_FACTORS: Final[dict[str, dict[str, float]]] = {
    "short": {
        "base": 0.155,
        "with_rfi": 0.245,
    },
    "medium": {
        "base": 0.098,
        "with_rfi": 0.155,
    },
    "long": {
        "base": 0.114,
        "with_rfi": 0.180,
    },
}

# Cabin Class Multipliers (passenger space footprint)
CABIN_CLASS_MULTIPLIERS: Final[dict[str, float]] = {
    "economy": 1.0,
    "premium_economy": 1.5,
    "business": 2.9,
    "first": 4.0,
}

# Cloud Compute Power Model (kW per hour per vCPU/device)
# Source: Cloud Carbon Footprint (CCF) benchmark coefficients
CLOUD_POWER_KW: Final[dict[str, float]] = {
    "standard_vcpu": 0.045,      # Standard general-purpose vCPU (e.g. n2-standard)
    "highmem_vcpu": 0.075,       # High-memory memory-optimized vCPU
    "gpu_accelerated": 0.350,    # GPU-attached node (e.g. NVIDIA A100/H100 slice)
    "storage_tb_hour": 0.0012,   # 1 TB storage active read/write per hour
}

# Cloud Provider Datacenter Power Usage Effectiveness (PUE)
CLOUD_PROVIDER_PUE: Final[dict[str, float]] = {
    "gcp": 1.10,          # Google Cloud industry-leading fleet average
    "aws": 1.15,          # AWS datacenter average
    "azure": 1.18,        # Azure hyperscale average
    "on_premise": 1.55,   # Legacy enterprise datacenter benchmark
}

# Direct Fuel Combustion Emission Factors (kgCO2e per unit) - Scope 1
FUEL_EMISSION_FACTORS: Final[dict[str, float]] = {
    "gasoline_liter": 2.31,      # Fleet gasoline
    "diesel_liter": 2.68,        # Fleet diesel / emergency backup generators
    "natural_gas_m3": 2.03,      # Facility heating
    "propane_liter": 1.51,       # Heating / standby
}


# ==============================================================================
# Modular Conversion Functions
# ==============================================================================

def kwh_to_kg_co2e(
    kwh: float,
    region: str = "North America (NAM)",
    renewable_pct: float = 0.0,
) -> float:
    """Calculate Scope 2 emissions from purchased electricity consumption.

    Args:
        kwh: Electricity consumed in kilowatt-hours (must be non-negative).
        region: Geographic region for grid intensity lookup.
        renewable_pct: Percentage of energy covered by certified renewable energy
            contracts or PPAs (0.0 to 100.0).

    Returns:
        Emissions in kilograms of CO2 equivalent (kgCO2e).
    """
    if kwh < 0:
        raise ValueError(f"Electricity consumption cannot be negative: {kwh}")

    renewable_clamped = max(0.0, min(100.0, renewable_pct))
    factor = GRID_EMISSION_FACTORS.get(region, GRID_EMISSION_FACTORS["Global Average"])
    effective_kwh = kwh * (1.0 - (renewable_clamped / 100.0))
    return round(effective_kwh * factor, 4)


def flight_km_to_kg_co2e(
    flight_km: float,
    haul_type: Literal["short", "medium", "long"] = "medium",
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy",
    include_radiative_forcing: bool = True,
) -> float:
    """Calculate Scope 3 Category 6 (Business Travel) flight emissions.

    Args:
        flight_km: Total passenger distance traveled in kilometers.
        haul_type: "short" (< 500 km), "medium" (500-3700 km), or "long" (> 3700 km).
        cabin_class: Seating class multiplier reflecting physical footprint.
        include_radiative_forcing: Whether to include high-altitude warming effects (RFI).

    Returns:
        Emissions in kilograms of CO2 equivalent (kgCO2e).
    """
    if flight_km < 0:
        raise ValueError(f"Flight distance cannot be negative: {flight_km}")

    haul_data = FLIGHT_EMISSION_FACTORS.get(
        haul_type.lower(), FLIGHT_EMISSION_FACTORS["medium"]
    )
    base_factor = haul_data["with_rfi"] if include_radiative_forcing else haul_data["base"]
    class_multiplier = CABIN_CLASS_MULTIPLIERS.get(cabin_class.lower(), 1.0)

    return round(flight_km * base_factor * class_multiplier, 4)


def cloud_compute_hours_to_kg_co2e(
    compute_hours: float,
    instance_type: str = "standard_vcpu",
    provider: str = "gcp",
    region: str = "North America (NAM)",
) -> float:
    """Calculate Scope 3 Category 1/8 emissions from cloud computing workloads.

    Formula:
        Energy (kWh) = compute_hours * power_draw_kw * PUE
        Emissions (kgCO2e) = Energy (kWh) * regional_grid_emission_factor

    Args:
        compute_hours: Total operating instance-hours.
        instance_type: Hardware tier key in `CLOUD_POWER_KW`.
        provider: Cloud provider key in `CLOUD_PROVIDER_PUE`.
        region: Datacenter region for grid emission factor.

    Returns:
        Emissions in kilograms of CO2 equivalent (kgCO2e).
    """
    if compute_hours < 0:
        raise ValueError(f"Compute hours cannot be negative: {compute_hours}")

    power_kw = CLOUD_POWER_KW.get(instance_type, CLOUD_POWER_KW["standard_vcpu"])
    pue = CLOUD_PROVIDER_PUE.get(provider.lower(), CLOUD_PROVIDER_PUE["gcp"])
    energy_kwh = compute_hours * power_kw * pue

    grid_factor = GRID_EMISSION_FACTORS.get(region, GRID_EMISSION_FACTORS["Global Average"])
    return round(energy_kwh * grid_factor, 4)


def fuel_liters_to_kg_co2e(
    volume: float,
    fuel_type: Literal["gasoline_liter", "diesel_liter", "natural_gas_m3", "propane_liter"] = "gasoline_liter",
) -> float:
    """Calculate Scope 1 direct combustion emissions from fuels and heating.

    Args:
        volume: Quantity of fuel in liters (or m3 for natural gas).
        fuel_type: Fuel classification key in `FUEL_EMISSION_FACTORS`.

    Returns:
        Emissions in kilograms of CO2 equivalent (kgCO2e).
    """
    if volume < 0:
        raise ValueError(f"Fuel volume cannot be negative: {volume}")

    factor = FUEL_EMISSION_FACTORS.get(fuel_type, FUEL_EMISSION_FACTORS["gasoline_liter"])
    return round(volume * factor, 4)


def kg_to_metric_tons(kg_value: float) -> float:
    """Convert kilograms to metric tons (MT CO2e)."""
    return round(kg_value / 1000.0, 4)


def metric_tons_to_kg(mt_value: float) -> float:
    """Convert metric tons (MT CO2e) to kilograms."""
    return round(mt_value * 1000.0, 4)


def calculate_gross_emissions_mt(
    scope1_kg: float,
    scope2_kg: float,
    scope3_kg: float,
) -> float:
    """Calculate total gross emissions in metric tons (MT CO2e) across Scopes 1, 2, and 3.

    Args:
        scope1_kg: Direct Scope 1 emissions in kgCO2e.
        scope2_kg: Indirect Scope 2 emissions in kgCO2e.
        scope3_kg: Value chain Scope 3 emissions in kgCO2e.

    Returns:
        Total gross emissions in MT CO2e.
    """
    total_kg = max(0.0, scope1_kg) + max(0.0, scope2_kg) + max(0.0, scope3_kg)
    return kg_to_metric_tons(total_kg)


def calculate_net_emissions_mt(
    gross_mt: float,
    offsets_mt: float,
) -> float:
    """Calculate net emissions after certified carbon offsets and removals.

    Net = max(0.0, Gross Emissions - Carbon Offsets)

    Args:
        gross_mt: Gross emissions in MT CO2e.
        offsets_mt: Certified carbon offsets in MT CO2e.

    Returns:
        Net emissions in MT CO2e.
    """
    net = max(0.0, gross_mt) - max(0.0, offsets_mt)
    return round(max(0.0, net), 4)


def calculate_mom_change(
    current_value: float,
    previous_value: float,
) -> float:
    """Calculate month-over-month (MoM) percentage change safely.

    Args:
        current_value: Value for current period.
        previous_value: Value for previous period.

    Returns:
        Percentage change as a float (e.g., -5.2 for a 5.2% reduction).
        Returns 0.0 if previous_value is zero.
    """
    if previous_value == 0:
        return 0.0
    return round(((current_value - previous_value) / abs(previous_value)) * 100.0, 2)


def calculate_carbon_intensity(
    gross_mt: float,
    fte_count: int | None = None,
    spend_million_usd: float | None = None,
) -> dict[str, float | None]:
    """Calculate standard ESG carbon intensity KPIs.

    Returns:
        Dictionary containing:
        - mt_per_fte: Metric tons CO2e per full-time equivalent employee.
        - mt_per_million_usd: Metric tons CO2e per million USD operational expenditure.
    """
    result: dict[str, float | None] = {
        "mt_per_fte": None,
        "mt_per_million_usd": None,
    }

    if fte_count and fte_count > 0:
        result["mt_per_fte"] = round(gross_mt / fte_count, 4)

    if spend_million_usd and spend_million_usd > 0:
        result["mt_per_million_usd"] = round(gross_mt / spend_million_usd, 4)

    return result


def calculate_scope_breakdown(
    scope1_mt: float,
    scope2_mt: float,
    scope3_mt: float,
) -> dict[str, float]:
    """Compute percentage distribution across Scopes 1, 2, and 3.

    Returns:
        Dictionary mapping scope labels to percentage shares (0.0 - 100.0).
    """
    total = max(0.0, scope1_mt) + max(0.0, scope2_mt) + max(0.0, scope3_mt)
    if total == 0:
        return {"Scope 1": 0.0, "Scope 2": 0.0, "Scope 3": 0.0}

    return {
        "Scope 1": round((scope1_mt / total) * 100.0, 2),
        "Scope 2": round((scope2_mt / total) * 100.0, 2),
        "Scope 3": round((scope3_mt / total) * 100.0, 2),
    }
