"""
Industry Reports Data Pipeline DAG

This DAG automates the end-to-end ingestion and processing of industry reports in sequence:
1. Scrapes reports from websites or directly downloads PDFs
2. Summarizes reports using Google Gemini
3. Stores PDFs in S3
4. Stores summaries in Snowflake
5. Stores embeddings in Pinecone
"""

from datetime import datetime, timedelta
import tempfile
import os
import base64
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowSkipException
from airflow.models import Variable

# Define the direct PDF URLs and print URLs at the top level
# We're keeping these here to avoid import errors with reports_scrape.py
DIRECT_PDFS = {
    "AI_2024_Report_Deloitte": "https://www2.deloitte.com/content/dam/Deloitte/us/Documents/consulting/us-state-of-gen-ai-q4.pdf",
    "Automotive_2024_Report_Deloitte": "https://www2.deloitte.com/content/dam/Deloitte/us/Documents/consumer-business/deloitte-2025-global-automotive-consumer-study-january-2025.pdf",
    "Defense_2024_Report_PwC": "https://www.pwc.com/us/en/industries/industrial-products/library/assets/pwc-aerospace-defense-annual-industry-performance-outlook-2024.pdf",
}

PRINT_URLS = {
    "Tech_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/technology/technology-media-telecom-outlooks/technology-industry-outlook.html",
    ],
    "Banking_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/financial-services/financial-services-industry-outlooks/banking-industry-outlook.html",
    ],
    "Healthcare_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/health-care/future-of-medtech-digital-business-models.html",
    ],
}

# Define a temp directory for storing PDFs between tasks
TEMP_DIR = "/tmp/industry_reports"
os.makedirs(TEMP_DIR, exist_ok=True)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=3),
}

# Create the DAG
dag = DAG(
    'industry_reports_pipeline',
    default_args=default_args,
    description='Pipeline to scrape, summarize, and store industry reports',
    schedule_interval='0 0 * * 1',  # Run weekly on Mondays at midnight
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['reports', 'market_research'],
    max_active_runs=1,
)

def process_direct_pdfs():
    """Download PDFs directly from URLs and save to temp files"""
    # Import inside the function to avoid loading at DAG parse time
    import requests
    import os
    
    pdf_info = []
    
    for name, url in DIRECT_PDFS.items():
        try:
            industry = name.split('_')[0]
            print(f"Downloading direct PDF: {name} from {url}")
            
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
            if response.status_code == 200:
                # Create a unique filename
                file_path = os.path.join(TEMP_DIR, f"{name}.pdf")
                
                # Save PDF to temp file
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # Store PDF info to be processed later
                pdf_info.append({
                    'name': name,
                    'industry': industry,
                    'file_path': file_path
                })
                print(f"Successfully downloaded {name}")
            else:
                print(f"Failed to download {name}, status code: {response.status_code}")
        
        except Exception as e:
            print(f"Error downloading {name}: {e}")
    
    if not pdf_info:
        raise AirflowSkipException("No direct PDFs were successfully downloaded")
    
    # Return results for the next task
    return pdf_info

def process_html_reports(**context):
    """Scrape reports from HTML pages using Playwright"""
    try:
        # Import inside the function to avoid loading at DAG parse time
        from playwright.sync_api import sync_playwright
        import os
        
        # Get results from previous tasks
        ti = context['ti']
        pdf_info = ti.xcom_pull(task_ids='process_direct_pdfs')
        
        if not pdf_info:
            pdf_info = []
            
        html_info = []
        
        for filename, urls in PRINT_URLS.items():
            industry = filename.split('_')[0]
            
            for i, url in enumerate(urls):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
                        )
                        
                        print(f"Visiting: {url}")
                        page.goto(url, timeout=120000, wait_until="networkidle")
                        page.wait_for_timeout(5000)
                        
                        # Create a unique filename
                        pdf_name = f"{filename}_{i+1}"
                        file_path = os.path.join(TEMP_DIR, f"{pdf_name}.pdf")
                        
                        # Generate PDF content and save directly to file
                        page.pdf({
                            "format": "A4",
                            "printBackground": True,
                            "margin": {"top": "0.4in", "right": "0.4in", "bottom": "0.4in", "left": "0.4in"},
                            "path": file_path
                        })
                        browser.close()
                        
                        # Store PDF info to be processed later
                        html_info.append({
                            'name': pdf_name,
                            'industry': industry,
                            'file_path': file_path
                        })
                        print(f"Successfully scraped {pdf_name}")
                
                except Exception as e:
                    print(f"Error scraping {url}: {str(e)}")
        
        # Combine results from direct PDFs and HTML scraping
        all_info = pdf_info + html_info
        
        if not all_info:
            raise AirflowSkipException("No PDFs or HTML reports were successfully collected")
        
        # Return all results for the next task
        return all_info
    except ImportError as e:
        print(f"Import error: {e}")
        raise AirflowSkipException("Playwright not available")

