from dataclasses import dataclass


@dataclass
class SolverMove:
    # Represents one solver recommendation for the current board state.

    x: int
    y: int
    action: str
    tier: str
    risk: float
    reason: str
