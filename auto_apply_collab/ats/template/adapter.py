from ..common.annotations_ import (
    template_to_prod_apply_adapter,
    template_to_prod_aq_adapter,
)
from .describe import ATS_NAME
from .template import *

additional_questions_decorator = template_to_prod_aq_adapter(ats_name=ATS_NAME)
apply_decorator = template_to_prod_apply_adapter()

# These functions will be used for AQ and Apply
additional_questions = additional_questions_decorator(additional_questions)
apply = apply_decorator(apply)
