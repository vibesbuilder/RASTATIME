import logging
import math
from subprocess import CalledProcessError, CompletedProcess, run
from typing import Any, Optional

logger = logging.getLogger(__name__)


def run_(*args, **kwargs) -> CompletedProcess:
    try:
        return run(
            args,
            check=True,
            capture_output=True,
            text=True,
            **kwargs,
        )

    except OSError as exception:  # executable was not found
        cmd = args[0]
        logger.warning("Failed to run: %s - %s. Is %s installed?", cmd, exception, cmd)
        raise exception

    except CalledProcessError as exception:  # returned an error code
        logger.error(exception)
        raise exception


# RASTATIME 2026-10-14 - ffprobe reports numbers as strings ("44100",
# "3.000000", "N/A"); these give None for anything that is not a positive,
# finite number.
def positive_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def positive_int(value: Any) -> Optional[int]:
    number = positive_float(value)
    return int(number) if number is not None and number >= 1 else None
