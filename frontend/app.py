import streamlit as st
import requests
import os
import base64
import io
import json
import traceback
import re
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

FAST_API_URL = "https://investorintel-backend-x4s2izvkca-uk.a.run.app/"

# Set page configuration
st.set_page_config(
    page_title="InvestorIntel",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for styling
def apply_custom_styling():
    st.markdown("""
    <style>
    .main-header {
        font-size: 42px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 10px;
    }
    .sidebar-content {
        padding: 20px;
    }
    .stButton>button {
        width: 100%;
        background-color: #1E3A8A;
        color: white;
    }
    .ai-analysis {
        background-color: #f0f7ff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 30px;
    }
    .chat-message {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        width: 100%;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #1E88E5;
        text-align: left;
    }
    .bot-message {
        background-color: #F5F7FF;
        border-left: 4px solid #1E3A8A;
        text-align: left;
    }
    /* Make text selectable in text areas */
    textarea {
        color: black !important;
        background-color: #f8f9fa !important;
    }
    /* Styling for the chat input */
    .user-input {
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 8px 12px;
        font-size: 14px;
        width: 100%;
        box-sizing: border-box;
    }
    /* Remove label names */
    div.stTextArea label {
        display: none;
    }
    /* Fix input field heights */
    .fixed-height textarea {
        min-height: 60px !important;
        max-height: 60px !important;
    }
    /* Answer formatting */
    .answer-box {
        background-color: #f5f7ff;
        border-left: 4px solid #1E3A8A;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .question-box {
        background-color: #e3f2fd;
        border-left: 4px solid #1E88E5;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .report-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-top: 20px;
        margin-bottom: 20px;
        overflow-y: auto;
        max-height: 800px;
    }
    </style>
    """, unsafe_allow_html=True)

# Apply custom styling
apply_custom_styling()

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'upload'  # Default page

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

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

# Create sidebar with logo and title
with st.sidebar:
    st.markdown('<div class="main-header">InvestorIntel</div>', unsafe_allow_html=True)
    
    # This is a placeholder for logo
    st.markdown("📊", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation
    st.subheader("Navigation")
    if st.button("📤 Upload Pitch Deck"):
        st.session_state.page = 'upload'
    if st.button("💬 Startup Assistant"):
        st.session_state.page = 'chatbot'
    
    st.markdown("---")
    
    # Only show these inputs on the upload page
    if st.session_state.page == 'upload':
        # Industry selection
        st.subheader("Select Industry")
        industry = st.selectbox(
            "Industry",
            options=["AI", "Healthcare", "Tech Services", "Automotive", "Defense", "Entertainment", "Renewable Energy"]
        )
        
        # Startup name
        st.subheader("Startup Information")
        startup_name = st.text_input("Startup Name")
        
        # LinkedIn URL(s)
        st.subheader("LinkedIn URLs")
        linkedin_urls = []
        num_urls = st.number_input("Number of LinkedIn URLs", min_value=1, max_value=5, value=1)
        
        for i in range(int(num_urls)):
            url = st.text_input(f"LinkedIn URL {i+1}", key=f"url_{i}")
            if url:
                linkedin_urls.append(url)

        # Website URL
        st.subheader("Company Website")
        website_url = st.text_input("Website URL", placeholder="https://company-website.com")

# UPLOAD PAGE
if st.session_state.page == 'upload':
    st.title("Pitch Deck Analysis")
    st.write("Upload your pitch deck PDF for intelligent analysis and investor-ready summaries.")

    # File uploader for pitch deck
    uploaded_file = st.file_uploader("Upload Pitch Deck (PDF)", type=["pdf"])

    if uploaded_file is not None:
        # Display the uploaded file info
        file_details = {"FileName": uploaded_file.name, "FileType": uploaded_file.type, "FileSize": f"{uploaded_file.size / 1024:.2f} KB"}
        st.write(file_details)
        
        # Process button
        if st.button("Process Pitch Deck"):
            # First check if the startup already exists
            startup_exists = False
            
            if startup_name and startup_name.lower() != "unknown":
                with st.spinner('Checking if startup already exists...'):
                    check_response = requests.post(
                        f"{FAST_API_URL}/check-startup-exists", 
                        json={"startup_name": startup_name}
                    )
                    
                    if check_response.status_code == 200:
                        check_result = check_response.json()
                        startup_exists = check_result.get("exists", False)
            
            # After the spinner completes, check if we should show an error
            if startup_exists:
                st.warning(f"A startup with the name '{startup_name}' already exists in our database.")
            else:
                # Only proceed to processing if the startup doesn't exist
                with st.spinner('Processing your pitch deck...'):
                    try:
                        # Prepare data for API request
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                        
                        # Prepare form data
                        form_data = {
                            "startup_name": startup_name if startup_name else "Unknown",
                            "industry": industry,
                            "linkedin_urls": json.dumps(linkedin_urls),
                            "website_url": website_url
                        }
                        
                        # Send to FastAPI backend
                        response = requests.post(
                            f"{FAST_API_URL}/process-pitch-deck",
                            files=files,
                            data=form_data
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # Check if error was returned (for duplicate startup)
                            if "error" in result and result["error"] == "startup_exists":
                                st.warning(result["message"])
                            else:
                                # Display the summary
                                st.success("Pitch deck processed successfully!")
                                st.subheader("Investor Summary")
                                st.markdown(result["summary"])
                                
                                # Display competitor visualizations if available
                                if "competitor_visualizations" in result and result["competitor_visualizations"]:
                                    st.subheader("Competitor Analysis")
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        if "revenue_chart" in result["competitor_visualizations"]:
                                            revenue_fig = go.Figure(result["competitor_visualizations"]["revenue_chart"])
                                            st.plotly_chart(revenue_fig, use_container_width=True)
                                    
                                    with col2:
                                        if "growth_chart" in result["competitor_visualizations"]:
                                            growth_fig = go.Figure(result["competitor_visualizations"]["growth_chart"])
                                            st.plotly_chart(growth_fig, use_container_width=True)
                                
                                # Display investment analysis report if available
                                if "final_report" in result and result["final_report"]:
                                    st.subheader("Investment Analysis Report")
                                    with st.expander("View Full Investment Report", expanded=True):
                                        st.markdown(f'<div class="report-container">{result["final_report"]}</div>', unsafe_allow_html=True)
                                
                                # Display S3 location info
                                st.subheader("Storage Information")
                                st.info(f"PDF stored at: {result['s3_location']}")
                                
                                # Display embedding status
                                if "embedding_status" in result:
                                    embedding_status = result["embedding_status"]
                                    if embedding_status == "success":
                                        st.success("✅ Embedding successfully stored in Pinecone")
                                    elif embedding_status == "failed":
                                        st.warning("⚠️ Failed to store embedding in Pinecone")
                                    elif embedding_status == "skipped":
                                        st.info("ℹ️ Embedding storage skipped - Pinecone not configured")
                                    else:
                                        st.error(f"❌ Error storing embedding: {embedding_status}")
                                    
                                # Display Snowflake storage status if available
                                if "snowflake_status" in result:
                                    snowflake_status = result["snowflake_status"]
                                    if snowflake_status == "success":
                                        st.success("✅ Summary successfully stored in Snowflake")
                                    elif snowflake_status == "failed":
                                        st.warning("⚠️ Failed to store summary in Snowflake")
                                    elif snowflake_status == "skipped":
                                        st.info("ℹ️ Snowflake storage skipped - not configured")
                                    else:
                                        st.error(f"❌ Error storing in Snowflake: {snowflake_status}")
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                        st.exception(e)

# CHATBOT PAGE
elif st.session_state.page == 'chatbot':
    st.title("Startup Assistant")
    st.write("Ask questions about startups in our database to get AI-powered insights.")
    
    # Create a container for chat history
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for i, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                # For user messages, use a styled div
                st.markdown(f"""
                <div class="question-box">
                {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                # For assistant messages, use a styled div with properly formatted text
                plain_text = convert_to_plain_text(message["content"])
                st.markdown(f"""
                <div class="answer-box">
                {plain_text}
                </div>
                """, unsafe_allow_html=True)
    
    # Create a container for the input area
    input_container = st.container()
    
    # Add a form with a single-line input field
    with input_container:
        with st.form(key="chat_form", clear_on_submit=True):
            # Small fixed-height input field
            st.markdown('<p style="margin-bottom: 5px;">Ask a question about startups</p>', unsafe_allow_html=True)
            user_input = st.text_input("", key="chat_input", placeholder="Type your question here...")
            
            # Add submit button at the bottom
            submit_button = st.form_submit_button("Send")
            
            if submit_button and user_input:
                # Get the user's query
                query = user_input
                
                # Add user message to chat history
                st.session_state.chat_history.append({"role": "user", "content": query})
                
                # Send query to backend
                with st.spinner('Searching database...'):
                    try:
                        response = requests.post(
                            f"{FAST_API_URL}/chat",
                            json={"query": query}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            ai_response = result.get("response", "Sorry, I couldn't find an answer to your question.")
                            
                            # Add assistant message to chat history
                            st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                        else:
                            error_msg = f"Error: {response.status_code} - {response.text}"
                            
                            # Add error message to chat history
                            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                            
                    except Exception as e:
                        error_msg = f"An error occurred: {str(e)}"
                        
                        # Add error message to chat history
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                
                # Force a rerun to update the chat history display
                st.rerun()
    
    # Button to clear chat
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown("© 2025 InvestorIntel - AI-Powered Pitch Deck Analysis")