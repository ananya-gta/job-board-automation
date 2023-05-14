import logging
print('Hello World')

logging.basicConfig(level=logging.DEBUG)
def get_task_logger(name='celery.task'):
    return logging.getLogger(name)
