import logging
from logging.handlers import TimedRotatingFileHandler

from twisted.python import log


def open_log(filepath='mudsling.log', level=logging.INFO, stdout=False):
    logger = logging.getLogger()  # Root logger.
    logger.setLevel(level)
    if not stdout:
        handler = TimedRotatingFileHandler(filepath, when="midnight",
                                           backupCount=7)
        formatter = logging.Formatter('%(asctime)s %(message)s',
                                      '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # This directs twisted logs into the python log.
    observer = log.PythonLoggingObserver()
    observer.start()
