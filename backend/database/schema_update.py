from snowflake_connect import account_login

def update_startup_schema():
    """
    Updates the Snowflake startup table schema to add new funding-related columns,
    delete the old valuation_ask column, and delete existing data.
    
    This function should be run once when updating the schema.
    """
    conn, cur = account_login()
    
    try:
        # First, add the new columns to the table
        alter_statements = [
            "ALTER TABLE startup_information.startup ADD COLUMN IF NOT EXISTS funding_amount_requested FLOAT",
            "ALTER TABLE startup_information.startup ADD COLUMN IF NOT EXISTS round_type VARCHAR(50)",
            "ALTER TABLE startup_information.startup ADD COLUMN IF NOT EXISTS equity_offered FLOAT",
            "ALTER TABLE startup_information.startup ADD COLUMN IF NOT EXISTS pre_money_valuation FLOAT",
            "ALTER TABLE startup_information.startup ADD COLUMN IF NOT EXISTS post_money_valuation FLOAT"
        ]
        
        for statement in alter_statements:
            cur.execute(statement)
            print(f"Executed: {statement}")
        
        # Drop the old valuation_ask column
        try:
            cur.execute("ALTER TABLE startup_information.startup DROP COLUMN valuation_ask")
            print("Dropped column valuation_ask from startup table")
        except Exception as column_error:
            print(f"Error dropping valuation_ask column: {column_error}")
            print("Continuing with other schema changes...")
        
        # Delete all existing data
        cur.execute("DELETE FROM startup_information.startup")
        rows_deleted = cur.rowcount
        print(f"Deleted {rows_deleted} rows from startup table")
        
        # Also delete related mappings
        cur.execute("DELETE FROM startup_information.startup_investor_map")
        map_rows_deleted = cur.rowcount
        print(f"Deleted {map_rows_deleted} rows from startup_investor_map table")
        
        cur.execute("DELETE FROM startup_information.startup_founder_map")
        founder_rows_deleted = cur.rowcount
        print(f"Deleted {founder_rows_deleted} rows from startup_founder_map table")
        
        # Commit all changes
        conn.commit()
        
        return {
            "status": "success",
            "message": f"Schema updated and {rows_deleted} startup records deleted",
            "details": {
                "statements_executed": alter_statements,
                "old_columns_dropped": ["valuation_ask"],
                "startup_rows_deleted": rows_deleted,
                "investor_map_rows_deleted": map_rows_deleted,
                "founder_map_rows_deleted": founder_rows_deleted
            }
        }
        
    except Exception as e:
        conn.rollback()
        print(f"Error updating schema: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
        
    finally:
        cur.close()
        conn.close()
        
if __name__ == "__main__":
    print("Updating database schema...")
    result = update_startup_schema()
    print(f"Result: {result}")