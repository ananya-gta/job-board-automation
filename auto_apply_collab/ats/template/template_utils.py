import itertools
import json
import logging
import re
import time
import traceback
import urllib.parse
from collections import defaultdict
from functools import lru_cache
from typing import Dict, List, Union

import requests
import selenium.common.exceptions

# from celery.bin import celery
# from celery.utils.log import get_task_logger
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ats.common import ats_common_utils as ats_utils

# from ats.ats_utils import dump_cookies
from ats.common.exceptions_ import (
    AtsApplyException,
    AtsApplyStatusFailedAsPerCheckException,
    AtsAQException,
    AtsException,
    AtsExpiredException,
    AtsLoginException,
    AtsPageNotChangingException,
    AtsPageNumException,
    AtsPageQuestionNotPresentException,
)
from ats.common.models_ import AdditionalAnswers, AdditionalQuestion, AQType
from ats.common.types_ import (
    CookieKey,
    Cookies,
    CookiesDict,
    CurrentPage,
    JobApplication,
    TotalPages,
    Xpath,
    XpathDict,
)
from ats.template import store

# logger = get_task_logger(__name__)
logger = logging.getLogger(__name__)

PROFILE_URL: str = "https://www.ziprecruiter.com/profile"
login_url: str = "https://www.ziprecruiter.com/authn/login"
cookie_url: str = "https://www.ziprecruiter.com/authn/login/404"
secure_page_url: str = "https://www.ziprecruiter.com/candidate/settings"


def login_password_and_dump_cookies(driver):
    """
    Login with username and password and dump the cookies to a file.
    Saves a lot of time on local development.
    ("AQ" is shorthand for "Addition Questions")

    We create two cookies files:
    1. aq_cookies.json: This is the cookies file for the fetching the additional questions
    2. apply_cookies.json: This is the cookies file for the applying the job

    We use different cookies files because sometimes the accounts used for fetching the additional questions
    can not be used for applying the job.

    """
    aq_credentials = {"email": "achopra2405@gmail.com", "password": "Hello_World05"}
    apply_credentials = {"email": "asmita@hicounselor.com", "password": "asmi1234"}

    def user_login(_credentials):
        wait = WebDriverWait(driver, 10)

        def stay_signedin():
            # Code here
            pass

        driver.get(login_url)

        # CAPTCH SOLVE IT MANUALLY
        # input('If Captcha showed up solve it here and press enter to continue')

        # time.sleep(5)
        input_username = driver.find_element(By.XPATH, store.login_username_xpath)
        if input_username:
            input_username.send_keys(_credentials["email"])
        input_password = driver.find_element(By.XPATH, store.login_password_xpath)
        if input_password:
            input_password.send_keys(_credentials["password"])
        # stay_signedin()
        wait.until(
            EC.presence_of_element_located((By.XPATH, store.login_button_xpath))
        ).click()

    def clear_cookies():
        driver.get(cookie_url)
        driver.delete_all_cookies()
        driver.get(login_url)
        driver.delete_all_cookies()
        driver.get(secure_page_url)
        driver.delete_all_cookies()

        driver.get(login_url)
        time.sleep(20)
        cookies = driver.get_cookies()
        driver.refresh()

    def _save_cookies(driver, filename):
        time.sleep(7)

        _cookies = ats_utils.dump_cookies(driver, url=cookie_url, filter_fn=None)
        with open(filename, "w") as f:
            f.write(_cookies)
        # save_cookies_by_env(_cookies, filename)

    def generate_cookies():
        # AQ cookies
        user_login(aq_credentials)
        logged_in = is_logged_in(driver)
        # stay_signedin()
        _save_cookies(driver, "aq_cookies.json")
        clear_cookies()
        time.sleep(10)

        logged_in = is_logged_in(driver, raise_exception=False)
        if not logged_in:
            pass
        else:
            raise AtsException("Should not be logged in.")

        # Apply cookies
        user_login(apply_credentials)
        logged_in = is_logged_in(driver)
        # stay_signedin()
        _save_cookies(driver, "apply_cookies.json")
        clear_cookies()
        return True

    generate_cookies()
    return True


