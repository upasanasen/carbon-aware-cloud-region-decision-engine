# Carbon-Aware Cloud Region Decision Engine

A Streamlit-based decision-support prototype that helps sustainability, cloud, product, and finance teams compare cloud deployment regions using estimated Scope 2 location-based emissions, PUE-adjusted energy use, internal shadow carbon pricing, and business constraints.

✅ Live app: https://carbon-aware-cloud-tool.streamlit.app

---

## What This Project Does

This tool helps users compare AWS, Azure, and Google Cloud regions across estimated operational carbon impact and business decision factors.

Instead of only showing the lowest-emission region, the tool is being developed into a strategic recommendation engine that considers carbon intensity, workload energy use, PUE, internal shadow carbon cost, data residency, latency sensitivity, and workload flexibility.

---

## Why This Matters

As cloud workloads grow, especially with AI, where a company deploys compute infrastructure can significantly affect estimated Scope 2 emissions because electricity grids differ by country.

Sustainability, cloud, and finance teams need a simple way to compare:

- Estimated annual Scope 2 location-based emissions per cloud region
- Avoided emissions from selecting a lower-carbon region
- Internal shadow carbon cost exposure
- Trade-offs between carbon reduction, workload flexibility, latency, and data residency

This project demonstrates how carbon-aware decision-making can be integrated into cloud infrastructure strategy and sustainability planning.

---

## What the Tool Does

### Inputs

- Workload energy use in kWh/month
- Data center efficiency using PUE
- Internal shadow carbon price in €/tCO₂e
- Cloud provider filter: AWS, Azure, GCP, or all providers

### Outputs

- Lowest-emission region
- Estimated annual Scope 2 location-based emissions
- Avoided emissions vs highest-emission region
- Estimated internal shadow carbon cost
- Regional comparison chart
- Interactive emissions map
- CSV export

---

## Current Version

### Version 2: Multi-Cloud Carbon Comparison

- Multi-cloud comparison across AWS, Azure, and GCP
- Cloud provider filtering
- PUE-adjusted emissions calculation
- Internal shadow carbon price scenario analysis
- CSV export for analysis and reporting
- Interactive emissions map across Europe

---

## Methodology

Estimated annual emissions are calculated using:

```text
Annual tCO₂e = (Monthly kWh × 12 × PUE × grid intensity gCO₂e/kWh) ÷ 1,000,000

```

Where:

- Monthly kWh = estimated monthly workload electricity use
- PUE = Power Usage Effectiveness, used to account for data center infrastructure energy
- Grid intensity = country-level electricity emissions intensity
- The result is expressed in tonnes of CO₂e per year

This prototype estimates Scope 2 location-based operational emissions. It does not estimate provider-specific market-based emissions claims, Scope 1 backup generator emissions, or Scope 3 embodied emissions from servers and data center construction.

---

## Data Sources

- European Environment Agency (EEA) electricity generation greenhouse gas intensity data
- Cloud region-country mapping for AWS, Azure, and Google Cloud European regions
- Region data stored in `data/regions.csv`

---

## Repo Structure

```text
.
├── app/
│   └── app.py
├── data/
│   └── regions.csv
├── docs/
├── requirements.txt
└── README.md

```
---

## Current Limitations

This project is a strategic screening prototype, not a full cloud carbon accounting platform.

It does not currently include:

- Real-time hourly carbon intensity data
- Provider-specific renewable energy procurement claims
- Market-based Scope 2 accounting
- Actual cloud pricing
- Actual latency benchmarking
- Service availability by cloud region
- Scope 3 embodied emissions from hardware or data center construction

---

## Roadmap

### Version 3: Strategic Decision Engine

Planned upgrades:

- Workload type selection
- Data residency filter
- Latency sensitivity input
- Weighted decision scoring
- Strategic recommendation output
- Business trade-off explanation

### Version 4: Advanced Carbon-Aware Scheduling

Future upgrades:

- Hourly carbon intensity API integration
- Carbon-aware workload shifting
- Scenario comparison
- Exportable decision report
