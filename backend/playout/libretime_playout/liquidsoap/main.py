import logging
import os
from pathlib import Path
from typing import Optional

import click

# RASTATIME: libretime_api_client is not installed on Windows.
# Guard the import so this module can be safely imported without it.
try:
    from libretime_api_client.v2 import ApiClient
    _API_CLIENT_AVAILABLE = True
except ImportError:
    ApiClient = None  # type: ignore[assignment, misc]
    _API_CLIENT_AVAILABLE = False

from libretime_shared.cli import cli_config_options, cli_logging_options
from libretime_shared.config import DEFAULT_ENV_PREFIX
from libretime_shared.logging import setup_logger

# RASTATIME: jinja2 and other playout deps are not installed on Windows.
# Guard all local liquidsoap sub-imports for safe import on Windows.
try:
    from ..config import Config
    from .entrypoint import generate_entrypoint
    from .models import Info, StreamPreferences
    from .version import get_liquidsoap_version
    _PLAYOUT_DEPS_AVAILABLE = True
except (ImportError, Exception) as _playout_e:
    Config = generate_entrypoint = Info = StreamPreferences = get_liquidsoap_version = None  # type: ignore[assignment, misc]
    _PLAYOUT_DEPS_AVAILABLE = False
    import logging as _log
    _log.getLogger(__name__).warning(
        "libretime_playout.liquidsoap.main: deps unavailable (%s). "
        "Playout is disabled (RASTATIME Windows mode).", _playout_e
    )

logger = logging.getLogger(__name__)

here = Path(__file__).parent


@click.command(context_settings={"auto_envvar_prefix": DEFAULT_ENV_PREFIX})
@cli_logging_options()
@cli_config_options()
def cli(log_level: str, log_filepath: Optional[Path], config_filepath: Optional[Path]):
    """
    Run liquidsoap.
    """
    setup_logger(log_level, log_filepath)
    config = Config(config_filepath)

    api_client = ApiClient(
        base_url=config.general.public_url,
        api_key=config.general.api_key,
    )

    version = get_liquidsoap_version()

    info = Info(**api_client.get_info().json())
    preferences = StreamPreferences(**api_client.get_stream_preferences().json())

    entrypoint_filepath = Path.cwd() / "radio.liq"
    entrypoint_filepath.write_text(
        generate_entrypoint(
            log_filepath,
            config,
            preferences,
            info,
            version,
        ),
        encoding="utf-8",
    )

    exec_args = [
        "/usr/bin/liquidsoap",
        "libretime-liquidsoap",
        "--verbose",
        str(entrypoint_filepath),
    ]
    if log_level == "debug":
        exec_args.append("--debug")

    logger.debug("liquidsoap %s using script: %s", version, entrypoint_filepath)
    os.execl(*exec_args)