@lru_cache(maxsize=None)
def _get_unique_id(url):
    """
    Parse url for job id
    >>> url = r'https://www.ziprecruiter.com/k/t/AAI_nSVWvO-eXJA-n-Y9ehZxYFgmxkO5oOMm1cspyX6ce2qZj56XemqiygRU6L3r2ZjgM0f7yZCiVS7E5ISk5wgQwUgRNlKylb_nXqLW3uajK06FmmlHG9tKkJyOzaZ92KewvHx9TaqwgxNI6iywIaxGQacOBYXxSxsnTUDEGziH-OKTRMiXVQRaeSQ2ynOQDHtAGg9AvZYBkMTX1Dy0TpsJxCUlRJJ4G5X5lQ1vJdE3BxqG10L6660VVZfeOpW1rguO3ZczkHc6lZU_8PGkGKxgV_a6D5ycdQ-926ftR847iYDnY4Uhj6Uapy0jwnI-0BB46ZQnuOBMOHGpz9kF1BiAX0DH5YLzrmq2R-QeV38bDtG4YwjVHSIN'
    >>> _get_unique_id(url)
    '057cee74'
    >>> url = r'https://www.ziprecruiter.com/jobs/057cee74'
    >>> _get_unique_id(url)
    '057cee74'
    >>> url = r'https://www.ziprecruiter.com/jobs/resiliency-llc-f1ca7a4d/senior-software-engineer-i-java-data-structures-and-algorithms-knowledge-057cee74'
    >>> _get_unique_id(url)
    '057cee74'
    >>> url = r'http://ziprecruiter.com/jobs/jobot-9cb907eb/senior-software-engineer-847f873c'
    >>> _get_unique_id(url)
    '847f873c'
    >>> url = r'https://www.ziprecruiter.com/c/PEAK-Technical-Staffing-USA/Job/Sr.-Software-Engineer-(Level-3)/-in-Chandler,AZ?jid=51e59ab1824d22d1&lvk=7nN8Ie52SkfuzsJq-_3reg.--MmTaUZvb7'
    >>> _get_unique_id(url) # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    Exception: Could not find supported url. hence could not get unique id.
    """
    # http://ziprecruiter.com/jobs/jobot-9cb907eb/senior-software-engineer-847f873c
    # http://ziprecruiter.com/job/9cb907eb
    # https://www.ziprecruiter.com/k/t/AAI_nSVWvO-eXJA-n-Y9ehZxYFgmxkO5oOMm1cspyX6ce2qZj56XemqiygRU6L3r2ZjgM0f7yZCiVS7E5ISk5wgQwUgRNlKylb_nXqLW3uajK06FmmlHG9tKkJyOzaZ92KewvHx9TaqwgxNI6iywIaxGQacOBYXxSxsnTUDEGziH-OKTRMiXVQRaeSQ2ynOQDHtAGg9AvZYBkMTX1Dy0TpsJxCUlRJJ4G5X5lQ1vJdE3BxqG10L6660VVZfeOpW1rguO3ZczkHc6lZU_8PGkGKxgV_a6D5ycdQ-926ftR847iYDnY4Uhj6Uapy0jwnI-0BB46ZQnuOBMOHGpz9kF1BiAX0DH5YLzrmq2R-QeV38bDtG4YwjVHSIN
    # https://www.ziprecruiter.com/c/Jobot/Job/Senior-Software-Engineer/-in-Palo-Alto,CA?jid=777cb0a80f835a48
    basic_supported_url_start = "https://www.ziprecruiter.com/job"

    # _parsed_url = urllib.parse.urlparse(url)
    # _path = _parsed_url.path.split('/')
    # if len(_path[1]) <= 3:  # generally it is either k/c/ek e.g. ziprecuriter.com/k/ or ziprecuriter.com/c/
    #     job_application = {'apply_url': url}
    #     is_expired = is_job_expired(driver, job_application)
    #     if is_expired:
    #         raise Exception('Job has expired .')
    #     else:
    #         _parsed_url = urllib.parse.urlparse(resp.url)

    def get_job_id(supported_url):
        _parsed_url = urllib.parse.urlparse(supported_url)
        path = _parsed_url.path.split("/")
        if path[1] == "job":
            return path[-1]
        elif path[1] == "jobs":
            return _parsed_url.path.split("/")[-1].split("-")[-1]
        raise AtsException(
            f"Could not get unique id. Even though it is a valid url.{supported_url}"
        )

    if url.startswith(basic_supported_url_start):
        # _parsed_url = urllib.parse.urlparse(url)
        return get_job_id(url)
    else:
        resp = requests.get(url)
        possible_urls = [resp.url, *[h.url for h in resp.history]]
        supported_urls = [
            u for u in possible_urls if u.startswith(basic_supported_url_start)
        ]
        if len(supported_urls) == 0:
            raise AtsException(
                "Could not find supported url. hence could not get unique id."
            )
        # _parsed_url = urllib.parse.urlparse(supported_urls[0])
        return get_job_id(supported_urls[0])


