"""
Login using cookies and apply to a job posting.
"""
import json
import time

from ats.common.ats_common_utils import initialize_webdriver
from ats.common.types_ import CookieKey, Cookies, CookiesDict
from ats.template import template
from ats.template.template import utils

FAKE_APPLICATION = {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "8084385352",
    "resume_path": f"dummy.pdf",
    "cover_letter_text": "This is a cover letter",
    "email": "test@gmail.com",
}


def main(apply_url):
    with initialize_webdriver() as driver:
        job_url = apply_url
        standard_url = utils.get_standard_url(job_url)
        print(f'{standard_url}')
        with open("apply_cookies.json") as f:
            cookies = {CookieKey("additional_cookies"): Cookies(f.read())}
        with open("answers.json") as f:
            answers = json.load(f)
        application = {
            **FAKE_APPLICATION,
            **{"additional_questions": answers},
            **{"apply_url": standard_url},
        }
        result = template.apply(
            driver, application, CookiesDict(cookies), template.utils.PROFILE_URL
        )
        return result


if __name__ == "__main__":
    apply_url = "https://www.ziprecruiter.com/k/l/AAI3cQzkffapUzQkyamgpHlD0SGagr4FcH0c_hlimb-FV-nfzjc-28XE_wMgC32_A_ebkkxMkYrwGht590fz4WdnUY3NfI4WED02hZlft-NifedPQ7PQ5P7MCOjOOsFYSempSvy-Fvamj9Fv-lyt8a_qs4Hf4h3axJQwJhoryA-X73XKlDfsOIiwBbJZU1vv?apply=yes"
    output = main(apply_url)
    print(output)
