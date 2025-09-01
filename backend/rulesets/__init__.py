"""Ruleset registrations.

Importing a ruleset module registers it via side effects.
Only TBS is kept in this trimmed build.
"""

from .tbs.ruleset import ruleset as tbs_ruleset  # noqa: F401