def get_unique_id(url) -> str:
    """
    >>> url = r'https://www.ziprecruiter.com/ek/t/AAKweUJR-rJgrR7TrmHeM-iHFK37_UzfThfcjM4ADdC16qPR7pXMxn-56O1dRp1X1oEnbUYieh7KkkEIkbMBd7iY3n8dNsQ0BYop3mxQhHLta7VwzjYI26fth2-gsQ3Qg_S3vEkeNhzWUk7eXFeIM54BU-j4NQATyV6SysDnsvh4z4N7EPgJKskDr8m-1STcn7j4qHUkSS4JFJ8L2eN0AK-Wrogwn46m6IJLdGEQMI9rHBoiXlk38mHfGlDmTOnOI6gHQi1AHPcCxcmpxgm51kNXELLMH_bqqLJiI1LKC4hknm5AZwNv3UydRi-fc4bkv97hJQ1277D65AYj1EsQJ8oC7O2eFFLuoQXspVDb0Cu2q8fgsbqp3qhFsnWoStaL8R24qVCi0ELteUt_Ak7A0xO3u7t84ruRPnFSjaBPpJ3roCfQU5poA8BFh-XAn7EoCWaQpiUpMDV5JTBMzp'
    >>> get_unique_id(url)
    'wo_uid'
    """
    try:
        return _get_unique_id(url)
    except requests.exceptions.RequestException:
        raise
    except:
        return "wo_uid"


@lru_cache()
def get_standard_url(url):
    _job_id = _get_unique_id(url)

    def convert(job_id):
        return f"https://www.ziprecruiter.com/job/{job_id}"

    standard_url = convert(_job_id)
    return standard_url


def is_last_page(current_page, total_page):
    return current_page == total_page


def skip_questions(driver, current_page, total_page, apply_flow: bool) -> (bool, bool):
    """
    :return: True if the questions are skipped. False otherwise.
    """
    is_skip_able = False
    is_last = is_last_page(current_page, total_page)
    skip_button_ = skip_button(driver)
    # skip button is present
    if skip_button_:
        is_skip_able = True
        # Press skip button on the page as long it is not last page. We don't want to apply on last page.
        if is_last and not apply_flow:
            return False, is_skip_able
        else:
            logger.info("Skipping questions on page = %s", current_page)
            click_button(driver, skip_button_)
            return True, is_skip_able
    # skip button is not present
    return False, is_skip_able


def page_nums(driver) -> (CurrentPage, TotalPages):
    """
    Generator function to get the current page number and total page number.
    Read more about generator function here: https://wiki.python.org/moin/Generators
    or here: https://www.programiz.com/python-programming/generator
    or here: https://realpython.com/introduction-to-python-generators/
    or here : https://www.geeksforgeeks.org/generators-in-python/

    Return the number of current page and total pages.
    1st page with additional questions is page 1.
    2nd page with additional questions is page 2.
    and so on.

    Every question will have a page number.
     Example,
        page = 1 (for all additional questions in 1st page),
        page = 2 (for all additional questions in 2nd page)
        and so on.
    """
    wait = WebDriverWait(driver, 10)
    previous_page = None
    while True:
        try:
            time.sleep(2)
            question_progress = wait.until(
                EC.presence_of_element_located((By.XPATH, store.page_num_xpath))
            ).text

            # Regex logic to get page number and total pages.
            regex = r"[\d]+"
            matches = list(re.finditer(regex, question_progress))
            current_page, total_pages = list(map(lambda x: int(x.group()), matches))

            # If the current page is same as previous page, meaning we are stuck on the same page. Raise exception.
            if previous_page == current_page:
                raise AtsPageNotChangingException("Page number is not changing.")
            yield current_page, total_pages

            # Only way to exit gracefully. Every other way will raise an exception.
            if current_page == total_pages:
                break

            # Saving current page for next iteration.
            previous_page = current_page

        # We did not find the question progress bar. And we are not on the last page.
        # How can I tell? because we did not exit gracefully in the previous if statement. So we are not on the last page.
        except (NoSuchElementException, TimeoutException) as e:
            logger.info(
                "Could not find question progress bar. "
                "Assuming job had no additional questions. or question screen is not loaded yet."
            )
            raise AtsPageQuestionNotPresentException(
                "Could not find page number."
            ) from e


def multistage_common(
    driver, job_application, wait, apply_flow: Union[bool, None] = None
):
    open_job_apply_url(driver, job_application)
    _easyapply_button = easyapply_button(driver)
    if _easyapply_button:
        click_button(driver, easyapply_button(driver))
    bypass_prescreening_questions(driver)
    fill_primary_q(driver, job_application)


