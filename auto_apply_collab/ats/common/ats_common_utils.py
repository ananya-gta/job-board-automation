import datetime
import json

# logger = get_task_logger(__name__)
import logging

# import logging
import os
import random
import re
import signal
import subprocess
import time
from contextlib import contextmanager
from itertools import permutations
from random import randint
from typing import Any, List, Tuple, Union

import requests
import selenium
from pydantic import BaseModel

# from celery.utils.log import get_task_logger
from selenium import webdriver as basic_webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

# from selenium_stealth import stealth
# from seleniumwire import webdriver as wire_webdriver
from webdriver_manager.chrome import ChromeDriverManager

import ats
import ats.common._ats_config
from ats.common.config import IS_DEBUG

# from ats.config import ENV, IS_DEBUG

logger = logging.getLogger(__name__)
s = requests.Session()


def fill_additional_q(q, driver, wait):
    # if application.get('additional_questions', None):
    #     for q in application['additional_questions']:
    school_class = "select2-container school-name background-field"
    if q["type"] in ["input", "text", "textarea"]:
        if school_class in q["xpath"]:
            greenhouse_provide_school(driver, wait, q)
        else:
            raw_elem = q["xpath"]
            element_xp = (
                list(raw_elem.values())[0]
                if isinstance(raw_elem, dict) and len(raw_elem) == 1
                else raw_elem
            )
            driver.find_element_by_xpath(element_xp).clear()
            driver.find_element_by_xpath(element_xp).send_keys(q["answer"])
    elif q["type"] == "file":  # e.g. cover letter - is it from gdrive?
        driver.find_element_by_xpath(q["xpath"]).send_keys(q["answer"])
    elif q["type"] == "radio":
        answer_key = q["answer"]
        answer_xpath = q["xpath"][answer_key]
        scroll_to_and_click(driver, wait, answer_xpath)
    elif q["type"] == "checkbox":
        answers = q["answer"] if isinstance(q["answer"], list) else [q["answer"]]
        # ans_xpathes = [q['xpath'].get(ans) for ans in answers]
        xpath_dict_subset = {
            key: value for key, value in q["xpath"].items() if key in answers
        }
        for ans_text, xpath in xpath_dict_subset.items():
            try:
                scroll_to_and_click(driver, wait, xpath)
            except Exception as e:
                # escaped_ans = escape_string_for_xpath(ans_text)
                # alter_xpath = f'//div[@class="field" and contains(string(), {escaped_ans})]//input[@type="checkbox"]'
                # driver.find_element_by_xpath(alter_xpath).click()
                msg = f"scroll_to_and_click failed : {e}"
                logger.debug(f"{e}")
    elif q["type"] == "dropdown" and "_xpath_division_" in q["xpath"][q["answer"]]:
        xpath = q["xpath"][q["answer"]].split("_xpath_division_")
        dropdown_xpath = xpath[0]
        option_xpath = xpath[1]
        dropdown_elm = driver.find_element(By.XPATH, dropdown_xpath)
        driver.execute_script("arguments[0].scrollIntoView();", dropdown_elm)
        dropdown_elm.click()
        time.sleep(0.5)

        # options_elm = driver.find_elements(By.XPATH, option_xpath)
        # for option_elm in options_elm:
        #     if option_elm.text == q["answer"]:
        #         option_elm.click()
        #         break

        action = ActionChains(driver)
        option_elm = driver.find_element(By.XPATH, option_xpath)
        action.move_to_element(option_elm).perform()
        wait.until(EC.visibility_of_element_located((By.XPATH, option_xpath))).click()
        action.reset_actions()
        for device in action.w3c_actions.devices:
            device.clear_actions()

    elif q["type"] == "dropdown":
        dropdown_xpath = q["xpath"][q["answer"]]
        select_elem = driver.find_element_by_xpath(dropdown_xpath)
        if not select_elem.is_displayed():
            driver.execute_script("arguments[0].style.display='block'", select_elem)
        ds = Select(select_elem)
        ds.select_by_visible_text(q["answer"])


@contextmanager
def initialize_webdriver(
    headless=False if IS_DEBUG else True, remote=False, proxy_url=None, sel_wire=False
) -> WebDriver:
    # install newest chromedriver locally and create webdriver session
    driver = None
    try:
        options = basic_webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        logger.info("Initializing basic selenium driver")
        driver = basic_webdriver.Chrome(
            ChromeDriverManager().install(),
            options=options,
            # desired_capabilities=capabilities,
        )
        yield driver
    finally:
        if driver:
            try:
                logger.debug("Driver closed.")
                driver.close()
                driver.quit()
            except WebDriverException:
                pass


