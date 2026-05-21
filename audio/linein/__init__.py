"""
audio.linein — Line-In domain model and runtime.

T14.1: LineIn pure domain model.
T14.2: API serialization helpers.
T15.1: Line-In runtime activation contract.
"""

from .domain import LineIn
from ._api_helpers import list_lineins_response, serialize_linein
from ._runtime import ActivationResult, LineInRuntime, StubLineInRuntime
from ._registry import connect_runtime, default_runtime

__all__ = [
    # T14.1 — domain model
    "LineIn",
    # T14.2 — serialization
    "serialize_linein",
    "list_lineins_response",
    # T15.1 — runtime contract
    "ActivationResult",
    "LineInRuntime",
    "StubLineInRuntime",
    # T15.1 — registry
    "connect_runtime",
    "default_runtime",
]