def multistage_apply(driver, job_application, wait):
    multistage_common(driver, job_application, wait)

    all_page_answers: List[AdditionalAnswers] = [
        AdditionalAnswers.parse_obj(q_wa)
        for q_wa in job_application["additional_questions"]
    ]
    answers_grouped_by_page: Dict[int, List[AdditionalAnswers]] = group_answers_by_page(
        all_page_answers
    )

    if len(answers_grouped_by_page) == 0:
        logger.warning(
            "No additional questions/answer found in job_application. "
            "Are all questions skip-able? Or maybe there are no additional questions? Hope so."
        )

    try:
        for current_page, total_pages in page_nums(driver):
            is_skipped, _ = skip_questions(
                driver, current_page, total_pages, apply_flow=True
            )
            if is_skipped:
                continue
            answers_current_page = answers_grouped_by_page.get(current_page, [])
            fill_additional_q(driver, answers_current_page)
            # We want to submit the application on the last page. So unlike additional questions, we click every time.
            click_button(driver, continue_button(driver))
    except AtsPageNotChangingException as e:
        logger.error(
            "Page number is not changing. Probably unable to fill answer."
            "Please check the answers and try again."
        )
        raise e
    except AtsPageQuestionNotPresentException as e:
        if len(answers_grouped_by_page) == 0:
            logger.info("My bet is on this job had no additional questions. ")
        else:
            logger.error(
                "As I have additional questions, I am assuming the question screen is not loaded yet. So driver threw error"
            )
            raise e
    return


def has_additional_questions(
    driver: WebDriver, job_application: JobApplication
) -> bool:
    """
    One way to check is if job was applied after easy apply button was clicked.
    """
    is_applied = is_job_already_applied(driver=driver, job_application=job_application)
    if is_applied:
        return False
    else:
        return True


def multistage_additional_questions(
    driver, job_application: JobApplication, wait
) -> List[AdditionalQuestion]:
    def generate_answers(
        questions_of_current_page: List[AdditionalQuestion],
    ) -> List[AdditionalAnswers]:
        if not questions_of_current_page:
            return []
        questions_of_current_page_json = [
            question.dict() for question in questions_of_current_page
        ]
        answers_current_page_json = auto_generate_answers(
            questions_of_current_page_json
        )
        answers_current_page = [
            AdditionalAnswers.parse_obj(answer) for answer in answers_current_page_json
        ]
        return answers_current_page

    multistage_common(driver, job_application, wait)
    # has_aq = has_additional_questions(driver=driver, job_application=job_application)
    questions_all = []
    try:
        for current_page, total_page in page_nums(driver):
            is_last_p: bool = is_last_page(
                current_page=current_page, total_page=total_page
            )
            is_skipped, is_skip_able = skip_questions(
                driver=driver,
                current_page=current_page,
                total_page=total_page,
                apply_flow=False,
            )

            # it could be it is the last
            if is_skip_able and is_skipped:
                continue
            elif is_skip_able and not is_skipped:
                logger.info(
                    "We are not skipping questions. So we are on the last page."
                )
                if not is_last_p:
                    raise AtsAQException(
                        "Something is wrong. We are not skipping questions. "
                        "But we are not on the last page. So why are we not skipping questions?"
                    )
                else:
                    continue

            questions_of_current_page = get_question_for_single_stage(
                driver=driver, job_application=job_application, page=current_page
            )
            questions_all.extend(questions_of_current_page)
            answers_current_page = generate_answers(
                questions_of_current_page=questions_of_current_page
            )
            fill_additional_q(driver, answers_current_page)

            # In additional questions, we don't want to apply on last page.
            if not is_last_p:
                click_button(driver=driver, button=(continue_button(driver=driver)))
    except AtsPageNotChangingException as e:
        logger.error(
            "Page number is not changing. Probably unable to fill answer."
            "Please check the answers and try again."
        )
        raise e
    except AtsPageQuestionNotPresentException as e:
        logger.info(
            "Additional questions are not present. Double check by checking if job was applied."
            "If job was applied, then additional questions are not present."
        )
        if not is_job_already_applied(driver=driver, job_application=job_application):
            #     return []
            # else:
            raise e
    return questions_all


def single_stage_common(driver, job_application, wait) -> None:
    open_job_apply_url(driver, job_application)
    click_button(driver, easyapply_button(driver))
    bypass_prescreening_questions(driver)
    fill_primary_q(driver, job_application)
    return


def singlestage_apply(driver, job_application, wait) -> None:
    """ """
    click_button(driver, easyapply_button(driver))

    single_stage_common(driver, job_application, wait)
    answers: List[AdditionalAnswers] = [
        AdditionalAnswers.parse_obj(q_wa)
        for q_wa in job_application["additional_questions"]
    ]
    fill_additional_q(driver, answers)
    click_button(driver, submit_button(driver))
    return


