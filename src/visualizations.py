"""Plotly Data Visualizations for Amex Scaled Analytics & BI.

Implements executive-grade, interactive ESG charts styled with American Express
enterprise design tokens (Amex Deep Navy, Electric Blue, Amex Cyan, and Emerald ESG Accents).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Amex Enterprise Design Tokens
AMEX_NAVY = "#002663"
AMEX_BLUE = "#006FCF"
AMEX_CYAN = "#00A3E0"
AMEX_SLATE = "#4D4F53"
AMEX_EMERALD = "#00875A"
AMEX_AMBER = "#E67E22"
AMEX_CRIMSON = "#D9381E"
AMEX_BG_LIGHT = "#F8FAFC"
AMEX_CARD_BORDER = "#E2E8F0"

PLOTLY_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif", color="#1E293B"),
    hoverlabel=dict(
        bgcolor="#002663",
        font_size=12,
        font_color="#FFFFFF",
        font_family="Inter, sans-serif",
    ),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11),
    ),
)


def create_monthly_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Create monthly carbon emissions trend line with Scope layers and Net trajectory.

    Args:
        df: Filtered ESG DataFrame.

    Returns:
        Plotly Figure with interactive tooltips and historical trajectory.
    """
    # Group by month
    monthly = (
        df.groupby("date")
        .agg({
            "scope1_kg_co2e": "sum",
            "scope2_kg_co2e": "sum",
            "scope3_kg_co2e": "sum",
            "gross_emissions_mt": "sum",
            "offsets_purchased_mt": "sum",
            "net_emissions_mt": "sum",
            "sbti_target_max_mt": "sum",
        })
        .reset_index()
    )

    monthly["scope1_mt"] = monthly["scope1_kg_co2e"] / 1000.0
    monthly["scope2_mt"] = monthly["scope2_kg_co2e"] / 1000.0
    monthly["scope3_mt"] = monthly["scope3_kg_co2e"] / 1000.0
    # 3-Month Moving Average
    monthly["gross_3m_ma"] = monthly["gross_emissions_mt"].rolling(window=3, min_periods=1).mean()

    fig = go.Figure()

    # Scope 1 Area
    fig.add_trace(
        go.Bar(
            x=monthly["date"],
            y=monthly["scope1_mt"],
            name="Scope 1 (Direct Facilities)",
            marker_color=AMEX_AMBER,
            opacity=0.85,
            hovertemplate="<b>Scope 1</b>: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    # Scope 2 Area
    fig.add_trace(
        go.Bar(
            x=monthly["date"],
            y=monthly["scope2_mt"],
            name="Scope 2 (Electricity)",
            marker_color=AMEX_CYAN,
            opacity=0.85,
            hovertemplate="<b>Scope 2</b>: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    # Scope 3 Area
    fig.add_trace(
        go.Bar(
            x=monthly["date"],
            y=monthly["scope3_mt"],
            name="Scope 3 (Value Chain)",
            marker_color=AMEX_BLUE,
            opacity=0.85,
            hovertemplate="<b>Scope 3</b>: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    # Net Emissions Line
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["net_emissions_mt"],
            name="Net Emissions (Post-Offsets)",
            mode="lines+markers",
            line=dict(color=AMEX_EMERALD, width=3),
            marker=dict(size=6, symbol="circle"),
            hovertemplate="<b>Net Emissions</b>: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    # 3-Month Rolling Average Line
    fig.add_trace(
        go.Scatter(
            x=monthly["date"],
            y=monthly["gross_3m_ma"],
            name="3M Gross Rolling Avg",
            mode="lines",
            line=dict(color=AMEX_NAVY, width=2, dash="dash"),
            hovertemplate="<b>3M Moving Avg</b>: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        barmode="stack",
        title=dict(
            text="<b>Monthly Carbon Emissions & Decarbonization Trajectory</b>",
            font=dict(size=15, color=AMEX_NAVY),
            x=0.01,
        ),
        xaxis=dict(
            title="",
            tickformat="%b %Y",
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Emissions (Metric Tons CO2e)",
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False,
        ),
    )
    return fig


def create_scope_donut_chart(df: pd.DataFrame) -> go.Figure:
    """Create donut chart showing distribution across Scope 1, Scope 2, and Scope 3."""
    total_s1 = df["scope1_kg_co2e"].sum() / 1000.0
    total_s2 = df["scope2_kg_co2e"].sum() / 1000.0
    total_s3 = df["scope3_kg_co2e"].sum() / 1000.0
    total_gross = total_s1 + total_s2 + total_s3

    if total_gross <= 0:
        fig = go.Figure()
        fig.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            title=dict(
                text="<b>Emissions by GHG Scope</b>",
                font=dict(size=15, color=AMEX_NAVY),
                x=0.01,
            ),
            annotations=[
                dict(
                    text="<b>0 MT CO2e</b><br><span style='font-size:11px;color:#64748B;'>No Active Scope Emissions</span>",
                    x=0.5,
                    y=0.5,
                    font_size=15,
                    font_color=AMEX_NAVY,
                    showarrow=False,
                )
            ],
        )
        return fig

    labels = ["Scope 1 (Direct)", "Scope 2 (Electricity)", "Scope 3 (Value Chain)"]
    values = [total_s1, total_s2, total_s3]
    colors = [AMEX_AMBER, AMEX_CYAN, AMEX_BLUE]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="percent",
                hoverinfo="label+value+percent",
                hovertemplate="<b>%{label}</b><br>%{value:,.1f} MT CO2e (%{percent})<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        title=dict(
            text="<b>Emissions by GHG Scope</b>",
            font=dict(size=15, color=AMEX_NAVY),
            x=0.01,
        ),
        annotations=[
            dict(
                text=f"<b>{total_gross:,.0f}</b><br><span style='font-size:11px;color:#64748B;'>Gross MT CO2e</span>",
                x=0.5,
                y=0.5,
                font_size=16,
                font_color=AMEX_NAVY,
                showarrow=False,
            )
        ],
    )
    return fig


def create_department_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Create ranked horizontal bar chart of emissions across departments."""
    dept_agg = (
        df.groupby("department")
        .agg({
            "gross_emissions_mt": "sum",
            "net_emissions_mt": "sum",
            "offsets_purchased_mt": "sum",
        })
        .reset_index()
        .sort_values(by="gross_emissions_mt", ascending=True)
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=dept_agg["department"],
            x=dept_agg["gross_emissions_mt"],
            orientation="h",
            name="Gross Emissions",
            marker=dict(
                color=AMEX_BLUE,
                opacity=0.9,
                line=dict(color=AMEX_NAVY, width=1),
            ),
            hovertemplate="<b>%{y}</b><br>Gross: %{x:,.1f} MT CO2e<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            y=dept_agg["department"],
            x=dept_agg["net_emissions_mt"],
            orientation="h",
            name="Net Emissions",
            marker=dict(
                color=AMEX_EMERALD,
                opacity=0.9,
            ),
            hovertemplate="<b>%{y}</b><br>Net: %{x:,.1f} MT CO2e<extra></extra>",
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        barmode="group",
        title=dict(
            text="<b>Emissions by Enterprise Department</b>",
            font=dict(size=15, color=AMEX_NAVY),
            x=0.01,
        ),
        xaxis=dict(
            title="Metric Tons CO2e",
            showgrid=True,
            gridcolor="#F1F5F9",
        ),
        yaxis=dict(title="", tickfont=dict(size=11)),
    )
    return fig


def create_activity_driver_breakdown(df: pd.DataFrame) -> go.Figure:
    """Create breakdown of key enterprise emission activity categories."""
    total_electricity = (df["scope2_kg_co2e"].sum()) / 1000.0
    total_flights = (df["scope3_flight_kg_co2e"].sum()) / 1000.0
    total_cloud = (df["scope3_cloud_kg_co2e"].sum()) / 1000.0
    total_scope1 = (df["scope1_kg_co2e"].sum()) / 1000.0
    total_other_s3 = (
        (df["scope3_kg_co2e"].sum() - df["scope3_flight_kg_co2e"].sum() - df["scope3_cloud_kg_co2e"].sum())
        / 1000.0
    )

    drivers_df = pd.DataFrame({
        "Activity Category": [
            "Purchased Electricity (Scope 2)",
            "Commercial Flights (Scope 3)",
            "Cloud Infrastructure (Scope 3)",
            "Direct Facilities & Fleet (Scope 1)",
            "Commuting & Supply Chain (Scope 3)",
        ],
        "Emissions MT": [
            total_electricity,
            total_flights,
            total_cloud,
            total_scope1,
            max(0.0, total_other_s3),
        ],
    }).sort_values(by="Emissions MT", ascending=False)

    colors = [AMEX_NAVY, AMEX_BLUE, AMEX_CYAN, AMEX_AMBER, "#8B95A5"]

    fig = px.bar(
        drivers_df,
        x="Activity Category",
        y="Emissions MT",
        color="Activity Category",
        color_discrete_sequence=colors,
        text_auto=",.1f",
    )

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        showlegend=False,
        title=dict(
            text="<b>Key Activity Drivers (Decarbonization Levers)</b>",
            font=dict(size=15, color=AMEX_NAVY),
            x=0.01,
        ),
        xaxis=dict(title="", tickangle=-15, tickfont=dict(size=11)),
        yaxis=dict(title="Emissions (MT CO2e)", showgrid=True, gridcolor="#F1F5F9"),
    )
    return fig


def create_regional_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Create regional performance chart showing gross footprint and renewable energy %."""
    reg_agg = (
        df.groupby("region")
        .agg({
            "gross_emissions_mt": "sum",
            "net_emissions_mt": "sum",
            "renewable_energy_pct": "mean",
            "electricity_kwh": "sum",
        })
        .reset_index()
        .sort_values(by="gross_emissions_mt", ascending=False)
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=reg_agg["region"],
            y=reg_agg["gross_emissions_mt"],
            name="Gross Emissions (MT)",
            marker_color=AMEX_BLUE,
            yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Gross: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=reg_agg["region"],
            y=reg_agg["net_emissions_mt"],
            name="Net Emissions (MT)",
            marker_color=AMEX_EMERALD,
            yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Net: %{y:,.1f} MT CO2e<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=reg_agg["region"],
            y=reg_agg["renewable_energy_pct"],
            name="Avg Renewable Energy %",
            mode="lines+markers",
            marker=dict(size=9, color=AMEX_AMBER, symbol="diamond"),
            line=dict(width=3, color=AMEX_AMBER),
            yaxis="y2",
            hovertemplate="<b>Renewable Share</b>: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        **PLOTLY_LAYOUT_DEFAULTS,
        barmode="group",
        title=dict(
            text="<b>Regional Footprint & Clean Energy Adoption</b>",
            font=dict(size=15, color=AMEX_NAVY),
            x=0.01,
        ),
        xaxis=dict(title=""),
        yaxis=dict(
            title="Emissions (MT CO2e)",
            showgrid=True,
            gridcolor="#F1F5F9",
        ),
        yaxis2=dict(
            title="Renewables (%)",
            overlaying="y",
            side="right",
            range=[0, 100],
            showgrid=False,
            ticksuffix="%",
        ),
    )
    return fig
