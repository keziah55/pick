import time
import logging

_logging_initialised = False


def initialise_logging():
    global _logging_initialised

    ts = time.strftime("%Y-%m-%d-%H:%M:%S")
    logger = logging.getLogger("populate_db")
    logging.basicConfig(
        filename=f"populate_db-{ts}.log",
        level=logging.INFO,
        format="%(levelname)s: %(name)s: %(asctime)s: %(message)s",
    )
    _logging_initialised = True

    return logger


def get_logger():
    global _logging_initialised
    if not _logging_initialised:
        initialise_logging()
    return logging.getLogger("populate_db")