def singlestage_additional_questions(
    driver, job_application, wait
) -> List[AdditionalQuestion]:
    """
    In case all additiona questions are in one page.
    if there are multiple pages, use _multistage_additional_questions
    All questions will have page number 0.
    page = 0 (for all additional questions)
    """
    single_stage_common(driver, job_application, wait)
    questions = get_question_for_single_stage(driver)
    return questions


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
    return ats_utils._get_answer(q)


def auto_generate_answers(questions: list):
    """
    Auto generate answers for the additional questions
    """
    return [_get_answer(q) for q in questions]


def wait_till_page_loaded(driver, job_application, *args, **kwargs):
    time.sleep(5)



def is_job_open_for_apply(
    driver: WebDriver, job_application: JobApplication, raise_exception=True
):
    """
    Check if the job is open for apply
    return True if open
    urls:
    1.
    """

    wait = WebDriverWait(driver, 10)
    #
    time.sleep(5)
    open_job_apply_url(driver, job_application)
    def check_if_redirected_to_suggested_jobs(*, driver):
        _is_redirected = driver.current_url == 'https://www.ziprecruiter.com/candidate/suggested-jobs'
        if _is_redirected:
            return True
        else:
            return False
    on_suggested_jobs_page = check_if_redirected_to_suggested_jobs(driver=driver)
    # Means Job is not open for apply must be an expired job
    if on_suggested_jobs_page:
        return False
    found = get_element_wo_exception(driver, store.should_not_exist_on_expired_xpath)
    if not found:
        if raise_exception:
            raise AtsExpiredException(job_application)
        return False
    return True



def is_job_expired(driver: WebDriver, job_application: JobApplication) -> bool:
    """
    Check if the job is expired
    return True if expired
    """
    is_expired = not is_job_open_for_apply(
        driver, job_application, raise_exception=False
    )
    return is_expired


def is_submitted_before(driver, job_application) -> bool:
    """
    Check if the job is already submitted (Probably by another bot)
    return True if submitted
    """
    try:
        already_button = WebDriverWait(driver, 2).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(@class,'pc_text_control')]")
            )
        )
    except:
        return False
    return True


def open_url_with_timeout(driver, url, page_load_timeout: int = 60) -> None:
    """
    Open the url. Always use this function to open the url.
    """
    driver.set_page_load_timeout(page_load_timeout)
    try:
        driver.get(url)
    except selenium.common.exceptions.TimeoutException:
        logger.warning(
            f"Couldn't load page {url} in time. It's taking too long... Network issues maybe? Or Javascript heavy website?"
        )


def open_job_apply_url(driver, job_application, page_load_timeout: int = 60) -> None:
    """
    Open the job apply url from job_application. Always use this function to open the job apply url.
    """
    driver.set_page_load_timeout(page_load_timeout)
    apply_url = get_standard_url(job_application["apply_url"])
    open_url_with_timeout(driver, apply_url)


# def save_cookies_by_env(_cookies, filename):
#     """
#     """
#     pass


def login_cookies(
    driver, job_application: JobApplication, cookies: CookiesDict
) -> None:
    """
    Login with cookies
    """
    try:
        _load_cookies_from_json(driver, job_application, cookies)
    except Exception as e:
        logger.error("Error loading cookies: {}".format(e))
        # login_password_and_dump_cookies(driver)
        raise AtsLoginException("Error loading cookies: {}".format(e))
    return


def _load_cookies_from_json(
    driver: WebDriver, job_application: JobApplication, cookies: CookiesDict
) -> None:
    """
    Load cookies of all websites into browser.
    For example, if you use googlr authentication to login to a website, you need to load the cookies of google.com
    and the cookies of the website you are trying to login to.
    """

    is_value_missing = any(
        [True for cookie_key, cookies in cookies.items() if (cookies is None)]
    )
    if is_value_missing:
        missing_keys = [
            cookie_key for cookie_key, cookies in cookies.items() if (cookies is None)
        ]
        msg = (
            f'Missing {missing_keys} for job_seeker: {job_application["job_seeker_id"]}'
        )
        logger.warning(msg)
        raise AtsLoginException(msg)

    for cookie_key, cookies_of_domain in cookies.items():
        cookie_key: CookieKey
        cookies_of_domain: Cookies

        try:
            ats_utils.load_cookies(driver, cookies_of_domain)
        except json.JSONDecodeError as e:
            msg = f'Invalid cookies for job_seeker: {job_application["job_seeker_id"]}'
            logger.warning(msg)
            raise json.JSONDecodeError(msg) from e