def load_localstorage(driver, localstorage_string: str):
    local_storage = json.loads(localstorage_string)
    url = local_storage["url"]
    data = local_storage["data"]
    driver.get(url)
    for key, value in data.items():
        script = f"window.localStorage.setItem('{key}', '{value}');"
        driver.execute_script(script)


def load_cookies(driver, cookies_string: str):
    cookies = json.loads(cookies_string)
    url = cookies["url"]
    data = cookies["data"]
    driver.get(url)
    driver.delete_all_cookies()
    for cookie in data:
        driver.add_cookie(cookie)


def dump_cookies(driver, url=None, skip_same_site=True, filter_fn=None) -> str:
    if url:
        driver.get(url)
    cookies = driver.get_cookies()
    if filter_fn:
        cookies = list(filter(filter_fn, cookies))
    # Prevent AssertationError in add_cookies()
    for cookie in cookies:
        if cookie.get("sameSite", "") == "None" and skip_same_site is True:
            del cookie["sameSite"]
    return json.dumps({"url": url, "data": cookies})


def dump_localstorage(driver, url=None, skip_same_site=True, filter_fn=None) -> str:
    if url:
        driver.get(url)
    localstorage = driver.execute_script("return window.localStorage;")

    if filter_fn:
        localstorage = list(filter(filter_fn, localstorage))
    # Prevent AssertationError in add_cookies()
    return json.dumps({"url": url, "data": localstorage})


def login_indeed_gmail_acct(driver, creds_dict):
    logger.debug("Start login flow on indeed.com")
    login_page = "https://secure.indeed.com/account/login?hl=en_US&co=US"
    driver.implicitly_wait(4)
    driver.get(login_page)
    driver.find_element_by_xpath('//button[@id="login-google-button"]').click()
    driver.switch_to.window(driver.window_handles[1])
    userfield = driver.find_element_by_xpath('//input[@type="email"]')
    userfield.send_keys(creds_dict["username"])
    userfield.send_keys(Keys.ENTER)
    # In headless mode an older version of GMail login might appear, handle that here:
    pwfield = None
    for xpath in ('//*[@id="password"]/div[1]/div/div[1]/input', '//*[@id="password"]'):
        try:
            pwfield = driver.find_element_by_xpath(xpath)
        except NoSuchElementException:
            continue
    if pwfield is None:
        r = randint(1e4, 1e5)
        logger.error(f"Password field not found, exiting..., {r}")
        # Save screenshot and dump HTML
        dump_screenshot_html(driver, "gmail_login_error", r)
        raise RuntimeError
    pwfield.send_keys(creds_dict["pw"])
    pwfield.send_keys(Keys.ENTER)
    time.sleep(6)
    if len(driver.window_handles) != 1:
        # It may be necessary to give phone number
        pn = get_element_wo_exception(driver, '//*[@id="phoneNumber"]')
        if pn is not None:
            phone_number_field = driver.find_element_by_xpath()
            # phone_number_field.send_keys("+36308120199")
            sms_button = driver.find_element_by_xpath('//*[@id="submitSms"]')
            sms_button.click()

        send_sms_button = get_element_wo_exception(
            driver, '//*[@id="idvPreresteredPhoneSms"]'
        )
        if send_sms_button is not None:
            send_sms_button.click()
            pin = driver.find_element_by_xpath('//*[@id="idvPreregisteredPhonePin"]')
            # pin.send_keys("fds")
            done = driver.find_element_by_xpath('//*[@id="submit"]')
            done.click()

        pn = get_element_wo_exception(driver, '//*[@type="tel"]')
        if pn is not None:
            pn.send_keys("+14082036834")
            done = driver.find_element_by_xpath('//*[@id="submit"]')
            done.click()

    driver.switch_to.window(driver.window_handles[0])
    return driver


def get_element_wo_exception(driver, xpath):
    try:
        return driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return None


def dump_screenshot_html(driver, file_name_ending, _id=None, folder="/tmp"):
    if _id is None:
        r = randint(1e4, 1e5)
    else:
        r = _id
    logger.debug(f"Debugging test, ID: {r}")
    # Save screenshot and dump HTML
    driver.save_screenshot(f"{folder}/{r}_{file_name_ending}.png")
    html = driver.execute_script("return document.body.innerHTML;")
    with open(f"{folder}/{r}_{file_name_ending}.html", "w") as f:
        f.write(html)


