# InvestorIntel: Smart Investor Co-Pilot Platform

InvestorIntel is a smart investor co-pilot platform that helps venture capitalists and angel investors analyze, evaluate, and decide on early-stage startup investments. The platform uses a multi-agent AI system, real-time data pipelines, and integrated unstructured and structured data sources to automate due diligence, pitch deck summarization, market and trend analysis, and competitive benchmarking. It offers investors a rich dashboard with various AI-powered tabs to assess startups end-to-end using contextual insights from financial datasets, industry reports, web trends, and historical investments.

The InvestorIntel project is designed to enhance and streamline the startup evaluation process for venture capitalists and angel investors through AI-powered automation, structured summarization, and intelligent insights.

---

## **📌 Project Resources**
- **Streamlit:** [Application Link](http://34.85.173.233:8501/)
- **Airflow Dashboard:** [Airflow Link](http://34.44.200.7:8080/)
- **Backend:** [Backend Link](https://investorintel-backend-299824117494.us-east4.run.app/)
- **Demo Video:** [YouTube Demo](https://youtu.be/Fjgoe4PK9Uc)
- **Documentation:** [Codelab/Documentation Link](https://codelabs-preview.appspot.com/?file_id=1DAQgdaG6QE0N1GGwdIrf04m-IIFwZIo1U9bLJ6JgNRk#0)

---

## **📌 Technologies Used**
<p align="center">
  <img src="https://img.shields.io/badge/-Apache_Airflow-017CEE?style=for-the-badge&logo=apache-airflow&logoColor=white" alt="Apache Airflow">
  <img src="https://img.shields.io/badge/-Snowflake-007FFF?style=for-the-badge" alt="Snowflake">
  <img src="https://img.shields.io/badge/-Pinecone-734BD4?style=for-the-badge" alt="Pinecone">
  <img src="https://img.shields.io/badge/-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/-Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/-Web_Search-FFA500?style=for-the-badge" alt="Web Search API">
  <img src="https://img.shields.io/badge/-LangGraph-4B0082?style=for-the-badge" alt="LangGraph">
  <img src="https://img.shields.io/badge/-MCP-00B050?style=for-the-badge" alt="MCP">
  <img src="https://img.shields.io/badge/-Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white" alt="GCP">
</p>

---

## **📌 Architecture Diagram**
<p align="center">
  <img src="https://github.com/Damg7245-BigDataIntelligence/InvestorIntel.Ai/blob/main/architecture-diagram/investorintel_architecture.png" alt="Architecture Diagram" width="600">
</p>

---
## **📌 Installation & Setup Guide**

### **Step 1: Clone the Repository**
```bash
git clone https://github.com/Damg7245-BigDataIntelligence/InvestorIntel.Ai.git
cd InvestorIntel
```

### **Step 2: Set Up Environment Variables**
Create a `.env` file in the root directory with the following variables:
```
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your_snowflake_account
SNOWFLAKE_USER=your_snowflake_user
SNOWFLAKE_PASSWORD=your_snowflake_password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=INVESTOR_INTEL_DB

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=pitchdeckpdf

# API Keys
GEMINI_MODEL=gemini-2.0-flash
GEMINI_API_KEY=your_gemini_api_key
MISTRAL_API_KEY=your_mistral_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

### **Step 3: Set Up Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install -r requirements.txt
```

### **Step 4: Start Airflow**
```bash
cd airflow
docker-compose up -d
```
Access the Airflow dashboard at http://localhost:8080

### **Step 5: Start FastAPI Backend**
```bash
cd backend
uvicorn main:app --reload
```
The API will be available at http://localhost:8000

### **Step 6: Start Streamlit Frontend**
```bash
cd frontend
streamlit run main_app.py
```
The Streamlit application will be available at http://localhost:8501
----------------
## **📌 Project Flow**

InvestorIntel operates through a sophisticated multi-agent system that serves both startup founders and investors through different login interfaces:

### **Startup Founder Interface**
Startup founders can upload their pitch decks along with essential details including:
- Startup name
- Industry category
- LinkedIn URLs
- Website URL

Once uploaded, the pitch deck is securely stored in Amazon S3, triggering the InvestorIntel analysis pipeline.

### **Investor Interface**
When investors log in, the LangGraph-powered multi-agent system activates, providing comprehensive startup analysis through five specialized agents:

#### **1. Summary Agent**
- Extracts critical information from uploaded pitch decks
- Generates concise, structured summaries of the startup's value proposition
- Stores these summaries in Pinecone for rapid retrieval

#### **2. Competitor Analysis Agent**
- Provides visual graphs and detailed summaries of competitors in the same industry
- Sources competitor data from Growjo and Crunchbase
- Fetches structured competitive intelligence from Snowflake databases

#### **3. Industry Analysis Agent**
- Analyzes McKinsey Industry Reports (pre-loaded PDFs)
- Delivers industry-level insights and trend analysis
- Stores and indexes this data in both Snowflake and Pinecone for contextual retrieval

#### **4. Web Search Agent**
- Gathers live news and web trends via Tavily/SerpAPI/Google Trends
- Enhances trend insights and competitor monitoring
- Provides real-time market intelligence to supplement stored data

#### **5. Q&A Bot**
- Leverages Pinecone vector database for retrieving contextual information
- Allows investors to ask specific questions about the startup
- Implements a comprehensive RAG (Retrieval Augmented Generation) pipeline for accurate responses

This integrated workflow enables investors to perform thorough due diligence on startups with AI-powered intelligence, saving time and improving decision quality.

---

## **📌 Attestation**
**WE CERTIFY THAT WE HAVE NOT USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND COMPLY WITH THE POLICIES OUTLINED IN THE STUDENT HANDBOOK.**