def is_logged_in(driver, raise_exception=True) -> bool:
    """
    Check if the user is logged in.
    Use secure_page_url to check if the user is logged in.
    """
    time.sleep(5)
    driver.get(secure_page_url)
    opened_url = driver.current_url

    if opened_url.startswith(secure_page_url):
        return True
    else:
        if raise_exception:
            raise AtsLoginException("Not logged in")
        return False


# def apply_for_job(driver: WebDriver, job_application: JobApplication) -> None:
#     """
#         Apply for the job.
#         This function is called after the additional questions are answered.
#
#     """
#     easyapply_button(driver).click()
#     wait_till_page_loaded(driver, job_application)
#     # Start of custom code
#     fill_primary_q(driver, job_application)
#     # if IS_MULTI_
#     # answers =
#     # fill_additional_q(driver, job_application)
#     # End of custom code
#     apply_success = is_apply_for_job_successful(driver, job_application)
#     if apply_success:
#         logger.info("Application submitted successfully")
#     else:
#         logger.info("Application submission failed")
#         raise AtsApplyException("Application submission failed")


def is_apply_for_job_successful(
    driver: WebDriver, job_application: JobApplication, raise_exception=True
) -> bool:
    """
    Check if the job is applied successfully
    """
    # is_success = driver.current_url.startswith("https://www.ziprecruiter.com/candidate/suggested-jobs"):
    is_success = is_job_already_applied(driver=driver, job_application=job_application)
    if is_success:
        return True
    else:
        if raise_exception:
            raise AtsApplyStatusFailedAsPerCheckException(
                "Application failed as per check. "
                "It might be successfully submitted as well. Reapply job to check."
            )
        return False


