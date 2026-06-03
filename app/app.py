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
DEFAULT_CARBON_PRICE = 100.0  # Internal shadow carbon price in €/tCO2e

WORKLOAD_PRESETS = {
    "Small App / API": 150.0,
    "Data Pipeline": 1500.0,
    "ML Inference": 8000.0,
    "Custom": 1000.0
}
EU_COUNTRIES = [
    "Sweden",
    "France",
    "Ireland",
    "Germany",
    "Italy",
    "Netherlands",
    "Finland",
    "Belgium"
]


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
   
    # Sort by cleanest
    out = out.sort_values("annual_tco2e", ascending=True).reset_index(drop=True)
    out["rank_cleanest"] = out.index + 1
    return out

def normalize_inverse(series: pd.Series) -> pd.Series:
    if series.max() == series.min():
        return pd.Series([1.0] * len(series), index=series.index)
    return 1 - ((series - series.min()) / (series.max() - series.min()))


# --------------------------
# LOAD DATA
# --------------------------
df = pd.read_csv(DATA_PATH)
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
# BUSINESS CONSTRAINTS
# --------------------------
st.sidebar.header("Business Constraints")

workload_type = st.sidebar.selectbox(
    "Workload Type",
    [
        "Batch / AI Training",
        "Analytics Pipeline",
        "User-Facing App",
        "Critical Production System"
    ]
)

data_residency = st.sidebar.selectbox(
    "Data Residency Requirement",
    [
        "EU-only",
        "Flexible"
    ]
)

latency_sensitivity = st.sidebar.selectbox(
    "Latency Sensitivity",
    [
        "Low",
        "Medium",
        "High"
    ]
)

# --------------------------
# DECISION WEIGHTS
# --------------------------
st.sidebar.header("Decision Weights")

carbon_weight = st.sidebar.slider("Carbon Reduction Weight (%)", 0, 100, 40)
cost_weight = st.sidebar.slider("Shadow Cost Weight (%)", 0, 100, 25)
latency_weight = st.sidebar.slider("Latency Weight (%)", 0, 100, 20)
compliance_weight = st.sidebar.slider("Compliance Weight (%)", 0, 100, 15)

total_weight = carbon_weight + cost_weight + latency_weight + compliance_weight

if total_weight != 100:
    st.sidebar.warning(f"Weights should add up to 100%. Current total: {total_weight}%.")
# --------------------------
# COMPUTE RESULTS
# --------------------------
# Apply provider filter
filtered_df = df.copy()

if provider_filter != "All":
    filtered_df = filtered_df[filtered_df["provider"] == provider_filter]

if data_residency == "EU-only":
    filtered_df = filtered_df[filtered_df["country"].isin(EU_COUNTRIES)]

if filtered_df.empty:
    st.error("No regions available for the selected provider and data residency requirement.")
    st.stop()
    
# Compute emissions
result = compute(filtered_df, kwh_month, pue, carbon_price)

# Decision scoring
result["carbon_score"] = normalize_inverse(result["annual_tco2e"])
result["cost_score"] = normalize_inverse(result["annual_carbon_cost_eur"])

if latency_sensitivity == "Low":
    result["latency_score"] = 1.0
elif latency_sensitivity == "Medium":
    result["latency_score"] = 0.7
else:
    result["latency_score"] = 0.4

if data_residency == "EU-only":
    result["compliance_score"] = 1.0
else:
    result["compliance_score"] = 0.8

if total_weight == 100:
    result["decision_score"] = (
        result["carbon_score"] * (carbon_weight / 100)
        + result["cost_score"] * (cost_weight / 100)
        + result["latency_score"] * (latency_weight / 100)
        + result["compliance_score"] * (compliance_weight / 100)
    ) * 100
else:
    result["decision_score"] = None
    
best = result.iloc[0]
worst = result.iloc[-1]

if total_weight == 100:
    recommended = result.sort_values("decision_score", ascending=False).iloc[0]
else:
    recommended = best
    
savings_tco2e = float(worst["annual_tco2e"] - best["annual_tco2e"])
savings_eur = float(savings_tco2e * carbon_price)
# Scenario carbon price impact
scenario_cost_best = float(best["annual_tco2e"] * scenario_carbon_price)
scenario_cost_worst = float(worst["annual_tco2e"] * scenario_carbon_price)
scenario_cost_difference = scenario_cost_worst - scenario_cost_best

