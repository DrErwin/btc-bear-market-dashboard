"""Offline boundaries for the public dashboard's AI contract.

Imports are deliberately lazy: evidence compilation and AI input building
refer to each other during packet assembly, so eager package imports would
create a circular dependency.
"""

from .validator import InvalidAnalysisError, validate_analysis


def build_ai_input(*args, **kwargs):
    from .input_builder import build_ai_input as _build_ai_input

    return _build_ai_input(*args, **kwargs)


__all__ = ["InvalidAnalysisError", "build_ai_input", "validate_analysis"]
