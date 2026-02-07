import streamlit as st
import pandas as pd

# -----------------------------
# CONFIG & CONSTANTS
# -----------------------------
ZONING = {
    "GR2 (Residential - 1.0 FF)": {"ff": 1.0, "coverage": 0.6},
    "GR4 (High Density - 1.5 FF)": {"ff": 1.5, "coverage": 0.6},
    "MU1 (Mixed Use - 1.5 FF)": {"ff": 1.5, "coverage": 0.75},
    "MU2 (High Density Mixed - 4.0 FF)": {"ff": 4.0, "coverage": 1.0},
    "GB7 (CBD/High Rise - 12.0 FF)": {"ff": 12.0, "coverage": 1.0},
}

DC_RATE = 514.10      # ZAR per m2 (estimate)
IH_CAP_PRICE = 15000  # Affordable cap price


# -----------------------------
# HELPERS
# -----------------------------
def apply_css() -> None:
    st.set_page_config(page_title="CPT Property Redevelopment Calc", layout="wide")
    st.markdown(
        """
        <style>
        .main { background-color: #f5f7f9; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_inputs():
    st.sidebar.title("🛠️ Development Inputs")

    land_size = st.sidebar.number_input("Land Area (m²)", value=1000, step=100, min_value=1)
    zone_choice = st.sidebar.selectbox("Zoning Preset", list(ZONING.keys()))
    parking_zone = st.sidebar.radio("Parking Zone", ["Standard", "PT1 (Reduced)", "PT2 (Zero)"])

    st.sidebar.subheader("Market Assumptions")
    market_price = st.sidebar.slider("Market Sales Price (R/m²)", 20000, 80000, 45000)
    const_cost_base = st.sidebar.slider("Base Construction (R/m²)", 12000, 25000, 17000)

    # Adjust cost based on parking zone
    if parking_zone == "PT2 (Zero)":
        const_cost = const_cost_base * 0.85
    elif parking_zone == "PT1 (Reduced)":
        const_cost = const_cost_base * 0.95
    else:
        const_cost = const_cost_base

    st.sidebar.subheader("Policy Sensitivity")
    ih_req = st.sidebar.slider("Inclusionary Housing (%)", 0, 30, 20)
    density_bonus = st.sidebar.slider("Density Bonus (%)", 0, 100, 20)

    return {
        "land_size": land_size,
        "zone_choice": zone_choice,
        "parking_zone": parking_zone,
        "market_price": market_price,
        "const_cost": const_cost,
        "ih_req": ih_req,
        "density_bonus": density_bonus,
    }


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
    return {
        "rlv": rlv,
        "bulk": total_bulk,
        "dcs": dev_charges,
        "gdv": gdv,
    }


@st.cache_data(show_spinner=False)
def build_sensitivity_table(land_size, ff_val, market_price, const_cost):
    matrix = []
    ih_levels = [0, 10, 20, 30]
    bonus_levels = [0, 20, 40, 60, 80, 100]

    for ih in ih_levels:
        row = []
        for b in bonus_levels:
            out = calculate_metrics(land_size, ff_val, b, ih, market_price, const_cost)
            row.append(round(out["rlv"] / 1e6, 2))
        matrix.append(row)

    return pd.DataFrame(
        matrix,
        index=[f"{i}% IH" for i in ih_levels],
        columns=[f"+{b}% Bonus" for b in bonus_levels],
    )


def render_header(inputs):
    st.title("Cape Town Residual Land Value Calculator")
    st.info(
        f"Scenario: {inputs['zone_choice']} in a {inputs['parking_zone']} area "
        f"with {inputs['ih_req']}% Inclusionary Housing."
    )


def render_metrics(outputs):
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(label="Residual Land Value", value=f"R {max(0, outputs['rlv'] / 1e6):.2f}M")
    c2.metric(label="Total Bulk (GBA)", value=f"{outputs['bulk']:,.0f} m²")
    c3.metric(label="Dev Charges", value=f"R {outputs['dcs'] / 1e3:,.0f}k")
    c4.metric(label="Total GDV", value=f"R {outputs['gdv'] / 1e6:.2f}M")


def render_sensitivity(df_map):
    st.subheader("Sensitivity: How Density Bonuses offset Inclusionary Requirements")
    st.write("### Land Value Matrix (ZAR Millions)")
    st.dataframe(df_map.style.background_gradient(cmap="RdYlGn", axis=None))
    st.caption(
        "Note: Green cells indicate higher land value. Red/Yellow indicates the policy is making the land less valuable."
    )


def main():
    apply_css()

    # UI guard: show helpful errors in the app instead of a blank crash
    try:
        inputs = get_inputs()
        ff_val = ZONING[inputs["zone_choice"]]["ff"]

        outputs = calculate_metrics(
            inputs["land_size"],
            ff_val,
            inputs["density_bonus"],
            inputs["ih_req"],
            inputs["market_price"],
            inputs["const_cost"],
        )

        render_header(inputs)
        render_metrics(outputs)

        df_map = build_sensitivity_table(
            inputs["land_size"], ff_val, inputs["market_price"], inputs["const_cost"]
        )
        render_sensitivity(df_map)

    except Exception as e:
        st.error("Something went wrong while running the app.")
        st.exception(e)


if __name__ == "__main__":
    main()
