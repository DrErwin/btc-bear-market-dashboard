"""v0.4 dual-axis evidence compilation boundary.

Raw indicator cards remain a display concern.  The functions in this package
turn one snapshot into a small, auditable evidence brief that can constrain
the AI without turning the sixteen indicators into a weighted score.
"""

from .compiler import compile_evidence
from .quality import evaluate_snapshot_quality

__all__ = ["compile_evidence", "evaluate_snapshot_quality"]
