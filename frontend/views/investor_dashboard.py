import streamlit as st
import requests
import pandas as pd
from PIL import Image
import os
import importlib.util
import sys
import plotly.graph_objects as go
import json
import re
import plotly.express as px

FAST_API_URL = "https://investorintel-backend-x4s2izvkca-uk.a.run.app/"

# Define status options at the module level
STATUS_OPTIONS = {
    "New":      "Not Viewed",
    "Reviewed": "Decision Pending",
    "Funded":   "Funded",
    "Rejected": "Rejected"
}

# Dynamically add project root (InvestorIntel.Ai/) to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# ✅ Now do the imports
# from backend.database import db_utils

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Function to convert formatted text to plain text with proper bullet formatting
def convert_to_plain_text(text):
    # Remove the initial information line if present
    text = re.sub(r'^Here\'s the (CEO )?information.*?:', '', text)
    text = re.sub(r'^Based on the provided search results:?', '', text)
    text = re.sub(r'^Here are the.*?:', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Replace HTML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
    
    # Replace Markdown emphasis and bold with plain text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold **text**
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic *text*
    
    # Remove result references (e.g., "(Result #2)")
    text = re.sub(r'\s*\(Result #\d+\)', '', text)
    text = re.sub(r'\s*\(Source \d+\)', '', text)
    
    # Split into lines for processing
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            lines.append('')
            continue
            
        # Process bullet points on same line
        if '• ' in line and not line.startswith('• '):
            parts = re.split(r'(• )', line)
            result = []
            for i in range(len(parts)):
                if parts[i] == '• ' and i > 0 and parts[i-1] != '':
                    # This is a bullet point that needs to start on a new line
                    result.append('\n• ')
                else:
                    result.append(parts[i])
            lines.append(''.join(result))
        else:
            # Handle other bullets format
            if line.startswith('* ') or line.startswith('- '):
                line = '• ' + line[2:]
            lines.append(line)
    
    # Join lines back
    text = '\n'.join(lines)
    
    # Make sure each bullet point starts on a new line
    text = re.sub(r'([^\n])• ', r'\1\n• ', text)
    
    # Fix spacing after bullet points
    text = re.sub(r'•\s*', '• ', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text

# Cache startup data to prevent repeated API calls
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_startups_by_status(investor_id, status):
    resp = requests.post(
        f"{FAST_API_URL}/fetch-startups-by-status",
        json={"investor_id": investor_id, "status": status}
    )
    data = resp.json()
    return data.get("startups", [])

# Cache startup details to prevent repeated API calls
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_startup_info(startup_id):
    resp = requests.post(
        f"{FAST_API_URL}/fetch-startup-info",
        json={"startup_id": startup_id}
    )
    data = resp.json()
    if data.get("status") == "success":
        return data["startup"]
    return None

# Cache report data to prevent repeated API calls
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_report(column_name, startup_id):
    resp = requests.post(
        f"{FAST_API_URL}/get-startup-column",
        json={"column_name": column_name, "startup_id": startup_id}
    )
    if resp.status_code == 200:
        value = resp.json().get("value")
        # For visualization data, we need to ensure it's valid JSON
        if column_name == "competitor_visualizations" and value:
            try:
                # Try to parse JSON if it's not already parsed
                if isinstance(value, str):
                    return json.loads(value)
                return value
            except json.JSONDecodeError:
                print(f"Failed to parse visualization JSON: {value}")
                return None
        return value
    else:
        return None

# Add a new function to fetch competitors based on industry
@st.cache_data(ttl=3)  # Cache for 5 minutes
def fetch_industry_competitors(industry, limit=5):
    resp = requests.post(
        f"{FAST_API_URL}/get-industry-competitors",
        json={"industry": industry, "limit": limit}
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"status": "error", "competitors": [], "city_distribution": {}}

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
            st.rerun()

    # 🧱 Horizontal divider comes immediately after header
    st.markdown("<hr style='border: 1px solid #ccc; margin-top: 0;'>", unsafe_allow_html=True)

def dashboard_sidebar(sidebar_col, investor_id):
    with sidebar_col:
        st.markdown("""
        <style>
        .sidebar-interior {
            padding: 18px 15px;
            background-color: #f9f9f9;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        .sidebar-title {
            font-size: 18px;
            font-weight: 600;
            color: #1E3A8A;
            margin-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
        }
        
        /* Status button styling */
        .stButton > button {
            margin-bottom: 8px !important;
            height: 42px !important;
            font-weight: 500 !important;
            transition: all 0.2s !important;
        }
        
        /* Active button */
        .stButton > button[data-baseweb="button"][kind="primary"] {
            background-color: #1E3A8A !important;
            border-color: #1E3A8A !important;
        }
        
        /* Hover state for inactive buttons */
        .stButton > button[data-baseweb="button"][kind="secondary"]:hover {
            background-color: #f0f2f6 !important;
            border-color: #1E3A8A !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='sidebar-container'>", unsafe_allow_html=True)

            # 📌 Status Filters
            st.markdown("<div class='sidebar-interior'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-title'>📌 Startup Portfolio</div>", unsafe_allow_html=True)
            
            # Status buttons - vertical layout with better styling
            selected_status_key = st.session_state.get("selected_status", "New")
            
            # New vertical layout - one button per row
            if st.button("New", key="status_btn_New", 
                      use_container_width=True,
                      type="primary" if selected_status_key == "New" else "secondary"):
                st.session_state.selected_status = "New"
                st.session_state.selected_startup_id = None
                st.session_state.show_chat = False
                st.rerun()
            
            if st.button("Reviewed", key="status_btn_Reviewed", 
                      use_container_width=True,
                      type="primary" if selected_status_key == "Reviewed" else "secondary"):
                st.session_state.selected_status = "Reviewed"
                st.session_state.selected_startup_id = None
                st.session_state.show_chat = False
                st.rerun()
            
            if st.button("Funded", key="status_btn_Funded", 
                      use_container_width=True,
                      type="primary" if selected_status_key == "Funded" else "secondary"):
                st.session_state.selected_status = "Funded"
                st.session_state.selected_startup_id = None
                st.session_state.show_chat = False
                st.rerun()
            
            if st.button("Rejected", key="status_btn_Rejected", 
                      use_container_width=True,
                      type="primary" if selected_status_key == "Rejected" else "secondary"):
                st.session_state.selected_status = "Rejected"
                st.session_state.selected_startup_id = None
                st.session_state.show_chat = False
                st.rerun()
                
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Add divider
            st.markdown("<hr style='margin: 20px 0; border-color: #e0e0e0;'>", unsafe_allow_html=True)
            
            # Add Q&A Bot Button with better styling
            st.markdown("<div class='sidebar-interior'>", unsafe_allow_html=True)
            st.markdown("<div class='sidebar-title'>💬 AI Assistant</div>", unsafe_allow_html=True)
            
            if st.button("💬 Q&A Bot for Startups & Industry", 
                    key="chat_button", 
                    use_container_width=True,
                    type="primary" if st.session_state.get("show_chat", False) else "secondary"):
                st.session_state.show_chat = True
                st.session_state.selected_startup_id = None
                st.rerun()
            
            # Add button to return to startup view
            if st.session_state.get("show_chat", False):
                if st.button("🔙 Return to Startups", key="return_button", use_container_width=True):
                    st.session_state.show_chat = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

def display_startup_cards(startup_list, main_col):
    with main_col:
        st.markdown("## 🚀 Available Startups")
        st.markdown("Select a startup to view detailed information")
        
        # Calculate how many startups to display per row (3 looks good)
        startups_per_row = 3
        
        # Define round type colors
        round_colors = {
            "Seed": "#4CAF50",       # Green
            "Series A": "#2196F3",   # Blue
            "Series B": "#9C27B0",   # Purple
            "Series C": "#F44336",   # Red
            "Convertible Note": "#FF9800", # Orange
            "SAFE": "#795548"        # Brown
        }
        
        # Create rows based on number of startups
        for i in range(0, len(startup_list), startups_per_row):
            # Get startups for this row
            row_startups = startup_list[i:i+startups_per_row]
            
            # Create columns for this row
            cols = st.columns(startups_per_row)
            
            # Display each startup in its column
            for j, startup in enumerate(row_startups):
                # Get startup details for display
                startup_id = startup['startup_id']
                
                # Use the existing function to get full startup data
                # This makes an API call but we benefit from caching
                full_startup_data = fetch_startup_info(startup_id)
                
                if full_startup_data:
                    # Extract the correct fields from the database
                    industry = full_startup_data.get('INDUSTRY', 'N/A')
                    funding_amount = full_startup_data.get('FUNDING_AMOUNT_REQUESTED', 0)
                    round_type = full_startup_data.get('ROUND_TYPE', 'N/A')
                    # Get color for round type, default to gray if not found
                    round_color = round_colors.get(round_type, "#9E9E9E")
                else:
                    industry = "N/A"
                    funding_amount = 0
                    round_type = "N/A"
                    round_color = "#9E9E9E"
                
                with cols[j]:
                    # Create a card-like container for each startup with round type badge
                    with st.container():
                        st.markdown(f"""
                        <div class="startup-card">
                            <h3>{startup['startup_name']}</h3>
                            <p><strong>Industry:</strong> {industry}</p>
                            <p><strong>Funding Request:</strong> ${float(funding_amount):,.2f}</p>
                            <div style="display: inline-block; background-color: {round_color}; color: white; 
                                        padding: 4px 8px; border-radius: 4px; font-size: 0.8em; margin-top: 5px;">
                                {round_type}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Reliable button for interaction
                        if st.button(f"View Details", key=f"startup_{startup_id}"):
                            st.session_state.selected_startup_id = startup_id
                            st.session_state.show_chat = False
                            st.rerun()

def display_chatbot(main_col):
    with main_col:
        st.markdown("## 💬 InvestorIntel AI Assistant")
        st.markdown("Ask me any questions about startups, market trends, or investment strategies.")
        
        # Initialize chat history if not exists
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Add improved styling for chat interface alignment
        st.markdown("""
        <style>
        /* Better chat container styles */
        .chat-history {
            display: flex;
            flex-direction: column;
            max-height: 60vh;
            overflow-y: auto;
            border: 1px solid #e6e9ef;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #f8f9fa;
            width: 100%;
        }
        
        /* Message containers */
        .user-message-container, .assistant-message-container {
            display: flex;
            width: 100%;
            margin-bottom: 16px;
        }
        
        /* User message container - align to right */
        .user-message-container {
            justify-content: flex-end;
        }
        
        /* Assistant message container - align to left */
        .assistant-message-container {
            justify-content: flex-start;
        }
        
        /* Message bubbles */
        .message-content {
            padding: 14px 18px;
            border-radius: 18px;
            max-width: 75%;
            word-wrap: break-word;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            font-size: 15px;
            line-height: 1.5;
        }
        
        /* User message specific styling */
        .user-message-container .message-content {
            background-color: #1E88E5;
            color: white;
            text-align: left;
            border-bottom-right-radius: 5px;
        }
        
        /* Assistant message specific styling */
        .assistant-message-container .message-content {
            background-color: white;
            color: #333;
            border: 1px solid #e0e0e0;
            text-align: left;
            border-bottom-left-radius: 5px;
        }
        
        /* Input container */
        .chat-input-container {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 15px;
        }
        
        /* Make send button align vertically with input */
        .send-button-container {
            display: flex;
            align-items: center;
            height: 38px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create a container for chat history
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            st.markdown('<div class="chat-history">', unsafe_allow_html=True)
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"""
                    <div class="user-message-container">
                        <div class="message-content">
                            {message["content"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    plain_text = convert_to_plain_text(message["content"])
                    st.markdown(f"""
                    <div class="assistant-message-container">
                        <div class="message-content">
                            {plain_text}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Create a container for the input area with better alignment
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_input(
                "", 
                key="dashboard_chat_input", 
                placeholder="Type your question here..."
            )
        
        with col2:
            st.markdown('<div class="send-button-container">', unsafe_allow_html=True)
            send_button = st.button("Send", key="send_button", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if send_button and user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Send query to backend
            with st.spinner('Searching database...'):
                try:
                    response = requests.post(
                        f"{FAST_API_URL}/chat",
                        json={"query": user_input}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        ai_response = result.get("response", "Sorry, I couldn't find an answer to your question.")
                        
                        # Add assistant message to chat history
                        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    else:
                        error_msg = f"Error: {response.status_code} - {response.text}"
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                        
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            
            # Force a rerun to update the chat history display
            st.rerun()
        
        # Add button to clear chat history
        if st.button("Clear Chat History", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

def display_startup_details(startup_id, main_col):
    with main_col:
        # Add a back button at the top
        if st.button("← Back to Startup List", key="back_button"):
            st.session_state.selected_startup_id = None
            st.rerun()
            
        # Use cached function to prevent repeated API calls
        startup_data = fetch_startup_info(startup_id)
        if not startup_data:
            st.error("Failed to load startup data")
            return

        # Create Tabs with improved styling
        st.markdown("""
        <style>
        /* Make tabs larger and more visible */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 5px;
            padding: 10px 16px;
            font-size: 16px;
            font-weight: 500;
            background-color: #f0f2f6;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #1E3A8A !important;
            color: white !important;
        }
        
        /* Funding details card */
        .funding-details {
            background-color: #f8f9fa;
            border: 1px solid #e6e9ef;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .funding-metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        
        .metric-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .metric-label {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 20px;
            font-weight: 600;
            color: #1E3A8A;
        }
        
        .round-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            color: white;
            font-weight: 500;
            font-size: 14px;
            margin-bottom: 15px;
        }
        
        /* Status change button styling */
        .status-section {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 15px;
            margin-top: 25px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["📄 Summary", "📊 Competitor Analysis", "📈 Market Analysis", "📰 News Trends"])

        # ---------- 🟢 Summary Tab ----------
        with tab1:
            st.markdown("## 🚀 Startup Details")
            
            # Basic information
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Startup Name:** {startup_data['STARTUP_NAME']}")
                st.markdown(f"**Industry:** {startup_data['INDUSTRY']}")
                st.markdown(f"**Email:** {startup_data['EMAIL_ADDRESS']}")
            
            with col2:
                st.markdown(f"**Website:** [Visit]({startup_data['WEBSITE_URL']})")
                if startup_data["PITCH_DECK_LINK"]:
                    st.markdown(f"[📄 View Pitch Deck]({startup_data['PITCH_DECK_LINK']})")
                if startup_data.get("ANALYTICS_REPORT"):
                    st.download_button("📊 Download Analytics Report", data=startup_data["ANALYTICS_REPORT"], file_name="analytics_report.txt")
            
            # Round type with color coding
            round_type = startup_data.get('ROUND_TYPE', 'N/A')
            round_colors = {
                "Seed": "#4CAF50",
                "Series A": "#2196F3",
                "Series B": "#9C27B0",
                "Series C": "#F44336",
                "Convertible Note": "#FF9800",
                "SAFE": "#795548"
            }
            round_color = round_colors.get(round_type, "#9E9E9E")
            
            # Enhanced funding details section
            st.markdown(f"""
            <div class="funding-details">
                <div class="round-badge" style="background-color: {round_color};">
                    {round_type}
                </div>
                <h3>💰 Funding Details</h3>
                <div class="funding-metrics">
                    <div class="metric-card">
                        <div class="metric-label">Funding Requested</div>
                        <div class="metric-value">${float(startup_data.get('FUNDING_AMOUNT_REQUESTED', 0)):,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Equity Offered</div>
                        <div class="metric-value">{float(startup_data.get('EQUITY_OFFERED', 0)):,.2f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Pre-money Valuation</div>
                        <div class="metric-value">${float(startup_data.get('PRE_MONEY_VALUATION', 0)):,.2f}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Post-money Valuation</div>
                        <div class="metric-value">${float(startup_data.get('POST_MONEY_VALUATION', 0)):,.2f}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show the executive summary
            summary_text = fetch_report("summary_report", startup_id)
            if summary_text:
                st.markdown("### Pitch Deck Summary")
                st.info(summary_text)
            else:
                st.info("No summary available for this startup.")

            # Add status change section
            st.markdown("""
            <div class="status-section">
                <h3>✅ Update Startup Status</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Get current status - this would need to be fetched from the database
            # For now, we'll assume it's in the startup data
            current_status = startup_data.get('STATUS', 'Not Viewed')
            
            # Status selection dropdown
            new_status = st.selectbox(
                "Select New Status:",
                options=["Not Viewed", "Decision Pending", "Funded", "Rejected"],
                index=["Not Viewed", "Decision Pending", "Funded", "Rejected"].index(current_status) if current_status in ["Not Viewed", "Decision Pending", "Funded", "Rejected"] else 0
            )
            
            # Get the investor ID from session state
            investor_id = st.session_state.get('investor_id', None)
            
            # Update status button
            if st.button("Update Status", key="update_status_btn", use_container_width=True):
                if investor_id:
                    try:
                        # Call API to update status
                        response = requests.post(
                            f"{FAST_API_URL}/update-startup-status",
                            json={
                                "investor_id": investor_id,
                                "startup_id": startup_id,
                                "status": new_status
                            }
                        )
                        
                        if response.status_code == 200:
                            st.success(f"Status updated to: {new_status}")
                            # Clear cache to refresh the startup data
                            fetch_startup_info.clear()
                            fetch_startups_by_status.clear()
                        else:
                            st.error(f"Failed to update status: {response.text}")
                    except Exception as e:
                        st.error(f"Error updating status: {str(e)}")
                else:
                    st.error("Could not determine investor ID. Please log in again.")
            
            
        # ---------- 🟡 Competitor Analysis Tab ----------
        with tab2:
            st.markdown("### 🧩 Competitor Analysis")
            
            # Get industry from startup data
            industry = startup_data.get('INDUSTRY', 'Unknown')
            print("Industry: ", industry)
            if industry != 'Unknown':
                # Fetch competitors using the new API
                competitors_data = fetch_industry_competitors(industry, limit=10)
                print("Competitors Data: ", competitors_data)
                if competitors_data.get('status') == 'success' and competitors_data.get('competitors'):
                    competitors = competitors_data['competitors']
                    
                    # Display header and explanation
                    st.markdown(f"#### Top Industry Competitors in {industry}")
                    st.markdown("Below are the leading companies in this industry based on revenue and growth metrics. These companies represent potential competitors or market benchmarks for the startup.")
                    
                    # Display competitor details with descriptions
                    for i, comp in enumerate(competitors):
                        with st.expander(f"{comp.get('COMPANY', 'Unknown Company')}"):
                            st.markdown(f"**Description:** {comp.get('SHORT_DESCRIPTION', 'No description available')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Revenue:** {comp.get('REVENUE_FORMATTED', 'N/A')}")
                                st.markdown(f"**Growth Rate:** {comp.get('GROWTH_FORMATTED', 'N/A')}")
                            
                            with col2:
                                st.markdown(f"**Employees:** {comp.get('EMPLOYEES_FORMATTED', 'N/A')}")
                                st.markdown(f"**Location:** {comp.get('CITY', 'N/A')}, {comp.get('COUNTRY', 'N/A')}")
                            
                            # Display links if available
                            links_col1, links_col2 = st.columns(2)
                            with links_col1:
                                if comp.get('HOMEPAGE_URL'):
                                    st.markdown(f"[Visit Website]({comp.get('HOMEPAGE_URL')})")
                            
                            with links_col2:
                                if comp.get('LINKEDIN_URL'):
                                    st.markdown(f"[LinkedIn Profile]({comp.get('LINKEDIN_URL')})")
                    
                    # Display the competitor data in a table
                    st.markdown("### Competitor Metrics")
                    
                    # Create a DataFrame for the table
                    table_data = {
                        "Company": [comp.get('COMPANY', 'Unknown') for comp in competitors],
                        "Revenue": [comp.get('REVENUE_FORMATTED', 'N/A') for comp in competitors],
                        "Growth Rate": [comp.get('GROWTH_FORMATTED', 'N/A') for comp in competitors],
                        "Employees": [comp.get('EMPLOYEES_FORMATTED', 'N/A') for comp in competitors],
                        "Location": [f"{comp.get('CITY', 'N/A')}, {comp.get('COUNTRY', 'N/A')}" for comp in competitors]
                    }
                    
                    comp_df = pd.DataFrame(table_data)
                    st.dataframe(comp_df, use_container_width=True)
                    
                    # Create city distribution chart if we have city data
                    city_distribution = competitors_data.get('city_distribution', {})
                    if city_distribution:
                        st.markdown("### Geographic Distribution")
                        st.markdown("Distribution of competitors by city:")
                        
                        # Create a DataFrame for the chart
                        city_df = pd.DataFrame({
                            'City': list(city_distribution.keys()),
                            'Count': list(city_distribution.values())
                        })
                        
                        # Sort by count descending
                        city_df = city_df.sort_values('Count', ascending=False)
                        
                        # Create the bar chart
                        fig = px.bar(
                            city_df, 
                            x='City', 
                            y='Count',
                            title='Competitor Distribution by City',
                            color='Count',
                            color_continuous_scale='Blues'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(f"No competitor data available for the {industry} industry.")
            else:
                st.info("Industry information is not available for this startup.")

        # ---------- 🔵 Market Analysis Tab ----------
        with tab3:
            st.markdown("### 🌐 Market Analysis")
            
            # Display the analytics report
            analytics_text = fetch_report("analytics_report", startup_id) 
            if analytics_text:
                st.markdown("### Market Insights")
                st.info(analytics_text)
            else:
                st.info("No market analysis data available for this startup.")
                
            # ---------- Add visualization section only in Market Analysis tab ----------
            st.markdown("## 📈 Performance Visualizations")
            st.markdown("### Key Metrics and Competitive Analysis")
            
            visualization_data = fetch_report("competitor_visualizations", startup_id)
            
            if visualization_data:
                try:
                    # Parse the JSON data
                    viz_data = visualization_data
                    if isinstance(viz_data, str):
                        viz_data = json.loads(viz_data)
                    
                    # Create columns for visualization charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if "revenue_chart" in viz_data:
                            st.subheader("Revenue Comparison")
                            revenue_fig = go.Figure(viz_data["revenue_chart"])
                            st.plotly_chart(revenue_fig, use_container_width=True, key="revenue_chart")
                    
                    with col2:
                        if "growth_chart" in viz_data:
                            st.subheader("Growth Metrics")
                            growth_fig = go.Figure(viz_data["growth_chart"])
                            st.plotly_chart(growth_fig, use_container_width=True, key="growth_chart")
                except Exception as e:
                    st.error(f"Error displaying visualizations: {e}")
            else:
                st.info("No visualization data available for this startup.")

        # ---------- 🔴 News Trends Tab ----------
        with tab4:
            st.markdown("### 🗞️ News Trends")
            news_text = fetch_report("news_report", startup_id)
            if news_text:
                # Parse the news text - assuming format like "Title: URL"
                st.markdown(news_text)
            else:
                st.info("No news data available for this startup.")

def render():
    # Initialize session state variables
    if "selected_status" not in st.session_state:
        st.session_state.selected_status = "New"
        
    if "show_chat" not in st.session_state:
        st.session_state.show_chat = False
        
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Add custom styling for the dashboard and chat components
    st.markdown("""
    <style>
    /* General styles */
    .main-header {
        font-size: 42px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 10px;
    }
    
    .block-container {
        padding-top: 0 !important;
    }
    
    /* Header styles */
    .header {
        position: sticky;
        top: 0;
        z-index: 100;
        background-color: white;
    }
    
    /* Sidebar styles */
    .sidebar-container {
        border-right: 1px solid #ccc;
        padding-right: 20px;
        margin-right: 20px;
        max-height: 80vh;
        overflow-y: auto;
    }
    
    /* Improve spacing between sidebar and main content */
    [data-testid="column"]:first-child {
        padding-right: 2rem;
        border-right: 2px solid #eaeaea;
    }
    
    [data-testid="column"]:nth-child(2) {
        padding-left: 2.5rem !important;
        margin-left: 1.5rem !important;
    }
    
    /* Startup card styles */
    .startup-card {
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .startup-card h3 {
        margin-top: 0;
        color: #1E3A8A;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("is_logged_in"):
        st.warning("You must log in first.")
        st.session_state.page = "home"
        st.rerun()

    # Get investor info (cached to prevent repeated API calls)
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_investor_info(username):
        resp = requests.post(
            f"{FAST_API_URL}/fetch-investor-by-username",
            json={"username": username}
        )
        data = resp.json()
        if data.get("status") == "success":
            return data["investor"]
        return None

    investor_info = get_investor_info(st.session_state.username)
    if not investor_info:
        st.error("Could not load investor information")
        return

    investor_id = investor_info["INVESTOR_ID"]
    first_name = investor_info["FIRST_NAME"]

    # -------- 🧢 HEADER (Logo + Welcome + Logout) --------
    st.markdown('<div class="header">', unsafe_allow_html=True)
    dashboard_header(first_name)
    st.markdown('</div>', unsafe_allow_html=True)

    # -------- 🧭 MAIN LAYOUT (Sidebar + Main) --------
    sidebar_col, main_col = st.columns([1, 4])  # Changed from [1.3, 5.7] to make the ratio clearer
    
    # Load the sidebar with status buttons and chat button
    dashboard_sidebar(sidebar_col, investor_id)
    
    # Main content - Three modes:
    # 1. Chat Mode
    # 2. Startup Cards (Grid View)
    # 3. Startup Details (Selected startup)
    
    # Mode 1: Chat Interface
    if st.session_state.get("show_chat", False):
        display_chatbot(main_col)
    
    # Mode 2 & 3: Startup View
    else:
        selected_status = STATUS_OPTIONS[st.session_state.selected_status]
        
        # Use cached function to prevent repeated API calls
        startup_list = fetch_startups_by_status(investor_id, selected_status)
        
        # If a startup is selected, show its details
        if st.session_state.get("selected_startup_id"):
            display_startup_details(st.session_state.selected_startup_id, main_col)
        # Otherwise, show the grid of startup cards
        else:
            if not startup_list:
                with main_col:
                    st.info(f"No startups found in the '{st.session_state.selected_status}' category.")
            else:
                display_startup_cards(startup_list, main_col)