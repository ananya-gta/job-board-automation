# import ats.__tweaks__

import traceback
from typing import Dict, List, Union

# from celery.utils.log import get_task_logger
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

# import config
# from ats import ats_utils
from ats.common.exceptions_ import *
from ats.common.models_ import AdditionalQuestion
from ats.common.types_ import CookieKey, Cookies, CookiesDict, JobApplication
# from config import FAKE_APPLICATION

from . import template_utils as utils
from .describe import ADDITIONAL_QUESTIONS, IS_ADDITIONAL_QUESTIONS_MULTI_STAGE, LOGIN
from ats.common.ats_common_logger import get_task_logger
from ats.common import ats_common_utils as ats_utils, config

logger = get_task_logger(__name__)


def _cross_concerns_common(driver: WebDriver, job_application, cookies: CookiesDict):
    if LOGIN:
        utils.login_cookies(driver, job_application, cookies)
        logged_in = utils.is_logged_in(driver)
        if not logged_in:
            raise AtsLoginException("Login failed")
    is_expired = utils.is_job_expired(driver, job_application)
    if is_expired:
        logger.info("Job posting is expired")
        raise AtsExpiredException("Job posting is expired")
    # utils.open_job_apply_url(driver, job_application)
    is_already_applied = utils.is_job_already_applied(driver, job_application)
    if is_already_applied:
        logger.info("Job already applied")
        raise AtsAlreadyAppliedException("Job already applied")
    return


def _cross_concerns_apply(
    driver: WebDriver, job_application: JobApplication, cookies: CookiesDict
):
    _cross_concerns_common(driver, job_application, cookies)


def _cross_concerns_additional_questions(
    driver: WebDriver, job_application: JobApplication, cookies: CookiesDict
):
    _cross_concerns_common(driver, job_application, cookies)


# @apply_adapter()
def apply(driver, job_application, cookies: CookiesDict, profile_url):
    try:
        wait = WebDriverWait(driver, 15)
        try:
            _cross_concerns_apply(driver, job_application, cookies)
        except AtsLoginException as e:
            msg = f"Login failed: {e}"
            return ats_utils.apply_error_status(msg)
        except AtsExpiredException as e:
            msg = f"Job posting is expired: {e}"
            return ats_utils.apply_error_status(msg)
        except AtsAlreadyAppliedException as e:
            msg = f"Job already applied: {e}"
            return ats_utils.apply_success_status(msg)

        # utils.apply_for_job(driver, job_application)
        if ADDITIONAL_QUESTIONS and IS_ADDITIONAL_QUESTIONS_MULTI_STAGE:
            utils.multistage_apply(driver, job_application, wait)
        else:
            utils.singlestage_apply(driver, job_application, wait)

        apply_success = utils.is_apply_for_job_successful(driver, job_application)
        if apply_success:
            logger.info("Application submitted successfully")
            pass
        else:
            logger.info("Application submission failed")
            raise AtsApplyException("Application submission failed")
    except AtsException as e:
        _message = traceback.format_exc(limit=config.TRACEBACK_LIMIT)
        logger.warning(_message)
        return ats_utils.apply_error_status(str(e) + _message)
    except Exception as e:
        _message = traceback.format_exc(limit=config.TRACEBACK_LIMIT)
        logger.error(_message)
        return ats_utils.apply_error_status(str(e) + _message)

    msg = f"Successfully applied to job posting: {job_application['apply_url']}"
    return ats_utils.apply_success_status(msg)


# @additional_questions_adapter(ats_name=ATS_NAME)
def additional_questions(
    apply_url: str, dummy_creds_store: CookiesDict, cookie_key
) -> Dict[Union[str, List[AdditionalQuestion]], Union[str, List[AdditionalQuestion]]]:
    """
    Fetch Additional Questions from the job posting.
    """

    def fake_application() -> JobApplication:
        d = {
            "job_id": -1,
            "city": "Fake City",
            "state": "Fake State",
            "current_company": "Fake Company",
            **config.FAKE_APPLICATION,
            "apply_url": apply_url,
        }
        return JobApplication(d)

    def get_cookies() -> CookiesDict:
        d = {
            CookieKey("additional_cookies"): Cookies(
                dummy_creds_store.get(cookie_key, {})
            )
        }
        return CookiesDict(d)

    cookies = get_cookies()
    job_application = fake_application()

    if not ADDITIONAL_QUESTIONS:
        return ats_utils.aq_empty_list()

    try:
        with ats_utils.initialize_webdriver() as driver:
            wait = WebDriverWait(driver, 15)
            _cross_concerns_additional_questions(driver, job_application, cookies)
            if ADDITIONAL_QUESTIONS and IS_ADDITIONAL_QUESTIONS_MULTI_STAGE:
                return ats_utils.aq_results(
                    questions=utils.multistage_additional_questions(
                        driver, job_application, wait
                    )
                )
            elif ADDITIONAL_QUESTIONS and not IS_ADDITIONAL_QUESTIONS_MULTI_STAGE:
                return ats_utils.aq_results(
                    questions=utils.singlestage_additional_questions(
                        driver, job_application, wait
                    )
                )

    except AtsException as e:
        _message = traceback.format_exc(config.TRACEBACK_LIMIT)
        logger.warning(_message)
        return ats_utils.aq_error_status(str(e) + _message)
    except Exception as e:
        _message = traceback.format_exc(config.TRACEBACK_LIMIT)
        logger.error(_message)
        return ats_utils.aq_error_status(str(e) + _message)
