from .models import State
from .rules import initial_board


def quickstart() -> State:
    return State(board=initial_board())
