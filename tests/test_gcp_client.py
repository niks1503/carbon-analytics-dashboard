"""Unit tests for src/gcp_client.py BigQuery client and CSV fallback."""

import pandas as pd
from src.gcp_client import _clean_and_cast_dataframe, fetch_carbon_data, get_bigquery_schema_ddl


def test_fetch_carbon_data_fallback():
    """Verify that when no GCP credentials are set, it falls back cleanly to local CSV."""
    df, metadata = fetch_carbon_data()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert metadata["source"] == "Local CSV (Scrubbed Anonymized Mock)"
    assert metadata["is_fallback"] is True
    assert "date" in df.columns
    assert "gross_emissions_mt" in df.columns
    assert "net_emissions_mt" in df.columns


def test_clean_and_cast_dataframe():
    """Verify date parsing and numeric coercion."""
    raw_dict = {
        "record_id": ["REC-1"],
        "date": ["2024-05-01"],
        "department": ["Global Commercial Services"],
        "region": ["North America (NAM)"],
        "gross_emissions_mt": ["120.5"],
        "offsets_purchased_mt": ["20.0"],
    }
    df = pd.DataFrame(raw_dict)
    cleaned = _clean_and_cast_dataframe(df)

    assert pd.api.types.is_datetime64_any_dtype(cleaned["date"])
    assert cleaned["gross_emissions_mt"].iloc[0] == 120.5
    assert cleaned["year_month"].iloc[0] == "2024-05"


def test_bigquery_schema_ddl():
    """Verify production BigQuery DDL generation contains partitioning and clustering."""
    ddl = get_bigquery_schema_ddl(project_id="test-proj", dataset_id="test-ds", table_id="test-tbl")
    assert "CREATE OR REPLACE TABLE `test-proj.test-ds.test-tbl`" in ddl
    assert "PARTITION BY date" in ddl
    assert "CLUSTER BY department, region" in ddl
