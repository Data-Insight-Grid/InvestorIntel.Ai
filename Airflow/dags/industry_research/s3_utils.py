import os
import boto3
from dotenv import load_dotenv
import datetime
import os.path

# Load environment variables from .env file
load_dotenv()

# Fetch the credentials and region from the environment variables
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
bucket_name = os.getenv('AWS_S3_BUCKET_NAME')

# Initialize a session using AWS credentials
s3_client = boto3.client(
    's3',
    region_name=aws_region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

def generate_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for an S3 object
    
    Args:
        bucket_name: Name of the S3 bucket
        object_key: Key of the object in S3
        expiration: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned URL for the object
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return None

def upload_file_to_s3(file_content, filname, folder=None):
    """
    Uploads file content (e.g., csv) directly to S3.

    :param file_content: Binary content of the file.
    :param s3_key: Name of the file in S3.
    :param folder: Optional folder name in the S3 bucket (default is None).
    :return: True if upload is successful, False otherwise.
    """
    try:
        # If a folder is specified, prepend it to the key
        s3_key = f"{folder}/{filname}"

        # Upload the binary content to S3
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=file_content)
        print(f"File uploaded successfully to {bucket_name}/{s3_key}")
        return f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
    except Exception as e:
        print(f"Error uploading binary content: {e}")
        return False

def upload_pdf_to_s3(file_content, filename, industry):
    """
    Uploads PDF file to S3 in the pdfs/{industry} folder and returns a presigned URL.
    
    Args:
        file_content: Binary content of the PDF file
        filename: Name of the PDF file
        industry: Industry category for folder organization
    
    Returns:
        Presigned URL of the uploaded file
    """
    try:
        # Store PDFs in pdfs/{industry} folder
        s3_key = f"pdfs/{industry}/{filename}"
        
        # Upload the binary content to S3
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=file_content)
        print(f"PDF uploaded successfully to {bucket_name}/{s3_key}")
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = generate_presigned_url(bucket_name, s3_key)
        if presigned_url:
            print(f"Generated presigned URL for {filename}")
            return presigned_url
        else:
            raise Exception("Failed to generate presigned URL")
            
    except Exception as e:
        print(f"Error uploading PDF: {e}")
        return None

def upload_markdown_to_s3(markdown_content, industry, filename):
    """
    Uploads markdown file to S3 in the markdown/{industry} folder.
    
    Args:
        markdown_content: Content of the markdown file
        industry: Industry category for folder organization
        filename: Name of the markdown file
    
    Returns:
        S3 key of the uploaded file
    """
    try:
        # Store markdown files in markdown/{industry} folder
        s3_key = f"markdown/{industry}/{filename}"
        
        # Upload the markdown content to S3
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=markdown_content)
        print(f"Markdown uploaded successfully to {bucket_name}/{s3_key}")
        return s3_key  # Return just the S3 key since we don't need URL for markdown files
    except Exception as e:
        print(f"Error uploading markdown: {e}")
        return None

def get_s3_object(s3_key: str) -> str:
    """
    Get an object from S3 by its key
    
    Args:
        s3_key: The S3 key of the object
    
    Returns:
        The content of the object as string
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        print(f"Error getting S3 object: {e}")
        return None

def upload_pitch_deck_to_s3(file_path, startup_name=None, industry=None, original_filename=None):
    """
    Uploads a pitch deck PDF file to S3 and returns a presigned URL for access.
    This function combines the naming logic from summary.py's upload_to_s3 and
    the presigned URL generation from s3_utils.py's upload_pdf_to_s3.
    
    Args:
        file_path: Path to the PDF file
        startup_name: Name of the startup
        industry: Industry category
        original_filename: Original filename of the PDF
    
    Returns:
        Presigned URL of the uploaded file
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            return None
        print("File exists")
        # Generate a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine the base filename
        if original_filename:
            # Use the original filename without path or extension
            base_filename = os.path.splitext(os.path.basename(original_filename))[0]
        else:
            # Fallback to a default name
            base_filename = "pitch_deck"
        
        # Clean up the filename - replace spaces and special chars with underscores
        base_filename = ''.join(c if c.isalnum() else '_' for c in base_filename)
        
        # Create the S3 object name
        # Format: [Filename]_[Timestamp].pdf
        s3_object_name = f"{base_filename}_{timestamp}.pdf"
        
        # Add startup name and industry prefixes if they're valid values
        prefix = ""
        if startup_name and startup_name.lower() != "unknown":
            safe_name = ''.join(c if c.isalnum() else '_' for c in startup_name)
            prefix += f"{safe_name}_"
        
        if industry and industry.lower() != "unknown":
            safe_industry = ''.join(c if c.isalnum() else '_' for c in industry)
            prefix += f"{safe_industry}_"
        
        # Combine prefix with the base filename and timestamp
        if prefix:
            s3_object_name = f"{prefix}{s3_object_name}"
        
        # Create the complete S3 key with proper folder structure
        # Store pitch decks in pitchdecks/{industry} folder
        s3_key = f"pitchdecks/{industry}/{s3_object_name}"
        
        # Upload the file to S3
        with open(file_path, 'rb') as file_data:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_data.read()
            )
        print(f"Pitch deck uploaded successfully to {bucket_name}/{s3_key}")
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = generate_presigned_url(bucket_name, s3_key)
        if presigned_url:
            print(f"Generated presigned URL for {s3_object_name}")
            return presigned_url
        else:
            raise Exception("Failed to generate presigned URL")
    
    except Exception as e:
        print(f"Error uploading pitch deck to S3: {e}")
        return None