def dump_network_logs(driver, file_name_ending, _id=None, folder="/tmp"):
    pass


def scroll_to_and_click_retry(driver, xp: str):
    try:
        xp = xp + "/.."
        btn = driver.find_element(By.XPATH, xp)
        action = ActionChains(driver)
        # action.move_to_element(btn).click().pause(1).perform()
        action.move_to_element(btn).perform()
        action.reset_actions()
        for device in action.w3c_actions.devices:
            device.clear_actions()
        time.sleep(1)
        btn.click()
    except Exception as e:
        msg = f"We could not move to and click on the element, error: {e}"
        # logger.debug(f'We could not move to and click on the element, error: {e}')
        print(msg)


def scroll_to_and_click(driver, wait: WebDriverWait, xp: str):
    try:
        elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, xp)))
    except TimeoutException:
        msg = f'Element(s) not found for xpath: "{xp}", therefore we cannot scroll and click on it'
        print(msg)
        # logger.debug(f'Element(s) not found for xpath: "{xp}", therefore we cannot scroll and click on it')
        return
    for element in elements:
        try:
            # driver.execute_script("arguments[0].scrollIntoView(true);", element)
            action = ActionChains(driver)
            # action.move_to_element(element).click().pause(1).perform()
            action.move_to_element(element).perform()
            time.sleep(1)
            element.click()

            # reset_actions() on its own doesn't work, solution:
            # https://stackoverflow.com/questions/67614276/perform-and-reset-actions-in-actionchains-not-working-selenium-python
            action.reset_actions()
            for device in action.w3c_actions.devices:
                device.clear_actions()
        except Exception as e:
            scroll_to_and_click_retry(
                driver, xp
            )  # msg = f"We could not move to and click on the element, error: {e}"  # # logger.debug(f'We could not move to and click on the element, error: {e}')  # print(msg)


def check_aq_length(driver, url: str):
    try:
        if "jobs.lever.co" in url:
            lever_aq_xp = '//li[@class="application-question custom-question"]//span[@class="required"]'
            questions = driver.find_elements_by_xpath(lever_aq_xp)
        elif "workable" in url:
            workable_aq_xp = (
                "//div[contains(@class,'styles__field--') and contains(string(), '*')]"
            )
            questions = driver.find_elements_by_xpath(workable_aq_xp)
        elif "greenhouse" in url:
            custom_fields_block = driver.find_element_by_id("custom_fields")
            questions = get_greenhouse_aq(driver, custom_fields_block)
        else:
            questions = ["test", "test", "test"]
        aq_len = len(questions)
    except Exception as e:
        logger.info(
            f"Cannot determine AQ length during application, moving on with the apply. url: {url} error: {e}"
        )
        aq_len = None
    return aq_len


def has_not_been_mutated(driver, wait, xpath: str):
    """Check if the element hasn't been touched in 1,5 sec, append a 'done div' if the condition is true,
    selenium checks if the 'done div' is in the DOM, which indicates that the original element is idle,
    remove the 'done div'"""

    wait = WebDriverWait(driver, 25)
    base_script = r"""
    const targetNode = document.evaluate('XPATH_LOCATOR_TAG', document, null, 
                                         XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue
    const config = { attributes: true, childList: true, subtree: true, characterData: true};

    function done() {
        const el = document.createElement('div');
        el.id = "done98765432100"
        document.body.appendChild(el);
        observer.disconnect()
    }

    let timeout = null;
    const callback = function(mutationsList, observer) {
        clearTimeout(timeout);
        timeout = setTimeout(done, 5000);
        for (const mutation of mutationsList) {
            console.log('Time is ticking');
        }
        };
    const observer = new MutationObserver(callback);
    observer.observe(targetNode, config);
    """
    mutation_script = base_script.replace("XPATH_LOCATOR_TAG", xpath)
    driver.execute_script(mutation_script)
    wait.until(
        EC.presence_of_element_located((By.XPATH, '//div[@id="done98765432100"]'))
    )
    driver.execute_script(
        r"""
    let done_node = document.querySelector('div#done98765432100')
    done_node.remove()
    """
    )


def apply_error_status(msg):
    return {"status": "error", "message": msg}


def apply_success_status(msg):
    return {"status": "success", "message": msg}


def aq_error_status(msg):
    qs = {
        "questions": {
            "status": "error",
            "message": msg,
        }
    }
    return qs


