"""Streamlit Dashboard for Helix Education L&D Department.

Visualizes TMK Pattern Detection, Competency Profiles, and Operational Impact.
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# Page Configuration
st.set_page_config(page_title="Helix Education L&D Dashboard", page_icon="🎓", layout="wide")

st.title("🎓 Helix Education: L&D Performance Dashboard")
st.markdown("**Real-time insights into organizational learning and operational impact.**")

# Sidebar Filters
st.sidebar.header("Filters")
engine_filter = st.sidebar.multiselect("Select Engines", ["RTA", "B2B", "PERS", "CRM"], default=["RTA", "B2B"])
time_range = st.sidebar.selectbox("Time Range", ["Last 24h", "Last 7 Days", "Last 30 Days"])

# --- Section 1: TMK Pattern Visualization ---
st.header("1. Metacognitive Memory (TMK) Patterns")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Gap Distribution by Engine")
    # Placeholder data - will be replaced by live API calls in Phase 3
    gap_data = pd.DataFrame(
        {
            "Engine": ["RTA", "B2B", "PERS", "RTA", "B2B"],
            "Gap Type": ["Adherence", "Onboarding", "Competency", "Error Rate", "SOP Compliance"],
            "Severity": [85, 60, 90, 75, 50],
        }
    )
    fig_gaps = px.bar(gap_data, x="Engine", y="Severity", color="Gap Type", title="Detected Gap Severity")
    st.plotly_chart(fig_gaps, use_container_width=True)

with col2:
    st.subheader("Pattern Trend Analysis")
    trend_data = pd.DataFrame(
        {"Date": pd.date_range(start="2026-07-01", periods=10), "Patterns Detected": [5, 7, 4, 8, 6, 9, 5, 4, 3, 2]}
    )
    fig_trend = px.line(trend_data, x="Date", y="Patterns Detected", title="TMK Pattern Frequency")
    st.plotly_chart(fig_trend, use_container_width=True)

# --- Section 2: Competency Profile Tracking ---
st.header("2. Learner Competency Profiles")
col3, col4 = st.columns(2)

with col3:
    st.subheader("Top Competency Gaps")
    comp_data = pd.DataFrame(
        {
            "Skill": ["Advanced RTA Logic", "B2B Onboarding SOPs", "Crisis Management", "Data Privacy Protocols"],
            "Proficiency": [65, 70, 45, 80],
        }
    )
    fig_comp = px.bar(comp_data, x="Skill", y="Proficiency", orientation="h", title="Current Proficiency Levels")
    st.plotly_chart(fig_comp, use_container_width=True)

with col4:
    st.subheader("Learning Path Progress")
    st.metric(label="Active Learners", value="142", delta="+12 this week")
    st.metric(label="Avg. Completion Rate", value="78%", delta="+5% vs last month")
    st.progress(0.78, text="Overall Curriculum Progress")

# --- Section 3: Operational Impact ---
st.header("3. Operational Impact Metrics")
col5, col6, col7 = st.columns(3)

with col5:
    st.metric(label="Adherence Rate", value="95.2%", delta="+1.2%")
with col6:
    st.metric(label="Error Rate", value="0.8%", delta="-0.4%", delta_color="inverse")
with col7:
    st.metric(label="Training ROI", value="3.5x", delta="+0.5x")

st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data Source: Helix Prime TMK Loop")
st.markdown("**Phase 2:** Live TMK Loop integration and automated content generation.")

# --- Configuration ---
API_BASE_URL = "http://localhost:8000/api/v1"
JWT_TOKEN = st.secrets.get("HELIX_JWT_SECRET", "dev-token-placeholder")
HEADERS = {"Authorization": f"Bearer {JWT_TOKEN}", "Content-Type": "application/json"}


# --- API Integration: Fetch Live Gap Patterns ---
@st.cache_data(ttl=60)
def fetch_gap_patterns():
    try:
        # In production, this hits the TMK Loop endpoint defined in DATA_PIPELINE.md
        # response = requests.get(f"{API_BASE_URL}/training-content/gap-patterns", headers=HEADERS)
        # return response.json()

        # Simulating live data for development
        return [
            {
                "pattern_id": "p_001",
                "source_engine": "RTA",
                "gap_description": "Adherence to new break protocols",
                "severity": "High",
                "trend": "Worsening",
                "competency_tag": "adherence_protocol",
            },
            {
                "pattern_id": "p_002",
                "source_engine": "B2B",
                "gap_description": "SOP generation for Client X",
                "severity": "Medium",
                "trend": "Stable",
                "competency_tag": "crm_workflow",
            },
            {
                "pattern_id": "p_003",
                "source_engine": "CX",
                "gap_description": "Churn risk mitigation tactics",
                "severity": "Critical",
                "trend": "Worsening",
                "competency_tag": "customer_sentiment",
            },
        ]
    except Exception as e:
        st.error(f"Failed to fetch gap patterns: {e}")
        return []


# --- Automated Content Generator Logic ---
def trigger_content_generation(gap):
    """Triggers the LessonOrchestrator via the Content Engine API."""
    payload = {
        "gap_pattern_id": gap["pattern_id"],
        "competency_tag": gap["competency_tag"],
        "source_sop_id": f"sop_{gap['source_engine'].lower()}_001",
        "priority": "high" if gap["severity"] in ["Critical", "High"] else "normal",
    }
    # In production: requests.post(f"{API_BASE_URL}/training-content/generate", json=payload, headers=HEADERS)
    return f"Lesson '{gap['gap_description']}' queued for generation."


gaps = fetch_gap_patterns()
gaps_df = pd.DataFrame(gaps)

# --- Operational Gap Analysis ---
st.subheader("🔍 Operational Gap Analysis (TMK Loop)")
col1, col2 = st.columns([3, 1])
with col1:
    st.dataframe(gaps_df, use_container_width=True, hide_index=True)
with col2:
    st.metric("Active Gaps", len(gaps))
    st.metric("Critical Severity", len(gaps_df[gaps_df["severity"] == "Critical"]) if not gaps_df.empty else 0)

# --- Action Panel ---
st.sidebar.header("Automated Actions")
selected_gap_idx = st.sidebar.selectbox(
    "Select Gap to Address",
    range(len(gaps)),
    format_func=lambda x: gaps[x]["gap_description"] if gaps else "No gaps found",
)

if st.sidebar.button("🚀 Generate Targeted Lesson"):
    if gaps:
        result = trigger_content_generation(gaps[selected_gap_idx])
        st.sidebar.success(result)
    else:
        st.sidebar.warning("No active gaps to address.")

# --- Visualization: Interactive Competency Heatmap ---
st.subheader("🔥 Competency Distribution Heatmap")
if not gaps_df.empty:
    # Simulating team-level competency scores based on gap trends
    teams = ["Team Alpha", "Team Beta", "Team Gamma", "Team Delta"]
    competencies = ["adherence_protocol", "crm_workflow", "customer_sentiment", "forecasting", "quality_assurance"]

    # Generating mock heatmap data for visualization
    heatmap_data = np.random.uniform(0.5, 1.0, (len(teams), len(competencies)))
    df_heatmap = pd.DataFrame(heatmap_data, index=teams, columns=competencies)

    fig = px.imshow(
        df_heatmap,
        labels=dict(x="Competency Tag", y="Team", color="Proficiency Score"),
        x=competencies,
        y=teams,
        color_continuous_scale="RdYlGn",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Waiting for operational data to populate heatmap...")
