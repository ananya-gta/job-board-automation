import json

# from ats.common.ats_utils import initialize_webdriver
from ats.common.types_ import CookieKey, Cookies, CookiesDict
from ats.template import template as ats_impl

# from ats.careerbuilder.careerbuilder import utils
from ats.template.template import utils

cookie_key = "ziprecruiter_cookies"


def main(apply_url):
    with open("aq_cookies.json") as f:
        _cookie = f.read()

    dummy_creds_store = CookiesDict({CookieKey(cookie_key): Cookies(_cookie)})
    aq = ats_impl.additional_questions(
        apply_url=apply_url,
        dummy_creds_store=dummy_creds_store,
        cookie_key=f"{cookie_key}",
    )
    with open("questions.json", "w") as f:
        json.dump(aq["questions"], f, indent=2)
    return aq


if __name__ == "__main__":
    # apply_url = 'https://www.ziprecruiter.com/k/t/AAJuWBJqmI6YwvORyX4yngPiecf6pe9tHENWIfykM9iMxNZmX8jxIU926TMs-NYJ0lHsc-W0VqD5lQGyQoKYho3GhcTplrONolux898ONrhmqF52N769fZGqeWAIoqdQPMVxQnhd3Qj0aKcvJ6uEO6gPjOgEDijejztn8EieFh9Dzw8_OQyvVQdXzm3HBZ5BF8ULHd-Fq-amGh0YArp3IHhLOUQw-S6gQsVu9vih73_k807BOhZWYrgOxcjMYrfAdrY9dbgYgkFXDr51V2okNOMHJPZZN8erZIdIBGCUz3sdOW-WMr1UcQnY0mAy'
    # apply_url = 'https://www.ziprecruiter.com/c/PEAK-Technical-Staffing-USA/Job/Sr.-Software-Engineer-(Level-3)/-in-Chandler,AZ?jid=51e59ab1824d22d1&lvk=7nN8Ie52SkfuzsJq-_3reg.--MmTaUZvb7'
    apply_url = "https://www.ziprecruiter.com/k/t/AAIOsrjAhJcolDIAI8PyOJoz6Hq_IuQ0fFyC_8v4ja99CAv2wF4NlzB6WZgJ2ItSNAKafqx3Pptc9vkg_JRHWCGVSpxNAJ0KCcE3fnnt49iFLds7CI_Rn5MdFGTgzG2UnLiMeoUVB7DVrmlM9Vytjojc2kupLc5qPf17ax69t76uStPvZR_zg3PbUOqaJTEkr-dmpz6gN4Tr7S11NUAVWBWh4Hfd1Px4wXTkSdlbVQZ5YoTptOZyBgqOQae29UDDhSTubsj0_XQDN2BJB2k3qT3M56Xrn7mwpwSs8Mzu5uH9lBRYEccMnALdE2u2dhjGN84FWGg"
    main(apply_url)
