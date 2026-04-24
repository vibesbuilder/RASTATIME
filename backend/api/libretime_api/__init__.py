from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version

PACKAGE = __name__
try:
    VERSION = get_version(__name__)
except PackageNotFoundError:
    VERSION = "dev"
