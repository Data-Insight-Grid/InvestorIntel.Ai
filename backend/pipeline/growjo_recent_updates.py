from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def get_recent_updates():
    # Setup driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Silent browsing
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # Directly access the updates page
        driver.get("https://growjo.com/")  # Verify actual URL
        
        # Wait for card content
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.recent-card-maping"))
        )
        
        # Parse data
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return parse_card_data(soup)
        
    finally:
        driver.quit()

def parse_card_data(soup):
    results = []
    for div in soup.select("div.recent-card-maping"):
        company = div.select_one("h4 a").get_text(strip=True)
        spans = div.select("span")
        
        results.append({
            "company": company,
            "funding": spans[0].text.replace("Funding ", ""),
            "valuation": spans[1].text.replace("Valuation: ", ""),
            "revenue": spans[2].text.replace("Revenue ", ""),
            "growth": spans[3].text.replace("Growth ", "")
        })
    return results

# Usage
if __name__ == "__main__":
    data = get_recent_updates()
    print(data)
    print("Data length:"+str(len(data))+" entry type"+str(type(data)))
    print(f"Scraped {len(data)} entries:")
    for entry in data:
        print(entry)


# data = [
#             {'company': 'SSI Inc.', 'funding': '$2000M', 'valuation': '$B', 'revenue': '$100M', 'growth': '114%'},
#             {'company': 'Marshmallow', 'funding': '$90M', 'valuation': '$2B', 'revenue': '$100M', 'growth': '32%'},
#             {'company': 'Jobandtalent', 'funding': '$103M', 'valuation': '$1.5B', 'revenue': '$100M', 'growth': '6%'},
#             {'company': 'incident.io', 'funding': '$62M', 'valuation': '$400M', 'revenue': '$100M', 'growth': '-9%'},
#             {'company': 'Meanwhile', 'funding': '$40M', 'valuation': '$190M', 'revenue': '$100M', 'growth': '25%'}
#         ]