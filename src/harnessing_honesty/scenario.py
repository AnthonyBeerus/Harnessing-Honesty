"""Scenario record: public prompt view plus private answer key.

Compatibility bridge. The types live in ``domain.scenario``. This module
re-exports them so no import migrates in this step.
"""

from harnessing_honesty.domain.scenario import AnswerKey, ScenarioRecord

__all__ = ["AnswerKey", "ScenarioRecord"]
