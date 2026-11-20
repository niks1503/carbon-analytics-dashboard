"""Script to generate realistic, scrubbed, anonymized sample ESG data."""

import csv
import random
import sys
from pathlib import Path

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.calculator import (  # noqa: E402 (needs the sys.path setup above)
    calculate_gross_emissions_mt,
    calculate_net_emissions_mt,
    cloud_compute_hours_to_kg_co2e,
    flight_km_to_kg_co2e,
    fuel_liters_to_kg_co2e,
    kwh_to_kg_co2e,
)

DEPARTMENTS = [
    "Global Commercial Services",
    "Global Consumer Services",
    "Enterprise Digital & Data Solutions",
    "Global Technology & Infrastructure",
    "Global Risk, Compliance & Legal",
    "Corporate Affairs & Real Estate",
]

REGIONS = [
    "North America (NAM)",
    "Europe, Middle East & Africa (EMEA)",
    "Asia-Pacific (APAC)",
    "Latin America (LATAM)",
]

# Generate monthly dates for 2024 and 2025 (24 months)
MONTHS = []
for year in [2024, 2025]:
    for month in range(1, 13):
        MONTHS.append(f"{year}-{month:02d}-01")

def generate_dataset():
    random.seed(42)  # Deterministic reproducibility
    rows = []

    # Department headcount and profile baselines
    dept_profiles = {
        "Global Commercial Services": {"fte": (2500, 3200), "spend_m": (45.0, 65.0), "flight_heavy": True, "cloud_heavy": False},
        "Global Consumer Services": {"fte": (3500, 4800), "spend_m": (60.0, 85.0), "flight_heavy": False, "cloud_heavy": False},
        "Enterprise Digital & Data Solutions": {"fte": (1800, 2400), "spend_m": (55.0, 75.0), "flight_heavy": False, "cloud_heavy": True},
        "Global Technology & Infrastructure": {"fte": (4200, 5600), "spend_m": (90.0, 130.0), "flight_heavy": False, "cloud_heavy": True},
        "Global Risk, Compliance & Legal": {"fte": (1200, 1600), "spend_m": (25.0, 38.0), "flight_heavy": False, "cloud_heavy": False},
        "Corporate Affairs & Real Estate": {"fte": (800, 1100), "spend_m": (35.0, 50.0), "flight_heavy": False, "cloud_heavy": False, "facility_heavy": True},
    }

    # Region weights for distributed operations
    region_weights = {
        "North America (NAM)": 0.48,
        "Europe, Middle East & Africa (EMEA)": 0.24,
        "Asia-Pacific (APAC)": 0.18,
        "Latin America (LATAM)": 0.10,
    }

    record_id = 10001

    for month_idx, month_str in enumerate(MONTHS):
        # Gradual ESG decarbonization improvement over the 24 months
        progress_factor = 1.0 - (month_idx * 0.008)  # ~18% reduction over 2 years
        renewable_trend = min(85.0, 35.0 + (month_idx * 1.8))  # Renewable adoption ramps up from 35% to ~78%

        for dept in DEPARTMENTS:
            prof = dept_profiles[dept]
            for reg in REGIONS:
                rw = region_weights[reg]

                # Scaled activity metrics
                base_fte = int(random.uniform(*prof["fte"]) * rw)
                base_spend = round(random.uniform(*prof["spend_m"]) * rw, 2)

                # Scope 2 Electricity (kWh)
                base_kwh = (base_fte * random.uniform(280.0, 420.0)) * progress_factor
                # Seasonal variation for HVAC in summer/winter
                m_num = int(month_str.split("-")[1])
                seasonal = 1.15 if m_num in [6, 7, 8, 12, 1, 2] else 0.92
                kwh = round(base_kwh * seasonal, 1)

                # Renewable energy contract coverage
                renewable_pct = min(100.0, max(15.0, renewable_trend + random.uniform(-6.0, 6.0)))
                scope2_kg = kwh_to_kg_co2e(kwh, region=reg, renewable_pct=renewable_pct)

                # Scope 3 Flights (km)
                is_flight_heavy = prof.get("flight_heavy", False)
                flight_multiplier = 4.5 if is_flight_heavy else 1.0
                flight_km = round(base_fte * random.uniform(120.0, 260.0) * flight_multiplier * progress_factor, 1)
                # Q3/Q4 corporate travel bump
                travel_seasonal = 1.25 if m_num in [9, 10, 11] else 0.85
                flight_km = round(flight_km * travel_seasonal, 1)
                scope3_flight_kg = flight_km_to_kg_co2e(flight_km, haul_type="medium", cabin_class="economy")

                # Scope 3 Cloud compute (hours)
                is_cloud_heavy = prof.get("cloud_heavy", False)
                cloud_multiplier = 8.0 if is_cloud_heavy else 1.2
                compute_hours = round(base_fte * random.uniform(40.0, 90.0) * cloud_multiplier, 1)
                scope3_cloud_kg = cloud_compute_hours_to_kg_co2e(compute_hours, instance_type="standard_vcpu", provider="gcp", region=reg)

                # Scope 3 Commuting & Procurement indirect
                scope3_indirect_kg = round(base_fte * random.uniform(45.0, 75.0), 1)
                scope3_kg = round(scope3_flight_kg + scope3_cloud_kg + scope3_indirect_kg, 4)

                # Scope 1 Direct fuels & facility heating
                is_fac_heavy = prof.get("facility_heavy", False)
                fuel_multiplier = 3.5 if is_fac_heavy else 0.7
                fuel_liters = round(base_fte * random.uniform(8.0, 18.0) * fuel_multiplier * progress_factor, 1)
                scope1_kg = fuel_liters_to_kg_co2e(fuel_liters, fuel_type="natural_gas_m3")

                # Gross Emissions MT
                gross_mt = calculate_gross_emissions_mt(scope1_kg, scope2_kg, scope3_kg)

                # Certified Carbon Offsets purchased (e.g. Gold Standard / Verra high quality credits)
                offset_budget_rate = random.uniform(0.12, 0.28) + (month_idx * 0.005)
                offsets_mt = round(min(gross_mt * 0.95, gross_mt * offset_budget_rate), 2)

                # Net Emissions MT
                net_mt = calculate_net_emissions_mt(gross_mt, offsets_mt)

                rows.append({
                    "record_id": f"REC-{record_id}",
                    "date": month_str,
                    "year": month_str.split("-")[0],
                    "month": month_str.split("-")[1],
                    "department": dept,
                    "region": reg,
                    "fte_headcount": base_fte,
                    "operational_spend_m_usd": base_spend,
                    "electricity_kwh": kwh,
                    "renewable_energy_pct": round(renewable_pct, 1),
                    "flight_km": flight_km,
                    "cloud_compute_hours": compute_hours,
                    "fuel_liters": fuel_liters,
                    "scope1_kg_co2e": round(scope1_kg, 2),
                    "scope2_kg_co2e": round(scope2_kg, 2),
                    "scope3_kg_co2e": round(scope3_kg, 2),
                    "scope3_flight_kg_co2e": round(scope3_flight_kg, 2),
                    "scope3_cloud_kg_co2e": round(scope3_cloud_kg, 2),
                    "gross_emissions_mt": round(gross_mt, 2),
                    "offsets_purchased_mt": round(offsets_mt, 2),
                    "net_emissions_mt": round(net_mt, 2),
                    "sbti_target_max_mt": round(gross_mt * 0.85, 2),
                })
                record_id += 1

    fieldnames = list(rows[0].keys())
    output_path = ROOT_DIR / "data" / "anonymized_sample_data.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Successfully generated {len(rows)} records in {output_path}")

if __name__ == "__main__":
    generate_dataset()
