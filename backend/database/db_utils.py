from database.snowflake_connect import account_login
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
def get_investor_by_username(username):
    conn, cur = account_login()
    cur.execute("SELECT * FROM startup_information.investor WHERE username = %s", (username,))
    row = cur.fetchone()
    return dict(zip([desc[0] for desc in cur.description], row))

def get_startups_by_status(investor_id, status):
    conn, cur = account_login()
    query = """
        SELECT s.startup_id, s.startup_name
        FROM startup_information.startup_investor_map m
        JOIN startup_information.startup s ON m.startup_id = s.startup_id
        WHERE m.investor_id = %s AND m.status = %s
    """
    cur.execute(query, (investor_id, status))
    rows = cur.fetchall()
    return pd.DataFrame(rows, columns=["startup_id", "startup_name"])

def get_startup_info_by_id(startup_id):
    conn, cur = account_login()
    cur.execute("SELECT * FROM startup_information.startup WHERE startup_id = %s", (startup_id,))
    row = cur.fetchone()
    return dict(zip([desc[0] for desc in cur.description], row))

def get_startup_column_by_id(column_name: str, startup_id: int):
    conn, cur = account_login()
    # Build the query with the column name injected
    query = f"""
        SELECT s.{column_name}
        FROM startup_information.startup AS s
        WHERE s.startup_id = %s
    """
    print(query)

    # Execute with only the ID as a parameter
    try:
        cur.execute(query, (startup_id,))
        row = cur.fetchone()
        print("row", row)
    finally:
        cur.close()
        conn.close()

    # 4) Return the single value (or None if not found)
    return row[0] if row else None

def update_startup_status(investor_id, startup_id, status):
    """
    Update the status of a startup for a specific investor
    
    Args:
        investor_id (int): The ID of the investor
        startup_id (int): The ID of the startup
        status (str): The new status ('New', 'Reviewed', 'Funded', 'Rejected')
    
    Returns:
        bool: True if successful, False otherwise
    """
    conn, cur = account_login()
    try:
        query = """
        UPDATE startup_information.startup_investor_map
        SET status = %s
        WHERE investor_id = %s AND startup_id = %s
        """
        cur.execute(query, (status, investor_id, startup_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating startup status: {e}")
        return False
    finally:
        cur.close()
        conn.close()
