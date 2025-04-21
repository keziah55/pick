import logging
from pathlib import Path
from datetime import datetime
import pytz

_logging_initialised = False


def timestamp():
    return datetime.now(pytz.timezone("Europe/London"))


def initialise_logging():
    global _logging_initialised

    ts = timestamp().strftime("%Y-%m-%d-%H:%M:%S")
    logger = logging.getLogger("populate_db")

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    log_file = str(log_dir.joinpath(f"populate_db-{ts}.log"))

    logging.basicConfig(
        filename=log_file,
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
