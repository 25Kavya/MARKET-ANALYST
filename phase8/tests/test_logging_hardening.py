from logging.handlers import RotatingFileHandler

from phase1 import logging_config


def test_dump_log_uses_a_rotating_file_handler():
    logging_config.get_logger("test_logging_hardening")  # ensure configured

    root = logging_config.logging.getLogger(logging_config._ROOT_LOGGER_NAME)
    rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]

    assert len(rotating_handlers) == 1
    handler = rotating_handlers[0]
    assert handler.maxBytes == logging_config._MAX_BYTES
    assert handler.backupCount == logging_config._BACKUP_COUNT
