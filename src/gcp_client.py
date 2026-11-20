"""GCP BigQuery integration module for Scaled Analytics & BI.

Implements BigQuery connection handling with Streamlit caching (@st.cache_data),
graceful local CSV fallback when GCP credentials are not supplied,
and data quality validation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

# Configure logger
logger = logging.getLogger(__name__)

# Fallback dataset location
LOCAL_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "anonymized_sample_data.csv"

# Default GCP BigQuery Configuration
DEFAULT_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "esg-analytics-prod")
DEFAULT_DATASET_ID = os.getenv("BIGQUERY_DATASET", "esg_carbon_mart")
DEFAULT_TABLE_ID = os.getenv("BIGQUERY_TABLE", "anonymized_carbon_footprint_monthly")


def is_gcp_configured() -> bool:
    """Check if GCP credentials or application default credentials exist."""
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        return True
    # In GCP Cloud Run / Compute Engine / GKE, metadata service provides ambient credentials
    return bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_carbon_data(
    project_id: str = DEFAULT_PROJECT_ID,
    dataset_id: str = DEFAULT_DATASET_ID,
    table_id: str = DEFAULT_TABLE_ID,
    query_override: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch ESG carbon footprint dataset from Google Cloud BigQuery with local CSV fallback.

    Uses Streamlit's @st.cache_data to cache queries in-memory for 1 hour, minimizing
    BigQuery query compute costs and optimizing dashboard responsiveness.

    Args:
        project_id: GCP Project ID.
        dataset_id: BigQuery dataset containing ESG marts.
        table_id: BigQuery table name.
        query_override: Optional custom SQL query to execute.

    Returns:
        A tuple of (pandas DataFrame, metadata dictionary detailing source and status).
    """
    metadata: dict[str, Any] = {
        "source": "BigQuery",
        "status": "pending",
        "project": project_id,
        "dataset": dataset_id,
        "table": table_id,
        "rows": 0,
        "is_fallback": False,
        "error_message": None,
    }

    # Check if GCP environment is configured; if not, immediately use local fallback
    if not is_gcp_configured():
        metadata["source"] = "Local CSV (Scrubbed Anonymized Mock)"
        metadata["status"] = "Fallback Active (Local Mode)"
        metadata["is_fallback"] = True
        df = pd.read_csv(LOCAL_DATA_PATH)
        metadata["rows"] = len(df)
        return _clean_and_cast_dataframe(df), metadata

    try:
        from google.cloud import bigquery

        # Initialize BigQuery Client
        client = bigquery.Client(project=project_id)


        query = query_override or f"""
            SELECT
                record_id,
                date,
                year,
                month,
                department,
                region,
                fte_headcount,
                operational_spend_m_usd,
                electricity_kwh,
                renewable_energy_pct,
                flight_km,
                cloud_compute_hours,
                fuel_liters,
                scope1_kg_co2e,
                scope2_kg_co2e,
                scope3_kg_co2e,
                scope3_flight_kg_co2e,
                scope3_cloud_kg_co2e,
                gross_emissions_mt,
                offsets_purchased_mt,
                net_emissions_mt,
                sbti_target_max_mt
            FROM `{project_id}.{dataset_id}.{table_id}`
            ORDER BY date ASC
        """

        logger.info(f"Executing BigQuery query against {project_id}.{dataset_id}.{table_id}")
        query_job = client.query(query)
        df = query_job.to_dataframe()

        metadata["status"] = "Connected to BigQuery"
        metadata["rows"] = len(df)
        metadata["is_fallback"] = False
        return _clean_and_cast_dataframe(df), metadata

    except Exception as exc:
        logger.warning(
            f"GCP BigQuery connection unavailable or failed ({type(exc).__name__}: {exc}). "
            f"Falling back to local anonymized sample dataset."
        )
        metadata["source"] = "Local CSV (Scrubbed Anonymized Mock)"
        metadata["status"] = "Fallback Active (Local Mode)"
        metadata["is_fallback"] = True
        metadata["error_message"] = str(exc)

        # Fallback to local anonymized CSV
        if not LOCAL_DATA_PATH.exists():
            raise FileNotFoundError(
                f"Neither BigQuery nor local fallback dataset at {LOCAL_DATA_PATH} was found."
            ) from exc

        df = pd.read_csv(LOCAL_DATA_PATH)
        metadata["rows"] = len(df)
        return _clean_and_cast_dataframe(df), metadata


