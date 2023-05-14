class AtsException(Exception):
    """Base class for all ATS exceptions."""

    pass


class AtsLoginException(AtsException):
    """Raised when login fails."""

    pass


class AtsExpiredException(AtsException):
    """Raised when job posting is expired."""

    pass


class AtsAlreadyAppliedException(AtsException):
    """Raised when job posting is already applied to for the current user."""

    pass


class AtsCaptchaException(AtsException):
    """Raised when captcha solver fails."""

    pass


class AtsAQException(AtsException):
    """Raised when additional questions parsing fails."""

    pass


class AtsApplyException(AtsException):
    """Raised when apply fails."""

    pass


class AtsApplyStatusFailedAsPerCheckException(AtsApplyException):
    """Raised when apply fails."""

    pass


class AtsPageNumException(AtsException):
    """Raised when page number parsing fails."""

    pass


class AtsPageQuestionNotPresentException(AtsPageNumException):
    """Raised when question page not found."""

    pass


class AtsPageNotChangingException(AtsPageNumException):
    """Raised when page number parsing fails."""

    pass
