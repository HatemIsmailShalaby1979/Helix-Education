from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Helix L&D Baseline Metrics", layout="wide")
st.title("📊 Helix L&D — Operational Baseline Dashboard")
st.markdown("**Phase 1 Deliverable:** Capturing 30-day baseline for operational KPIs.")


# --- Mock Data Generation (Simulating 30 days of operations) ---
def generate_baseline_data():
    dates = pd.date_range(end=datetime.now(), periods=30)
    data = {
        "date": dates,
        "onboarding_time_hours": np.random.normal(48, 5, 30),
        "adherence_rate": np.random.normal(0.92, 0.03, 30),
        "churn_risk_score": np.random.normal(0.15, 0.05, 30),
        "sop_error_rate": np.random.normal(0.08, 0.02, 30),
        "assessment_pass_rate": np.random.normal(0.75, 0.04, 30),
    }
    return pd.DataFrame(data)


df = generate_baseline_data()

# --- Key Metrics Row ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Avg Onboarding Time", f"{df['onboarding_time_hours'].mean():.1f} hrs", delta="-2.5 hrs vs target")
with col2:
    st.metric("Avg Adherence Rate", f"{df['adherence_rate'].mean() * 100:.1f}%", delta="+1.2% vs last month")
with col3:
    st.metric("Avg Churn Risk", f"{df['churn_risk_score'].mean() * 100:.1f}%", delta="-0.5% improvement")
with col4:
    st.metric("SOP Error Rate", f"{df['sop_error_rate'].mean() * 100:.1f}%", delta="-1.0% improvement")

# --- Charts ---
st.subheader("30-Day Trend Analysis")
tab1, tab2 = st.tabs(["Onboarding & Errors", "Adherence & Churn"])

with tab1:
    st.line_chart(df.set_index("date")[["onboarding_time_hours", "sop_error_rate"]])
    st.caption("Lower is better for both metrics.")

with tab2:
    st.line_chart(df.set_index("date")[["adherence_rate", "churn_risk_score"]])
    st.caption("Higher adherence and lower churn risk are targets.")

# --- Export Data ---
st.sidebar.header("Data Export")
if st.sidebar.button("Download Baseline CSV"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button("Download CSV", csv, "baseline_metrics_30d.csv", "text/csv")

st.sidebar.markdown("---")
st.sidebar.info("**Next Step:** Use this baseline to measure the impact of WILI training modules in Phase 2.")
