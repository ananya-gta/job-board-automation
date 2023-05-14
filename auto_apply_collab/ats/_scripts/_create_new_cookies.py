import logging

from ats._scripts.describe import ATS_NAME
from ats.common._ats_config import search_ats
from ats.common.ats_common_utils import initialize_webdriver

logging.basicConfig(level=logging.DEBUG)


def main():
    # ats_impl = importlib.import_module('ats.resumelibrary.resumelibrary')
    ats_impl = search_ats(ATS_NAME)
    with initialize_webdriver() as driver:
        ats_impl.utils.login_password_and_dump_cookies(driver)


if __name__ == "__main__":
    main()