def get_question_for_single_stage(
    driver: WebDriver, job_application: dict, page: int
) -> List[AdditionalQuestion]:
    """
    Essentially there are only three type of tags:
    1. input
        For input, we use driver.send_keys to fill the input
    2. select
        For select, we use Select(driver.find_element_by_xpath(xpath)).select_by_value(value)
    3. textarea
        For textarea, we use driver.send_keys to fill the input

    But you can make other elements to act like input, select, textarea by using javascript.
    For example,
    1. ul or ol can be made to act like select by using javascript
    2. div can be made to act like input by using javascript
    3. div can be made to act like textarea by using javascript

    Solutions for these custom types of elements:
    1. Click on <li> in case of <ul> or <ol>
    2. set div.innerHTML = "some text"

    Using the above solutions, you can have the following types of elements:
    1. text input
    2. dropdown
    3. textarea
    4. radio button
    5. checkbox
    6. date
    7. file upload
    8. custom select
    9. custom input
    10. custom textarea
    11. custom radio button
    12. custom checkbox
    13. custom date
    14. custom file upload

    We support only these types:
        # input[type="text"] is "text"
        # input[type="radio"] is "radio"
        # input[type="checkbox"] is "checkbox"
        # input (remaining) is "input"
        # input[type="file"] is "file"
        # testarea is "textarea"
        # select is "dropdown"


    """

    def determine_type(field: WebElement) -> AQType:
        try:
            select = field.find_element(By.XPATH, ".//select")
            if select:
                return AQType.DROPDOWN
        except NoSuchElementException:
            pass
        try:
            textarea = field.find_element(By.XPATH, ".//textarea")
            if textarea:
                return AQType.TEXTAREA
        except NoSuchElementException:
            pass

        def determine_specific_input_type(field) -> AQType:
            input_tag = field.find_element(By.XPATH, store.rel_input_xpath)
            if input_tag:
                input_tag_type = input_tag.get_attribute("type")
                input_tag_class = input_tag.get_attribute("class")

                def check_for_standard_input_type():
                    if input_tag_type == "text":
                        return AQType.TEXT
                    elif input_tag_type == "radio":
                        return AQType.RADIO
                    elif input_tag_type == "checkbox":
                        return AQType.CHECKBOX
                    elif input_tag_type == "file":
                        return AQType.FILE
                    elif input_tag_type == "number":
                        return AQType.NUMBER
                    else:
                        return AQType.INPUT

                def check_for_custom_input_type():
                    if (
                        "date" not in input_tag_type.lower()
                        and "date" in input_tag_class.lower()
                    ):
                        return AQType.DATE
                    return None

                # Custom input type gets priority over standard input type
                return check_for_custom_input_type() or check_for_standard_input_type()

        try:
            return determine_specific_input_type(field)
        except NoSuchElementException:
            pass
        # Code should never reach here. If it does, it means that the element is not supported.
        raise AtsException("Unknown type")

    def handle_select_aka_dropdown(
        field: WebElement,
    ) -> Union[AdditionalQuestion, None]:
        def get_xpath_dict(field: WebElement) -> XpathDict:
            select = field.find_element(By.XPATH, store.rel_select_xpath)
            select_xpath = get_select_xpath_generic(select)
            xpath_dict = {}
            options = field.find_elements(By.XPATH, store.rel_option_xpath)[
                1:
            ]  # Ignoring the first one
            for option in options:
                xpath_dict[option.text] = select_xpath
            return XpathDict(xpath_dict)

        def get_select_xpath_generic(field: WebElement) -> Xpath:
            """
            This works when only one input_tag is present in the field.

            :param field: ancestor of select tag or the select tag itself
            """
            if field.tag_name != "select":
                select_tag = field.find_element(By.XPATH, store.rel_select_xpath)
            else:
                select_tag = field
            id_attribute = select_tag.get_attribute("id")
            generated_xpath = store.select_xpath_template.format(
                id_attribute=id_attribute
            )
            return generated_xpath

        question_text = field.find_element(By.XPATH, store.rel_question_text_xpath).text
        aq = AdditionalQuestion(
            type=AQType.DROPDOWN,
            question_text=field.find_element(
                By.XPATH, store.rel_question_text_xpath
            ).text,
            xpath=get_xpath_dict(field),
            long_response=False,
            page=page,
        )
        return aq

    def handle_textarea(field: WebElement) -> Union[AdditionalQuestion, None]:
        aq = AdditionalQuestion(
            type=AQType.TEXTAREA,
            question_text=field.find_element(
                By.XPATH, store.rel_question_text_xpath
            ).text,
            xpath=store.textarea_xpath_template.format(
                id_attribute=field.find_element(
                    By.XPATH, store.rel_textarea_xpath
                ).get_attribute("id")
            ),
            long_response=False,
            page=page,
        )
        return aq

    def handle_input(
        field: WebElement, aq_type: AQType
    ) -> Union[AdditionalQuestion, None]:
        def get_question_text(field: WebElement) -> str:
            basic = field.find_element(By.XPATH, store.rel_question_text_xpath).text
            if aq_type in (AQType.DATE, AQType.NUMBER):
                extra = field.find_element(
                    By.XPATH, store.rel_input_xpath
                ).get_attribute("placeholder")
                if extra:
                    extra_ = extra.strip("( )")
                    return basic + f" ({extra_})"
            return basic

        def get_xpath_dict_radio(field: WebElement) -> XpathDict:
            input_tags = field.find_elements(By.XPATH, store.rel_input_xpath)
            xpath_dict = {}
            for input_tag in input_tags:
                generated_xpath = store.input_xpath_template.format(
                    id_attribute=input_tag.get_attribute("id")
                )
                display_value = driver.execute_script(
                    "return arguments[0].closest('label')", input_tag
                ).text
                xpath_dict[display_value] = generated_xpath

            return XpathDict(xpath_dict)

        def get_xpath_dict_checkbox(field: WebElement) -> XpathDict:
            input_tags = field.find_elements(By.XPATH, store.rel_input_xpath)
            xpath_dict = {}
            for input_tag in input_tags:
                generated_xpath = get_input_xpath_generic(input_tag)
                display_value = driver.execute_script(
                    "return arguments[0].closest('label')", input_tag
                ).text
                xpath_dict[display_value] = generated_xpath

            return XpathDict(xpath_dict)

        def get_input_xpath_generic(field: WebElement) -> Xpath:
            """
            This works when only one input_tag is present in the field.
            """
            if field.tag_name != "input":
                input_tag = field.find_element(By.XPATH, store.rel_input_xpath)
            else:
                input_tag = field
            id_attribute = input_tag.get_attribute("id")
            generated_xpath = store.input_xpath_template.format(
                id_attribute=id_attribute
            )
            return generated_xpath

        def generate_xpath_for_input(field: WebElement) -> Union[Xpath, XpathDict]:
            xpath_dict, xpath_ = None, None

            if aq_type == AQType.RADIO:
                xpath_dict = get_xpath_dict_radio(field)
            elif aq_type == AQType.CHECKBOX:
                xpath_dict = get_xpath_dict_checkbox(field)
            elif aq_type in [AQType.DATE, AQType.INPUT]:
                xpath_ = get_input_xpath_generic(field)

            if not xpath_dict and not xpath_:
                raise AtsException(
                    "XpathDict and xpath_ is empty. This should not be happening."
                )

            is_xpath_dict_needed = aq_type in [AQType.RADIO, AQType.CHECKBOX]
            return XpathDict(xpath_dict) if is_xpath_dict_needed else Xpath(xpath_)

        xpath_ = generate_xpath_for_input(field)
        questions_text = get_question_text(field)
        aq = AdditionalQuestion(
            type=aq_type,
            question_text=questions_text,
            xpath=xpath_,
            long_response=False,
            page=page,
        )
        return aq

    # Not using find_elements because expecting a single element.
    field = get_element_wo_exception(driver, store.fields_xpath)
    aq_type = determine_type(field)
    if aq_type == AQType.DROPDOWN:
        return [handle_select_aka_dropdown(field)]
    elif aq_type == AQType.TEXTAREA:
        return [handle_textarea(field)]
    else:
        return [handle_input(field, aq_type)]


