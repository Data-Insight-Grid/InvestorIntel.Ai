from backend.pipeline.snowflake_connect import account_login
from backend.pipeline.growjo_recent_updates import get_recent_updates
from datetime import datetime

def company_exists(cur, company_name):
    # First: check in COMPANY_MERGED_VIEW
    query1 = """
        SELECT * FROM INVESTOR_INTEL_DB.GROWJO_SCHEMA.COMPANY_MERGED_VIEW
        WHERE LOWER(COMPANY) = LOWER(%(company)s) AND COUNTRY = 'USA'
        LIMIT 1
    """
    cur.execute(query1, {"company": company_name})
    row = cur.fetchone()
    if row:
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))

    # Fallback: check in Crunchbase summary
    query2 = """
        SELECT * FROM CRUNCHBASE_BASIC_COMPANY_DATA.PUBLIC.ORGANIZATION_SUMMARY
        WHERE LOWER(NAME) = LOWER(%(company)s) AND COUNTRY_CODE = 'USA'
        LIMIT 1
    """
    cur.execute(query2, {"company": company_name})
    row = cur.fetchone()
    if row:
        columns = [desc[0] for desc in cur.description]
        return dict(zip(columns, row))

    return None


def record_exists_in_staging(cur, company_name):
    query = f"""
        SELECT 1 FROM INVESTOR_INTEL_DB.GROWJO_SCHEMA.STG_GROWJO_DATA
        WHERE LOWER(COMPANY) = LOWER(%(company)s)
        LIMIT 1
    """
    cur.execute(query, {"company": company_name})
    return cur.fetchone() is not None

def insert_record(cur, db_row, scraped_record):
    is_crunchbase = "NAME" in db_row
    query = f"""
        INSERT INTO INVESTOR_INTEL_DB.GROWJO_SCHEMA.STG_GROWJO_DATA 
        (COMPANY, CITY, COUNTRY, INDUSTRY, EMPLOYEES, REVENUE, EMP_GROWTH_PERCENT, FUNDING)
        VALUES (%(company)s, %(city)s, %(country)s, %(industry)s, %(employees)s, %(revenue)s, %(growth)s, %(funding)s)
    """
    cur.execute(query, {
        "company": db_row.get("COMPANY") or db_row.get("NAME"),
        "city": db_row.get("CITY"),
        "country": db_row.get("COUNTRY") or db_row.get("COUNTRY_CODE"),
        "industry": db_row.get("INDUSTRY") if not is_crunchbase else None,
        "employees": db_row.get("EMPLOYEES") if not is_crunchbase else None,
        "revenue": scraped_record.get("revenue"),
        "growth": scraped_record.get("growth"),
        "funding": scraped_record.get("funding")
    })

def update_record(cur, company_name, scraped_record):
    query = f"""
        UPDATE INVESTOR_INTEL_DB.GROWJO_SCHEMA.STG_GROWJO_DATA
        SET FUNDING = %(funding)s,
            REVENUE = %(revenue)s,
            EMP_GROWTH_PERCENT = %(growth)s
        WHERE LOWER(COMPANY) = LOWER(%(company)s)
    """
    cur.execute(query, {
        "funding": scraped_record.get("funding"),
        "revenue": scraped_record.get("revenue"),
        "growth": scraped_record.get("growth"),
        "company": company_name
    })

