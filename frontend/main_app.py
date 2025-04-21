import streamlit as st
import sys
import os

from views import home, investor_dashboard

st.set_page_config(page_title="InvestorIntel.ai", layout="wide")

# Initialize routing
if "page" not in st.session_state:
    st.session_state.page = "home"
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

# Routing
if st.session_state.page == "home":
    home.render()
elif st.session_state.page == "investor_dashboard":
    investor_dashboard.render()