def fill_primary_q(driver, job_application):
    pass


def group_answers_by_type(
    answers: List[AdditionalAnswers],
) -> Dict[AQType, List[AdditionalAnswers]]:
    grouped_answers = defaultdict(list)
    for answer in answers:
        grouped_answers[answer.type].append(answer)
    return grouped_answers


def group_answers_by_page(
    answers: List[AdditionalAnswers],
) -> Dict[int, List[AdditionalAnswers]]:
    grouped_answers = defaultdict(list)
    for answer in answers:
        grouped_answers[answer.page].append(answer)
    return grouped_answers


def fill_additional_q(driver, answers: List[AdditionalAnswers]):
    wait = WebDriverWait(driver, 10)

    def fill_date(driver, answer: AdditionalAnswers):
        xpath = answer.xpath
        driver.find_element(By.XPATH, xpath).send_keys(answer.answer)

    answers_grouped_by_type = group_answers_by_type(answers)

    date_qanswers = answers_grouped_by_type.pop(AQType.DATE, [])
    if date_qanswers:
        for answer in date_qanswers:
            fill_date(driver, answer)
    # Read more here: https://www.geeksforgeeks.org/python-itertools-chain/
    remaining_qanswers = itertools.chain.from_iterable(answers_grouped_by_type.values())
    [
        ats_utils.fill_additional_q(q_wa.dict(), driver, wait)
        for q_wa in remaining_qanswers
    ]


def bypass_prescreening_questions(driver):
    """
    Bypasses prescreening questions. These q do not require candidate input so answer can be hardcoded.
    Generally called after clicking easyapply or after filling primary questions.
    """
    pass


def is_job_already_applied(driver: WebDriver, job_application: JobApplication) -> bool:
    """
    Check if the job is already applied.
    """
    wait = WebDriverWait(driver, 2)
    open_job_apply_url(driver, job_application)
    try:
        field = ats_utils.wait_for_xpath_presence(driver=driver, xpath=store.fields_xpath, timeout=10)
        if field:
            logger.info("Job is not already applied. There are few questions to answer.")
            return False
        already_button = wait.until(
            EC.presence_of_element_located((By.XPATH, store.already_applied_xpath))
        )
    except:
        return False
    return True


def get_element_wo_exception(driver, xpath, wait: WebDriverWait = None, timeout=None):

    timeout = timeout if timeout else wait._timeout if wait else None

    if timeout is not None:
        ats_utils.wait_for_xpath_presence(driver=driver, xpath=xpath, timeout=timeout)
    try:
        return driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return None


def apply_button(driver, job_application):
    elm = get_element_wo_exception(store.next_button_xpath)
    return elm


def next_button(driver, raise_error=True) -> Union[WebElement, None]:
    """
    Return the next button element.
    """
    wait = WebDriverWait(driver, 10)
    try:
        next_button = wait.until(
            EC.presence_of_element_located((By.XPATH, store.next_button_xpath))
        )
    except TimeoutException as e:
        if raise_error:
            raise TimeoutException("Next button not found") from e
        else:
            return None
    return next_button


def submit_button(driver) -> WebElement:
    pass


def easyapply_button(driver: WebDriver) -> WebElement:
    elm = get_element_wo_exception(driver, store.easyapply_button_xpath)
    return elm


def continue_button(driver: WebDriver) -> WebElement:
    elm = get_element_wo_exception(driver, store.continue_button_xpath)
    return elm


def skip_button(driver: WebDriver) -> WebElement:
    elm = get_element_wo_exception(driver, store.skip_button_xpath)
    return elm


def click_button(driver, button: WebElement) -> None:
    """
    Check if button is present and is clickable.Then click it.
    """
    if button:
        try:
            button.click()
        except selenium.common.exceptions.ElementClickInterceptedException as e:
            # This is a hack to click the button when it is not clickable.
            # This happens when the button is not visible on the screen.
            driver.execute_script("arguments[0].click();", button)
    else:
        raise AtsException("Button not found")
