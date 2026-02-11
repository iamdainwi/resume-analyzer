"""
Shared utilities — timing decorator and performance logger.
"""

import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def timing_decorator(func: Callable) -> Callable:
    """Decorator that logs execution time and warns on slow calls."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start

        logger.info("⏱️ %s executed in %.2fs", func.__name__, elapsed)
        if elapsed > 10:
            logger.warning("🐌 %s is slow! Took %.2fs", func.__name__, elapsed)
        elif elapsed > 5:
            logger.warning("⚠️ %s took %.2fs", func.__name__, elapsed)

        return result

    return wrapper


def log_performance_metrics(
    operation: str, duration: float, success: bool = True,
) -> None:
    """Log a performance measurement with severity based on duration."""
    icon = "✅" if success else "❌"

    if duration < 1:
        logger.info("%s %s: %.2fs (Fast)", icon, operation, duration)
    elif duration < 3:
        logger.info("%s %s: %.2fs (Normal)", icon, operation, duration)
    elif duration < 10:
        logger.warning("⚠️ %s: %.2fs (Slow)", operation, duration)
    else:
        logger.error("🐌 %s: %.2fs (Very Slow)", operation, duration)

    if duration > 15:
        logger.error("💡 Consider optimizing %s — it's taking too long", operation)