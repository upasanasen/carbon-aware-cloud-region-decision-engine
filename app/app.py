import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(
    page_title="Carbon-Aware Cloud Region Decision Engine",
    layout="wide"
)

# --------------------------
# PATHS
# --------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "regions.csv"

# --------------------------
# DEFAULTS
# --------------------------
DEFAULT_PUE = 1.15
DEFAULT_CARBON_PRICE = 100.0  # €/tCO2e

WORKLOAD_PRESETS = {
    "Small App / API": 150.0,
    "Data Pipeline": 1500.0,
    "ML Inference": 8000.0,
    "Custom": 1000.0
}

# --------------------------
# FUNCTIONS
# --------------------------
def compute(df: pd.DataFrame, kwh_month: float, pue: float, carbon_price: float) -> pd.DataFrame:
    out = df.copy()

    # Monthly tCO2e
    out["monthly_tco2e"] = (kwh_month * pue * out["intensity_gco2e_per_kwh"]) / 1_000_000

    # Annual tCO2e + cost
    out["annual_tco2e"] = out["monthly_tco2e"] * 12
    out["annual_carbon_cost_eur"] = out["annual_tco2e"] * carbon_price

    # Sort by cleanest
    out = out.sort_values("annual_tco2e", ascending=True).reset_index(drop=True)
    out["rank_cleanest"] = out.index + 1
    return out

# --------------------------
# LOAD DATA
# --------------------------
df = pd.read_csv(DATA_PATH)

