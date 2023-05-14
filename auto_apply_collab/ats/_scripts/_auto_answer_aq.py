import datetime
import json
import random
import re


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

    def smart_answer(xpath: dict, qtext: str):
        key_for_dont_answer = [
            k for k in xpath.keys() if re.search(r"\bwish|\bchoose", k.lower())
        ]
        key_for_yes = [k for k in xpath.keys() if "yes" in k.lower()]
        key_for_no = [
            k for k in xpath.keys() if "no" in k.lower() or "not" in k.lower()
        ]
        if key_for_dont_answer:
            return key_for_dont_answer[0]
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
        answer = smart_answer(q["xpath"], q["question_text"]) or first_answer(
            q["xpath"]
        )
    if q["type"] == "radio":
        answer = smart_answer(q["xpath"], q["question_text"]) or first_answer(
            q["xpath"]
        )
    if q["type"] == "checkbox":
        answer = smart_answer(q["xpath"], q["question_text"]) or all_answers(q["xpath"])
    if q["type"] == "file":
        answer = None
    # if q["type"] == "number":
    #     answer = 3
    if q["type"] == "date":
        answer = str(datetime.date.today() + datetime.timedelta(days=7))
    q["answer"] = answer
    return q


def generate_answer():
    """Generate a random answer for a question."""
    with open("questions.json") as f:
        questions = json.load(f)
    answers = []
    for q in questions:
        answers.append(_get_answer(q))
    return answers


def main():
    answers = generate_answer()
    with open("answers.json", "w") as f:
        json.dump(answers, f, indent=4)
    return


if __name__ == "__main__":
    main()
