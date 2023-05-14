import json
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ats import ats_utils
from ats.careerbuilder import careerbuilder

jobs_with_aq = []

urls = []
with open("urls.txt") as f:
    urls = f.readlines()
with open("aq_cookies.json") as f:
    cookies = f.read()

with ats_utils.initialize_webdriver() as driver:
    ats_utils.load_cookies(driver, cookies)

    for url in urls:
        driver.get(url)
        try:
            apply_button = driver.find_element(
                "xpath", '//a[@data-gtm="job-action|apply-internal-top"]'
            )
        except NoSuchElementException:
            print("No Such Element")
            continue

        if apply_button.text == "Quick Apply":
            continue
        else:
            apply_button.click()
            try:
                next_elm = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            '//button[@type="submit" and contains(text(),"Next")]',
                        )
                    )
                )
            except:
                pass
            else:
                print(url)
                jobs_with_aq.append(url)
with open("urls_aq.txt", "w") as f:
    json.dump(jobs_with_aq, f)
