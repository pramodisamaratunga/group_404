from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.binary_location = "/usr/bin/chromium-browser"

service = Service("/home/user1/grp404/chromedriver-linux64/chromedriver")

driver = webdriver.Chrome(service=service, options=options)

try:
    # Open the target website
    driver.get("https://aserg-ufmg.github.io/why-we-refactor/#/projects")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))

    print(driver.page_source)

    project_elements = driver.find_elements(By.XPATH, "//table/tbody/tr/td[1]/a")

    project_links = [element.get_attribute("href") for element in project_elements]

    if project_links:
        # Write project links to a text file
        with open("project_links.txt", "w") as file:
            for link in project_links:
                file.write(link + "\n")

        print(f"Project links have been saved to project_links.txt. Found {len(project_links)} links.")
    else:
        print("No project links were found.")

finally:
    driver.quit()
