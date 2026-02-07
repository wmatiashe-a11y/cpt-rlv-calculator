import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIG & STYLING ---
st.set_page_config(page_title="CPT Property Redevelopment Calc", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_view_all=True)

# --- DATA PRESETS (Cape Town DMS) ---
ZONING = {
    "GR2 (Residential - 1.0 FF)": {"ff": 1.0, "coverage": 0.6},
    "GR4 (High Density - 1.5 FF)": {"ff": 1.5, "coverage": 0.6},
    "MU1 (Mixed Use - 1.5 FF)": {"ff": 1.5, "coverage": 0.75},
    "MU2 (High Density Mixed - 4.0 FF)": {"ff": 4.0, "coverage": 1.0},
    "GB7 (CBD/High Rise - 12.0 FF)": {"ff": 12.0, "coverage": 1.0},
}

DC_RATE = 514.10  # ZAR per m2 (2024/25 Estimate)
IH_CAP_PRICE = 15000  # Capped sales price for affordable units

# --- SIDEBAR ---
st.sidebar.title("🛠️ Development Inputs")
land_size = st.sidebar.number_input("Land Area (m²)", value=1000, step=100)
zone_choice = st.sidebar.selectbox("Zoning Preset", list(ZONING.keys()))
parking_zone = st.sidebar.radio("Parking Zone", ["Standard", "PT1 (Reduced)", "PT2 (Zero)"])

st.sidebar.subheader("Market Assumptions")
market_price = st.sidebar.slider("Market Sales Price (R/m²)", 20000, 80000, 45000)
const_cost_base = st.sidebar.slider("Base Construction (R/m²)", 12000, 25000, 17000)

# Adjust cost based on parking zone
if parking_zone == "PT2 (Zero)":
    const_cost = const_cost_base * 0.85 # 15% saving without basement parking
elif parking_zone == "PT1 (Reduced)":
    const_cost = const_cost_base * 0.95
else:
    const_cost = const_cost_base

st.sidebar.subheader("Policy Sensitivity")
ih_req = st.sidebar.slider("Inclusionary Housing (%)", 0, 30, 20)
density_bonus = st.sidebar.slider("Density Bonus (%)", 0, 100, 20)

# --- CALCULATION ENGINE ---
def calculate_metrics(land, ff, bonus, ih, m_price, c_cost):
    total_bulk = (land * ff) * (1 + (bonus / 100))
    ih_bulk = total_bulk * (ih / 100)
    market_bulk = total_bulk - ih_bulk
    
    gdv = (market_bulk * m_price) + (ih_bulk * IH_CAP_PRICE)
    dev_charges = market_bulk * DC_RATE
    construction = total_bulk * c_cost
    fees = construction * 0.125
    profit_target = gdv * 0.20
    
    rlv = gdv - construction - dev_charges - fees - profit_target
    return rlv, total_bulk, dev_charges, gdv

# --- EXECUTION ---
ff_val = ZONING[zone_choice]["ff"]
rlv, bulk, dcs, gdv = calculate_metrics(land_size, ff_val, density_bonus, ih_req, market_price, const_cost)

# --- UI DISPLAY ---
st.title("Cape Town Residual Land Value Calculator")
st.info(f"Scenario: {zone_choice} in a {parking_zone} area with {ih_req}% Inclusionary Housing.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Residual Land Value", f"R {max(0, rlv/1e6):.2f}M")
c2.metric("Total Bulk (GBA)", f"{bulk:,.0f} m²")
c3.metric("Dev Charges", f"R {dcs/1e3:,.0f}k")
c4.metric("Total GDV", f"R {gdv/1e6:.2f}M")

# --- SENSITIVITY HEATMAP ---
st.subheader("Sensitivity: How Density Bonuses offset Inclusionary Requirements")
matrix = []
ih_levels = [0, 10, 20, 30]
bonus_levels = [0, 20, 40, 60, 80, 100]

for ih in ih_levels:
    row = []
    for b in bonus_levels:
        val, _, _, _ = calculate_metrics(land_size, ff_val, b, ih, market_price, const_cost)
        row.append(round(val / 1e6, 2))
    matrix.append(row)

df_map = pd.DataFrame(matrix, index=[f"{i}% IH" for i in ih_levels], columns=[f"+{b}% Bonus" for b in bonus_levels])
st.write("### Land Value Matrix (ZAR Millions)")
st.dataframe(df_map.style.background_gradient(cmap='RdYlGn', axis=None))

st.caption("Note: Green cells indicate higher land value. Red/Yellow indicates the policy is making the land less valuable.")
