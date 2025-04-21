from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
from dotenv import load_dotenv
import os
import io

def growjo_login():
    load_dotenv()
    GROWJO_EMAIL = os.getenv("GROWJO_EMAIL")
    GROWJO_PASSWORD = os.getenv("GROWJO_PASSWORD")
    if not GROWJO_EMAIL or not GROWJO_PASSWORD:
        raise ValueError("Please set GROWJO_EMAIL and GROWJO_PASSWORD in your .env file.")

    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument('--headless=new')  # Uncomment if needed
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--window-size=1920,1080")
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    driver.get("https://growjo.com/login")
    wait = WebDriverWait(driver, 10)
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
    email_input.send_keys(GROWJO_EMAIL)
    password_input.send_keys(GROWJO_PASSWORD)
    sign_in_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Sign In']")))
    sign_in_button.click()
    time.sleep(10)
    return wait, driver

def select_company_country(wait):
    companies_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'nav-link') and text()='Companies']")))
    companies_tab.click()
    time.sleep(8)

    try:
        clear_all_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/search' and contains(text(),'Clear All')]")))
        clear_all_button.click()
        print("🧹 Cleared all filters")
        time.sleep(5)
    except Exception as e:
        print("⚠️ Could not find or click the 'Clear All' button:", e)

    dropdown_placeholder = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'select__placeholder') and contains(text(),'Select Country')]")))
    dropdown_placeholder.click()
    options_list = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'select__option')]")))
    options_list[0].click()
    print("✅ Selected 'United States'")
    time.sleep(20)

def scrape_growjo_data_by_page(start_page: int, end_page: int = None):
    print("HI")
    wait, driver = growjo_login()
    select_company_country(wait)

    # Go to the start page
    current_page = 1
    while current_page < start_page:
        try:
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@class='next']/a[@href]")))
            driver.execute_script("arguments[0].click();", next_button)
            current_page += 1
            if current_page % 10 == 0:
                print(f"➡️ Navigated to page {current_page}")
            if current_page % 100 == 0:
                time.sleep(10)
            time.sleep(1)
        except Exception as e:
            print(f"❌ Couldn't navigate to start page {start_page}: {e}")
            driver.quit()
            return None

    if end_page is None:
        try:
            pagination_items = wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//ul[contains(@class, 'pagination')]/li/a")
            ))
            page_numbers = [int(el.text) for el in pagination_items if el.text.strip().isdigit()]
            end_page = max(page_numbers) if page_numbers else start_page
            print(f"🔢 Detected last page as {end_page}")
        except Exception as e:
            print(f"⚠️ Could not determine end page, defaulting to start page only: {e}")
            end_page = start_page

    all_rows = []
    headers = []
    time.sleep(90)
    first_rows = []

    while current_page <= end_page:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.cstm-table')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', {'class': 'cstm-table'})

            if not headers:
                headers = [th.text.strip() for th in table.find('thead').find_all('th')]

            first_row_text = table.find('tbody').find('tr').text.strip()

            # Check if data is already seen
            if first_row_text in first_rows:
                print(f"⚠️ Already seen content on page {current_page}, waiting for fresh data...")
                retries = 0
                max_retries = 10
                while first_row_text in first_rows and retries < max_retries:
                    time.sleep(2)
                    retries += 1
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    table = soup.find('table', {'class': 'cstm-table'})
                    first_row_text = table.find('tbody').find('tr').text.strip()
                    print(f"⏳ Attempt {retries}/{max_retries} to get fresh data on page {current_page}...")

                if retries == max_retries:
                    print(f"🚨 Skipping page {current_page} after {max_retries} retries due to no new data.")
                    current_page += 1
                    if current_page <= end_page:
                        try:
                            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@class='next']/a[@href]")))
                            driver.execute_script("arguments[0].click();", next_button)
                            time.sleep(2)
                        except Exception as e:
                            print(f"❌ Failed to click Next while skipping page: {e}")
                            break
                    continue

            first_rows.append(first_row_text)
            print(f"{current_page} | New unique pages seen: {len(first_rows)} | First row preview: {first_row_text}")

            for tr in table.find('tbody').find_all('tr'):
                cells = tr.find_all('td')
                row = []
                for idx, cell in enumerate(cells):
                    if idx == 1:
                        anchors = cell.find_all('a')
                        full_name = None
                        for a in anchors:
                            href = a.get('href')
                            if href and "/company/" in href:
                                full_name = href.split('/')[-1].replace('_', ' ')
                                break
                        row.append(full_name if full_name else cell.text.strip())
                    elif idx == 5:  # Assuming industry is at index 3 – change if needed
                        anchors = cell.find_all('a')
                        industry_name = None
                        for a in anchors:
                            href = a.get('href')
                            if href and "/industry/" in href:
                                industry_name = href.split('/')[-1].replace('_', ' ')
                                break
                        row.append(industry_name if industry_name else cell.text.strip())

                    else:
                        row.append(cell.text.strip())
                all_rows.append(row)

            print(f"📄 Scraped page {current_page}")
            current_page += 1

            if current_page <= end_page:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@class='next']/a[@href]")))
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)

        except Exception as e:
            print(f"❌ Error scraping page {current_page}: {e}")
            break

    df = pd.DataFrame(all_rows, columns=headers)
    pages = f"{str(start_page).zfill(5)}_{str(end_page).zfill(5)}"

    driver.quit()

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode(), pages

# def growjo_s3_upload():
#     """
#     This function is a wrapper for the scrape_growjo function.
#     It can be used to call the scraping process from other parts of the code.
#     """
#     print("ok")
#     csv_content, pages = scrape_growjo_data_by_page(1)
#     now = datetime.now()

#     # Format the datetime to YYYY-MM-DD_HH-MM-SS
#     formatted_time = now.strftime("%Y%m%d_Data")

#     # Combine the formatted time with "growjo_data" to create the filename
#     filename = f"{pages}_growjo_data.csv"
#     upload_file_to_s3(csv_content, filename, folder=f"growjo-data/{formatted_time}")
#     print(filename)