def _clean_and_cast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column datatypes and sort chronologically."""
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])

    numeric_cols = [
        "fte_headcount", "operational_spend_m_usd", "electricity_kwh",
        "renewable_energy_pct", "flight_km", "cloud_compute_hours", "fuel_liters",
        "scope1_kg_co2e", "scope2_kg_co2e", "scope3_kg_co2e",
        "scope3_flight_kg_co2e", "scope3_cloud_kg_co2e",
        "gross_emissions_mt", "offsets_purchased_mt", "net_emissions_mt",
        "sbti_target_max_mt"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Derive month label for BI displays
    if "date" in df.columns:
        df["year_month"] = df["date"].dt.strftime("%Y-%m")
        df["month_name"] = df["date"].dt.strftime("%b %Y")

    return df.sort_values(by="date").reset_index(drop=True)


def get_bigquery_schema_ddl(
    project_id: str = DEFAULT_PROJECT_ID,
    dataset_id: str = DEFAULT_DATASET_ID,
    table_id: str = DEFAULT_TABLE_ID,
) -> str:
    """Generate production BigQuery DDL for enterprise provisioning."""
    return f"""-- Scaled Analytics: BigQuery ESG Mart Table Provisioning
CREATE OR REPLACE TABLE `{project_id}.{dataset_id}.{table_id}`
(
  record_id STRING NOT NULL OPTIONS(description="Unique scrubbed identifier for partition"),
  date DATE NOT NULL OPTIONS(description="Reporting month start date"),
  year STRING OPTIONS(description="Calendar year YYYY"),
  month STRING OPTIONS(description="Calendar month MM"),
  department STRING NOT NULL OPTIONS(description="Enterprise business unit"),
  region STRING NOT NULL OPTIONS(description="Operating geographic theater"),
  fte_headcount INT64 OPTIONS(description="Department regional headcount"),
  operational_spend_m_usd FLOAT64 OPTIONS(description="Allocated OpEx spend in $M"),
  electricity_kwh FLOAT64 OPTIONS(description="Facility and purchased electricity (kWh)"),
  renewable_energy_pct FLOAT64 OPTIONS(description="Renewable contract share (0-100%)"),
  flight_km FLOAT64 OPTIONS(description="Commercial air travel passenger-kilometers"),
  cloud_compute_hours FLOAT64 OPTIONS(description="Virtual compute instance core-hours"),
  fuel_liters FLOAT64 OPTIONS(description="Direct combustion natural gas/fleet volume"),
  scope1_kg_co2e FLOAT64 OPTIONS(description="Direct combustion emissions (kgCO2e)"),
  scope2_kg_co2e FLOAT64 OPTIONS(description="Market-based electricity emissions (kgCO2e)"),
  scope3_kg_co2e FLOAT64 OPTIONS(description="Total value-chain emissions (kgCO2e)"),
  scope3_flight_kg_co2e FLOAT64 OPTIONS(description="Air travel sub-emissions (kgCO2e)"),
  scope3_cloud_kg_co2e FLOAT64 OPTIONS(description="Cloud compute sub-emissions (kgCO2e)"),
  gross_emissions_mt FLOAT64 OPTIONS(description="Gross emissions (MT CO2e)"),
  offsets_purchased_mt FLOAT64 OPTIONS(description="Certified carbon offsets (MT CO2e)"),
  net_emissions_mt FLOAT64 OPTIONS(description="Net emissions post-offsets (MT CO2e)"),
  sbti_target_max_mt FLOAT64 OPTIONS(description="Science-Based Target ceiling (MT CO2e)")
)
PARTITION BY date
CLUSTER BY department, region
OPTIONS(
  description="Curated Enterprise ESG Footprint Mart with Partitioning and Clustering for Scaled BI queries",
  labels=[("data_classification", "anonymized_esg"), ("owner", "scaled_analytics")]
);
"""
