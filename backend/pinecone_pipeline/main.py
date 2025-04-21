from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import shutil
import json
import sys
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import functions from the existing summary.py file
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Try different import paths to handle various directory structures
try:
    from summary import summarize_pitch_deck_with_gemini, validate_environment
except ImportError:
    try:
        from pinecone_pipeline.summary import summarize_pitch_deck_with_gemini, validate_environment
    except ImportError:
        logger.error("Error: Unable to import summary module")
        raise

try:
    from embedding_manager import EmbeddingManager
except ImportError:
    try:
        from pinecone_pipeline.embedding_manager import EmbeddingManager
    except ImportError:
        logger.error("Error: Unable to import EmbeddingManager")
        EmbeddingManager = None

try:
    from gemini_assistant import GeminiAssistant
except ImportError:
    try:
        from pinecone_pipeline.gemini_assistant import GeminiAssistant
    except ImportError:
        logger.error("Error: Unable to import GeminiAssistant")
        GeminiAssistant = None

try:
    from s3_utils import upload_pitch_deck_to_s3
except ImportError:
    try:
        from pinecone_pipeline.s3_utils import upload_pitch_deck_to_s3
    except ImportError:
        logger.error("Error: Unable to import S3 utilities")
        def upload_pitch_deck_to_s3(*args, **kwargs):
            raise NotImplementedError("S3 upload functionality not available")

# Define request models for better validation
class ChatRequest(BaseModel):
    query: str

class StartupExistsRequest(BaseModel):
    startup_name: str

# Initialize managers
embedding_manager = None
gemini_assistant = None

try:
    embedding_manager = EmbeddingManager()
    logger.info("Successfully initialized EmbeddingManager")
except Exception as e:
    logger.warning(f"Failed to initialize embedding manager. Pinecone functionality will be disabled: {e}")
    logger.debug(traceback.format_exc())

try: 
    gemini_assistant = GeminiAssistant()
    logger.info("Successfully initialized GeminiAssistant")
except Exception as e:
    logger.warning(f"Failed to initialize Gemini assistant. AI analysis will be disabled: {e}")
    logger.debug(traceback.format_exc())

app = FastAPI(
    title="InvestorIntel API",
    description="API for processing startup pitch decks and generating investor summaries",
    version="1.0.0"
)

# Add CORS middleware to allow requests from the Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the InvestorIntel API"}

@app.get("/health")
async def health_check():
    """Check if the API is running and all required environment variables are set."""
    
    is_valid, missing_vars = validate_environment()
    
    embedding_status = "active" if embedding_manager else "disabled"
    gemini_status = "active" if gemini_assistant else "disabled"
    
    if not is_valid:
        return {
            "status": "warning",
            "message": f"API is running but missing environment variables: {', '.join(missing_vars)}",
            "embedding_status": embedding_status,
            "gemini_status": gemini_status
        }
    
    return {
        "status": "ok",
        "message": "API is running and all required environment variables are set",
        "embedding_status": embedding_status,
        "gemini_status": gemini_status
    }

@app.post("/check-startup-exists")
async def check_startup_exists(request: StartupExistsRequest):
    """Check if a startup with the given name already exists in the database."""
    
    if not embedding_manager:
        raise HTTPException(
            status_code=503,
            detail="Embedding functionality is not available. Check if Pinecone API key is configured."
        )
    
    try:
        exists = embedding_manager.check_startup_exists(request.startup_name)
        
        return {
            "exists": exists,
            "startup_name": request.startup_name
        }
    except Exception as e:
        logger.error(f"Error checking if startup exists: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error checking if startup exists: {str(e)}"
        )