def insert_refined_data(conn, cur):
    cur.execute("""
        INSERT INTO INVESTOR_INTEL_DB.GROWJO_SCHEMA.REFINED_GROWJO_DATA
        SELECT * FROM (
            SELECT
                CASE 
                    WHEN TRIM(Rank) = 'N/A' THEN NULL 
                    ELSE TRY_TO_NUMBER(Rank) 
                END AS Rank,

                Company,
                City,
                Country,

                -- Funding to USD
                CASE
                    WHEN upper(Funding) ILIKE '$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'M', '')) * 1e6
                    WHEN upper(Funding) ILIKE '$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'K', '')) * 1e3
                    WHEN upper(Funding) ILIKE '$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '$', ''), 'B', '')) * 1e9
                    WHEN upper(Funding) LIKE '$%'     THEN TRY_TO_DOUBLE(REPLACE(Funding, '$', ''))

                    WHEN upper(Funding) ILIKE '€%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'M', '')) * 1e6 * 1.1
                    WHEN upper(Funding) ILIKE '€%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'K', '')) * 1e3 * 1.1
                    WHEN upper(Funding) ILIKE '€%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, '€', ''), 'B', '')) * 1e9 * 1.1
                    WHEN upper(Funding) LIKE '€%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, '€', '')) * 1.1

                    WHEN upper(Funding) ILIKE 'CA$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'M', '')) * 1e6 * 0.73
                    WHEN upper(Funding) ILIKE 'CA$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'K', '')) * 1e3 * 0.73
                    WHEN upper(Funding) ILIKE 'CA$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CA$', ''), 'B', '')) * 1e9 * 0.73
                    WHEN upper(Funding) LIKE 'CA$%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, 'CA$', '')) * 0.73

                    WHEN upper(Funding) ILIKE 'CN¥%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'M', '')) * 1e6 * 0.14
                    WHEN upper(Funding) ILIKE 'CN¥%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'K', '')) * 1e3 * 0.14
                    WHEN upper(Funding) ILIKE 'CN¥%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Funding, 'CN¥', ''), 'B', '')) * 1e9 * 0.14
                    WHEN upper(Funding) LIKE 'CN¥%'    THEN TRY_TO_DOUBLE(REPLACE(Funding, 'CN¥', '')) * 0.14

                    ELSE TRY_TO_DOUBLE(Funding)
                END AS Funding_USD,

                Industry,
                TRY_TO_NUMBER(NULLIF(Employees, '')) AS Employees,

                -- Revenue to USD
                CASE
                    WHEN upper(Revenue) ILIKE '$%M' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'M', '')) * 1e6
                    WHEN upper(Revenue) ILIKE '$%K' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'K', '')) * 1e3
                    WHEN upper(Revenue) ILIKE '$%B' THEN TRY_TO_DOUBLE(REPLACE(REPLACE(Revenue, '$', ''), 'B', '')) * 1e9
                    WHEN upper(Revenue) LIKE '$%'     THEN TRY_TO_DOUBLE(REPLACE(Revenue, '$', ''))
                    ELSE TRY_TO_DOUBLE(Revenue)
                END AS Revenue_USD,

                TRY_TO_DOUBLE(REPLACE(Emp_Growth_Percent, '%', '')) AS Emp_Growth_Percent

            FROM INVESTOR_INTEL_DB.GROWJO_SCHEMA.STG_GROWJO_DATA
        ) AS refined
        EXCEPT
        SELECT * FROM INVESTOR_INTEL_DB.GROWJO_SCHEMA.REFINED_GROWJO_DATA;
    """)
    print("✅ Inserted new data into REFINED_GROWJO_DATA")

def create_combined_view(cur):
    cur.execute("""
        CREATE OR REPLACE VIEW INVESTOR_INTEL_DB.GROWJO_SCHEMA.COMPANY_MERGED_VIEW AS
        SELECT 
            r.Company,
            o.short_description,
            r.Industry,
            r.Revenue,
            r.Employees,
            r.Emp_Growth_Percent,
            r.City,
            r.Country,
            o.homepage_url,
            o.linkedin_url,
            o.cb_url,
            o.updated_at
        FROM INVESTOR_INTEL_DB.GROWJO_SCHEMA.REFINED_GROWJO_DATA r
        JOIN CRUNCHBASE_BASIC_COMPANY_DATA.PUBLIC.ORGANIZATION_SUMMARY o
            ON LOWER(r.Company) = LOWER(o.name);
    """)
    print("✅ COMPANY_MERGED_VIEW refreshed")

def snowflake_growjo_update():
    conn, cur = account_login()
    try:
        data = get_recent_updates()
        print(f"Scraped {len(data)} entries:")
        print(data)
        companies = ["NOBO", "Dream Project", "MegaFood", "Soul AI", "Access Solutions"]
        ind = 0 
        for record in data:
            company = record['company']
            #company = companies[ind]
            ind += 1
            print(f"🔍 Processing: {company}")
            db_row = company_exists(cur, company)

            if db_row:
                if record_exists_in_staging(cur, company):
                    print(f"🔄 Updating: {company}")
                    update_record(cur, company, record)
                else:
                    print(f"➕ Inserting: {company}")
                    insert_record(cur, db_row, record)
            else:
                print(f"❌ Skipped (Not in view or not USA): {company}")

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to process data: {e}")

    try:
        insert_refined_data(conn, cur)
        create_combined_view(cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Error in finalizing refined data: {e}")

    finally:
        cur.close()
        conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    snowflake_growjo_update()
    print("Script executed successfully.")
