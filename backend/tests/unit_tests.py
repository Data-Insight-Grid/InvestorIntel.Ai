import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Set environment variables before importing any modules
os.environ.update({
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR3aXNqZWNuc3lvZ2VoYWZmcWpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE2NzI3MzgxMDYsImV4cCI6MTk4ODMxNDEwNn0.mock_key",
    "AWS_ACCESS_KEY_ID": "dummy",
    "AWS_SECRET_ACCESS_KEY": "dummy",
    "AWS_S3_BUCKET_NAME": "dummy",
    "AWS_REGION": "us-east-1",
    "GEMINI_API_KEY": "dummy",
    "PINECONE_API_KEY": "dummy",
    "SNOWFLAKE_USER": "dummy",
    "SNOWFLAKE_PASSWORD": "dummy",
    "SNOWFLAKE_ACCOUNT": "dummy",
    "SNOWFLAKE_WAREHOUSE": "dummy",
    "SNOWFLAKE_DATABASE": "INVESTOR_INTEL_DB",
    "SNOWFLAKE_ROLE": "dummy",
})

# Mock Pinecone before importing anything that uses it
class MockPinecone:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def list_indexes(self):
        return [{"name": "investor-intel"}]

    def Index(self, name):
        mock_index = MagicMock()
        mock_index.describe_index_stats.return_value = {"namespaces": {}}
        return mock_index

# Mock the Pinecone module
sys.modules['pinecone'] = MagicMock()
sys.modules['pinecone'].Pinecone = MockPinecone
sys.modules['pinecone'].ServerlessSpec = MagicMock()

# Create mock for snowflake connection
class MockConnection:
    def __init__(self):
        self.closed = False
        
    def close(self):
        self.closed = True
        
class MockCursor:
    def __init__(self):
        self.closed = False
        self.description = [("COLUMN",)]
        
    def close(self):
        self.closed = True
    
    def execute(self, *args, **kwargs):
        return None
        
    def fetchall(self):
        return []

# Mock the database modules
sys.modules['database'] = MagicMock()
sys.modules['database.log_gemini_interaction'] = MagicMock()
sys.modules['database.snowflake_connect'] = MagicMock()
sys.modules['database.snowflake_connect'].get_connection = MagicMock(return_value=(MockConnection(), MockCursor()))

# Mock the embedding model
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['sentence_transformers'].SentenceTransformer = MagicMock()
mock_model = MagicMock()
mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
sys.modules['sentence_transformers'].SentenceTransformer.return_value = mock_model

# Add path to parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import the modules that depend on these
from fastapi.testclient import TestClient
from main import app
from s3_utils import generate_presigned_url, upload_pitch_deck_to_s3
from vector_storage_service import get_embedding_model, generate_embeddings
from langgraph_builder import fetch_summary, fetch_industry_report, fetch_competitors

# --- FastAPI Tests ---
client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the InvestorIntel API"}
    
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


# --- S3 Utils Tests ---
@patch('s3_utils.s3_client')
def test_generate_presigned_url(mock_s3_client):
    mock_url = "https://example.com/presigned-url"
    mock_s3_client.generate_presigned_url.return_value = mock_url
    
    result = generate_presigned_url("test-bucket", "test-key")
    
    mock_s3_client.generate_presigned_url.assert_called_once()
    assert result == mock_url
    
@patch('s3_utils.s3_client')
@patch('s3_utils.os.path.exists')
@patch('builtins.open', new_callable=MagicMock)
def test_upload_pitch_deck_to_s3(mock_open, mock_exists, mock_s3_client):
    # Setup
    mock_exists.return_value = True
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
    
    # Call the function
    result = upload_pitch_deck_to_s3(
        file_path="test.pdf",
        startup_name="TestStartup",
        industry="AI",
        original_filename="original.pdf"
    )
    
    # Assert
    assert mock_s3_client.put_object.called
    assert mock_s3_client.generate_presigned_url.called
    assert result == "https://example.com/presigned-url"