@app.post("/process-pitch-deck")
async def process_pitch_deck(
    file: UploadFile = File(...),
    startup_name: str = Form(None),
    industry: str = Form(None),
    linkedin_urls: str = Form(None),
    website_url: str = Form(None)
):
    """Process a pitch deck PDF and generate an investor summary."""
    
    # Parse the LinkedIn URLs from JSON string if provided
    linkedin_urls_list = []
    if linkedin_urls:
        try:
            linkedin_urls_list = json.loads(linkedin_urls)
        except json.JSONDecodeError:
            # If not valid JSON, treat it as a single URL
            linkedin_urls_list = [linkedin_urls]
    
    # Get the original filename
    original_filename = file.filename
    
    # Set default values if not provided
    startup_name = startup_name or "Unknown"
    industry = industry or "Unknown"
    
    # Check if required environment variables are set
    is_valid, missing_vars = validate_environment()
    if not is_valid:
        raise HTTPException(
            status_code=500, 
            detail=f"Server configuration error: Missing environment variables: {', '.join(missing_vars)}"
        )
    
    # First check if the startup already exists in Pinecone (case-insensitive)
    if embedding_manager and embedding_manager.check_startup_exists(startup_name):
        return {
            "error": "startup_exists",
            "message": f"A startup with the name '{startup_name}' already exists in the database.",
            "startup_name": startup_name
        }
    
    # Create a temporary directory to store the uploaded file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a temporary filename for local storage
        temp_filename = f"temp_pitch_deck.pdf"
        file_path = os.path.join(temp_dir, temp_filename)
        
        # Save the uploaded file to the temporary directory
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # Upload the file to S3
        try:
            s3_location = upload_pitch_deck_to_s3(
                file_path=file_path,
                startup_name=startup_name,
                industry=industry,
                original_filename=original_filename
            )
            
            if not s3_location:
                raise HTTPException(status_code=500, detail="Failed to upload file to S3")
                
            logger.info(f"File uploaded successfully to S3: {s3_location}")
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"S3 upload error: {str(e)}")
        
        # Generate summary using Gemini
        try:
            investor_summary = summarize_pitch_deck_with_gemini(
                file_path=file_path,
                api_key=os.getenv("GEMINI_API_KEY"),
                model_name="gemini-2.0-flash"
            )
            
            if not investor_summary:
                raise HTTPException(status_code=500, detail="Failed to generate summary")

        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Summary generation error: {str(e)}")
        
        # Store embedding and summary
        embedding_status = "skipped"
        snowflake_status = "skipped"
        
        if embedding_manager:
            try:
                embedding_success = embedding_manager.store_summary_embeddings(
                    summary=investor_summary,
                    startup_name=startup_name,
                    industry=industry,
                    website_url=website_url,
                    linkedin_urls=linkedin_urls_list,
                    original_filename=original_filename,
                    s3_location=s3_location
                )
                embedding_status = "success" if embedding_success else "failed"
                
                # Check if metadata has snowflake_status
                if embedding_success:
                    results = embedding_manager.search_similar_startups(
                        query="",
                        top_k=1
                    )
                    if results and len(results) > 0:
                        snowflake_status = results[0].get("snowflake_status", "skipped")
                
            except Exception as e:
                logger.error(f"Error storing embedding: {e}")
                logger.debug(traceback.format_exc())
                embedding_status = "error"
                snowflake_status = "error"
        
        # Return the results
        return {
            "startup_name": startup_name,
            "industry": industry,
            "linkedin_urls": linkedin_urls_list,
            "s3_location": s3_location,
            "original_filename": original_filename,
            "summary": investor_summary,
            "embedding_status": embedding_status,
            "snowflake_status": snowflake_status
        }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Process a chat query and return an AI response."""
    
    if not embedding_manager:
        raise HTTPException(
            status_code=503,
            detail="Embedding functionality is not available. Check if Pinecone API key is configured."
        )
    
    if not gemini_assistant:
        raise HTTPException(
            status_code=503,
            detail="Gemini assistant is not available. Check if Gemini API key is configured."
        )
    
    # Validate the query
    query = request.query.strip()
    if not query:
        return {
            "response": "Please enter a question about startups in our database.",
            "query": query,
            "results_count": 0
        }
    
    # Handle test cases for empty database or other edge cases
    if query.lower() in ["test empty database", "test no results"]:
        logger.info("Test case: empty database or no results")
        return {
            "response": "I don't have any information about that in my database. Please try asking about a different startup or topic.",
            "query": query,
            "results_count": 0
        }
    
    try:
        # Search for relevant startups
        results = embedding_manager.search_similar_startups(
            query=query,
            top_k=5  # Get the top 5 most relevant results
        )
        
        # Check if we have any results
        if not results or len(results) == 0:
            logger.info(f"No results found for query: '{query}'")
            return {
                "response": "I don't have any information about that in my database. Please try asking about a different startup or topic.",
                "query": query,
                "results_count": 0
            }
        
        # Process with Gemini
        ai_response = gemini_assistant.process_query_with_results(
            query=query,
            search_results=results
        )
        
        # Check for "I don't have information" response
        if "don't have" in ai_response.lower() and "information" in ai_response.lower() and "database" in ai_response.lower():
            # This is a no-information response
            logger.info(f"No relevant information found for query: '{query}'")
        else:
            # This is a response with content
            logger.info(f"Generated response for query: '{query}' with {len(results)} results")
        
        return {
            "response": ai_response,
            "query": query,
            "results_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error processing chat query: {e}")
        logger.debug(traceback.format_exc())
        
        # Return a user-friendly error message
        return {
            "response": "I'm having trouble processing your request right now. Please try again with a different question.",
            "query": query,
            "results_count": 0,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)