
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

if __name__ == "__main__":
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get("https://kmong.com/gig/674416")
    
    time.sleep(2)
    
    text = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/section[2]/div/main/div[6]").text
    
    print(text)
    driver.quit()