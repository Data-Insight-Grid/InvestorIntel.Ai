from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.client import Users
from diagrams.gcp.compute import Run
from diagrams.aws.compute import EC2
from diagrams.aws.storage import S3
from diagrams.custom import Custom
from diagrams.aws.database import RDS
from diagrams.onprem.database import Mysql

# Set diagram formatting
graph_attr = {
    "fontsize": "24",
    "bgcolor": "white",
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "margin": "0.5"
}

# Create the diagram
with Diagram("InvestorIntel Architecture", show=False, graph_attr=graph_attr, direction="TB"):
   
    # User/Client
    investor = Users("Investor")
    startup = Users("Startup Founder")
   
    # Frontend Cluster
    with Cluster("Frontend (User Interface)"):
        # Using built-in diagrams icons where possible
        streamlit = Custom("Streamlit UI", "architecture-diagram\input_icons\streamlit.png")
    
    # PDF Upload and Storage
    with Cluster("Pitch Deck Storage"):
        s3_storage = S3("S3 Bucket")
   
    # Cloud Infrastructure Cluster
    with Cluster("Google Cloud Platform"):
        # GCP Cloud Run hosting the FastAPI backend
        cloud_run = Run("Cloud Run")
        
        with Cluster("Backend API"):
            fastapi = Custom("FastAPI", "icons/fastapi.png")
    
    # AWS Infrastructure
    with Cluster("AWS Infrastructure"):
        ec2 = EC2("EC2 Instance")
    
    # Data Storage and Processing
    with Cluster("Data Storage & Analytics"):
        snowflake = Custom("Snowflake", "icons/snowflake.png")
        
        with Cluster("Vector Database"):
            pinecone = Custom("Pinecone", "icons/pinecone.png")
    
    # AI Components
    with Cluster("Multi-Agent System (LangGraph)"):
        with Cluster("AI Agents"):
            summary_agent = Custom("Summary Agent", "icons/agent.png")
            competitor_agent = Custom("Competitor Analysis", "icons/agent.png")
            industry_agent = Custom("Industry Analysis", "icons/agent.png")
            web_search_agent = Custom("Web Search Agent", "icons/agent.png")
            qa_agent = Custom("Q&A Agent", "icons/agent.png")
        
        with Cluster("LLM Integration"):
            llm = Custom("LLM Integration", "icons/brain.png")
            gemini = Custom("Gemini", "icons/gemini.png")
            mistral = Custom("Mistral", "icons/mistral.png")
    
    # Airflow as a standalone component with no connections
    # Create a separate cluster for it to set it visually apart
    with Cluster("External Scheduler"):
        airflow = Custom("Airflow", "icons/airflow.png")
    
    # Flow connections
    startup >> streamlit
    investor >> streamlit
    
    # Startup flow
    streamlit >> s3_storage
    
    # Backend connections
    streamlit >> cloud_run
    cloud_run >> fastapi
    
    # EC2 connection
    fastapi >> ec2
    
    # Data processing (bypassing Airflow in the main diagram)
    ec2 >> snowflake
    ec2 >> pinecone
    
    # AI agent flows
    s3_storage >> summary_agent
    snowflake >> competitor_agent
    snowflake >> industry_agent
    web_search_agent >> fastapi
    pinecone >> qa_agent
    
    # Connect agents to LLMs
    summary_agent >> llm
    competitor_agent >> llm
    industry_agent >> llm
    web_search_agent >> llm
    qa_agent >> llm
    
    llm >> [gemini, mistral]
    [gemini, mistral] >> llm
    
    # Results flow back to the user
    [summary_agent, competitor_agent, industry_agent, web_search_agent, qa_agent] >> fastapi
    fastapi >> cloud_run
    cloud_run >> streamlit
    streamlit >> investor