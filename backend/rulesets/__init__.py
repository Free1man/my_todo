# Importing registers both rulesets via side effects.
from .tbs.ruleset import ruleset as tbs_ruleset  # noqa: F401
from .chess.ruleset import ruleset as chess_ruleset  # noqa: F401
