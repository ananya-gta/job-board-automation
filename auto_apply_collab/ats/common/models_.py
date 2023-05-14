from collections import namedtuple
from enum import Enum
from typing import List, Optional, Union

from pydantic import AnyHttpUrl
from sqlmodel import Field, SQLModel

from ats.common.types_ import Xpath, XpathDict, XpathTextValue

Status = namedtuple("Status", ["status", "message"])


class StatusType:
    SUCCESS = "success"
    FAILURE = "error"


class AQType(str, Enum):
    NUMBER = "number"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXT = "text"
    INPUT = "input"
    DROPDOWN = "dropdown"
    TEXTAREA = "textarea"
    FILE = "file"
    DATE = "date"


class AdditionalQuestion(SQLModel):
    question_text: str
    xpath: Union[Xpath, XpathDict]
    long_response: bool
    page: int
    type: AQType

    class Config:
        orm_mode = True
        validate_assignment = True
        use_enum_values = True


class AdditionalAnswers(SQLModel):
    xpath: Union[Xpath, XpathDict]
    answer: Union[XpathTextValue, List[XpathTextValue], None]
    type: str
    page: Union[int, None]

    class Config:
        orm_mode = True
        validate_assignment = True
        use_enum_values = True


# class JobApplication(SQLModel):
#     job_id: int
#     first_name: str
#     last_name: str
#     city: str
#     state: str
#     email: str
#     phone: str
#     resume_url: Union[AnyHttpUrl, None]
#     linkedin_url: Union[str, None]
#     current_company: str
#     cover_letter_text: str
#     additional_questions: Union[List[AdditionalAnswers], None] = []


if __name__ == "__main__":
    # job_application = JobApplication(
    #     job_id=1,
    #     first_name="John",
    #     last_name="Doe",
    #     city="New York",
    #     state="NY",
    #     email="a@b.com",
    #     phone="1234567890",
    #     # resume_url=None,
    #     current_company="Google",
    #     cover_letter_text="Hello",
    #     # additional_questions=[]
    # )
    # print(job_application)

    aq = AdditionalQuestion(
        question_text="What is your name?",
        xpath="xpath",
        long_response="False",
        page=1,
        type="text",
    )
    print(aq.dict())
