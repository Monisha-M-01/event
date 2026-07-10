"""Organizer Dashboard for FanFlow AI using Streamlit.

Provides a real-time, premium Command Center view of:
1. Crowd status and AI routing guidance.
2. Prioritized Alert feed for incidents.

Uses st.empty() and a loop to avoid full-page flickering.
"""

import time
import requests
import pandas as pd
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="FanFlow AI Dashboard",
    page_icon="🏟️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Premium Custom CSS (Dark Theme + FIFA colors)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Dark premium theme overrides */
    [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Hide top header line */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    .metric-card {
        background-color: #1E2127;
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #E3003F;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 16px;
    }
    .alert-card {
        background-color: #1E2127;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #333;
    }
    .alert-critical { border-left: 4px solid #FF4B4B; }
    .alert-high { border-left: 4px solid #FFA421; }
    .alert-medium { border-left: 4px solid #FCE83A; }
    
    .guidance-box {
        background: linear-gradient(135deg, #1A1A24 0%, #0E1117 100%);
        border: 1px solid #00A3E0;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(0,163,224,0.15);
    }
</style>
""", unsafe_allow_html=True)

st.title("🏟️ FanFlow AI — Operations Command Center")
st.markdown("**FIFA World Cup 2026™ • MetLife Stadium**", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------------------------------------------------------
# UI Placeholders (Prevents screen flickering)
# ---------------------------------------------------------------------------
guidance_placeholder = st.empty()

col_left, col_right = st.columns([1.5, 1], gap="large")

with col_left:
    st.subheader("📊 Live Zone Occupancy")
    chart_placeholder = st.empty()
    table_placeholder = st.empty()

with col_right:
    st.subheader("🚨 Prioritized AI Alerts")
    metrics_placeholder = st.empty()
    alerts_placeholder = st.empty()

# ---------------------------------------------------------------------------
# Data Fetching & Rendering
# ---------------------------------------------------------------------------
def fetch_data(endpoint: str):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

def update_dashboard():
    crowd_data = fetch_data("crowd-status")
    alert_data = fetch_data("alerts")
    
    # Render Crowd Data
    if crowd_data:
        guidance_html = f"""
        <div class="guidance-box">
            <h4 style="margin-top:0; color:#00A3E0; display:flex; align-items:center; gap:8px;">
                🤖 Live AI Routing Guidance
            </h4>
            <p style="white-space: pre-line; margin-bottom:0; font-size:1.05rem;">{crowd_data['guidance']}</p>
        </div>
        """
        guidance_placeholder.markdown(guidance_html, unsafe_allow_html=True)
        
        zones = crowd_data.get("zones", [])
        if zones:
            df = pd.DataFrame([
                {
                    "Zone": z["zone_name"],
                    "Occupancy": float(z["occupancy_percent"]),
                    "Count": z["crowd_count"],
                    "Capacity": z["capacity"],
                    "Status": z["density_level"].upper(),
                }
                for z in zones
            ])
            
            # Bar Chart
            chart_placeholder.bar_chart(df.set_index("Zone")["Occupancy"], height=250, color="#E3003F")
            
            # Styled Dataframe with Progress Bars
            table_placeholder.dataframe(
                df,
                column_config={
                    "Occupancy": st.column_config.ProgressColumn(
                        "Occupancy %",
                        help="Current zone fill percentage",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Status": st.column_config.TextColumn("Status")
                },
                hide_index=True,
                use_container_width=True
            )
            
    # Render Alerts Data
    if alert_data:
        total = alert_data.get("total_alerts", 0)
        crit = alert_data.get("critical_count", 0)
        
        metrics_html = f"""
        <div style="display: flex; gap: 16px; margin-bottom: 16px;">
            <div class="metric-card" style="flex: 1;">
                <div style="font-size: 14px; color: #888; text-transform: uppercase;">Active Alerts</div>
                <div style="font-size: 32px; font-weight: bold;">{total}</div>
            </div>
            <div class="metric-card" style="flex: 1; border-left-color: #FF4B4B;">
                <div style="font-size: 14px; color: #888; text-transform: uppercase;">Critical Priority</div>
                <div style="font-size: 32px; font-weight: bold; color: #FF4B4B;">{crit}</div>
            </div>
        </div>
        """
        metrics_placeholder.markdown(metrics_html, unsafe_allow_html=True)
        
        cards = alert_data.get("cards", [])
        alerts_html = ""
        for card in cards:
            a = card["alert"]
            sev = a["severity"]
            rank = card["priority_rank"]
            
            if sev >= 4:
                cls = "alert-critical"
                icon = "🔴"
            elif sev == 3:
                cls = "alert-high"
                icon = "🟠"
            else:
                cls = "alert-medium"
                icon = "🟡"
                
            alerts_html += f"""
            <div class="alert-card {cls}">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <strong style="font-size:1.1rem;">{icon} Rank {rank}: {a['type'].replace('_', ' ').upper()}</strong>
                    <span style="color: #AAA; font-size: 0.85rem; background:#333; padding:2px 8px; border-radius:12px;">{a['zone']}</span>
                </div>
                <div style="font-size: 0.95rem; margin-bottom: 10px; color:#DDD;">{a['description']}</div>
                <div style="font-size: 0.9rem; color: #00A3E0; background:#0E1117; padding:8px; border-radius:6px; border-left:2px solid #00A3E0;">
                    <strong>AI Action:</strong> {card['llm_summary']}
                </div>
            </div>
            """
        alerts_placeholder.markdown(alerts_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Continuous Background Loop (Flicker-Free)
# ---------------------------------------------------------------------------
while True:
    update_dashboard()
    time.sleep(5)