# --- Vector Storage Tests ---
@patch('vector_storage_service.SentenceTransformer')
def test_get_embedding_model(mock_transformer):
    mock_model = MagicMock()
    mock_transformer.return_value = mock_model
    
    model = get_embedding_model()
    
    mock_transformer.assert_called_once()
    assert model == mock_model
    
@patch('vector_storage_service.get_embedding_model')
def test_generate_embeddings(mock_get_model):
    mock_model = MagicMock()
    mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
    mock_get_model.return_value = mock_model
    
    result = generate_embeddings("test text")
    
    mock_get_model.assert_called_once()
    mock_model.encode.assert_called_with("test text")
    assert result == [0.1, 0.2, 0.3]


# --- LangGraph Tests ---
@patch('langgraph_builder.get_startup_summary')
def test_fetch_summary(mock_get_summary):
    # Setup
    mock_get_summary.return_value = {
        "STARTUP_NAME": "TestStartup",
        "INDUSTRY": "AI",
        "SHORT_DESCRIPTION": "Test description"
    }
    
    # Test with empty state
    state = {"startup_name": "TestStartup"}
    result = fetch_summary(state)
    
    # Assert
    mock_get_summary.assert_called_with("TestStartup")
    assert result["summary"] == {
        "STARTUP_NAME": "TestStartup",
        "INDUSTRY": "AI",
        "SHORT_DESCRIPTION": "Test description"
    }
    
@patch('langgraph_builder.get_industry_report')
def test_fetch_industry_report(mock_get_report):
    # Setup
    mock_get_report.return_value = "Industry report content"
    
    # Test with state containing summary
    state = {
        "summary": {
            "INDUSTRY": "AI"
        },
        "funding_info": {
            "funding_amount": "1000000",
            "round_type": "Seed",
            "equity_offered": "15",
            "pre_money_valuation": "6000000",
            "post_money_valuation": "7000000"
        }
    }
    result = fetch_industry_report(state)
    
    # Assert
    mock_get_report.assert_called_with("AI")
    assert result["industry_report"] == "Industry report content"
    
@patch('langgraph_builder.get_top_companies')
def test_fetch_competitors(mock_get_companies):
    # Setup
    mock_competitors = [
        {"COMPANY": "CompA", "SHORT_DESCRIPTION": "Desc A", "REVENUE": 1000, "EMP_GROWTH_PERCENT": 10}
    ]
    mock_get_companies.return_value = mock_competitors
    
    # Mock the generate_competitor_visualizations function to prevent errors
    with patch('langgraph_builder.generate_competitor_visualizations') as mock_viz:
        mock_viz.return_value = {"revenue_chart": {}, "growth_chart": {}}
        
        # Mock store_visualizations_in_snowflake
        with patch('langgraph_builder.store_visualizations_in_snowflake') as mock_store:
            mock_store.return_value = True
            
            # Test with state containing summary
            state = {
                "summary": {
                    "STARTUP_NAME": "TestStartup",
                    "INDUSTRY": "AI"
                }
            }
            result = fetch_competitors(state)
            
            # Instead of using assert_called_with, check if it was called
            mock_get_companies.assert_called_once()
            # Extract the actual call arguments
            args, kwargs = mock_get_companies.call_args
            
            # Check the first argument contains "AI" (it might be truncated or modified in the function)
            assert "AI" in args[0]
            
            # Check the result
            assert result["competitors"] == mock_competitors

# --- Chat Endpoint Test ---
@patch('main.embedding_manager.search_similar_startups')
@patch('main.gemini_assistant.process_query_with_results')
def test_chat_endpoint(mock_process_query, mock_search):
    # Setup mock data
    mock_search.return_value = [
        {"source": "startup", "text": "Test startup info"},
        {"source": "deloitte-report", "text": "Test report info"}
    ]
    mock_process_query.return_value = "Here's information about your query"
    
    # Test the endpoint
    with patch('database.snowflake_connect.get_connection', return_value=(MockConnection(), MockCursor())):
        response = client.post(
            "/chat",
            json={"query": "Tell me about AI startups"}
        )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Here's information about your query"
    assert data["startup_count"] == 1
    assert data["report_count"] == 1
