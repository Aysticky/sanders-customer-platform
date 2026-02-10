import logging
import os


def get_logger(name: str) -> logging.Logger:
    """
    Creates and configures a logger instance with the specified name.

    This function sets up a logger with basic configuration including log level
    (read from the LOG_LEVEL environment variable, defaulting to INFO) and a
    standardized format for log messages.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    return logging.getLogger(name)
