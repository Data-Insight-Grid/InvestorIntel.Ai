import os
from snowflake.connector import connect
from dotenv import load_dotenv

load_dotenv()

def get_snowflake_connection():
    """Create Snowflake connection using environment variables"""
    return connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        role=os.getenv('SNOWFLAKE_ROLE'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE')
    )

def initialize_snowflake_objects():
    """Initialize Snowflake database, schema, and table"""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    
    try:
        # Create database if not exists
        cur.execute(f"""
        CREATE DATABASE IF NOT EXISTS {os.getenv('SNOWFLAKE_DATABASE')}
        """)
        
        # Create schema if not exists
        cur.execute("""
        CREATE SCHEMA IF NOT EXISTS MARKET_RESEARCH
        """)
        
        # Create table if not exists
        cur.execute("""
        CREATE TABLE IF NOT EXISTS MARKET_RESEARCH.INDUSTRY_REPORTS (
            ID VARCHAR(255),
            INDUSTRY_NAME VARCHAR(255),
            REPORT_SUMMARY TEXT,
            CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            UPDATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """)
        
        print("Successfully initialized Snowflake objects")
    except Exception as e:
        print(f"Error initializing Snowflake objects: {e}")
    finally:
        cur.close()
        conn.close()

def store_report_summary(report_id: str, industry: str, summary: str):
    """Store report summary in Snowflake"""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        INSERT INTO MARKET_RESEARCH.INDUSTRY_REPORTS (ID, INDUSTRY_NAME, REPORT_SUMMARY)
        VALUES (%s, %s, %s)
        """, (report_id, industry, summary))
        
        conn.commit()
        print(f"Successfully stored summary for {industry} report")
    except Exception as e:
        print(f"Error storing report summary: {e}")
    finally:
        cur.close()
        conn.close() 