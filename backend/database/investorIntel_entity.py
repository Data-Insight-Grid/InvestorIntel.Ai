from .snowflake_connect import account_login
from dotenv import load_dotenv

load_dotenv()

# Function to create the InvestorIntel schema and tables
def create_InvestorIntel_entities(conn, cur):

    # Step 0: Set the context
    print("Context set to Investor Intel database and warehouse.")

    # Step 1: Create Schema
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS startup_information;
    """)
    print("Schema - startup_information: created successfully.")

    # Step 2: Create Investor Table
    cur.execute("""
        CREATE OR REPLACE TABLE startup_information.investor (
            investor_id         NUMBER AUTOINCREMENT PRIMARY KEY,
            first_name          STRING,
            last_name           STRING,
            email_address       STRING UNIQUE,
            username            STRING UNIQUE,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("Investor table created successfully.")

    # Step 3: Create Startup Table
    cur.execute("""
        CREATE OR REPLACE TABLE startup_information.startup (
            startup_id          NUMBER AUTOINCREMENT PRIMARY KEY,
            startup_name        STRING UNIQUE,
            industry            STRING,
            email_address       STRING,
            website_url         STRING,
            valuation_ask       NUMBER(18, 2),
            summary_report      STRING,
            analytics_report    STRING,
            news_report         STRING,
            pitch_deck_link     STRING,
            pitch_deck_filename STRING,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("Startup table created successfully.")

    # Step 4: Create Bridge Table to map Investors to Startups
    cur.execute("""
        CREATE OR REPLACE TABLE startup_information.startup_investor_map (
            map_id              NUMBER AUTOINCREMENT PRIMARY KEY,
            startup_id          NUMBER,
            investor_id         NUMBER,
            status              STRING DEFAULT 'Not Viewed',  -- Other values: Viewed, Decision Pending, Rejected, Funded
            invested_amount     NUMBER(18, 2),                -- NULL if not funded
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_startup FOREIGN KEY (startup_id)
                REFERENCES startup_information.startup(startup_id),

            CONSTRAINT fk_investor FOREIGN KEY (investor_id)
                REFERENCES startup_information.investor(investor_id)
        );
    """)
    print("Bridge table startup_investor_map created successfully.")

    # Step 5: Create Startup Bridge table to map Startups to Founders
    cur.execute("""
        CREATE OR REPLACE TABLE startup_information.startup_founder_map (
            map_id              NUMBER AUTOINCREMENT PRIMARY KEY,
            startup_name        STRING,
            founder_name        STRING,
            founder_linkedin    STRING,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_startup FOREIGN KEY (startup_name)
                REFERENCES startup_information.startup(startup_name)
        );
    """)
    print("Bridge table startup_founder_map created successfully.")
    
    conn.commit()  # Commit the changes
    print("InvestorIntel schema and tables created successfully.")

def insert_investor(first_name, last_name, email_address, username):
    conn, cur = account_login()
    try:
        insert_query = """
            INSERT INTO startup_information.investor (
                first_name,
                last_name,
                email_address,
                username
            )
            VALUES (%s, %s, %s, %s);
        """
        cur.execute(insert_query, (first_name, last_name, email_address, username))
        conn.commit()
        print("✅ Investor inserted successfully.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to insert investor: {e}")

def insert_startup(
    startup_name,
    email_address,
    website_url,
    industry,
    funding_amount_requested,
    round_type,
    equity_offered,
    pre_money_valuation,
    post_money_valuation
):
    """Insert a new startup into the database with the expanded funding details."""
    conn, cur = account_login()
    
    try:
        # Check if startup exists
        cur.execute(
            "SELECT startup_id FROM startup_information.startup WHERE startup_name = %s",
            (startup_name,)
        )
        existing = cur.fetchone()
        
        if existing:
            # Update existing startup
            cur.execute("""
                UPDATE startup_information.startup
                SET email_address = %s,
                    website_url = %s,
                    industry = %s,
                    funding_amount_requested = %s,
                    round_type = %s,
                    equity_offered = %s,
                    pre_money_valuation = %s,
                    post_money_valuation = %s
                WHERE startup_name = %s
                """,
                (
                    email_address,
                    website_url,
                    industry,
                    funding_amount_requested,
                    round_type,
                    equity_offered,
                    pre_money_valuation,
                    post_money_valuation,
                    startup_name
                )
            )
        else:
            # Insert new startup
            cur.execute("""
                INSERT INTO startup_information.startup (
                    startup_name,
                    email_address,
                    website_url,
                    industry,
                    funding_amount_requested,
                    round_type,
                    equity_offered,
                    pre_money_valuation,
                    post_money_valuation
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    startup_name,
                    email_address,
                    website_url,
                    industry,
                    funding_amount_requested,
                    round_type,
                    equity_offered,
                    pre_money_valuation,
                    post_money_valuation
                )
            )
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        print(f"Error inserting startup: {e}")
        raise
    
    finally:
        cur.close()
        conn.close()
    
def insert_startup_founder_map(founders_list):
    conn, cur = account_login()
    """
    founders_list should be a list of dicts like:
      {"startup_name": "...",
       "founder_name": "...",
       "linkedin_url": "..."}
    """
    cur = conn.cursor()
    
    try:
        for founder in founders_list:
            startup_name   = founder.get("startup_name")
            founder_name   = founder.get("founder_name")
            linkedin_url   = founder.get("linkedin_url")

            if not (startup_name and founder_name and linkedin_url):
                print(f"⚠️ Missing data for founder entry {founder!r}, skipping.")
                continue

            cur.execute(
                """
                INSERT INTO startup_information.startup_founder_map
                  (startup_name, founder_name, founder_linkedin)
                VALUES (%s, %s, %s);
                """,
                (startup_name, founder_name, linkedin_url)
            )

        conn.commit()
        print("✅ Mapping complete.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to map startup to founders: {e}")
        # re‑raise if you want upstream code to also see the failure
        raise


def map_startup_to_investors(startup_name, investor_usernames):
    conn, cur = account_login()
    try:
        # Step 1: Get startup_id
        cur.execute("""
            SELECT startup_id FROM startup_information.startup
            WHERE LOWER(startup_name) = LOWER(%s);
        """, (startup_name,))
        result = cur.fetchone()
        
        if not result:
            raise ValueError(f"❌ Startup '{startup_name}' not found.")

        startup_id = result[0]

        # Step 2: Get investor_ids for each username
        for username in investor_usernames:
            cur.execute("""
                SELECT investor_id FROM startup_information.investor
                WHERE LOWER(username) = LOWER(%s);
            """, (username,))
            investor_result = cur.fetchone()

            if not investor_result:
                print(f"⚠️ Investor with username '{username}' not found. Skipping.")
                continue

            investor_id = investor_result[0]

            # Step 3: Insert into mapping table
            cur.execute("""
                INSERT INTO startup_information.startup_investor_map (
                    startup_id, investor_id, status, invested_amount
                ) VALUES (%s, %s, 'Not Viewed', NULL);
            """, (startup_id, investor_id))

        conn.commit()
        print("✅ Mapping complete.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to map startup to investors: {e}")

def get_all_investor_usernames():
    conn, cur = account_login()
    try:
        cur.execute("""
            SELECT username, first_name, last_name FROM startup_information.investor;
        """)
        results = cur.fetchall()

        # Format: "username (First Last)"
        formatted_options = [f"{row[0]} ({row[1]} {row[2]})" for row in results]

        print("✅ Investor usernames fetched successfully.")
        return formatted_options
    except Exception as e:
        print(f"❌ Failed to fetch investor usernames: {e}")
        return []


if __name__ == "__main__":
    conn, cur = account_login()
    create_InvestorIntel_entities(conn, cur)
    print("InvestorIntel schema and tables created successfully.")

    # Close the cursor and connection   
    cur.close()
    conn.close()
    print("Snowflake connection closed.")
    # Close the connection  
    
