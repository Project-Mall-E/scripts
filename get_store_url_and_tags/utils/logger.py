import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    include_console: bool = True
) -> None:
    """
    Configure logging for the discovery system.
    
    Args:
        log_file: Path to log file. If None, uses 'discovery_{date}.log'
        level: Logging level
        include_console: Whether to also log to console
    """
    if log_file is None:
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = str(log_dir / f"discovery_{datetime.now():%Y%m%d}.log")
    
    handlers = []
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    handlers.append(file_handler)
    
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(levelname)-8s | %(name)s | %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    logging.basicConfig(level=level, handlers=handlers, force=True)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
