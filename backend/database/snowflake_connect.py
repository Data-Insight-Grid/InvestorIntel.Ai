from dotenv import load_dotenv
import snowflake.connector
load_dotenv()
import os

# Global connection and cursor that will be reused
_connection = None
_cursor = None

# Function to get the existing connection or create a new one if needed
def get_connection():
    global _connection, _cursor
    
    # If we already have a connection, check if it's still valid
    if _connection:
        try:
            # Test if connection is still alive with a simple query
            _cursor.execute("SELECT 1")
            return _connection, _cursor
        except:
            # Connection is dead, close it and create a new one
            try:
                _cursor.close()
                _connection.close()
            except:
                pass
            _connection = None
            _cursor = None
    
    # Create a new connection
    SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
    SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
    SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
    SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
    
    # Connecting to Snowflake
    _connection = snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        role=SNOWFLAKE_ROLE
    )
    
    _cursor = _connection.cursor()
    
    # Set up the session
    _cursor.execute("USE WAREHOUSE INVESTOR_INTEL_WH;")
    _cursor.execute("USE DATABASE INVESTOR_INTEL_DB;")
    _connection.commit()
    
    return _connection, _cursor

# For backward compatibility with existing code
def account_login():
    return get_connection()