import logging
from rich.logging import RichHandler
from rich.console import Console


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure standard logging with structural and colored formatting via Rich.
    Applies to the entire application and integrates well with FastAPI and Celery.
    """
    # Remove existing handlers to avoid duplicates
    logging.getLogger().handlers = []

    # Initialize Rich console for robust colored output
    console = Console(color_system="auto", stderr=True)

    # Configure RichHandler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        omit_repeated_times=False,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
    )

    # Optional: Customize log format string for standard python logs
    # Using simple message since Rich handles time, level, and path
    formatter = logging.Formatter(
        fmt="%(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]"
    )
    rich_handler.setFormatter(formatter)

    # Configure FileHandler for app.log
    file_handler = logging.FileHandler("app.log", mode="w")
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)

    # Tweak third-party loggers
    logging.getLogger("uvicorn.access").handlers = [rich_handler, file_handler]
    logging.getLogger("uvicorn.error").handlers = [rich_handler, file_handler]
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = False

    # Silence or reduce noise from loud third-party libs
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)

    logging.info("Logging configured with Rich ✅")
