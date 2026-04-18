from solver.analysis import SolverAnalysisMixin
from solver.search import SolverSearchMixin
from solver.types import SolverMove


class MultiAgentMinesweeperSolver(SolverSearchMixin, SolverAnalysisMixin):
    # Combines board analysis and move selection into one solver API.

    def __init__(self, max_frontier_size=18, search_depth=2, candidate_limit=6):
        self.max_frontier_size = max_frontier_size
        self.search_depth = search_depth
        self.candidate_limit = candidate_limit


__all__ = ["MultiAgentMinesweeperSolver", "SolverMove"]
