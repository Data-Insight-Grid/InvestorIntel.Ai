import os
import uuid
from snowflake.connector import connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SnowflakeManager:
    """Class to manage Snowflake operations for startup summaries"""
    
    def __init__(self):        
        # Get Snowflake credentials from environment
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = os.getenv('SNOWFLAKE_USER')
        self.password = os.getenv('SNOWFLAKE_PASSWORD')
        self.role = os.getenv('SNOWFLAKE_ROLE')
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
        self.database = os.getenv('SNOWFLAKE_DATABASE')
        
        # Validate credentials
        if not all([self.account, self.user, self.password, self.warehouse, self.database]):
            raise ValueError("Missing required Snowflake credentials")
            
        # Initialize Snowflake objects
        # self.initialize_snowflake_objects()
        
    def get_connection(self):
        """Create and return a Snowflake connection"""
        return connect(
            account=self.account,
            user=self.user,
            password=self.password,
            role=self.role,
            warehouse=self.warehouse,
            database=self.database
        )
        
    # def initialize_snowflake_objects(self):
    #     """Initialize Snowflake database, schema, and table"""
    #     conn = self.get_connection()
    #     cur = conn.cursor()
        
    #     try:
    #         cur.execute("USE DATABASE INVESTOR_INTEL_DB")
    #         # Create schema if not exists
    #         cur.execute("""
    #         CREATE SCHEMA IF NOT EXISTS STARTUP_INFORMATION
    #         """)
            
    #         # Create table if not exists
    #         cur.execute("""
    #         CREATE TABLE IF NOT EXISTS STARTUP_INFORMATION.STARTUP (
    #             STARTUP_ID VARCHAR(36) PRIMARY KEY,
    #             STARTUP_NAME VARCHAR(255) NOT NULL UNIQUE,
    #             INDUSTRY VARCHAR(255),
    #             SHORT_DESCRIPTION TEXT,
    #             ANALYSIS_REPORT TEXT,
    #             NEWS TEXT,
    #             WEBSITE_URL VARCHAR(1000),
    #             S3_LOCATION VARCHAR(1000),
    #             ORIGINAL_FILENAME VARCHAR(255),
    #             CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    #             UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    #         )
    #         """)
                        
    #     except Exception as e:
    #         raise
    #     finally:
    #         cur.close()
    #         conn.close()
            
            
    def store_startup_summary(self, 
                            startup_name: str,
                            summary: str,
                            industry: str = None,
                            website_url: str = None,
                            s3_location: str = None,
                            original_filename: str = None) -> str:
        """
        Store startup summary in Snowflake
        
        Args:
            startup_name: Name of the startup
            summary: Generated summary from Gemini
            industry: Industry category
            s3_location: S3 URI of the stored PDF
            original_filename: Original filename of the PDF
            
        Returns:
            startup_id: Generated UUID for the startup
        """
        conn = self.get_connection()
        cur = conn.cursor()
        
        try:
            # Generate a unique ID for the startup
            # Insert the summary into Snowflake
            cur.execute("""
            UPDATE INVESTOR_INTEL_DB.STARTUP_INFORMATION.STARTUP
    SET 
        SUMMARY_REPORT = %s,
        PITCH_DECK_LINK = %s,
        PITCH_DECK_FILENAME = %s
        WHERE 
            STARTUP_NAME = %s
    """, (
                summary,
                s3_location,
                original_filename,
                startup_name
        ))
            
            conn.commit()
            return startup_name
            
        except Exception as e:
            raise e
        finally:
            cur.close()
            conn.close() 