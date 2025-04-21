import streamlit as st
import pandas as pd
from PIL import Image
import os
import importlib.util
import sys

# Dynamically add project root (InvestorIntel.Ai/) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# ✅ Now do the imports
from backend.database import db_utils

def dashboard_header(first_name):
    # Set padding to 0 for top alignment
    st.markdown("""
            <style>
            /* Keep small top padding to avoid image clipping */
            .block-container {
                padding-top: 0.5rem !important;
            }
            .welcome-text {
                text-align: left;
                margin-top: 30px;
                font-size: 22px;
            }
            /* Prevent image cropping */
            .stImage > img {
                margin-top: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Columns with precise proportions
    header_col1, header_col2, header_col3 = st.columns([1.3, 4.7, 1])

    with header_col1:
        logo_path = os.path.join(PROJECT_ROOT, "frontend", "assets", "InvestorIntel_Logo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        else:
            st.warning("⚠️ Logo image not found.")

    with header_col2:
        st.markdown(
            f"<h3 style='text-align:left; margin-top: 30px;'>👋 Welcome, {first_name}!</h3>",
            unsafe_allow_html=True
        )

    with header_col3:
        st.write("")  # vertical alignment spacer
        st.write("")
        if st.button("🚪 Logout"):
            st.session_state.page = "home"
            st.session_state.is_logged_in = False
            st.experimental_rerun()

    # 🧱 Horizontal divider comes immediately after header
    st.markdown("<hr style='border: 1px solid #ccc; margin-top: 0;'>", unsafe_allow_html=True)


def dashboard_sidebar(sidebar_col, investor_id):
    with sidebar_col:
        with st.container():
            st.markdown("<div class='sidebar-container'>", unsafe_allow_html=True)

            # 📌 Status Filters
            st.markdown("### 📌 Select Startup")
            status_options = {
                "New": "Not Viewed",
                "Reviewed": "Decision Pending",
                "Funded": "Funded",
                "Rejected": "Rejected"
            }
            selected_status_key = st.radio("**Stage:**", list(status_options.keys()))
            selected_status = status_options[selected_status_key]

            # 📄 Startup List
            startup_list = db_utils.get_startups_by_status(investor_id, selected_status)
            if startup_list.empty:
                st.info("No startups found in this category.")
                st.session_state.selected_startup_id = None
            else:
                startup_names = startup_list["startup_name"].tolist()
                selected_startup_name = st.selectbox("**📄 Startups:**", startup_names)
                selected_startup_id = startup_list[startup_list["startup_name"] == selected_startup_name]["startup_id"].values[0]
                st.session_state.selected_startup_id = selected_startup_id

            st.markdown("</div>", unsafe_allow_html=True)  # Close sidebar container

def render():
    if not st.session_state.get("is_logged_in"):
        st.warning("You must log in first.")
        st.session_state.page = "home"
        st.experimental_rerun()

    investor_username = st.session_state.username
    investor_info = db_utils.get_investor_by_username(investor_username)
    investor_id = investor_info["INVESTOR_ID"]
    first_name = investor_info["FIRST_NAME"]

    # -------- 🧢 HEADER (Logo + Welcome + Logout) --------
    dashboard_header(first_name)

    # -------- 🧭 MAIN LAYOUT (Sidebar + Main) --------
    # 👉 Wrap sidebar in scrollable styled container with right border
    st.markdown("""
        <style>
            .sidebar-container {
                border-right: 1px solid #ccc;
                padding-right: 15px;
                max-height: 75vh;
                overflow-y: auto;
            }
        </style>
    """, unsafe_allow_html=True)

    # Columns layout
    sidebar_col, main_col = st.columns([1.3, 5.7])

    dashboard_sidebar(sidebar_col, investor_id)

    with main_col:
        if not st.session_state.get("selected_startup_id"):
            st.info("Select a startup from the left panel to view details.")
        else:
            startup_data = db_utils.get_startup_info_by_id(st.session_state.selected_startup_id)
            st.markdown("## 🚀 Startup Details")
            st.markdown(f"**Name:** {startup_data['STARTUP_NAME']}")
            st.markdown(f"**Industry:** {startup_data['INDUSTRY']}")
            st.markdown(f"**Founder:** {startup_data['FOUNDER_NAME']}")
            st.markdown(f"**Email:** {startup_data['EMAIL_ADDRESS']}")
            st.markdown(f"**Website:** [Visit]({startup_data['WEBSITE_URL']})")
            st.markdown(f"**LinkedIn:** [Profile]({startup_data['LINKEDIN_URL']})")
            st.markdown(f"**Valuation Ask:** ${startup_data['VALUATION_ASK']:,.2f}")
            st.markdown(f"**Short Description:** {startup_data['SHORT_DESCRIPTION']}")

            if startup_data["PITCH_DECK_LINK"]:
                st.markdown(f"[📄 View Pitch Deck]({startup_data['PITCH_DECK_LINK']})")

            if startup_data.get("ANALYTICS_REPORT"):
                st.download_button("📊 Download Analytics Report", data=startup_data["ANALYTICS_REPORT"], file_name="analytics_report.txt")
