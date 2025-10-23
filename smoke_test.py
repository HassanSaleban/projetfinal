from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://data.un.org/Data.aspx?d=ComTrade&f=_l1Code%3a85"  # NOTE: https

service = FirefoxService()   # nécessite geckodriver dans le PATH
options = webdriver.FirefoxOptions()
driver = webdriver.Firefox(service=service, options=options)

try:
    driver.get(URL)
    print("Title after .get():", driver.title)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.XPATH, "//a[normalize-space()='Download']")))
    print("✓ Page loaded & action bar visible.")
    driver.save_screenshot("smoke_loaded.png")
finally:
    driver.quit()