# Basic sanity: ensure numeric
df["intensity_gco2e_per_kwh"] = pd.to_numeric(df["intensity_gco2e_per_kwh"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

# --------------------------
# HEADER
# --------------------------
st.title("Carbon-Aware Cloud Region Decision Engine")
st.caption(
    "Decision-support prototype for comparing cloud regions using Scope 2 location-based emissions, "
    "PUE-adjusted energy use, internal shadow carbon pricing, and business constraints."
)

# --------------------------
# SIDEBAR INPUTS
# --------------------------
st.sidebar.header("Workload Parameters")
provider_filter = st.sidebar.selectbox(
    "Cloud Provider",
    ["All", "AWS", "Azure", "GCP"]
)

preset = st.sidebar.selectbox("Workload preset", list(WORKLOAD_PRESETS.keys()))

if preset == "Custom":
    kwh_month = st.sidebar.number_input(
        "Monthly workload energy (kWh)",
        min_value=1.0,
        value=WORKLOAD_PRESETS["Custom"],
        step=50.0
    )
else:
    kwh_month = st.sidebar.number_input(
        "Monthly workload energy (kWh)",
        min_value=1.0,
        value=float(WORKLOAD_PRESETS[preset]),
        step=50.0
    )

pue = st.sidebar.slider("PUE", 1.0, 2.0, float(DEFAULT_PUE), step=0.01)

carbon_price = st.sidebar.number_input(
    "Internal carbon price (€/tCO₂e)",
    min_value=0.0,
    value=float(DEFAULT_CARBON_PRICE),
    step=10.0
)

scenario_carbon_price = st.sidebar.slider(
    "Scenario carbon price (€/tCO₂e)",
    min_value=50.0,
    max_value=250.0,
    value=150.0,
    step=10.0
)
# --------------------------
# COMPUTE RESULTS
# --------------------------
# Apply provider filter
filtered_df = df.copy()

if provider_filter != "All":
    filtered_df = filtered_df[filtered_df["provider"] == provider_filter]

# Compute emissions
result = compute(filtered_df, kwh_month, pue, carbon_price)

best = result.iloc[0]
worst = result.iloc[-1]

savings_tco2e = float(worst["annual_tco2e"] - best["annual_tco2e"])
savings_eur = float(savings_tco2e * carbon_price)
# Scenario carbon price impact
scenario_cost_best = float(best["annual_tco2e"] * scenario_carbon_price)
scenario_cost_worst = float(worst["annual_tco2e"] * scenario_carbon_price)
scenario_cost_difference = scenario_cost_worst - scenario_cost_best

# --------------------------
# KPI CARDS
# --------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Lowest-Emission Region", f"{best['region_label']}")
c2.metric("Avoided Emissions vs Highest", f"{savings_tco2e:.2f} tCO₂e")
c3.metric("Avoided Shadow Carbon Cost", f"€{savings_eur:,.0f}")

st.divider()
# -------------------------------
# Carbon Price Scenario Impact
# -------------------------------

st.subheader("Carbon Price Scenario Impact")

scenario_result = compute(df, kwh_month, pue, scenario_carbon_price)

scenario_best = scenario_result.iloc[0]
scenario_worst = scenario_result.iloc[-1]

scenario_cost_best = float(scenario_best["annual_carbon_cost_eur"])
scenario_cost_worst = float(scenario_worst["annual_carbon_cost_eur"])

scenario_cost_difference = scenario_cost_worst - scenario_cost_best

c4, c5, c6 = st.columns(3)

c4.metric(
    "Scenario Price",
    f"€{scenario_carbon_price:.0f}/tCO₂e"
)

c5.metric(
    "Best Region Carbon Cost",
    f"€{scenario_cost_best:,.0f}"
)

c6.metric(
    "Avoided Cost Under Scenario",
    f"€{scenario_cost_difference:,.0f}"
)

# --------------------------
# MAP VISUALIZATION
# --------------------------
st.subheader("Europe Map (Emissions by Region)")

map_fig = px.scatter_mapbox(
    result,
    lat="latitude",
    lon="longitude",
    size="annual_tco2e",
    color="annual_tco2e",
    hover_name="region_label",
    hover_data={
        "country": True,
        "annual_tco2e": ":.2f",
        "annual_carbon_cost_eur": ":.0f",
        "intensity_gco2e_per_kwh": True,
    },
    zoom=3,
    height=550
)

map_fig.update_layout(
    mapbox_style="carto-positron",
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

st.plotly_chart(map_fig, use_container_width=True)

# --------------------------
# BAR CHART (KEEP FOR ANALYSTS)
# --------------------------
st.subheader("Annual Emissions Comparison (tCO₂e)")

bar_fig = px.bar(
    result,
    x="region_label",
    y="annual_tco2e",
    hover_data=["country", "intensity_gco2e_per_kwh", "annual_carbon_cost_eur"],
    labels={"annual_tco2e": "tCO₂e/year", "region_label": "Region"}
)

st.plotly_chart(bar_fig, use_container_width=True)

# --------------------------
# TABLE OUTPUT
# --------------------------
st.subheader("Detailed Results")

display_cols = [
    "rank_cleanest",
    "region_id",
    "region_label",
    "country",
    "intensity_gco2e_per_kwh",
    "annual_tco2e",
    "annual_carbon_cost_eur",
]

st.dataframe(
    result[display_cols].rename(
        columns={
            "rank_cleanest": "Rank",
            "region_id": "Cloud Region",
            "region_label": "Region Label",
            "country": "Country",
            "intensity_gco2e_per_kwh": "Grid Intensity (gCO₂e/kWh)",
            "annual_tco2e": "Annual Emissions (tCO₂e)",
            "annual_carbon_cost_eur": "Annual Shadow Carbon Cost (€)",
        }
    ),
    use_container_width=True
)
# --------------------------
# CSV EXPORT
# --------------------------
csv_data = result.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download results as CSV",
    data=csv_data,
    file_name="carbon_aware_cloud_results.csv",
    mime="text/csv"
)
# --------------------------
# METHODOLOGY
# --------------------------
with st.expander("Methodology, Boundary & Limitations"):
    st.markdown(
        """
**Emissions boundary:**  
This tool estimates Scope 2 location-based operational emissions from cloud workload electricity use.

**Formula:**  
Annual tCO₂e = (Monthly kWh × 12 × PUE × grid intensity) / 1,000,000

**What is included:**  
- Workload electricity use
- PUE-adjusted data center energy use
- Country-level grid carbon intensity
- Internal shadow carbon price

**What is excluded:**  
- Scope 1 backup generator emissions
- Scope 3 embodied emissions from servers and data center construction
- Provider-specific renewable energy contracts
- Market-based Scope 2 claims
- Real-time 24/7 carbon-free energy matching
- Actual latency benchmarking
- Actual cloud service pricing

**Data note:**  
Grid intensity values are annual country averages mapped to AWS, Azure, and GCP European cloud regions.

**Use case:**  
This is a strategic screening prototype, not a full cloud carbon accounting platform.
        """
    )
