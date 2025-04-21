from backend.pipeline.scrape_growjo_page import scrape_growjo_data
from backend.pipeline.growjo_pages_scrape import scrape_growjo_data_by_page
from datetime import datetime
from backend.s3_utils import upload_file_to_s3

# def growjo_s3_upload():
#     """
#     This function is a wrapper for the scrape_growjo function.
#     It can be used to call the scraping process from other parts of the code.
#     """
#     csv_content = scrape_growjo_data()
#     now = datetime.now()

#     # Format the datetime to YYYY-MM-DD_HH-MM-SS
#     formatted_time = now.strftime("%Y%m%d")

#     # Combine the formatted time with "growjo_data" to create the filename
#     filename = f"{formatted_time}_growjo_data.csv"
#     upload_file_to_s3(csv_content, filename, folder=f"growjo-data/{formatted_time}-Data")
#     print(filename)

def growjo_s3_upload():
    """
    This function is a wrapper for the scrape_growjo function.
    It can be used to call the scraping process from other parts of the code.
    """
    print("ok")
    csv_content, pages = scrape_growjo_data_by_page(5001,6000)
    now = datetime.now()

    # Format the datetime to YYYY-MM-DD_HH-MM-SS
    formatted_time = now.strftime("%Y%m%d_Data")

    # Combine the formatted time with "growjo_data" to create the filename
    filename = f"{pages}_growjo_data.csv"
    upload_file_to_s3(csv_content, filename, folder=f"growjo-data/{formatted_time}")
    print(filename)

growjo_s3_upload()
