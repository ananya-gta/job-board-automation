# from __future__ import annotations

import importlib.util
import logging
import sys

# sys.modules['tweaks'] = sys.modules['__tweaks__']
# findspec = importlib.util.find_spec('ats.tweaks')
# module = importlib.util.module_from_spec(findspec)
sys.modules["celery"] = __import__("tweaks")
sys.modules["celery.utils"] = __import__("ats.tweaks")
sys.modules["celery.utils.log"] = __import__("ats.tweaks")
sys.modules["config"] = __import__("ats.config")

# findspec = importlib.util.find_spec('ats.tweaks')
# module = importlib.util.module_from_spec(findspec)
# print(module.get_task_logger)