def aq_empty_list():
    data = {
        "questions": [],
        "cover_letter_is_required": False,
    }
    return data


def _get_answer(q):
    """
    # https://jsonformatter.org/json-to-python
    import json
    print(json.loads('<json>')

        >>> q = {'page': 0, 'type': 'checkbox', 'xpath': {'Confirm': '//div[@class="field" and contains(string(),"Privacy Policy Consent Form")]//label[text()[contains(.,"Confirm")]]//input[@type="checkbox"]'}, 'long_response': False, 'question_text': 'Privacy Policy Consent Form'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'checkbox', 'xpath': {'Confirm': '//div[@class="field" and contains(string(),"Privacy Policy Consent Form")]//label[text()[contains(.,"Confirm")]]//input[@type="checkbox"]'}, 'long_response': False, 'question_text': 'Privacy Policy Consent Form', 'answer': ['Confirm']}
        >>> q = {'page': 0, 'type': 'dropdown', 'xpath': {'No': '//select[@id="job_application_answers_attributes_1_boolean_value"]', 'Yes': '//select[@id="job_application_answers_attributes_1_boolean_value"]'}, 'long_response': False, 'question_text': 'Are you legally authorized to work in the US?'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'dropdown', 'xpath': {'No': '//select[@id="job_application_answers_attributes_1_boolean_value"]', 'Yes': '//select[@id="job_application_answers_attributes_1_boolean_value"]'}, 'long_response': False, 'question_text': 'Are you legally authorized to work in the US?', 'answer': 'Yes'}
        >>> q = {'page': 0, 'type': 'radio', 'xpath': {'No': '(//div[@data-qa="additional-cards"][1]//li[@class="application-question custom-question"][1]//input)[2]', 'Yes': '(//div[@data-qa="additional-cards"][1]//li[@class="application-question custom-question"][1]//input)[1]'}, 'long_response': False, 'question_text': 'Do you have the right to work in the US without sponsorship indefinitely?'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'radio', 'xpath': {'No': '(//div[@data-qa="additional-cards"][1]//li[@class="application-question custom-question"][1]//input)[2]', 'Yes': '(//div[@data-qa="additional-cards"][1]//li[@class="application-question custom-question"][1]//input)[1]'}, 'long_response': False, 'question_text': 'Do you have the right to work in the US without sponsorship indefinitely?', 'answer': 'Yes'}
        >>> q = {'page': 0, 'type': 'textarea', 'xpath': '//div[@class="field"]/*/textarea[@id="job_application_answers_attributes_2_text_value"]', 'long_response': True, 'question_text': 'How did you first hear about 98point6?'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'textarea', 'xpath': '//div[@class="field"]/*/textarea[@id="job_application_answers_attributes_2_text_value"]', 'long_response': True, 'question_text': 'How did you first hear about 98point6?', 'answer': 'This is a great opportunity for me.'}
        >>> q = {'page': 0, 'type': 'input', 'xpath': '//div[@class="field"]/*/input[@id="job_application_answers_attributes_1_text_value"]', 'long_response': False, 'question_text': 'If you are based  in the US, will you need the company to sponsor your right to work in the US now or in the future?'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'input', 'xpath': '//div[@class="field"]/*/input[@id="job_application_answers_attributes_1_text_value"]', 'long_response': False, 'question_text': 'If you are based  in the US, will you need the company to sponsor your right to work in the US now or in the future?', 'answer': 'Yes'}
        >>> q = {'page': 0, 'type': 'number'}
        >>> _get_answer(q)
        {'page': 0, 'type': 'number', 'answer': 3}
    """
    answer = None

    def guess_required_date_format(text: str):
        """
        %m - zero padded month = mm
        %d - zero padded day = dd
        %y - zero padded year wo century (2 digits) = yy
        %Y - zero padded year with century (4 digits) = yyyy
        seprators = - /
        use regex.
        """
        text.lower()

        date_fmt_order_3 = [p for p in permutations(["yy", "mm", "dd"], 3)] + [
            p for p in permutations(["yyyy", "mm", "dd"], 3)
        ]
        date_fmt_order_2 = [p for p in permutations(["yy", "mm", "dd"], 2)] + [
            p for p in permutations(["yyyy", "mm", "dd"], 2)
        ]

        sep = ["-", "/"]
        date_fmt_order_3_text = [s.join(date) for date in date_fmt_order_3 for s in sep]
        date_fmt_order_2_text = [s.join(date) for date in date_fmt_order_2 for s in sep]

        found_date_fmt = [x for x in date_fmt_order_3_text if re.search(x, text)]
        if not found_date_fmt:
            found_date_fmt = [x for x in date_fmt_order_2_text if re.search(x, text)]

        if found_date_fmt:
            return (
                found_date_fmt[0]
                .replace("yyyy", "%Y")
                .replace("yy", "%y")
                .replace("mm", "%m")
                .replace("dd", "%d")
            )
        else:
            return None

    def smart_answer(xpath: dict):
        key_for_yes = [k for k in xpath.keys() if "yes" in k.lower()]
        if key_for_yes:
            return key_for_yes[0]
        return None

    def first_answer(xpath: dict):
        return list(xpath.keys())[0]

    def last_answer(xpath: dict):
        return list(xpath.keys())[-1]

    def random_answer(xpath: dict):
        return random.choice(list(xpath.keys()))

    def all_answers(xpath: dict):
        return list(xpath.keys())

    if q["type"] in ["input", "text", "textarea"]:
        if q["long_response"]:
            answer = "This is a great opportunity for me."
        elif "salary" in q["question_text"].lower():
            answer = "60000"
        else:
            answer = "Yes"

    if q["type"] == "dropdown":
        answer = smart_answer(q["xpath"]) or first_answer(q["xpath"])
    if q["type"] == "radio":
        answer = smart_answer(q["xpath"]) or first_answer(q["xpath"])
    if q["type"] == "checkbox":
        answer = smart_answer(q["xpath"]) or all_answers(q["xpath"])
    if q["type"] == "file":
        answer = None
    # if q["type"] == "number":
    #     answer = 3
    if q["type"] == "date":
        answer_ = datetime.date.today() + datetime.timedelta(days=7)
        answer = answer_.strftime(guess_required_date_format(q["question_text"]))

    q["answer"] = answer
    return q


