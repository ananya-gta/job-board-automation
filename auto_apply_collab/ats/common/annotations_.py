from functools import wraps

from ats.common.types_ import CookieKey
from ats.common.utils import get_cookie_key
from .config import DUMMY_USER_CREDS


def template_to_prod_aq_adapter(ats_name: str):
    cookie_key = CookieKey(get_cookie_key(ats_name))

    def decorator(func):
        @wraps(func)
        def wrapper(apply_url: str):
            return func(
                apply_url=apply_url,
                dummy_creds_store=DUMMY_USER_CREDS,
                cookie_key=cookie_key,
            )

        return wrapper

    return decorator


def template_to_prod_apply_adapter():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            job_application = kwargs.pop("app", None)
            kwargs["job_application"] = job_application
            return func(*args, **kwargs)

        return wrapper

    return decorator
