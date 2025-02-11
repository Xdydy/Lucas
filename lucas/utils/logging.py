import logging
import os

log_level = int(os.getenv('LUCAS_LOG', "2"))*10
log = logging.getLogger('lucas')
log.setLevel(log_level)

handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")

handler.setFormatter(formatter)

log.addHandler(handler)