def check_url_redirect(driver, wait, load_url, target_url=None):
    if target_url is None:
        target_url = load_url
    try:
        driver.get(load_url)
        wait.until(EC.url_contains(target_url.strip()))
    except TimeoutException:
        # target_url = target_url.replace("http", "https")
        # if target_url == driver.current_url:
        #     return None
        # else:
        msg = f'Loading of the desired url: "{target_url}" failed'
        logger.warning(msg)
        return {"status": "error", "message": msg}


def aq_results(questions: List[Any], cover_letter_required: bool = False):
    class PydanticJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, BaseModel):
                return o.dict()
            return super().default(o)

    data = {
        "questions": json.loads(json.dumps(questions, cls=PydanticJSONEncoder)),
        "cover_letter_is_required": cover_letter_required,
    }
    return data


def remove_all_events_from_page(
    driver: WebDriver,
    event_type: str,
):
    _script = f"""
    typeof(getEventListeners(document).blur)!='undefined' && 
    getEventListeners(document).{event_type}.forEach(function (value) {{
      document.removeEventListener('{event_type}', value.listener,"true")
    }})
    """
    driver.execute_script(_script)
    return


def wait_for_xpath_presence(*, driver, xpath, timeout=10) -> Union[WebElement, None]:
    """
    Wait for element to be present
    :param driver:
    :param xpath:
    :param timeout:
    :return:
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
    except TimeoutException:
        logger.info(f"Timed out waiting for element to be present : {xpath}")
        return None
    return element


def wait_for_selector_presence(
    *, driver, selector, timeout=10, shadow_root=None
) -> None:
    """
    Wait for element to be present
    :param driver:
    :param xpath:
    :param timeout:
    :return:
    """
    end_time = time.time() + timeout
    if shadow_root:
        while True:
            element = driver.execute_script(
                "return arguments[0].shadowRoot.querySelector(arguments[1]);",
                shadow_root,
                selector,
            )
            if element:
                return element
            if time.time() > end_time:
                break
            time.sleep(0.5)
        return None

    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        logger.info(f"Timed out waiting for element to be present : {selector}")
        return None
    return element


def open_url_with_timeout(*, driver, url, page_load_timeout: int = 60) -> None:
    """
    Open the url. Always use this function to open the url.
    """
    driver.set_page_load_timeout(page_load_timeout)
    try:
        driver.get2(url)
    except selenium.common.exceptions.TimeoutException:
        logger.warning(
            f"Couldn't load page {url} in time. It's taking too long... Network issues maybe? Or Javascript heavy website?"
        )
    return