# --------------------------
# KPI CARDS
# --------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Lowest-Emission Region", f"{best['region_label']}")
c2.metric("Recommended Region", f"{recommended['region_label']}")
c3.metric("Avoided Emissions vs Highest", f"{savings_tco2e:.2f} tCO₂e")

if total_weight == 100:
    c4.metric("Decision Score", f"{recommended['decision_score']:.1f}/100")
else:
    c4.metric("Decision Score", "Adjust weights")

# --------------------------
# STRATEGIC RECOMMENDATION
# --------------------------
st.subheader("Strategic Recommendation")

if total_weight == 100:
    st.success(
        f"Recommended region: {recommended['region_label']} "
        f"({recommended['provider']}) with a decision score of "
        f"{recommended['decision_score']:.1f}/100."
    )

    if recommended["region_label"] != best["region_label"]:
        st.info(
            f"The lowest-emission region is {best['region_label']}, but the recommended region may provide "
            "a better balance based on the selected decision weights and business constraints."
        )
else:
    st.warning(
        "Adjust the decision weights so they add up to 100% to generate a recommendation score."
    )

st.divider()

# --------------------------
# STRATEGIC DECISION NOTES
# --------------------------
st.subheader("Strategic Decision Notes")

if workload_type == "Batch / AI Training":
    st.success(
        "This workload is highly flexible. It is a strong candidate for carbon-aware region selection, "
        "because batch and AI training jobs can often be shifted to lower-carbon regions if service availability and compliance requirements are met."
    )
elif workload_type == "Analytics Pipeline":
    st.info(
        "This workload has moderate flexibility. Carbon-aware region selection may be practical, especially if the pipeline does not require real-time processing."
    )
elif workload_type == "User-Facing App":
    st.warning(
        "This workload may be latency-sensitive. The lowest-emission region should not be selected without checking user location, response time, and service availability."
    )
else:
    st.warning(
        "This is a critical production workload. Carbon impact should be balanced with resilience, latency, availability zones, failover design, and service availability."
    )

if latency_sensitivity == "High":
    st.warning(
        "High latency sensitivity selected: carbon reduction should be balanced carefully against user experience and response-time requirements."
    )
elif latency_sensitivity == "Medium":
    st.info(
        "Medium latency sensitivity selected: a balanced region choice may be more appropriate than choosing only the lowest-emission region."
    )
else:
    st.success(
        "Low latency sensitivity selected: this workload may be suitable for stronger carbon-aware placement."
    )

if data_residency == "EU-only":
    st.info(
        "EU-only data residency selected: the region comparison is filtered to EU countries in the dataset."
    )
else:
    st.info(
        "Flexible data residency selected: future versions can compare both EU and non-EU regions when added to the dataset."
    )
# -------------------------------
# Carbon Price Scenario Impact
# -------------------------------

st.subheader("Carbon Price Scenario Impact")

scenario_result = compute(filtered_df, kwh_month, pue, scenario_carbon_price)

scenario_best = scenario_result.iloc[0]
scenario_worst = scenario_result.iloc[-1]

scenario_cost_best = float(scenario_best["annual_carbon_cost_eur"])
scenario_cost_worst = float(scenario_worst["annual_carbon_cost_eur"])

scenario_cost_difference = scenario_cost_worst - scenario_cost_best

c4, c5, c6 = st.columns(3)

c4.metric(
    "Scenario Shadow Price",
    f"€{scenario_carbon_price:.0f}/tCO₂e"
)

c5.metric(
    "Lowest-Emission Region Shadow Cost",
    f"€{scenario_cost_best:,.0f}"
)

c6.metric(
    "Avoided Shadow Cost Under Scenario",
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
    "carbon_score",
    "cost_score",
    "latency_score",
    "compliance_score",
    "decision_score",
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
            "carbon_score": "Carbon Score",
            "cost_score": "Cost Score",
            "latency_score": "Latency Score",
            "compliance_score": "Compliance Score",
            "decision_score": "Decision Score",
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
