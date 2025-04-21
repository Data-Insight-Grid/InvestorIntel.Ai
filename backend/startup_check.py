from pydantic import BaseModel
import snowflake.connector
import os

# Snowflake connection parameters from environment variables
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")

class StartupCheckRequest(BaseModel):
    startup_name: str

def check_startup_exists(startup_name: str) -> bool:
    """
    Check if a startup with the given name already exists in Snowflake.
    Returns True if exists, False otherwise.
    """
    query = """
    SELECT startup_name
    FROM INVESTOR_INTEL_DB.STARTUP_INFORMATION.STARTUP
    WHERE LOWER(startup_name) = LOWER(%s)
    LIMIT 1
    """
    
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
        )
        cursor = conn.cursor()
        cursor.execute(query, (startup_name,))
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return len(result) > 0
    except Exception as e:
        print(f"Error checking startup existence: {str(e)}")
        return False

# Function to be used in the main.py API
def startup_exists_check(startup_name: str) -> dict:
    """
    API endpoint to check if a startup already exists
    """
    if not startup_name or startup_name.lower() == "unknown":
        return {
            "exists": False,
            "message": "Valid startup name not provided"
        }
    
    exists = check_startup_exists(startup_name)
    
    if exists:
        return {
            "exists": True,
            "message": f"Startup '{startup_name}' already exists in our database"
        }
    else:
        return {
            "exists": False,
            "message": f"Startup '{startup_name}' not found in our database"
        }