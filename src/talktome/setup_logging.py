import logging
import logging.handlers


def setup_logging():
    adjust_unused_logging()
    setup_terminal_logging()
    return setup_file_logging()


def setup_file_logging():
    logger = logging.getLogger("root")
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def setup_terminal_logging():
    logger = logging.getLogger("talktome")
    logger.setLevel(logging.INFO)
    terminal_handler = logging.StreamHandler()
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    terminal_handler.setFormatter(formatter)
    logger.addHandler(terminal_handler)


def adjust_unused_logging():
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
    httpcore_logger = logging.getLogger("httpcore")
    httpcore_logger.setLevel(logging.WARNING)
