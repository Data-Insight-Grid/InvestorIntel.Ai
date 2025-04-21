from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os, json, sys

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'growjo_scripts'))
from growjo_scraper import get_recent_updates
from snowflake_helpers import account_login, company_exists, record_exists_in_staging, insert_record, update_record, insert_refined_data, create_combined_view

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'growjo_snowflake__update_pipeline',
    default_args=default_args,
    description='Modular Growjo ETL in Snowflake',
    schedule_interval='0 0 * * 2',
    catchup=False
)

def scrape_and_push(**context):
    data = get_recent_updates()
    context['ti'].xcom_push(key='growjo_data', value=data)
    print(f"✅ Scraped {len(data)} records")

def check_and_upsert(**context):
    data = context['ti'].xcom_pull(key='growjo_data', task_ids='scrape_growjo_data')
    conn, cur = account_login()
    try:
        for record in data:
            company = record['company']
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
        raise e
    finally:
        cur.close()
        conn.close()

def insert_refined(**context):
    conn, cur = account_login()
    try:
        insert_refined_data(conn, cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def refresh_view(**context):
    conn, cur = account_login()
    try:
        create_combined_view(cur)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

# Define Tasks
scrape_task = PythonOperator(
    task_id='scrape_growjo_data',
    python_callable=scrape_and_push,
    provide_context=True,
    dag=dag
)

upsert_task = PythonOperator(
    task_id='upsert_growjo_data',
    python_callable=check_and_upsert,
    provide_context=True,
    dag=dag
)

refine_task = PythonOperator(
    task_id='insert_refined_data',
    python_callable=insert_refined,
    provide_context=True,
    dag=dag
)

view_task = PythonOperator(
    task_id='refresh_final_view',
    python_callable=refresh_view,
    provide_context=True,
    dag=dag
)

# DAG Flow
scrape_task >> upsert_task >> refine_task >> view_task
