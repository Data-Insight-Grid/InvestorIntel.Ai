import boto3
import google.generativeai as genai
import os
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

# --- Configuration ---
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')


# --- Functions ---
def validate_environment():
    """
    Validates that all required environment variables are set.
    Returns a tuple (is_valid, missing_vars) where is_valid is a boolean
    and missing_vars is a list of missing variable names.
    """
    required_vars = {
        "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
        "AWS_S3_BUCKET_NAME": AWS_S3_BUCKET_NAME,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    
    missing_vars = [name for name, value in required_vars.items() if value is None]
    return len(missing_vars) == 0, missing_vars

def summarize_pitch_deck_with_gemini(file_path, api_key, model_name):
    """
    Uploads a PDF to the Gemini API and generates a summary tailored for investors.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    uploaded_file_resource = None # Keep track of the uploaded file resource for cleanup
    try:
        print(f"\nConfiguring Gemini API with model '{model_name}'...")
        genai.configure(api_key=api_key)

        # 1. Upload the file to the Gemini API service
        print(f"Uploading '{os.path.basename(file_path)}' to Google for analysis...")
        uploaded_file_resource = genai.upload_file(
            path=file_path,
            display_name=os.path.basename(file_path)
        )
        print(f"Uploaded file '{uploaded_file_resource.display_name}' as: {uploaded_file_resource.uri}")
        print(f"File State: {uploaded_file_resource.state.name}")

        # 2. Wait for the file to be processed by the API
        print("Waiting for file processing...")
        while uploaded_file_resource.state.name == "PROCESSING":
            print('.', end='', flush=True)
            time.sleep(5) # Check status every 5 seconds
            uploaded_file_resource = genai.get_file(uploaded_file_resource.name) # Fetch updated status

        if uploaded_file_resource.state.name != "ACTIVE":
            print(f"\nFile processing failed. Final state: {uploaded_file_resource.state.name}")
            if uploaded_file_resource:
                 print(f"Attempting to delete non-active file: {uploaded_file_resource.name}")
                 genai.delete_file(uploaded_file_resource.name)
            return None

        print("\nFile processed successfully. Generating investor summary...")

        # 3. Configure the generative model
        model = genai.GenerativeModel(model_name=model_name)

        # 4. Create a detailed prompt for investor-focused summarization
        prompt = """
        Analyze the provided startup pitch deck PDF from the perspective of a venture capital investor.
        Generate a concise summary covering the key aspects an investor needs to evaluate the opportunity.
        Structure the summary clearly, addressing the following points based *only* on the document's content:

        1.  **Problem:** Clearly state the core problem the startup addresses.
        2.  **Solution:** Describe the startup's proposed solution.
        3.  **Product/Service:** Briefly detail the offering.
        4.  **Business Model:** Explain how the company intends to generate revenue.
        5.  **Target Market & Opportunity:** Identify the customer segment and the market's size/potential.
        6.  **Team:** Summarize key team members and their relevant background (if mentioned).
        7.  **Traction/Milestones:** Highlight any achievements like user growth, revenue, partnerships, or completed milestones.
        8.  **Competition:** List key competitors and the startup's differentiation (if provided).
        9.  **Financials:** Summarize key financial data or projections presented.
        10. **Funding Ask & Use:** State the amount of funding sought and its intended use.
        11. **Investor Synopsis:** Conclude with a brief assessment of potential strengths, weaknesses, and overall investment appeal based *strictly* on the deck's content.

        Be objective and extract information accurately. If information for a section is not present in the PDF, state that clearly (e.g., "Financial projections were not provided.").
        """

        # 5. Generate the summary using the prompt and the uploaded file
        response = model.generate_content([prompt, uploaded_file_resource])

        print("Summary generated.")
        return response.text

    except Exception as e:
        print(f"\nAn error occurred during Gemini interaction: {e}")
        return None

    finally:
        # 6. Clean up: Delete the file from the Gemini service
        if uploaded_file_resource and genai.get_file(uploaded_file_resource.name).state.name != "DELETED":
            try:
                print(f"Attempting to delete uploaded file: {uploaded_file_resource.name}")
                genai.delete_file(uploaded_file_resource.name)
                print(f"Successfully deleted file {uploaded_file_resource.name}.")
            except Exception as delete_e:
                print(f"Warning: Could not delete file {uploaded_file_resource.name}: {delete_e}")

# This will only run if summary.py is executed directly (not when imported)
if __name__ == "__main__":
    print("This module provides functions for pitch deck processing and should be imported, not run directly.")