from dotenv import load_dotenv
import snowflake.connector
load_dotenv()
import os


# Load environment variables and set up Snowflake connection
def account_login():
    # Snowflake connection details
    SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")  # e.g. 'vwcoqxf-qtb83828'
    SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")  # Your Snowflake username
    SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")  # Your Snowflake password
    SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")  # Your role, e.g., 'SYSADMIN'

    print(SNOWFLAKE_ROLE)

    # Connecting to Snowflake
    conn = snowflake.connector.connect(
        user=SNOWFLAKE_USER,        # This should be your username
        password=SNOWFLAKE_PASSWORD,       # This should be your password
        account=SNOWFLAKE_ACCOUNT,     # This should be your Snowflake account URL
        role=SNOWFLAKE_ROLE          # Optional, if you need to specify the role
    )

    cur = conn.cursor()
    print("Connected to Snowflake",cur)

    return conn, cur


# Create Snowflake entities (Warehouse, Database, Schema)
def entity_creation(conn, cur):
     # Create Warehouse (if it doesn't exist)
    def create_warehouse(cur):
        cur.execute("""
            CREATE WAREHOUSE IF NOT EXISTS INVESTOR_INTEL_WH
            WAREHOUSE_SIZE = 'SMALL'
            AUTO_SUSPEND = 60
            AUTO_RESUME = TRUE;
        """)
        cur.execute("USE WAREHOUSE INVESTOR_INTEL_WH;")  # Specify the warehouse

    print("Created Warehouse- INVESTOR_INTEL_WH")

    # Create Database (if it doesn't exist)
    def create_database(cur):
        cur.execute("""
            CREATE DATABASE IF NOT EXISTS INVESTOR_INTEL_DB;
        """)
        cur.execute("USE DATABASE INVESTOR_INTEL_DB;")  # Specify the database
        print("Created Database INVESTOR_INTEL_DB")

    # Create Schema (if it doesn't exist)
    def create_schema(cur):
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS GROWJO_SCHEMA;
        """)
        cur.execute("USE SCHEMA GROWJO_SCHEMA;")  # Specify the schema

        print("Created Schema INVESTOR_INTEL_DB.GROWJO_SCHEMA")

    create_warehouse(cur)
    create_database(cur)
    create_schema(cur)

    conn.commit()


# Create Snowflake Stage and Storage Integration
def stage_data(conn, cur):

    # Create Storage Integration
    def create_storage_integration(cur):
        cur.execute("""
            CREATE STORAGE INTEGRATION IF NOT EXISTS growjo_integration
                TYPE = 'EXTERNAL_STAGE'
                STORAGE_PROVIDER = 'S3'
                ENABLED = TRUE
                STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::699475925561:role/investor-intel-snowflake-role'
                STORAGE_ALLOWED_LOCATIONS = ('s3://investor-intel-ai/');
        """)
        print("Created Storage Integration growjo_integration")

    # Create CSV Format
    def create_csv_format(cur):
        cur.execute("""
            CREATE FILE FORMAT IF NOT EXISTS GROWJO_CSV_FORMAT
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER = 1; -- Ensures the first row is treated as column headers

        """)

    # Create Stage
    def create_stage(cur):
        cur.execute("""
            CREATE STAGE IF NOT EXISTS GROWJO_STAGE
            URL = 's3://investor-intel-ai/growjo-data/Initial_Data_Load/'
            STORAGE_INTEGRATION = growjo_integration
            FILE_FORMAT = (FORMAT_NAME = 'GROWJO_CSV_FORMAT');
        """)
        print("Created Stage GROWJO_STAGE")

    # Create Table by Inferring Schema
    def create_table(cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS STG_GROWJO_DATA (
                Rank STRING,
                Company STRING,
                City STRING,
                Country STRING,
                Funding STRING,
                Industry STRING,
                Employees STRING,
                Revenue STRING,
                Emp_Growth_Percent STRING
            );
        """)
        print("Created Table STG_GROWJO_DATA")

    # Load Data into Snowflake Table from Stage
    def load_data_into_snowflake(cur):
        cur.execute("""
            COPY INTO STG_GROWJO_DATA
            FROM @GROWJO_STAGE
            FILES = ('Initial_growjo_data.csv')
            FILE_FORMAT = (FORMAT_NAME = 'GROWJO_CSV_FORMAT')
        """)
        print("Loaded data into STG_GROWJO_DATA table")

    # Execute the functions
    create_storage_integration(cur)
    create_csv_format(cur)
    create_stage(cur)
    create_table(cur)
    load_data_into_snowflake(cur)

    conn.commit()