def init_snowflake():
    """Initialize Snowflake database, schema, and tables"""
    # Import inside the function to avoid loading at DAG parse time
    from industry_research.snowflake_utils import initialize_snowflake_objects
    
    try:
        initialize_snowflake_objects()
        return "Snowflake initialization successful"
    except Exception as e:
        raise Exception(f"Snowflake initialization failed: {str(e)}")

def generate_summaries(**context):
    """Generate summaries for all collected reports using Gemini"""
    # Import inside the function to avoid loading at DAG parse time
    from industry_research.reports_scrape import get_report_summary_with_gemini
    
    # Get results from previous tasks
    ti = context['ti']
    all_info = ti.xcom_pull(task_ids='process_html_reports')
    
    if not all_info:
        raise AirflowSkipException("No reports available to summarize")
    
    # Process each report
    processed_reports = []
    for report in all_info:
        try:
            name = report['name']
            industry = report['industry']
            file_path = report['file_path']
            
            # Read PDF content from file
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
            
            # Generate summary using Gemini
            print(f"Generating summary for {name}")
            summary = get_report_summary_with_gemini(pdf_content, name)
            
            if summary:
                processed_reports.append({
                    'name': name,
                    'industry': industry,
                    'file_path': file_path,
                    'summary': summary
                })
                print(f"Successfully generated summary for {name}")
            else:
                print(f"Failed to generate summary for {name}")
        
        except Exception as e:
            print(f"Error generating summary for {report['name']}: {e}")
    
    if not processed_reports:
        raise AirflowSkipException("No summaries were successfully generated")
    
    return processed_reports

def store_in_s3(**context):
    """Upload PDFs to S3"""
    # Import inside the function to avoid loading at DAG parse time
    from industry_research.s3_utils import upload_pdf_to_s3
    
    ti = context['ti']
    processed_reports = ti.xcom_pull(task_ids='generate_summaries')
    
    if not processed_reports:
        raise AirflowSkipException("No processed reports to store in S3")
    
    s3_results = []
    for report in processed_reports:
        try:
            name = report['name']
            industry = report['industry']
            file_path = report['file_path']
            
            # Read PDF content from file
            with open(file_path, 'rb') as f:
                pdf_content = f.read()
            
            # Upload PDF to S3
            presigned_url = upload_pdf_to_s3(
                file_content=pdf_content,
                filename=f"{name}.pdf",
                industry=industry
            )
            
            if presigned_url:
                s3_results.append({
                    'name': name,
                    'industry': industry,
                    'summary': report['summary'],
                    's3_url': presigned_url
                })
                print(f"Successfully uploaded {name} to S3")
            else:
                print(f"Failed to upload {name} to S3")
        
        except Exception as e:
            print(f"Error uploading {report['name']} to S3: {e}")
    
    if not s3_results:
        raise AirflowSkipException("No reports were successfully stored in S3")
    
    return s3_results

def store_in_snowflake(**context):
    """Store report summaries in Snowflake"""
    # Import inside the function to avoid loading at DAG parse time
    from industry_research.snowflake_utils import store_report_summary
    
    ti = context['ti']
    s3_results = ti.xcom_pull(task_ids='store_in_s3')
    snowflake_init = ti.xcom_pull(task_ids='initialize_snowflake')
    
    if not s3_results:
        raise AirflowSkipException("No S3 results to store in Snowflake")
    
    if not snowflake_init:
        print("Warning: Snowflake initialization may not have completed successfully")
    
    snowflake_results = []
    for report in s3_results:
        try:
            name = report['name']
            industry = report['industry']
            summary = report['summary']
            
            # Store in Snowflake
            store_report_summary(
                report_id=name,
                industry=industry,
                summary=summary
            )
            
            snowflake_results.append({
                'name': name,
                'industry': industry,
                's3_url': report['s3_url'],
                'summary': summary
            })
            print(f"Successfully stored {name} summary in Snowflake")
        
        except Exception as e:
            print(f"Error storing {report['name']} in Snowflake: {e}")
    
    if not snowflake_results:
        raise AirflowSkipException("No summaries were successfully stored in Snowflake")
    
    return snowflake_results

