import os
IS_DEBUG = True
ENV = 'development'
CURRENT_FOLDER = os.path.abspath(os.path.dirname(__file__))
FAKE_APPLICATION = {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "8084385352",
    "resume_path": f"{CURRENT_FOLDER}/data/fake_cv.pdf",
    "cover_letter_text": "This is a cover letter",
    "email": "test@gmail.com",
}
