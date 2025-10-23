# test_min.py
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

service = Service(GeckoDriverManager().install())
opts = webdriver.FirefoxOptions()
# Bypass proxy système pour voir si ça débloque:
opts.set_preference("network.proxy.type", 0)  # 0:none, 5:system

drv = webdriver.Firefox(service=service, options=opts)
drv.set_page_load_timeout(60)
try:
    drv.get("https://example.com")
    print("TITLE:", drv.title)
finally:
    drv.quit()
