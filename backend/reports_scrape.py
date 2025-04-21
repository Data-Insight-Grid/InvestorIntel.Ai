import os
import requests
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from chunking_strategies import markdown_header_chunks
from vector_storage_service import generate_embeddings, store_in_pinecone
from s3_utils import upload_pdf_to_s3
from snowflake_utils import initialize_snowflake_objects, store_report_summary
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')  # Using vision model for PDF analysis

# Directory to store reports
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True) 

# Part 1: URLs with Print buttons
PRINT_URLS = {
    "Tech_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/technology/technology-media-telecom-outlooks/technology-industry-outlook.html",
        # "https://www2.deloitte.com/us/en/insights/industry/technology/executives-expect-tech-industry-growth-in-2024.html",
    ],
    "Banking_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/financial-services/financial-services-industry-outlooks/banking-industry-outlook.html",
    ],
    "Healthcare_2024_Report_Deloitte": [
        # "https://www2.deloitte.com/us/en/insights/industry/health-care/life-sciences-and-health-care-industry-outlooks/2025-us-health-care-executive-outlook.html",
        "https://www2.deloitte.com/us/en/insights/industry/health-care/future-of-medtech-digital-business-models.html",
    ],
    "Entertainment_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/technology/digital-media-trends-consumption-habits-survey/2025.html",
    ],
    "Education_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/public-sector/2025-us-higher-education-trends.html",
    ],
    "RenewableEnergy_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/renewable-energy/renewable-energy-industry-outlook.html",
    ],
    "Sports_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/technology/technology-media-telecom-outlooks/sports-industry-outlook.html",
    ],
    "Semiconductors_2024_Report_Deloitte": [
        "https://www2.deloitte.com/us/en/insights/industry/technology/technology-media-telecom-outlooks/semiconductor-industry-outlook.html",
    ],
}

# Part 2: Direct PDF links
DIRECT_PDFS = {
    "AI_2024_Report_Deloitte": "https://www2.deloitte.com/content/dam/Deloitte/us/Documents/consulting/us-state-of-gen-ai-q4.pdf",
    "Automotive_2024_Report_Deloitte": "https://www2.deloitte.com/content/dam/Deloitte/us/Documents/consumer-business/deloitte-2025-global-automotive-consumer-study-january-2025.pdf",
    "Defense_2024_Report_PwC": "https://www.pwc.com/us/en/industries/industrial-products/library/assets/pwc-aerospace-defense-annual-industry-performance-outlook-2024.pdf",
}

def get_report_summary_with_gemini(pdf_content: bytes, filename: str) -> str:
    """Generate comprehensive summary of report using Gemini"""
    temp_pdf = None
    try:
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)
        
        # Create a temporary file with a unique name
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf_path = temp_pdf.name
        
        # Write content and close file handle immediately
        temp_pdf.write(pdf_content)
        temp_pdf.close()
        
        # Upload the file to Gemini
        file = genai.upload_file(temp_pdf_path)
        
        prompt = """
        Analyze this industry/market report comprehensively and generate a detailed summary. Consider text as well as images or graphs in the report. 
        Dont add any additional information or make any assumptions apart from the information provided in the report.
        Focus on the following aspects:

        1. Industry Overview
           - Current state and major trends
           - Market size and growth projections
           - Key drivers and challenges

        2. Technology & Innovation
           - Emerging technologies
           - Digital transformation trends
           - Innovation opportunities and challenges

        3. Market Dynamics
           - Supply chain analysis
           - Competitive landscape
           - Market segments and their growth potential

        4. Future Outlook
           - Short-term and long-term predictions
           - Potential disruptions
           - Growth opportunities

        5. Strategic Implications
           - Key recommendations
           - Risk factors
           - Success factors for industry players

        6. Economic Impact
           - Revenue projections
           - Investment trends
           - Economic indicators

        Please provide a comprehensive analysis that captures both explicit information and implicit insights from the report.
        Also capture key insights and statistics information from the images (if any) in the report.
        Focus on actionable intelligence and strategic implications.
        Include specific data points, statistics, and examples where available.
        Make sure to capture all the information from the report, including text, images, and graphs.
        Structure the response in clear sections with detailed explanations.
        """

        # Generate summary using the file and prompt
        response = model.generate_content([prompt, file])
        
        # Clean up: Delete the temporary file
        try:
            os.unlink(temp_pdf_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_pdf_path}: {e}")
        
        return response.text
            
    except Exception as e:
        print(f"Error generating summary with Gemini for {filename}: {e}")
        # Attempt to clean up even if there was an error
        if temp_pdf is not None:
            try:
                os.unlink(temp_pdf.name)
            except Exception as cleanup_error:
                print(f"Warning: Could not delete temporary file during error cleanup: {cleanup_error}")
        return None

