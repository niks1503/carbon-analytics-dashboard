"""American Express | Scaled Analytics & BI.

Carbon & ESG Footprint Analytics Dashboard
Production-ready Enterprise GHG Protocol Scopes 1, 2 & 3 Analytics Platform.
"""

from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.calculator import (
    calculate_gross_emissions_mt,
    calculate_mom_change,
    calculate_net_emissions_mt,
    calculate_scope_breakdown,
    cloud_compute_hours_to_kg_co2e,
    flight_km_to_kg_co2e,
    fuel_liters_to_kg_co2e,
    kg_to_metric_tons,
    kwh_to_kg_co2e,
)
from src.gcp_client import fetch_carbon_data, get_bigquery_schema_ddl
from src.genai_insights import generate_executive_insights, get_gemini_api_key
from src.visualizations import (
    create_activity_driver_breakdown,
    create_department_bar_chart,
    create_monthly_trend_chart,
    create_regional_comparison_chart,
    create_scope_donut_chart,
)

# ==============================================================================
# Page Configuration & Executive Styling
# ==============================================================================

st.set_page_config(
    page_title="Amex ESG Analytics | Carbon Footprint BI",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Helper to render Plotly charts using modern width='stretch'
def render_plotly_chart(fig: go.Figure, key: str | None = None) -> None:
    """Render Plotly figure with dynamic container stretching without deprecated warnings."""
    st.plotly_chart(fig, width="stretch", key=key)


# Custom Enterprise CSS for American Express Design Language
CUSTOM_CSS = """
<style>
    /* Global Typography & Font Family */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Amex Enterprise Header Banner */
    .amex-header {
        background: linear-gradient(135deg, #00173D 0%, #002663 50%, #004085 100%);
        border-radius: 12px;
        padding: 24px 32px;
        color: #FFFFFF;
        box-shadow: 0 4px 20px rgba(0, 38, 99, 0.15);
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 6px solid #00A3E0;
    }
    .amex-title {
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0;
        color: #FFFFFF;
    }
    .amex-subtitle {
        font-size: 14px;
        color: #93C5FD;
        margin-top: 4px;
        font-weight: 400;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    .dot-green { background-color: #10B981; }
    .dot-blue { background-color: #38BDF8; }

    /* Streamlit Metric Customization */
    div[data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #002663 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# Data Ingestion via GCP Client (@st.cache_data)
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_dashboard_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Cached loader invoking the GCP BigQuery client with local CSV fallback."""
    return fetch_carbon_data()


# Load dataset
df_raw, data_metadata = get_cached_dashboard_data()


# ==============================================================================
# Header Banner
# ==============================================================================

dot_color = "dot-green" if not data_metadata.get("is_fallback") else "dot-blue"
source_label = data_metadata.get("status", "Active")

st.markdown(
    f"""
    <div class="amex-header">
        <div>
            <div class="amex-title">American Express | Global ESG & Scaled Analytics Platform</div>
            <div class="amex-subtitle">Carbon & ESG Footprint Analytics Dashboard &mdash; GHG Protocol Scopes 1, 2 & 3</div>
        </div>
        <div>
            <div class="status-badge">
                <span class="status-dot {dot_color}"></span>
                <span>{source_label}</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# Sidebar: Executive BI Filters & Configuration
# ==============================================================================

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/f/fa/American_Express_logo_%282018%29.svg",
        width=120,
    )
    st.markdown("### 🎛️ Executive BI Controls")
    st.caption("Filter carbon footprint across enterprise dimensions.")

    # 1. Region Filter
    all_regions = sorted(df_raw["region"].unique().tolist())
    select_all_regions = st.checkbox("Select All Operating Regions", value=True, key="filter_all_regions")
    if select_all_regions:
        selected_regions = st.multiselect(
            "Operating Theaters:",
            options=all_regions,
            default=all_regions,
            key="filter_regions_select",
        )
    else:
        selected_regions = st.multiselect(
            "Operating Theaters:",
            options=all_regions,
            default=[all_regions[0]],
            key="filter_regions_select",
        )

    # 2. Department Filter
    all_departments = sorted(df_raw["department"].unique().tolist())
    select_all_depts = st.checkbox("Select All Business Units", value=True, key="filter_all_depts")
    if select_all_depts:
        selected_departments = st.multiselect(
            "Enterprise Departments:",
            options=all_departments,
            default=all_departments,
            key="filter_depts_select",
        )
    else:
        selected_departments = st.multiselect(
            "Enterprise Departments:",
            options=all_departments,
            default=[all_departments[0]],
            key="filter_depts_select",
        )

    # 3. Date Range Filter
    min_date = df_raw["date"].min().date()
    max_date = df_raw["date"].max().date()

    st.markdown("---")
    st.markdown("**Reporting Period (Date Range):**")
    date_range = st.date_input(
        "Timeline Boundaries",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed",
        key="filter_date_range",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    # 4. Scope Inclusion Filter
    st.markdown("---")
    st.markdown("**Emission Scope Inclusion:**")
    include_s1 = st.checkbox("Scope 1 (Direct Facilities & Fleet)", value=True, key="filter_scope1")
    include_s2 = st.checkbox("Scope 2 (Purchased Electricity)", value=True, key="filter_scope2")
    include_s3 = st.checkbox("Scope 3 (Value Chain: Travel & Cloud)", value=True, key="filter_scope3")

    # BigQuery Cache Control
    st.markdown("---")
    if st.button("🔄 Refresh Data Cache", key="btn_refresh_cache", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Cached rows: {len(df_raw):,} | Data Source: {data_metadata['source']}")


# ==============================================================================
# Filter Execution & Safe Scope Handling
# ==============================================================================

if not (include_s1 or include_s2 or include_s3):
    st.info("ℹ️ All emission scopes (Scope 1, 2, and 3) are currently excluded. Please check at least one scope in the sidebar to view emissions analytics.")
    st.stop()

if not selected_regions:
    selected_regions = all_regions
if not selected_departments:
    selected_departments = all_departments

# Apply filters
df_filtered = df_raw[
    (df_raw["region"].isin(selected_regions))
    & (df_raw["department"].isin(selected_departments))
    & (df_raw["date"].dt.date >= start_date)
    & (df_raw["date"].dt.date <= end_date)
].copy()

if df_filtered.empty:
    st.warning("⚠️ No records match the active filter criteria. Please broaden your selections.")
    st.stop()

# Synchronize scope columns across df_filtered so all downstream charts receive accurate scoped values
if not include_s1:
    df_filtered["scope1_kg_co2e"] = 0.0
if not include_s2:
    df_filtered["scope2_kg_co2e"] = 0.0
if not include_s3:
    df_filtered["scope3_kg_co2e"] = 0.0
    df_filtered["scope3_flight_kg_co2e"] = 0.0
    df_filtered["scope3_cloud_kg_co2e"] = 0.0

df_filtered["gross_emissions_mt"] = (
    df_filtered["scope1_kg_co2e"] + df_filtered["scope2_kg_co2e"] + df_filtered["scope3_kg_co2e"]
) / 1000.0
df_filtered["net_emissions_mt"] = np.maximum(
    0.0, df_filtered["gross_emissions_mt"] - df_filtered["offsets_purchased_mt"]
)


# ==============================================================================
# Executive Metrics Computation (KPI Layer)
# ==============================================================================

total_gross_mt = float(df_filtered["gross_emissions_mt"].sum())
total_offsets_mt = float(df_filtered["offsets_purchased_mt"].sum())
total_net_mt = float(df_filtered["net_emissions_mt"].sum())
offset_coverage_pct = (total_offsets_mt / total_gross_mt * 100.0) if total_gross_mt > 0 else 0.0

# Calculate Month-over-Month (MoM) Velocity for the latest two completed months
monthly_totals = (
    df_filtered.groupby("date")["gross_emissions_mt"]
    .sum()
    .sort_index()
)

if len(monthly_totals) >= 2:
    latest_month_gross = monthly_totals.iloc[-1]
    prev_month_gross = monthly_totals.iloc[-2]
    mom_pct = calculate_mom_change(latest_month_gross, prev_month_gross)
    mom_delta_label = f"{mom_pct:+.1f}% vs Prev Month"
else:
    mom_pct = 0.0
    mom_delta_label = "Baseline (Single Period)"

# Scope breakdown percentages
total_s1_mt = float(df_filtered["scope1_kg_co2e"].sum() / 1000.0)
total_s2_mt = float(df_filtered["scope2_kg_co2e"].sum() / 1000.0)
total_s3_mt = float(df_filtered["scope3_kg_co2e"].sum() / 1000.0)
scope_breakdown = calculate_scope_breakdown(total_s1_mt, total_s2_mt, total_s3_mt)

# Top emitting units for GenAI briefing
dept_totals = df_filtered.groupby("department")["gross_emissions_mt"].sum()
top_department = dept_totals.idxmax() if not dept_totals.empty else "N/A"
top_dept_mt = dept_totals.max() if not dept_totals.empty else 0.0

reg_totals = df_filtered.groupby("region")["gross_emissions_mt"].sum()
top_region = reg_totals.idxmax() if not reg_totals.empty else "N/A"


# ==============================================================================
# Executive Metrics Grid
# ==============================================================================

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(
        label="Total Gross Emissions",
        value=f"{total_gross_mt:,.1f} MT",
        delta=mom_delta_label,
        delta_color="inverse" if len(monthly_totals) >= 2 else "off",
        help="Aggregated Scope 1, 2, and 3 emissions in Metric Tons CO2e.",
    )

with kpi_col2:
    mom_direction = "Decarbonizing" if mom_pct < 0 else "Increasing"
    st.metric(
        label="MoM Velocity",
        value=f"{mom_pct:+.2f}%",
        delta=f"Trend: {mom_direction}" if len(monthly_totals) >= 2 else "Single Period",
        delta_color="off",
        help="Month-over-month rate of change in gross carbon footprint.",
    )

with kpi_col3:
    st.metric(
        label="Offsets Purchased",
        value=f"{total_offsets_mt:,.1f} MT",
        delta=f"{offset_coverage_pct:.1f}% Retired Coverage",
        delta_color="normal",
        help="Verified carbon credits retired across certified registries.",
    )

with kpi_col4:
    st.metric(
        label="Net Carbon Emissions",
        value=f"{total_net_mt:,.1f} MT",
        delta=f"-{total_offsets_mt:,.1f} MT Abated",
        delta_color="normal",
        help="Net enterprise emissions: Gross Footprint minus Offsets Applied.",
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# Dashboard BI Tabs
# ==============================================================================

tab_overview, tab_departments, tab_genai, tab_calculator, tab_data = st.tabs([
    "📈 Executive Overview & Trends",
    "🏢 Departmental & Activity Drivers",
    "🤖 GenAI Executive Insights (Gemini 3.8 Flash)",
    "🧮 Carbon Conversion Sandbox",
    "🗄️ Raw Data & BigQuery Lineage",
])


# ------------------------------------------------------------------------------
# Tab 1: Executive Overview & Trends
# ------------------------------------------------------------------------------

with tab_overview:
    col_trend, col_donut = st.columns([2.2, 1.1])
    with col_trend:
        render_plotly_chart(create_monthly_trend_chart(df_filtered), key="chart_monthly_trend")
    with col_donut:
        render_plotly_chart(create_scope_donut_chart(df_filtered), key="chart_scope_donut")

    col_reg, col_driver = st.columns([1.5, 1.5])
    with col_reg:
        render_plotly_chart(create_regional_comparison_chart(df_filtered), key="chart_regional_comp")
    with col_driver:
        render_plotly_chart(create_activity_driver_breakdown(df_filtered), key="chart_activity_drivers")


# ------------------------------------------------------------------------------
# Tab 2: Departmental & Activity Drivers
# ------------------------------------------------------------------------------

with tab_departments:
    st.markdown("#### 🏢 Enterprise Business Unit Breakdown & Efficiency KPIs")
    st.caption("Analyze decarbonization performance and resource intensity across operating units.")

    render_plotly_chart(create_department_bar_chart(df_filtered), key="chart_dept_bars")

    # Departmental KPI Summary Table
    st.markdown("##### 📊 Departmental Intensity & Activity Scorecard")
    dept_table = (
        df_filtered.groupby("department")
        .agg({
            "fte_headcount": "mean",
            "operational_spend_m_usd": "sum",
            "gross_emissions_mt": "sum",
            "offsets_purchased_mt": "sum",
            "net_emissions_mt": "sum",
            "electricity_kwh": "sum",
            "flight_km": "sum",
            "cloud_compute_hours": "sum",
        })
        .reset_index()
    )

    # Carbon Intensity Ratios
    dept_table["mt_per_fte"] = (dept_table["gross_emissions_mt"] / dept_table["fte_headcount"]).round(2)
    dept_table["mt_per_m_spend"] = (dept_table["gross_emissions_mt"] / dept_table["operational_spend_m_usd"]).round(2)

    # Format Display
    dept_display = dept_table.rename(columns={
        "department": "Business Unit",
        "fte_headcount": "Avg FTE Headcount",
        "operational_spend_m_usd": "Total Spend ($M)",
        "gross_emissions_mt": "Gross Emissions (MT)",
        "offsets_purchased_mt": "Offsets (MT)",
        "net_emissions_mt": "Net Emissions (MT)",
        "mt_per_fte": "MT / FTE",
        "mt_per_m_spend": "MT / $M Spend",
        "electricity_kwh": "Electricity (kWh)",
        "flight_km": "Flights (km)",
        "cloud_compute_hours": "Cloud Core-Hours",
    })

    st.dataframe(
        dept_display.style.format({
            "Avg FTE Headcount": "{:,.0f}",
            "Total Spend ($M)": "${:,.1f}M",
            "Gross Emissions (MT)": "{:,.1f}",
            "Offsets (MT)": "{:,.1f}",
            "Net Emissions (MT)": "{:,.1f}",
            "MT / FTE": "{:.2f}",
            "MT / $M Spend": "{:.2f}",
            "Electricity (kWh)": "{:,.0f}",
            "Flights (km)": "{:,.0f}",
            "Cloud Core-Hours": "{:,.0f}",
        }),
        width="stretch",
        hide_index=True,
    )


# ------------------------------------------------------------------------------
# Tab 3: GenAI Executive Insights (Gemini 3.8 Flash)
# ------------------------------------------------------------------------------

with tab_genai:
    st.markdown("### 🤖 C-Suite GenAI Executive Insights Engine")
    st.markdown(
        "Powered by **Gemini 3.8 Flash** (`google-genai` SDK). "
        "Synthesizes active filtered metrics into strategic, C-suite ready briefings, "
        "Science-Based Targets (SBTi) evaluations, and decarbonization levers."
    )

    # Prepare summary dictionary
    flight_mt = float(df_filtered["scope3_flight_kg_co2e"].sum() / 1000.0)
    cloud_mt = float(df_filtered["scope3_cloud_kg_co2e"].sum() / 1000.0)

    metrics_payload = {
        "date_range_label": f"{start_date.strftime('%b %Y')} to {end_date.strftime('%b %Y')}",
        "departments_count": len(selected_departments),
        "regions_label": ", ".join(selected_regions),
        "total_gross_mt": total_gross_mt,
        "total_offsets_mt": total_offsets_mt,
        "total_net_mt": total_net_mt,
        "offset_coverage_pct": offset_coverage_pct,
        "mom_change_pct": mom_pct,
        "scope1_mt": total_s1_mt,
        "scope2_mt": total_s2_mt,
        "scope3_mt": total_s3_mt,
        "scope1_pct": scope_breakdown["Scope 1"],
        "scope2_pct": scope_breakdown["Scope 2"],
        "scope3_pct": scope_breakdown["Scope 3"],
        "flight_mt": flight_mt,
        "cloud_mt": cloud_mt,
        "top_department": top_department,
        "top_dept_mt": top_dept_mt,
        "top_region": top_region,
    }

    # Configuration Expander
    with st.expander("⚙️ Gemini API Configuration & Key Settings", expanded=False):
        env_key = get_gemini_api_key()
        if env_key:
            st.success("✅ GEMINI_API_KEY detected in environment.")
        else:
            st.info("ℹ️ No GEMINI_API_KEY environment variable detected. Using built-in analytical briefing engine. You can paste a Gemini key below to run live.")
        
        user_api_key = st.text_input(
            "Gemini API Key Override (Optional)",
            type="password",
            value="",
            placeholder="AIzaSy...",
            help="Your key is kept only in session memory.",
            key="input_gemini_api_key",
        )

    # What-If Scenario Input
    col_scenario, col_btn = st.columns([3, 1])
    with col_scenario:
        scenario_text = st.text_input(
            "What-If Decarbonization Scenario Simulation:",
            value="Mandate 30% Sustainable Aviation Fuel (SAF) for corporate flights and migrate 40% of cloud workloads to carbon-neutral GCP regions.",
            help="Enter any operational hypothesis to model projected carbon savings.",
            key="input_scenario_simulation",
        )
    with col_btn:
        st.write("")
        st.write("")
        generate_btn = st.button("🚀 Generate Briefing", type="primary", width="stretch", key="btn_generate_briefing")

    # Output Container: Automatically update if filters change or button is clicked
    current_filter_signature = f"{sorted(selected_departments)}_{sorted(selected_regions)}_{start_date}_{end_date}_{include_s1}_{include_s2}_{include_s3}_{round(total_gross_mt, 1)}_{scenario_text}"

    if generate_btn or st.session_state.get("last_insights_sig") != current_filter_signature:
        with st.spinner("Analyzing portfolio emissions with Gemini 3.8 Flash..."):
            key_to_use = user_api_key.strip() if user_api_key.strip() else None
            insights_result = generate_executive_insights(
                metrics_summary=metrics_payload,
                custom_scenario=scenario_text if scenario_text else None,
                api_key_override=key_to_use,
            )
            st.session_state["cached_insights"] = insights_result
            st.session_state["last_insights_sig"] = current_filter_signature

    # Display Result
    st.markdown("---")
    st.markdown(st.session_state.get("cached_insights", ""))


# ------------------------------------------------------------------------------
# Tab 4: Carbon Conversion Sandbox
# ------------------------------------------------------------------------------

with tab_calculator:
    st.markdown("### 🧮 Interactive Carbon Conversion Sandbox (`src/calculator.py`)")
    st.markdown(
        "Test and validate the modular carbon conversion functions in real-time. "
        "All calculations strictly implement EPA eGRID, DEFRA 2024, and Cloud Carbon Footprint models."
    )

    calc_tab1, calc_tab2, calc_tab3, calc_tab4 = st.tabs([
        "⚡ Scope 2: Electricity (kWh)",
        "✈️ Scope 3: Commercial Flights (km)",
        "☁️ Scope 3: Cloud Compute (Hours)",
        "🔥 Scope 1: Direct Fuels & Heating",
    ])

    with calc_tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            test_kwh = st.number_input("Electricity Consumed (kWh):", min_value=0.0, value=150000.0, step=5000.0, key="sb_elec_kwh")
        with c2:
            test_grid_reg = st.selectbox(
                "Grid Region:",
                options=[
                    "North America (NAM)",
                    "Europe, Middle East & Africa (EMEA)",
                    "Asia-Pacific (APAC)",
                    "Latin America (LATAM)",
                    "Global Average",
                ],
                key="sb_elec_reg",
            )
        with c3:
            test_renew_pct = st.slider("Renewable PPA Coverage (%):", min_value=0.0, max_value=100.0, value=35.0, key="sb_elec_renew")

        calc_elec_kg = kwh_to_kg_co2e(test_kwh, region=test_grid_reg, renewable_pct=test_renew_pct)
        calc_elec_mt = kg_to_metric_tons(calc_elec_kg)
        st.success(f"**Result:** `{calc_elec_kg:,.2f} kgCO2e` ({calc_elec_mt:,.4f} Metric Tons CO2e)")

    with calc_tab2:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            test_km = st.number_input("Flight Distance (km):", min_value=0.0, value=250000.0, step=10000.0, key="sb_flight_km")
        with f2:
            test_haul = st.selectbox("Haul Category:", options=["short", "medium", "long"], index=1, key="sb_flight_haul")
        with f3:
            test_cabin = st.selectbox("Cabin Class:", options=["economy", "premium_economy", "business", "first"], index=0, key="sb_flight_cabin")
        with f4:
            test_rfi = st.checkbox("Radiative Forcing Index (RFI)", value=True, key="sb_flight_rfi")

        calc_flight_kg = flight_km_to_kg_co2e(test_km, haul_type=test_haul, cabin_class=test_cabin, include_radiative_forcing=test_rfi)
        calc_flight_mt = kg_to_metric_tons(calc_flight_kg)
        st.success(f"**Result:** `{calc_flight_kg:,.2f} kgCO2e` ({calc_flight_mt:,.4f} Metric Tons CO2e)")

    with calc_tab3:
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            test_compute_hrs = st.number_input("Compute Core-Hours:", min_value=0.0, value=500000.0, step=25000.0, key="sb_cloud_hrs")
        with cc2:
            test_inst = st.selectbox("Instance Hardware Tier:", options=["standard_vcpu", "highmem_vcpu", "gpu_accelerated"], index=0, key="sb_cloud_inst")
        with cc3:
            test_prov = st.selectbox("Infrastructure Provider:", options=["gcp", "aws", "azure", "on_premise"], index=0, key="sb_cloud_prov")
        with cc4:
            test_cloud_reg = st.selectbox(
                "Datacenter Region:",
                options=["North America (NAM)", "Europe, Middle East & Africa (EMEA)", "Asia-Pacific (APAC)", "Latin America (LATAM)"],
                key="sb_cloud_reg",
            )

        calc_cloud_kg = cloud_compute_hours_to_kg_co2e(test_compute_hrs, instance_type=test_inst, provider=test_prov, region=test_cloud_reg)
        calc_cloud_mt = kg_to_metric_tons(calc_cloud_kg)
        st.success(f"**Result:** `{calc_cloud_kg:,.2f} kgCO2e` ({calc_cloud_mt:,.4f} Metric Tons CO2e)")

    with calc_tab4:
        fu1, fu2 = st.columns(2)
        with fu1:
            test_fuel_vol = st.number_input("Combustion Fuel Volume (Liters / m³):", min_value=0.0, value=8500.0, step=500.0, key="sb_fuel_vol")
        with fu2:
            test_fuel_type = st.selectbox("Fuel Source:", options=["gasoline_liter", "diesel_liter", "natural_gas_m3", "propane_liter"], key="sb_fuel_type")

        calc_fuel_kg = fuel_liters_to_kg_co2e(test_fuel_vol, fuel_type=test_fuel_type)
        calc_fuel_mt = kg_to_metric_tons(calc_fuel_kg)
        st.success(f"**Result:** `{calc_fuel_kg:,.2f} kgCO2e` ({calc_fuel_mt:,.4f} Metric Tons CO2e)")


# ------------------------------------------------------------------------------
# Tab 5: Raw Data & BigQuery Lineage
# ------------------------------------------------------------------------------

with tab_data:
    st.markdown("### 🗄️ Enterprise Data Lakehouse Lineage & Mart Schema")
    st.caption("Inspect filtered dataset records, export reports, and review BigQuery table DDL.")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.json({
            "Source": data_metadata.get("source"),
            "GCP Project": data_metadata.get("project"),
            "BigQuery Dataset": data_metadata.get("dataset"),
            "Active Filtered Rows": len(df_filtered),
            "Total Ingested Rows": len(df_raw),
            "BigQuery Caching": "@st.cache_data (TTL=3600s)",
            "Data Governance": "Strict Anonymization & Synthetic Scrubbing",
        })

    with col_meta2:
        csv_export = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered ESG Mart (CSV)",
            data=csv_export,
            file_name=f"amex_esg_carbon_mart_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary",
            key="btn_download_csv",
            width="stretch",
        )
        st.caption("Exports sanitized dataset containing all activity records, Scopes 1-3, and net offsets.")

    st.markdown("---")
    st.markdown("##### 📋 Filtered Records Explorer")
    st.dataframe(df_filtered.head(100), width="stretch", hide_index=True)

    with st.expander("🛠️ BigQuery Mart Production DDL Schema"):
        st.code(get_bigquery_schema_ddl(), language="sql")