def refine_data(conn, cur):
    # This function will be used to refine the data in Snowflake
    
    # Create a refined table with the desired schema
    def create_refined_table(cur):
        cur.execute("""
            CREATE OR REPLACE TABLE REFINED_GROWJO_DATA (
                Rank NUMBER,
                Company STRING,
                City STRING,
                Country STRING,
                Funding FLOAT,
                Industry STRING,
                Employees INT,
                Revenue STRING,  -- You can change this later to float if needed
                Emp_Growth_Percent FLOAT
            );
        """)
        print("Created Table REFINED_GROWJO_DATA")
    
    # Insert data into the refined table with transformations
    def insert_refined_data(conn, cur):
        cur.execute("""
            INSERT INTO REFINED_GROWJO_DATA
            SELECT * FROM (
                SELECT
                    CASE 
                        WHEN TRIM(Rank) = 'N/A' THEN NULL 
                        ELSE TRY_TO_NUMBER(Rank) 
                    END AS Rank,

                    Company,
                    City,
                    Country,

                    -- Funding USD Conversion
                    CASE
                        WHEN upper(Funding) ILIKE '$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'M', '')) * 1000000
                        WHEN upper(Funding) ILIKE '$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'K', '')) * 1000
                        WHEN upper(Funding) ILIKE '$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'B', '')) * 1000000000
                        WHEN upper(Funding) LIKE '$%'     THEN TRY_TO_DOUBLE(REPLACE(Funding, '$', ''))

                        WHEN upper(Funding) ILIKE '€%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'M', '')) * 1000000 * 1.1
                        WHEN upper(Funding) ILIKE '€%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'K', '')) * 1000 * 1.1
                        WHEN upper(Funding) ILIKE '€%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'B', '')) * 1000000000 * 1.1
                        WHEN upper(Funding) LIKE '€%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, '€', '')) * 1.1

                        WHEN upper(Funding) ILIKE 'CA$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'M', '')) * 1000000 * 0.73
                        WHEN upper(Funding) ILIKE 'CA$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'K', '')) * 1000 * 0.73
                        WHEN upper(Funding) ILIKE 'CA$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'B', '')) * 1000000000 * 0.73
                        WHEN upper(Funding) LIKE 'CA$%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, 'CA$', '')) * 0.73

                        WHEN upper(Funding) ILIKE 'CN¥%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'M', '')) * 1000000 * 0.14
                        WHEN upper(Funding) ILIKE 'CN¥%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'K', '')) * 1000 * 0.14
                        WHEN upper(Funding) ILIKE 'CN¥%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'B', '')) * 1000000000 * 0.14
                        WHEN upper(Funding) LIKE 'CN¥%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, 'CN¥', '')) * 0.14

                        ELSE TRY_TO_DOUBLE(Funding)
                    END AS Funding_USD,

                    Industry,

                    TRY_TO_NUMBER(NULLIF(Employees, '')) AS Employees,

                    -- Revenue USD Conversion
                    CASE
                        WHEN upper(Revenue) ILIKE '$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'M', '')) * 1000000
                        WHEN upper(Revenue) ILIKE '$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'K', '')) * 1000
                        WHEN upper(Revenue) ILIKE '$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'B', '')) * 1000000000
                        WHEN upper(Revenue) LIKE '$%'     THEN TRY_TO_DOUBLE(REPLACE(Revenue, '$', ''))
                        ELSE TRY_TO_DOUBLE(Revenue)
                    END AS Revenue,

                    TRY_TO_DOUBLE(REPLACE(Emp_Growth_Percent, '%', '')) AS Emp_Growth_Percent

                FROM STG_GROWJO_DATA
            ) AS refined
            EXCEPT
            SELECT * FROM REFINED_GROWJO_DATA;


        """)
        print("Inserted data into REFINED_GROWJO_DATA table")

    create_refined_table(cur)
    insert_refined_data(conn, cur)
    conn.commit()

def create_combined_view(conn, cur):
    # Create a view to select the top 10 companies by funding
    cur.execute("""
        CREATE OR REPLACE VIEW investor_intel_db.growjo_schema.COMPANY_MERGED_VIEW AS
            SELECT 
                r.Company,
                o.short_description,
                r.Industry,
                r.Revenue AS Revenue,
                r.Employees,
                r.Emp_Growth_Percent,
                r.City,
                r.Country,
                o.homepage_url,
                o.linkedin_url,
                o.cb_url,
                o.updated_at
            FROM investor_intel_db.growjo_schema.REFINED_GROWJO_DATA r
            JOIN crunchbase_basic_company_data.public.organization_summary o
                ON LOWER(r.Company) = LOWER(o.name);
    """)
    print("Created view TOP_10_COMPANIES_BY_FUNDING")
    conn.commit()
    cur.close()
    conn.close()

# Example usage
if __name__ == "__main__":
    conn, cur = account_login()
    entity_creation(conn, cur)
    stage_data(conn, cur)
    refine_data(conn, cur)
    create_combined_view(conn, cur)