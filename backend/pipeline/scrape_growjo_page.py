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
    # Load environment variables
    load_dotenv()
    GROWJO_EMAIL = os.getenv("GROWJO_EMAIL")
    GROWJO_PASSWORD = os.getenv("GROWJO_PASSWORD")
    if not GROWJO_EMAIL or not GROWJO_PASSWORD:
        raise ValueError("Please set GROWJO_EMAIL and GROWJO_PASSWORD in your .env file.")

    # Set up Selenium WebDriver options
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    #options.add_argument('--headless=new')
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

    # Open login page
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
    # Navigate to the Companies tab
    companies_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'nav-link') and text()='Companies']")))
    companies_tab.click()
    time.sleep(8)

    # Clear all filters if present
    try:
        clear_all_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='/search' and contains(text(),'Clear All')]")))
        clear_all_button.click()
        print("🧹 Cleared all filters")
        time.sleep(5)
    except Exception as e:
        print("⚠️ Could not find or click the 'Clear All' button:", e)

    # Select the country from the dropdown
    dropdown_placeholder = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'select__placeholder') and contains(text(),'Select Country')]")))
    dropdown_placeholder.click()
    options_list = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'select__option')]")))
    options_list[0].click()
    print("✅ Selected 'United States'")
    time.sleep(20)


def scrape_growjo_data():
    wait, driver = growjo_login()
    select_company_country(wait)

    # Step 3: Scrape multiple pages
    all_rows = []
    headers = []
    time.sleep(2)
    first_rows = []

    cnt = 1  # Start at page 1
    while True:
        # Explicitly wait for the current table to load
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.cstm-table')))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', {'class': 'cstm-table'})

        if not headers:
            headers = [th.text.strip() for th in table.find('thead').find_all('th')]

        first_row_text = table.find('tbody').find('tr').text.strip()
        while first_row_text in first_rows:
            print("⏳ Waiting for new data to load...")
            time.sleep(1)
             # Refresh the page source
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            table = soup.find('table', {'class': 'cstm-table'})
            first_row_text = table.find('tbody').find('tr').text.strip()

        first_rows.append(first_row_text)


        # Your scraping logic here
        for tr in table.find('tbody').find_all('tr'):
            cells = tr.find_all('td')
            row = []
            for idx, cell in enumerate(cells):
                if idx == 1:
                    anchors = cell.find_all('a')
                    full_name = next((a.get('href').split('/')[-1].replace('_', ' ')
                                    for a in anchors if a.get('href') and "/company/" in a.get('href')),
                                    cell.text.strip())
                    row.append(full_name)
                else:
                    row.append(cell.text.strip())
            all_rows.append(row)

        print(f"📄 Page {cnt} scraped.")
        cnt += 1

        # Find and click "Next" button reliably
        try:
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//li[@class='next']/a[@href]")))
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
        except Exception as e:
            print(f"✅ Reached last page or pagination error: {e}")
            break

    # Save to CSV
    df = pd.DataFrame(all_rows, columns=headers)
    df.to_csv("new_pipeline.csv", index=False)
    # print(f"✅ Saved data to: {filename}")

    # Cleanup
    driver.quit()

    # In-memory CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode()

