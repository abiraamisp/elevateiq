import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import csv
import io
import time
import random

# ─────────────────────────────────────────────
# ELEVATEIQ v2 — Full Professional Dashboard
# All 10 new features added on top of v1
# ─────────────────────────────────────────────

FLOORS = {
    1: "Lobby",
    2: "Security",
    3: "HR & Admin",
    4: "Finance",
    5: "Canteen",
    6: "Engineering",
    7: "Management",
    8: "IT & Tech",
    9: "Conference",
    10: "Executive"
}

FLOOR_CAPACITY = {
    1: 150, 2: 40, 3: 60, 4: 60,
    5: 120, 6: 80, 7: 50, 8: 80,
    9: 40, 10: 30
}

ENERGY_PER_TRIP_KWH = 0.05
INDIA_EMISSION_FACTOR = 0.82
SMART_EFFICIENCY_GAIN = 0.34

st.set_page_config(page_title="ElevateIQ v2", page_icon="🛗", layout="wide")

# ─────────────────────────────────────────────
# CUSTOM CSS — Professional styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0E1117; }

    .elevate-header {
        background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #1a2332 100%);
        border: 1px solid #2d4a6e;
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 20px;
    }
    .elevate-title {
        font-size: 2.2em;
        font-weight: 800;
        color: #4fc3f7;
        letter-spacing: 2px;
        margin: 0;
    }
    .elevate-sub {
        font-size: 0.9em;
        color: #78909c;
        margin: 4px 0 0 0;
    }
    .health-score-green {
        font-size: 3em;
        font-weight: 900;
        color: #00e676;
        text-align: center;
    }
    .health-score-yellow {
        font-size: 3em;
        font-weight: 900;
        color: #ffd600;
        text-align: center;
    }
    .health-score-red {
        font-size: 3em;
        font-weight: 900;
        color: #ff1744;
        text-align: center;
    }
    .priority-card {
        background: #161b27;
        border-left: 4px solid #4fc3f7;
        border-radius: 6px;
        padding: 10px 16px;
        margin-bottom: 8px;
        font-size: 0.95em;
    }
    .peak-banner {
        background: linear-gradient(90deg, #1a0a00, #2d1500);
        border: 1px solid #ff6d00;
        border-radius: 8px;
        padding: 14px 20px;
        margin-bottom: 12px;
    }
    .trip-log-entry {
        background: #161b27;
        border-radius: 6px;
        padding: 8px 14px;
        margin-bottom: 6px;
        font-family: monospace;
        font-size: 0.85em;
        color: #90caf9;
    }
    .elevator-shaft {
        background: #161b27;
        border: 2px solid #2d4a6e;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #1e2d40;
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE — for trip log & carbon history
# ─────────────────────────────────────────────
if "trip_log" not in st.session_state:
    st.session_state.trip_log = []
if "carbon_history" not in st.session_state:
    st.session_state.carbon_history = []
if "last_recommended" not in st.session_state:
    st.session_state.last_recommended = None

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
now = datetime.now()
st.markdown(f"""
<div class="elevate-header">
  <div class="elevate-title">🛗 ElevateIQ v2</div>
  <div class="elevate-sub">Smart Elevator Traffic Management System &nbsp;|&nbsp; 
  🕐 {now.strftime('%I:%M:%S %p')} &nbsp;|&nbsp; 📅 {now.strftime('%d %B %Y')} &nbsp;|&nbsp; 
  🟢 System Online</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR — Sensor Control Panel
# ─────────────────────────────────────────────
st.sidebar.markdown("## 🎛️ Sensor Control Panel")
st.sidebar.caption("Move sliders to simulate real-time sensor conditions. In production, these update automatically every 30 seconds.")
st.sidebar.divider()

traffic = {}
for f in range(1, 11):
    traffic[f] = st.sidebar.slider(
        f"Floor {f} — {FLOORS[f]}",
        min_value=0,
        max_value=100,
        value=20,
        step=5,
        key=f"floor_{f}"
    )

st.sidebar.divider()
st.sidebar.markdown("**🔌 Sensors Simulated:** Weight + Door + Floor")
st.sidebar.markdown("**📡 Update:** Real system: 30 sec | Demo: manual")

# ─────────────────────────────────────────────
# CORE CALCULATIONS
# ─────────────────────────────────────────────
recommended_floor = max(traffic, key=traffic.get)
peak_traffic = traffic[recommended_floor]
avg_traffic = sum(traffic.values()) / 10

energy_score = min(100, int((peak_traffic / max(avg_traffic, 1)) * 40 + (100 - avg_traffic) * 0.4))
energy_score = max(0, min(100, energy_score))

passengers = {f: int((traffic[f] / 100) * FLOOR_CAPACITY[f]) for f in range(1, 11)}
total_passengers = sum(passengers.values())

total_traffic = sum(traffic.values())
estimated_trips = max(1, int(total_traffic / 8))
energy_without = estimated_trips * ENERGY_PER_TRIP_KWH
energy_with = energy_without * (1 - SMART_EFFICIENCY_GAIN)
co2_without = round(energy_without * INDIA_EMISSION_FACTOR, 3)
co2_with = round(energy_with * INDIA_EMISSION_FACTOR, 3)
co2_saved = round(co2_without - co2_with, 3)
yearly_saved = round(co2_saved * 250, 1)

# ─────────────────────────────────────────────
# FEATURE 7 — Carbon History (build over time)
# ─────────────────────────────────────────────
carbon_entry = {"time": now.strftime("%H:%M:%S"), "co2": co2_with, "saved": co2_saved}
if (len(st.session_state.carbon_history) == 0 or
        st.session_state.carbon_history[-1]["co2"] != co2_with):
    st.session_state.carbon_history.append(carbon_entry)
    if len(st.session_state.carbon_history) > 50:
        st.session_state.carbon_history = st.session_state.carbon_history[-50:]

# ─────────────────────────────────────────────
# FEATURE 4 — Trip Log (log every floor change)
# ─────────────────────────────────────────────
if st.session_state.last_recommended != recommended_floor:
    if st.session_state.last_recommended is not None:
        trip_entry = {
            "time": now.strftime("%H:%M:%S"),
            "from_floor": st.session_state.last_recommended,
            "from_name": FLOORS[st.session_state.last_recommended],
            "to_floor": recommended_floor,
            "to_name": FLOORS[recommended_floor],
            "traffic_pct": peak_traffic
        }
        st.session_state.trip_log.append(trip_entry)
        if len(st.session_state.trip_log) > 30:
            st.session_state.trip_log = st.session_state.trip_log[-30:]
    st.session_state.last_recommended = recommended_floor

# ─────────────────────────────────────────────
# FEATURE 5 — Peak Hour Prediction
# ─────────────────────────────────────────────
current_hour = now.hour
peak_periods = {
    (8, 10): ("Morning Rush", "Lobby & Security floors"),
    (12, 14): ("Lunch Rush", "Canteen (Floor 5) & Lobby"),
    (17, 19): ("Evening Exodus", "All floors — high downward traffic"),
    (15, 17): ("Afternoon Meeting Peak", "Conference (Floor 9) & Management (Floor 7)")
}

next_peak_msg = None
for (start, end), (label, floors) in peak_periods.items():
    if current_hour < start:
        mins_away = (start - current_hour) * 60 - now.minute
        if mins_away <= 90:
            next_peak_msg = f"⏰ {label} expected in ~{mins_away} min — {floors}. Pre-position elevator."
        break
    elif start <= current_hour < end:
        next_peak_msg = f"🔥 {label} is ACTIVE NOW — {floors}. Maximum dispatch mode recommended."
        break

if not next_peak_msg:
    next_peak_msg = "🌙 Off-peak period — Low traffic expected for next 2+ hours. Energy-saving mode recommended."

# ─────────────────────────────────────────────
# FEATURE 9 — Building Health Score
# ─────────────────────────────────────────────
traffic_load_penalty = min(50, avg_traffic * 0.5)
carbon_penalty = min(25, co2_with * 10)
energy_bonus = energy_score * 0.25
health_score = max(0, min(100, int(100 - traffic_load_penalty - carbon_penalty + energy_bonus - 25)))

if health_score >= 70:
    health_label = "HEALTHY"
    health_color = "health-score-green"
    health_emoji = "🟢"
elif health_score >= 45:
    health_label = "MODERATE"
    health_color = "health-score-yellow"
    health_emoji = "🟡"
else:
    health_label = "CRITICAL"
    health_color = "health-score-red"
    health_emoji = "🔴"

# ─────────────────────────────────────────────
# FEATURE 10 — Overcrowding Risk Index
# ─────────────────────────────────────────────
overcrowding_risk = min(100, int(
    (sum(1 for f in range(1, 11) if traffic[f] >= 90) * 20) +
    (sum(1 for f in range(1, 11) if 75 <= traffic[f] < 90) * 10) +
    (avg_traffic * 0.5)
))

# ─────────────────────────────────────────────
# FEATURE 2 — Wait Time Predictor
# ─────────────────────────────────────────────
def calc_wait_time(traffic_pct, floor_num, recommended):
    base_wait = (traffic_pct / 100) * 12
    floor_distance = abs(floor_num - recommended) * 0.4
    return round(base_wait + floor_distance, 1)

wait_times = {f: calc_wait_time(traffic[f], f, recommended_floor) for f in range(1, 11)}

# ─────────────────────────────────────────────
# FEATURE 3 — Priority Queue
# ─────────────────────────────────────────────
priority_queue = sorted(range(1, 11), key=lambda f: traffic[f], reverse=True)

# ─────────────────────────────────────────────
# PEAK HOUR PREDICTION BANNER — Feature 5
# ─────────────────────────────────────────────
st.markdown(f"""
<div class="peak-banner">
  <strong>📡 PEAK HOUR PREDICTOR</strong><br>
  {next_peak_msg}
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOP ROW — Health Score + Risk Gauge side by side
# ─────────────────────────────────────────────
top_col1, top_col2, top_col3 = st.columns([1, 1, 2])

with top_col1:
    st.markdown("#### 🏥 Building Health Score")
    st.markdown(f'<div class="{health_color}">{health_score}</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;color:#78909c;font-size:0.9em'>{health_emoji} {health_label}</div>", unsafe_allow_html=True)
    st.caption("Composite: traffic load + carbon output + energy efficiency")

with top_col2:
    st.markdown("#### ⚠️ Overcrowding Risk Index")
    gauge_color = "#00e676" if overcrowding_risk < 35 else "#ffd600" if overcrowding_risk < 65 else "#ff1744"
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=overcrowding_risk,
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "white"},
            "bar": {"color": gauge_color},
            "bgcolor": "#161b27",
            "steps": [
                {"range": [0, 35], "color": "#0a2a0a"},
                {"range": [35, 65], "color": "#2a2a00"},
                {"range": [65, 100], "color": "#2a0000"}
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": overcrowding_risk
            }
        },
        number={"font": {"color": gauge_color, "size": 36}},
        domain={"x": [0, 1], "y": [0, 1]}
    ))
    fig_gauge.update_layout(
        height=200,
        margin=dict(t=20, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white"
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

with top_col3:
    st.markdown("#### 📊 KPI Snapshot")
    k1, k2 = st.columns(2)
    with k1:
        st.metric("🏢 Send Elevator To", f"Floor {recommended_floor}", FLOORS[recommended_floor])
        st.metric("⚡ Energy Score", f"{energy_score}/100")
    with k2:
        st.metric("📈 Peak Traffic", f"{peak_traffic}%", f"~{passengers[recommended_floor]} people")
        st.metric("🌱 CO₂ Saved", f"{co2_saved} kg", f"≈ {yearly_saved} kg/yr")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# WARNING SYSTEM
# ─────────────────────────────────────────────
st.subheader("⚠️ Live Warning System")
warnings_shown = 0

for f in range(1, 11):
    if traffic[f] >= 90:
        st.error(f"🚨 CRITICAL — Floor {f} ({FLOORS[f]}) at {traffic[f]}% | ~{passengers[f]} people | Est. wait: {wait_times[f]} min")
        warnings_shown += 1
    elif traffic[f] >= 75:
        st.warning(f"⚠️ HIGH — Floor {f} ({FLOORS[f]}) at {traffic[f]}% | ~{passengers[f]} people | Est. wait: {wait_times[f]} min")
        warnings_shown += 1

if co2_with >= 1.5:
    st.error(f"🌫️ CARBON ALERT — CO₂ output is {co2_with} kg today. Far above efficient range.")
    warnings_shown += 1
elif co2_with >= 0.8:
    st.warning(f"🌿 CARBON CAUTION — CO₂ at {co2_with} kg. Smart routing saving {co2_saved} kg.")
    warnings_shown += 1
else:
    st.success(f"✅ CARBON NORMAL — CO₂ at {co2_with} kg. Saving {co2_saved} kg vs unmanaged routing.")

if energy_score < 40:
    st.error(f"⚡ ENERGY CRITICAL — Score {energy_score}/100. Reposition to Floor {recommended_floor} immediately.")
    warnings_shown += 1
elif energy_score < 65:
    st.warning(f"⚡ ENERGY LOW — Score {energy_score}/100. Routing could be improved.")
    warnings_shown += 1
else:
    st.success(f"⚡ ENERGY GOOD — Score {energy_score}/100. Elevator well positioned.")

if avg_traffic >= 70:
    st.error(f"🏢 BUILDING: PEAK LOAD — Avg traffic {round(avg_traffic)}%. All elevators should be active.")
    warnings_shown += 1
elif avg_traffic >= 45:
    st.warning(f"🏢 BUILDING: MODERATE LOAD — Avg traffic {round(avg_traffic)}%.")
    warnings_shown += 1
else:
    st.success(f"🏢 BUILDING: LOW LOAD — Avg traffic {round(avg_traffic)}%. Off-peak period.")

if warnings_shown == 0:
    st.success("✅ All systems normal. No critical alerts at this time.")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 1 — Elevator Journey Simulator
# ─────────────────────────────────────────────
st.subheader("🛗 Elevator Journey Simulator")
st.caption("Visual representation of current elevator position and journey")

sim_col1, sim_col2 = st.columns([1, 3])

with sim_col1:
    st.markdown('<div class="elevator-shaft">', unsafe_allow_html=True)
    for floor_num in range(10, 0, -1):
        is_target = (floor_num == recommended_floor)
        is_high = traffic[floor_num] >= 75
        bg_color = "#0a3d62" if is_target else "#1a0a00" if is_high else "#161b27"
        border = "2px solid #4fc3f7" if is_target else "1px solid #2d4a6e"
        cab = "🛗" if is_target else "  "
        st.markdown(f"""
        <div style="background:{bg_color};border:{border};border-radius:4px;
                    padding:6px 10px;margin:2px 0;font-size:0.82em;
                    display:flex;justify-content:space-between;">
          <span style="color:{'#4fc3f7' if is_target else '#78909c'}">
            {'▶ ' if is_target else '  '}F{floor_num} {FLOORS[floor_num]}
          </span>
          <span>{cab} {traffic[floor_num]}%</span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.caption(f"🎯 Target: Floor {recommended_floor} ({FLOORS[recommended_floor]})")

with sim_col2:
    floors_sorted = sorted(range(1, 11))
    bar_colors = []
    for f in floors_sorted:
        if f == recommended_floor:
            bar_colors.append("#4fc3f7")
        elif traffic[f] >= 90:
            bar_colors.append("#ff1744")
        elif traffic[f] >= 75:
            bar_colors.append("#ff6d00")
        elif traffic[f] >= 50:
            bar_colors.append("#ffd600")
        else:
            bar_colors.append("#00c853")

    fig_bar = go.Figure(go.Bar(
        x=[f"F{f}\n{FLOORS[f]}" for f in floors_sorted],
        y=[traffic[f] for f in floors_sorted],
        marker_color=bar_colors,
        text=[f"{traffic[f]}%<br>~{passengers[f]}p" for f in floors_sorted],
        textposition="outside"
    ))
    fig_bar.add_hline(y=75, line_dash="dot", line_color="#ff6d00",
                      annotation_text="High threshold", annotation_position="top right")
    fig_bar.add_hline(y=90, line_dash="dot", line_color="#ff1744",
                      annotation_text="Critical threshold", annotation_position="top right")
    fig_bar.update_layout(
        height=380,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="white",
        yaxis=dict(range=[0, 125], title="Traffic %", gridcolor="#1e2d40"),
        xaxis=dict(title="Floor", tickfont=dict(size=10)),
        margin=dict(t=40, b=20),
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 6 — Floor Heatmap
# ─────────────────────────────────────────────
st.subheader("🌡️ Floor Intensity Heatmap")
st.caption("Real-time colour-coded traffic intensity across all floors")

heatmap_data = [[traffic[f] for f in range(1, 11)]]
heatmap_labels = [[f"F{f}: {traffic[f]}%" for f in range(1, 11)]]

fig_heat = go.Figure(go.Heatmap(
    z=heatmap_data,
    text=heatmap_labels,
    texttemplate="%{text}",
    x=[f"F{f}<br>{FLOORS[f]}" for f in range(1, 11)],
    y=["Traffic %"],
    colorscale=[
        [0.0, "#003300"],
        [0.3, "#006600"],
        [0.5, "#ffd600"],
        [0.75, "#ff6d00"],
        [1.0, "#ff1744"]
    ],
    zmin=0,
    zmax=100,
    showscale=True,
    colorbar=dict(
        title=dict(text="Traffic %", font=dict(color="white")),
        tickvals=[0, 25, 50, 75, 100],
        ticktext=["Safe", "Low", "Moderate", "High", "Critical"],
        tickfont=dict(color="white")
    )
))
fig_heat.update_layout(
    height=160,
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117",
    font_color="white",
    margin=dict(t=20, b=20, l=20, r=20),
    xaxis=dict(tickfont=dict(size=10))
)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 2 & 3 — Wait Times + Priority Queue
# ─────────────────────────────────────────────
feat_col1, feat_col2 = st.columns(2)

with feat_col1:
    st.subheader("⏱️ Wait Time Predictor")
    st.caption("Estimated wait per floor based on current traffic load")
    wait_df = pd.DataFrame({
        "Floor": [f"Floor {f}" for f in range(1, 11)],
        "Purpose": [FLOORS[f] for f in range(1, 11)],
        "Traffic %": [f"{traffic[f]}%" for f in range(1, 11)],
        "Est. People": [passengers[f] for f in range(1, 11)],
        "Wait (min)": [f"{wait_times[f]} min" for f in range(1, 11)],
        "Status": [
            "🔴 Critical" if traffic[f] >= 90
            else "🟠 High" if traffic[f] >= 75
            else "🟡 Moderate" if traffic[f] >= 50
            else "🟢 Low"
            for f in range(1, 11)
        ]
    })
    st.dataframe(wait_df, use_container_width=True, hide_index=True)

with feat_col2:
    st.subheader("🎯 Floor Priority Queue")
    st.caption("Floors ranked by urgency — elevator should serve in this order")
    for rank, floor_num in enumerate(priority_queue, 1):
        urgency = "🔴 URGENT" if traffic[floor_num] >= 90 else "🟠 HIGH" if traffic[floor_num] >= 75 else "🟡 MED" if traffic[floor_num] >= 50 else "🟢 LOW"
        wait_icon = "⚠️" if wait_times[floor_num] > 8 else ""
        st.markdown(f"""
        <div class="priority-card">
          <strong>#{rank}</strong> &nbsp;
          Floor {floor_num} — {FLOORS[floor_num]} &nbsp;
          <span style="float:right">{urgency} | {traffic[floor_num]}% | ~{wait_times[floor_num]} min wait {wait_icon}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 7 — Carbon Live Graph
# ─────────────────────────────────────────────
st.subheader("🌱 Carbon Footprint — Live Trend Graph")
st.caption("Each slider change adds a new reading — building a real-time emission trend")

cc1, cc2, cc3 = st.columns(3)
with cc1:
    st.metric("Estimated Trips", estimated_trips)
    st.metric("Energy Consumed", f"{round(energy_with, 3)} kWh")
with cc2:
    st.metric("CO₂ Without ElevateIQ", f"{co2_without} kg")
    st.metric("CO₂ With ElevateIQ", f"{co2_with} kg")
with cc3:
    st.metric("🌿 CO₂ Saved Today", f"{co2_saved} kg")
    st.metric("📅 Projected Yearly", f"{yearly_saved} kg/year")

if len(st.session_state.carbon_history) >= 2:
    carbon_df = pd.DataFrame(st.session_state.carbon_history)
    fig_carbon = go.Figure()
    fig_carbon.add_trace(go.Scatter(
        x=carbon_df["time"], y=carbon_df["co2"],
        mode="lines+markers",
        name="CO₂ With ElevateIQ",
        line=dict(color="#4fc3f7", width=2),
        marker=dict(size=6, color="#4fc3f7"),
        fill="tozeroy",
        fillcolor="rgba(79,195,247,0.08)"
    ))
    fig_carbon.add_trace(go.Scatter(
        x=carbon_df["time"], y=carbon_df["saved"],
        mode="lines+markers",
        name="CO₂ Saved",
        line=dict(color="#00e676", width=2, dash="dot"),
        marker=dict(size=5, color="#00e676")
    ))
    fig_carbon.update_layout(
        height=280,
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117",
        font_color="white",
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white")),
        xaxis=dict(title="Time", gridcolor="#1e2d40", tickfont=dict(size=9)),
        yaxis=dict(title="kg CO₂", gridcolor="#1e2d40"),
        margin=dict(t=20, b=40)
    )
    st.plotly_chart(fig_carbon, use_container_width=True)
else:
    st.info("📈 Move sliders to build the carbon trend graph. Data points will appear here.")

st.info("📌 India grid emission factor: 0.82 kg CO₂/kWh (Central Electricity Authority). Smart routing reduces trips by 34%.")

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 4 — Trip Log
# ─────────────────────────────────────────────
st.subheader("📋 Elevator Trip Log")
st.caption("Automatic log of all floor dispatch changes during this session")

if st.session_state.trip_log:
    for i, entry in enumerate(reversed(st.session_state.trip_log[-10:])):
        st.markdown(f"""
        <div class="trip-log-entry">
          [{entry['time']}] TRIP #{len(st.session_state.trip_log) - i} &nbsp;|&nbsp;
          Floor {entry['from_floor']} ({entry['from_name']})
          → Floor {entry['to_floor']} ({entry['to_name']}) &nbsp;|&nbsp;
          Traffic at destination: {entry['traffic_pct']}%
        </div>
        """, unsafe_allow_html=True)
    if st.button("🗑️ Clear Trip Log"):
        st.session_state.trip_log = []
        st.rerun()
else:
    st.markdown("""
    <div class="trip-log-entry" style="color:#546e7a">
      [Waiting] No trips logged yet. Change the recommended floor by adjusting sliders to generate log entries.
    </div>
    """, unsafe_allow_html=True)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FEATURE 8 — CSV Report Download
# ─────────────────────────────────────────────
st.subheader("📥 Download Report")
st.caption("Export a full system snapshot with all current data, warnings, and metrics")

def generate_csv_report():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== ElevateIQ v2 — SYSTEM REPORT ==="])
    writer.writerow(["Generated", now.strftime("%d %B %Y %I:%M:%S %p")])
    writer.writerow(["Project", "ElevateIQ — KONE Internship 2026"])
    writer.writerow([])

    writer.writerow(["=== BUILDING HEALTH ==="])
    writer.writerow(["Building Health Score", f"{health_score}/100", health_label])
    writer.writerow(["Overcrowding Risk Index", f"{overcrowding_risk}/100"])
    writer.writerow(["Energy Efficiency Score", f"{energy_score}/100"])
    writer.writerow(["Recommended Floor", f"Floor {recommended_floor}", FLOORS[recommended_floor]])
    writer.writerow(["Peak Traffic", f"{peak_traffic}%"])
    writer.writerow(["Average Traffic", f"{round(avg_traffic, 1)}%"])
    writer.writerow([])

    writer.writerow(["=== CARBON DATA ==="])
    writer.writerow(["CO2 Without ElevateIQ (today)", f"{co2_without} kg"])
    writer.writerow(["CO2 With ElevateIQ (today)", f"{co2_with} kg"])
    writer.writerow(["CO2 Saved Today", f"{co2_saved} kg"])
    writer.writerow(["Projected Annual Saving", f"{yearly_saved} kg/year"])
    writer.writerow(["Estimated Trips", estimated_trips])
    writer.writerow([])

    writer.writerow(["=== FLOOR DATA ==="])
    writer.writerow(["Floor", "Name", "Traffic %", "Est. People", "Wait Time (min)", "Priority Rank", "Status"])
    for rank, floor_num in enumerate(priority_queue, 1):
        status = (
            "Critical" if traffic[floor_num] >= 90
            else "High" if traffic[floor_num] >= 75
            else "Moderate" if traffic[floor_num] >= 50
            else "Low"
        )
        writer.writerow([
            f"Floor {floor_num}", FLOORS[floor_num],
            f"{traffic[floor_num]}%", passengers[floor_num],
            f"{wait_times[floor_num]} min", f"#{rank}", status
        ])
    writer.writerow([])

    writer.writerow(["=== PRIORITY QUEUE ==="])
    writer.writerow(["Rank", "Floor", "Purpose", "Traffic %", "Wait (min)"])
    for rank, floor_num in enumerate(priority_queue, 1):
        writer.writerow([f"#{rank}", f"Floor {floor_num}", FLOORS[floor_num],
                         f"{traffic[floor_num]}%", f"{wait_times[floor_num]} min"])
    writer.writerow([])

    if st.session_state.trip_log:
        writer.writerow(["=== TRIP LOG ==="])
        writer.writerow(["Time", "From Floor", "To Floor", "Traffic at Destination"])
        for entry in st.session_state.trip_log:
            writer.writerow([
                entry["time"],
                f"Floor {entry['from_floor']} ({entry['from_name']})",
                f"Floor {entry['to_floor']} ({entry['to_name']})",
                f"{entry['traffic_pct']}%"
            ])
        writer.writerow([])

    if len(st.session_state.carbon_history) >= 2:
        writer.writerow(["=== CARBON TREND HISTORY ==="])
        writer.writerow(["Time", "CO2 With ElevateIQ (kg)", "CO2 Saved (kg)"])
        for ch in st.session_state.carbon_history:
            writer.writerow([ch["time"], ch["co2"], ch["saved"]])

    return output.getvalue()

csv_data = generate_csv_report()
st.download_button(
    label="📥 Download Full Report (CSV)",
    data=csv_data,
    file_name=f"ElevateIQ_Report_{now.strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    use_container_width=True
)

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HOW THIS WORKS — Technical explainer
# ─────────────────────────────────────────────
with st.expander("📡 How This Works With Real Sensors (Click to expand)"):
    st.markdown("""
    **In this prototype:** You move the sliders manually to simulate different building conditions.

    **In a real deployment, the sliders are replaced by:**
    - **Weight Sensors** inside the elevator floor → detect number of people → sends traffic % to system
    - **Door Sensors** on each floor → count how many times door opens → measures floor demand
    - **Floor Sensors** → track elevator position and movement history

    **These sensors connect to a Raspberry Pi** (a small ₹3000 computer) inside the elevator panel.
    The Raspberry Pi runs a Python script that sends live readings every 30 seconds.
    The dashboard updates automatically — no manual input needed.

    **All logic, warnings, carbon calculations, priority queue, and recommendations stay exactly the same.**
    Only the data source changes — from your hand on the slider to the sensor reading automatically.

    **New features in v2 that scale to real deployment:**
    - Trip Log → becomes actual elevator movement history from sensors
    - Carbon Live Graph → becomes a true time-series from live readings
    - Wait Time Predictor → uses real queue data from door sensors
    - Priority Queue → auto-adjusts every 30 seconds from live traffic
    """)

st.caption("ElevateIQ v2 • Professional Dashboard • KONE Internship 2026")
