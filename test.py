import argparse
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def check_farmer_status(aadhaar_number):
    if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
        print("Error: Please provide a valid 12-digit Aadhaar number.")
        sys.exit(1)

    # Configure headless Chrome so it runs silently in the background
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    
    # Initialize the WebDriver
    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://upfr.agristack.gov.in/farmer-registry-up/"
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # 1. Locate the Aadhaar input field using its aria-label
        aadhaar_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Enter Aadhaar Number']"))
        )
        aadhaar_input.clear()
        aadhaar_input.send_keys(aadhaar_number)
        
        # 2. Locate and click the 'Check' button or text
        # (Looking for a button or clickable element containing the text 'Check')
        check_btn = driver.find_element(By.XPATH, "//*[contains(text(), 'Check') and not(contains(text(), 'Against'))]")
        check_btn.click()
        
        # 3. Wait for the result list to populate and locate the Farmer Id list item
        farmer_id_element = wait.until(
            EC.presence_of_element_located((By.XPATH, "//li[contains(text(), 'Farmer Id')]"))
        )
        
        # Extract and print just the ID by stripping the label
        raw_text = farmer_id_element.text
        farmer_id = raw_text.replace("Farmer Id", "").strip()
        
        print(f"Success! Found Farmer ID: {farmer_id}")
        
    except Exception as e:
        print(f"Could not retrieve the Farmer ID. Ensure the Aadhaar number is registered or check your internet connection.\nError details: {e}")
        
    finally:
        # Always close the browser instance
        driver.quit()

if __name__ == "__main__":
    # Setup CLI argument parsing
    parser = argparse.ArgumentParser(description="Fetch Farmer ID from UP AgriStack Registry using an Aadhaar Number.")
    parser.add_argument("aadhaar", help="The 12-digit Aadhaar number of the farmer.")
    
    args = parser.parse_args()
    check_farmer_status(args.aadhaar)