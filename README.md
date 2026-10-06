# Carbon & ESG Footprint Analytics Dashboard

[![Streamlit](https://img.shields.io/badge/Streamlit-1.65+-FF4B4B.svg)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/GCP-BigQuery%20%7C%20Cloud%20Run-4285F4.svg)](https://cloud.google.com/)
[![Gemini](https://img.shields.io/badge/GenAI-Gemini%203.8%20Flash-8E75C2.svg)](https://ai.google.dev/)
[![GHG Protocol](https://img.shields.io/badge/Standard-GHG%20Protocol%20Scopes%201%2C%202%2C%203-00875A.svg)](https://ghgprotocol.org/)

A production-ready Enterprise Carbon & ESG Analytics Dashboard tailored for the **Scaled Analytics & BI** function at **American Express**. Built to ingest, calculate, model, and visualize corporate greenhouse gas emissions across **Scope 1 (Direct)**, **Scope 2 (Electricity)**, and **Scope 3 (Value Chain: Business Flights, Cloud Infrastructure)** with automated C-Suite briefings powered by Google Gemini 3.8 Flash.

---

## 🏛️ Architecture Overview

The platform is designed with a decoupled, enterprise lakehouse architecture. Data is queried from Google Cloud BigQuery with Streamlit caching (`@st.cache_data`) for sub-second dashboard rendering, falling back cleanly to an anonymized synthetic dataset for local development or disconnected environments.

```mermaid
flowchart TD
    subgraph Data_Tier ["1. Enterprise Data Lakehouse"]
        BQ[("GCP BigQuery Mart<br/>`anonymized_carbon_footprint_monthly`<br/>Partitioned by Date & Clustered")]
        CSV[("Anonymized Sample CSV<br/>`data/anonymized_sample_data.csv`<br/>576 Synthetic Records across 24 Months")]
    end

    subgraph Service_Tier ["2. Data Ingestion & Caching Layer"]
        GCP_CLIENT["`src/gcp_client.py`<br/>• @st.cache_data(ttl=3600)<br/>• Ambient Cloud Run Auth Check<br/>• Automated Local CSV Fallback"]
        CALC["`src/calculator.py`<br/>• kWh → kgCO2e (EPA eGRID / Regional Grid)<br/>• Flight km → kgCO2e (DEFRA RFI Models)<br/>• Cloud Hours → kgCO2e (GCP PUE & CCF)<br/>• Net Emissions & MoM Velocity"]
    end

    subgraph Intelligence_Tier ["3. GenAI Executive Insights"]
        GENAI["`src/genai_insights.py`<br/>• google-genai SDK (gemini-3.8-flash)<br/>• C-Suite Executive Briefing<br/>• What-If Scenario Decarbonization Simulator<br/>• Statistical Fallback Engine"]
    end

    subgraph Presentation_Tier ["4. Executive BI Dashboard (app.py)"]
        UI["Streamlit Executive BI Layer<br/>• Amex Corporate Design System<br/>• Multi-Select Filters (Region, Dept, Date, Scope)<br/>• KPI Tiles: Gross MT, MoM %, Offsets, Net MT<br/>• Plotly Visuals: Trendline, Scope Donut, Drivers<br/>• Interactive Conversion Sandbox"]
    end

    subgraph Deployment_Tier ["5. Production Containerization"]
        DOCKER["Docker Container<br/>• Python 3.11-slim Base<br/>• Non-Root Security (appuser)<br/>• Healthcheck Endpoint (/_stcore/health)"]
        CLOUD_RUN["Google Cloud Run<br/>• Serverless Autoscaling<br/>• Dynamic Port Binding ($PORT: 8080)"]
    end

    BQ -.-> GCP_CLIENT
    CSV -.-> GCP_CLIENT
    GCP_CLIENT --> CALC
    CALC --> UI
    UI --> GENAI
    UI --> DOCKER
    DOCKER --> CLOUD_RUN
```

---

## 🌟 Key Capabilities

### 1. Mathematical Rigor & GHG Protocol Calculations (`src/calculator.py`)
* **Scope 2 (Electricity)**: Implements regional grid emission factors (EPA eGRID 2024 for North America, EEA for EMEA, IEA for APAC/LATAM) with dynamic Virtual Power Purchase Agreement (PPA) and Renewable Energy Certificate (REC) offset discounts.
* **Scope 3 Category 6 (Commercial Flights)**: Incorporates short, medium, and long-haul factors (DEFRA 2024) with seating class multipliers (Economy, Business, First) and Radiative Forcing Index (RFI ~1.9x).
* **Scope 3 Category 1/8 (Cloud Compute)**: Implements Cloud Carbon Footprint (CCF) energy models multiplying instance power draw (kW) by datacenter Power Usage Effectiveness (PUE: 1.10 for GCP) and regional grid intensity.
* **Scope 1 (Direct Combustion)**: Converts fleet fuels and natural gas heating into direct kgCO2e emissions.
* **Net Footprint & Offsets**: Reconciles certified carbon credit retirements against gross emissions.

### 2. Executive BI Layer (`app.py`)
* **Executive Metrics Grid**: Displays Gross Emissions (MT CO2e), Month-over-Month (MoM) velocity with directional trend colors, Offsets Purchased, and Net Emissions.
* **Multi-Dimensional Filtering**: Dynamic slicing across Business Units (Global Commercial Services, Technology & Infrastructure, Consumer Services, etc.), Operating Theaters (NAM, EMEA, APAC, LATAM), Date Ranges, and Scopes.
* **Plotly Visualizations**:
  * Monthly Stacked Emissions Trend with 3-Month Moving Average.
  * Emissions distribution Donut by GHG Scope.
  * Ranked Departmental Footprint & Carbon Intensity Scorecard (MT / FTE, MT / $M Spend).
  * Regional footprint comparison with renewable energy adoption line.
  * Primary activity driver breakdown (Waterfall/Bar).
* **Interactive Sandbox**: Live calculator for operational teams to simulate individual asset conversions.

### 3. GenAI C-Suite Insights (`src/genai_insights.py`)
* Powered by the modern `google-genai` SDK and **Gemini 3.8 Flash**.
* Ingests real-time filtered metrics to generate:
  * Executive Scorecard with portfolio headwinds and decarbonization velocity.
  * Key driver diagnostic highlighting flight travel vs cloud infrastructure tradeoffs.
  * Top 3 Strategic Decarbonization Levers (Sustainable Aviation Fuel mandates, Green FinOps compute routing, Campus PPAs).
  * What-If Scenario Evaluation (e.g., *"Shift 40% of cloud workloads to low-carbon GCP regions and mandate 25% SAF on transatlantic travel"*).
  * High-precision analytical fallback engine when run offline or without API keys.

### 4. BigQuery Ingestion & Production Readiness (`src/gcp_client.py`)
* Implements `@st.cache_data(ttl=3600)` to optimize BigQuery query costs.
* Automatic fallback to synthetic dataset (`data/anonymized_sample_data.csv`) if GCP credentials are not detected.
* Production DDL generator with table partitioning by date and clustering by department and region.

---

## 📁 Repository Structure

```
.
├── app.py                         # Streamlit Executive BI Dashboard
├── Dockerfile                     # Production multi-stage Dockerfile for Cloud Run
├── requirements.txt               # Locked production dependencies
├── .gitignore                     # Git exclusions (excluding .env and secrets)
├── README.md                      # Comprehensive architecture and setup guide
├── data/
│   └── anonymized_sample_data.csv # 576 scrubbed, anonymized monthly ESG records
├── src/
│   ├── __init__.py
│   ├── calculator.py              # Modular GHG Protocol carbon conversion functions
│   ├── gcp_client.py              # BigQuery integration with @st.cache_data & CSV fallback
│   ├── genai_insights.py          # Gemini 3.8 Flash executive briefings & scenario engine
│   ├── generate_sample_data.py    # Deterministic synthetic data generation utility
│   └── visualizations.py          # Amex-styled Plotly charts
└── tests/
    ├── test_app.py                # Streamlit AppTest integration verification
    ├── test_calculator.py         # Unit tests for carbon conversion functions
    ├── test_gcp_client.py         # Unit tests for BigQuery client & caching fallback
    └── test_genai_insights.py     # Unit tests for GenAI briefing & fallback engine
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
* Python 3.11+
* Git
* Optional: Google Cloud SDK (`gcloud`), Docker

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone <repository_url>
cd "Carbon & ESG Footprint Analytics Dashboard"

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)

Create a `.env` file in the root directory (never committed to git):

```env
# Optional: Live Google Gemini API Key for dynamic C-suite briefings
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Google Cloud BigQuery configuration
GCP_PROJECT_ID=amex-analytics-prod
BIGQUERY_DATASET=esg_carbon_mart
BIGQUERY_TABLE=anonymized_carbon_footprint_monthly
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service_account.json
```

> **Note:** If `GEMINI_API_KEY` or GCP credentials are not configured, the dashboard automatically activates the built-in deterministic analytical briefing engine and local sample dataset.

### 3. Run Unit Tests

Execute the automated test suite verifying all conversion functions, BigQuery caching logic, and Streamlit execution:

```bash
PYTHONPATH=. pytest -v tests/
```

### 4. Run the Dashboard Locally

```bash
streamlit run app.py
```

The application will be accessible at `http://localhost:8501`.

---

## 🐳 Docker & GCP Cloud Run Deployment

### Local Container Build & Run

```bash
# Build the production Docker image
docker build -t amex-esg-dashboard:latest .

# Run container locally on port 8080
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e GEMINI_API_KEY="your_api_key" \
  amex-esg-dashboard:latest
```

Visit `http://localhost:8080` to interact with the containerized application.

### Deploy to Google Cloud Run

```bash
# 1. Set your GCP project
gcloud config set project YOUR_GCP_PROJECT_ID

# 2. Build and push image to Google Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_GCP_PROJECT_ID/amex-esg-dashboard:latest

# 3. Deploy to Cloud Run with public/internal access and 1Gi memory
gcloud run deploy amex-esg-dashboard \
  --image gcr.io/YOUR_GCP_PROJECT_ID/amex-esg-dashboard:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars="BIGQUERY_DATASET=esg_carbon_mart,BIGQUERY_TABLE=anonymized_carbon_footprint_monthly"
```

---

## 🔒 Data Governance & Anonymization

In strict compliance with American Express enterprise data governance and cybersecurity policies:
1. **Zero Proprietary Data**: All data contained in `data/anonymized_sample_data.csv` is completely synthetic, generated programmatically using standard statistical normal distributions with seasonal noise.
2. **Zero Internal Customer Data**: No customer accounts, cardholder data, vendor identifiers, or proprietary financial metrics are included.
3. **Secrets Protection**: All keys, `.env` files, and credentials are intentionally excluded via `.gitignore`.
