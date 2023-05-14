# fields_xpath = """//div[@class='question']"""
# easy_apply_xpath = """//button[@class='jobs-apply-button']"""
# next_button_xpath = """//button[@class='next_button']"""
# apply_button_xpath = """//button[@class='jobs-apply"""
# submit_button_xpath = f'{next_button_xpath}/following-sibling::button'


# apply_button_1_xpath = r"""//[contains(@class,'pc_link')]"""  # if text has answer questions
# apply_button_2_xpath = r"""//button[@class='apply_button_var2 ']"""  # if text has "apply"
easyapply_button_xpath = r"""//div[contains(@class, 'apply_buttons')]/a | //button[text() = '1-Click Apply'] | //button[text() = 'Apply']"""

# skip_button_xpath = r"""//section[@class='apply_flow_screen']//button[@class='skip'] or //button[@class='skip']"""
skip_button_xpath = r"""//button[@class='skip']"""
continue_button_xpath = r"""//button[@class='continue']"""
# or //section[@class='apply_flow_screen']//button[@type='submit']"""

fields_xpath = r"""//section[@class='apply_flow_screen']//fieldset"""
rel_question_text_xpath = r""".//label"""
rel_input_xpath = r""".//input"""
rel_textarea_xpath = r""".//textarea"""
rel_select_xpath = r""".//select"""
rel_option_xpath = r""".//option"""
# rel_input_xpath_template = r"//section[@class='apply_flow_screen']//*[@id='{id_attribute}']"
select_xpath_template = r"//select[@id='{id_attribute}']"
textarea_xpath_template = r"//textarea[@id='{id_attribute}']"
input_xpath_template = r"//input[@id='{id_attribute}']"

login_username_xpath = r"""//input[@id='email']"""
login_password_xpath = r"""//input[@id='password']"""
login_button_xpath = r"""//button[@type='submit']"""

# expired_xpath = "//span[contains(@class,'pc_text_control')]"

already_applied_xpath = (
    r"""//span[contains(@class,'pc_text_control')][text()[contains(.,"applied")]] | //*[text() = 'You have applied']"""
)
page_num_xpath = r"""//span[@class='progress_count']"""

redirect_on_expire_url = "https://www.ziprecruiter.com/candidate/suggested-jobs"
should_not_exist_on_expired_xpath = "//*[contains(@class,'pc_control ')]" \
                                    + '|' + easyapply_button_xpath \
                                    + '|' + already_applied_xpath
