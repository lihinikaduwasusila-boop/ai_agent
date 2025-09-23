import logging
import os


def setup_logger():
    logger = logging.getLogger("LegalIR")
    logger.setLevel(logging.INFO)

    log_file = os.getenv("AUDIT_LOG_FILE", "audit.log")
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)

    return logger


logger = setup_logger()