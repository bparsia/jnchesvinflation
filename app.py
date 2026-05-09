import streamlit as st

st.set_page_config(
    page_title="JNCHES Pay Spine vs Inflation",
    page_icon="💷",
    layout="wide",
)

overview = st.Page("pages/0_Overview.py", title="Overview", icon="📈", default=True)
spine = st.Page("pages/1_SpinePoints.py", title="Spine Points", icon="🔢")
data = st.Page("pages/2_Data.py", title="Raw Data", icon="📋")
uss = st.Page("pages/4_USS_Scenarios.py", title="USS Scenarios", icon="🏛️")
about = st.Page("pages/3_About.py", title="About", icon="ℹ️")

pg = st.navigation([overview, spine, data, uss, about])
pg.run()