def store_in_pinecone(**context):
    """Generate embeddings and store in Pinecone"""
    # Import inside the function to avoid loading at DAG parse time
    from industry_research.vector_storage_service import generate_embeddings, store_in_pinecone
    from industry_research.chunking_strategies import markdown_header_chunks
    
    ti = context['ti']
    snowflake_results = ti.xcom_pull(task_ids='store_in_snowflake')
    
    if not snowflake_results:
        raise AirflowSkipException("No Snowflake results to process for Pinecone")
    
    success_count = 0
    for report in snowflake_results:
        try:
            name = report['name']
            industry = report['industry']
            summary = report['summary']
            
            # Generate chunks for embeddings
            chunks = markdown_header_chunks(summary)
            
            if not chunks:
                print(f"No chunks generated for {name}, skipping")
                continue
                
            # Process each chunk
            embeddings_data = []
            for chunk in chunks:
                embedding = generate_embeddings(chunk)
                
                if embedding:
                    embeddings_data.append({
                        'content': chunk,
                        'embedding': embedding,
                        'metadata': {
                            'industry': industry,
                            'year': '2024',
                            'document_id': name
                        }
                    })
            
            if not embeddings_data:
                print(f"No embeddings generated for {name}, skipping")
                continue
                
            # Store embeddings in Pinecone
            store_success = store_in_pinecone(embeddings_data, index_name="deloitte-reports")
            
            if store_success:
                success_count += 1
                print(f"Successfully stored {name} embeddings in Pinecone")
            else:
                print(f"Failed to store {name} embeddings in Pinecone")
        
        except Exception as e:
            print(f"Error storing {report['name']} embeddings in Pinecone: {e}")
    
    if success_count == 0:
        raise AirflowSkipException("No embeddings were successfully stored in Pinecone")
    
    return f"Successfully stored {success_count} report embeddings in Pinecone"

def cleanup_temp_files(**context):
    """Clean up temporary PDF files"""
    import os
    import shutil
    
    try:
        # Clean up the temporary directory
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            os.makedirs(TEMP_DIR, exist_ok=True)
            print(f"Successfully cleaned up temporary files in {TEMP_DIR}")
        return "Cleanup completed"
    except Exception as e:
        print(f"Warning: Failed to clean up temporary files: {e}")
        return f"Cleanup failed: {str(e)}"

# Define the tasks
process_direct_pdfs_task = PythonOperator(
    task_id='process_direct_pdfs',
    python_callable=process_direct_pdfs,
    dag=dag,
)

process_html_reports_task = PythonOperator(
    task_id='process_html_reports',
    python_callable=process_html_reports,
    provide_context=True,
    dag=dag,
)

init_snowflake_task = PythonOperator(
    task_id='initialize_snowflake',
    python_callable=init_snowflake,
    dag=dag,
)

generate_summaries_task = PythonOperator(
    task_id='generate_summaries',
    python_callable=generate_summaries,
    provide_context=True,
    dag=dag,
)

store_in_s3_task = PythonOperator(
    task_id='store_in_s3',
    python_callable=store_in_s3,
    provide_context=True,
    dag=dag,
)

store_in_snowflake_task = PythonOperator(
    task_id='store_in_snowflake',
    python_callable=store_in_snowflake,
    provide_context=True,
    dag=dag,
)

store_in_pinecone_task = PythonOperator(
    task_id='store_in_pinecone',
    python_callable=store_in_pinecone,
    provide_context=True,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    provide_context=True,
    dag=dag,
    trigger_rule='all_done',  # Run this even if upstream tasks failed
)

# Define the task dependencies as a sequential pipeline
process_direct_pdfs_task >> process_html_reports_task >> generate_summaries_task >> store_in_s3_task
# Initialize Snowflake before storing in Snowflake
init_snowflake_task >> store_in_snowflake_task
# Continue the sequential pipeline
store_in_s3_task >> store_in_snowflake_task >> store_in_pinecone_task >> cleanup_task