def process_reports_pipeline():
    """Process reports through S3, Gemini, Snowflake, and Pinecone"""
    try:
        # Initialize Snowflake objects
        initialize_snowflake_objects()
        
        # Step 1: Process direct PDF URLs
        pdf_files = []
        for name, url in DIRECT_PDFS.items():
            try:
                industry = name.split('_')[0]
                response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if response.status_code == 200:
                    pdf_content = response.content
                    
                    # Generate summary using Gemini
                    print(f"Generating summary for {name}")
                    summary = get_report_summary_with_gemini(pdf_content, name)
                    
                    if summary:
                        # Upload PDF to S3
                        presigned_url = upload_pdf_to_s3(
                            file_content=pdf_content,
                            filename=f"{name}.pdf",
                            industry=industry
                        )
                        
                        # Store in Snowflake
                        store_report_summary(
                            report_id=name,
                            industry=industry,
                            summary=summary
                        )
                        
                        # Store in Pinecone
                        chunks = markdown_header_chunks(summary)
                        embeddings_data = []
                        for chunk in chunks:
                            embedding = generate_embeddings(chunk)
                            embeddings_data.append({
                                'content': chunk,
                                'embedding': embedding,
                                'metadata': {
                                    'industry': industry,
                                    'year': '2024',
                                    'document_id': name
                                }
                            })
                        
                        store_in_pinecone(embeddings_data, index_name="deloitte-reports")
                        print(f"Successfully processed and stored {name}")
                        
            except Exception as e:
                print(f"Error processing {name}: {e}")

        # Step 2: Process print-scraped PDFs
        for filename, urls in PRINT_URLS.items():
            industry = filename.split('_')[0]
            for i, url in enumerate(urls):
                try:
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        print(f"Visiting: {url}")
                        page.goto(url, timeout=60000)
                        page.wait_for_timeout(3000)
                        
                        # Generate PDF content  
                        pdf_content = page.pdf()
                        browser.close()
                        
                        pdf_name = f"{filename}_{i+1}"
                        
                        # Generate summary using Gemini
                        print(f"Generating summary for {pdf_name}")
                        summary = get_report_summary_with_gemini(pdf_content, pdf_name)
                        
                        if summary:
                            # Upload PDF to S3
                            presigned_url = upload_pdf_to_s3(
                                file_content=pdf_content,
                                filename=f"{pdf_name}.pdf",
                                industry=industry
                            )
                            
                            # Store in Snowflake
                            store_report_summary(
                                report_id=pdf_name,
                                industry=industry,
                                summary=summary
                            )
                            
                            # Store in Pinecone
                            chunks = markdown_header_chunks(summary)
                            embeddings_data = []
                            for chunk in chunks:
                                embedding = generate_embeddings(chunk)
                                embeddings_data.append({
                                    'content': chunk,
                                    'embedding': embedding,
                                    'metadata': {
                                        'industry': industry,
                                        'year': '2024',
                                        'document_id': pdf_name
                                    }
                                })
                            
                            store_in_pinecone(embeddings_data, index_name="deloitte-reports")
                            print(f"Successfully processed and stored {pdf_name}")
                            
                except Exception as e:
                    print(f"Error processing {url}: {str(e)}")

    except Exception as e:
        print(f"Error in pipeline: {str(e)}")

# Main execution
if __name__ == "__main__":
    process_reports_pipeline()
