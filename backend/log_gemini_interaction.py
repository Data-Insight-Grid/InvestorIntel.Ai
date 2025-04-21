import os
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load env vars
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def log_gemini_interaction(
    startup_name: str, 
    industry: str, 
    model: str, 
    prompt: str, 
    response: str, 
    response_time_ms: int = None,
    tokens_used: int = None,
    session_id: str = None
):
    """
    Log a Gemini model interaction to the Supabase GeminiLogs table.
    
    Args:
        startup_name: Name of the startup being analyzed
        industry: Industry of the startup
        model: Gemini model version used
        prompt: Full text of the prompt sent to Gemini
        response: Full text of the response from Gemini
        response_time_ms: Response time in milliseconds (optional)
        tokens_used: Number of tokens used (optional)
        session_id: Session ID to group related calls (optional)
    
    Returns:
        Dictionary with status of the operation
    """
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "startup_name": startup_name,
        "industry": industry,
        "model": model,
        "prompt": prompt,
        "response": response,
        "response_time_ms": response_time_ms,
        "tokens_used": tokens_used,
        "session_id": session_id
    }
    try:
        supabase.table("GeminiLogs").insert(log_entry).execute()
        return {"status": "success", "message": "Log entry created"}
    except Exception as e:
        print(f"Error logging Gemini interaction: {str(e)}")
        return {"status": "error", "message": str(e)}
