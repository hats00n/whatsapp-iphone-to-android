import logging
from termcolor import colored


class CustomFormatter(logging.Formatter):

    format = "%(message)s"

    FORMATS = {
        logging.DEBUG: colored(format, 'grey'),
        logging.INFO: colored(format, 'white'),
        logging.WARNING: colored(format, 'yellow'),
        logging.ERROR: colored(format, 'red'),
        logging.CRITICAL: colored(format, 'red')
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)