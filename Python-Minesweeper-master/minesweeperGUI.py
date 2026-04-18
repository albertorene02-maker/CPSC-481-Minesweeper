import random

try:
    import eel
    EEL_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    EEL_IMPORT_ERROR = (
        "Python could not import a module required by Eel: "
        f"{exc}. Try: python -m pip install -r requirements.txt"
    )

    class _EelStub(object):
        def init(self, *_args, **_kwargs):
            return None

        def expose(self, func):
            return func

        def start(self, *_args, **_kwargs):
            return None

    eel = _EelStub()

from solver import MultiAgentMinesweeperSolver


class boardSpot(object):
    value = 0
    selected = False
    mine = False

    def __init__(self):
        self.value = 0
        self.selected = False
        self.mine = False

    def __str__(self):
        return str(self.value)

    def isMine(self):
        return self.value == -1


class boardClass(object):
    def __init__(self, m_boardSize, m_numMines):
        self.board = [[boardSpot() for i in range(m_boardSize)]
                      for j in range(m_boardSize)]
        self.boardSize = m_boardSize
        self.numMines = m_numMines
        self.selectableSpots = m_boardSize * m_boardSize - m_numMines
        i = 0
        while i < m_numMines:
            x = random.randint(0, self.boardSize - 1)
            y = random.randint(0, self.boardSize - 1)
            if not self.board[x][y].mine:
                self.addMine(x, y)
                i += 1

    def __str__(self):
        return_string = ""
        for y in range(0, self.boardSize):
            for x in range(0, self.boardSize):
                if self.board[x][y].mine and self.board[x][y].selected:
                    return_string += "B"
                elif self.board[x][y].selected:
                    return_string += str(self.board[x][y].value)
                else:
                    return_string += "E"
        return return_string

    def addMine(self, x, y):
        self.board[x][y].value = -1
        self.board[x][y].mine = True
        for i in range(x - 1, x + 2):
            if i >= 0 and i < self.boardSize:
                if y - 1 >= 0 and not self.board[i][y - 1].mine:
                    self.board[i][y - 1].value += 1
                if y + 1 < self.boardSize and not self.board[i][y + 1].mine:
                    self.board[i][y + 1].value += 1
        if x - 1 >= 0 and not self.board[x - 1][y].mine:
            self.board[x - 1][y].value += 1
        if x + 1 < self.boardSize and not self.board[x + 1][y].mine:
            self.board[x + 1][y].value += 1

    def makeMove(self, x, y):
        if self.board[x][y].selected:
            return True

        self.board[x][y].selected = True
        self.selectableSpots -= 1
        if self.board[x][y].value == -1:
            return False
        if self.board[x][y].value == 0:
            for i in range(x - 1, x + 2):
                if i >= 0 and i < self.boardSize:
                    if y - 1 >= 0 and not self.board[i][y - 1].selected:
                        self.makeMove(i, y - 1)
                    if y + 1 < self.boardSize and not self.board[i][y + 1].selected:
                        self.makeMove(i, y + 1)
            if x - 1 >= 0 and not self.board[x - 1][y].selected:
                self.makeMove(x - 1, y)
            if x + 1 < self.boardSize and not self.board[x + 1][y].selected:
                self.makeMove(x + 1, y)
        return True

    def hitMine(self, x, y):
        return self.board[x][y].value == -1

    def isWinner(self):
        return self.selectableSpots == 0

    def isSelected(self, x, y):
        return self.board[x][y].selected

    def getValue(self, x, y):
        return self.board[x][y].value

    def toPublicGrid(self, flags=None, reveal_all_mines=False):
        flags = flags or set()
        grid = []
        for y in range(self.boardSize):
            row = []
            for x in range(self.boardSize):
                spot = self.board[x][y]
                if reveal_all_mines and spot.mine:
                    row.append("B")
                elif spot.selected:
                    row.append(spot.value)
                elif (x, y) in flags:
                    row.append("F")
                else:
                    row.append(None)
            grid.append(row)
        return grid

    def toCompactString(self, flags=None, reveal_all_mines=False):
        flags = flags or set()
        result = ""
        for y in range(self.boardSize):
            for x in range(self.boardSize):
                spot = self.board[x][y]
                if reveal_all_mines and spot.mine:
                    result += "B"
                elif spot.selected:
                    result += str(spot.value)
                elif (x, y) in flags:
                    result += "F"
                else:
                    result += "E"
        return result


class GameSession(object):
    def __init__(self):
        self.solver = MultiAgentMinesweeperSolver()
        self.board = None
        self.flags = set()
        self.mode = "classic"
        self.game_over = False
        self.winner = ""
        self.current_player = "A"
        self.last_move = None
        self.reasoning = ""

    def make_board(self, board_size, num_mines, mode="classic"):
        self.board = boardClass(board_size, num_mines)
        self.flags = set()
        self.mode = mode
        self.game_over = False
        self.winner = ""
        self.current_player = "A"
        self.last_move = None
        self.reasoning = "New board created."
        return self.snapshot()

    def snapshot(self):
        if self.board is None:
            return {
                "board": [],
                "boardString": "",
                "boardSize": 0,
                "numMines": 0,
                "mode": self.mode,
                "gameOver": self.game_over,
                "winner": self.winner,
                "currentPlayer": self.current_player,
                "reasoning": self.reasoning,
                "statusText": "No game loaded.",
                "lastMove": self.last_move,
            }

        reveal_all_mines = self.game_over and self.mode == "adversarial"
        board = self.board.toPublicGrid(self.flags, reveal_all_mines=reveal_all_mines)
        return {
            "board": board,
            "boardString": self.board.toCompactString(
                self.flags, reveal_all_mines=reveal_all_mines
            ),
            "boardSize": self.board.boardSize,
            "numMines": self.board.numMines,
            "mode": self.mode,
            "gameOver": self.game_over,
            "winner": self.winner,
            "currentPlayer": self.current_player,
            "reasoning": self.reasoning,
            "statusText": self._status_text(),
            "lastMove": self.last_move,
        }

    def _status_text(self):
        if self.game_over:
            if self.mode == "adversarial":
                if self.winner == "Tie":
                    return "Game over. Result: tie."
                return f"Game over. Winner: Agent {self.winner}."
            if self.winner == "Human":
                return "You cleared every safe cell."
            return "Game over."
        if self.mode == "adversarial":
            return f"Adversarial mode. Agent {self.current_player} to move."
        return "Classic mode. Left click to reveal, right click to flag."

    def _switch_player(self):
        self.current_player = "B" if self.current_player == "A" else "A"

    def _complete_reveal(self, x, y, actor):
        if self.game_over or self.board is None:
            return self.snapshot()
        if (x, y) in self.flags or self.board.isSelected(x, y):
            return self.snapshot()

        survived = self.board.makeMove(x, y)
        self.last_move = {"actor": actor, "x": x, "y": y, "action": "reveal"}
        if not survived or self.board.hitMine(x, y):
            self.game_over = True
            if self.mode == "adversarial":
                self.winner = "B" if actor == "A" else "A"
                self.reasoning = f"Agent {actor} hit a mine at ({x}, {y})."
            else:
                self.winner = ""
                self.reasoning = f"You hit a mine at ({x}, {y})."
            return self.snapshot()

        if self.board.isWinner():
            self.game_over = True
            if self.mode == "adversarial":
                self.winner = "Tie"
                self.reasoning = (
                    f"Agent {actor} cleared the final safe cell, so the adversarial game ends in a tie."
                )
            else:
                self.winner = "Human"
                self.reasoning = f"{actor} cleared the final safe cell."
            return self.snapshot()

        if self.mode == "adversarial":
            self._switch_player()
        return self.snapshot()

    def reveal_cell(self, x, y):
        actor = self.current_player if self.mode == "adversarial" else "Human"
        return self._complete_reveal(x, y, actor)

    def toggle_flag(self, x, y):
        if self.game_over or self.board is None or self.board.isSelected(x, y):
            return self.snapshot()
        if (x, y) in self.flags:
            self.flags.remove((x, y))
            self.reasoning = f"Flag removed from ({x}, {y})."
        else:
            self.flags.add((x, y))
            self.reasoning = f"Flag placed on ({x}, {y})."
        self.last_move = {"actor": "Human", "x": x, "y": y, "action": "flag"}
        return self.snapshot()

    def solver_hint(self):
        if self.board is None or self.game_over:
            return self.snapshot()
        move, analysis = self.solver.choose_move(
            self.board.toPublicGrid(self.flags),
            total_mines=self.board.numMines,
            adversarial=self.mode == "adversarial",
        )
        self.reasoning = (
            f"{analysis['reasoning']} Suggested move: {move.action} ({move.x}, {move.y}) "
            f"with estimated mine risk {move.risk:.2%}. {move.reason}"
        )
        self.last_move = {
            "actor": "Hint",
            "x": move.x,
            "y": move.y,
            "action": move.action,
            "tier": move.tier,
            "risk": move.risk,
        }
        return self.snapshot()

    def run_agent_turn(self):
        if self.board is None or self.game_over:
            return self.snapshot()

        analysis = self.solver.analyze(
            self.board.toPublicGrid(self.flags), total_mines=self.board.numMines
        )
        if analysis["mine_moves"]:
            for cell in analysis["mine_moves"]:
                if not self.board.isSelected(cell[0], cell[1]):
                    self.flags.add(cell)

        move, analysis = self.solver.choose_move(
            self.board.toPublicGrid(self.flags),
            total_mines=self.board.numMines,
            adversarial=self.mode == "adversarial",
        )
        actor = self.current_player if self.mode == "adversarial" else "Solver"

        if move.action == "flag":
            self.flags.add((move.x, move.y))
            self.last_move = {
                "actor": actor,
                "x": move.x,
                "y": move.y,
                "action": move.action,
                "tier": move.tier,
                "risk": move.risk,
            }
            self.reasoning = (
                f"{analysis['reasoning']} Agent {actor} flagged ({move.x}, {move.y}). "
                f"{move.reason}"
            )
            if self.mode == "adversarial":
                self._switch_player()
            return self.snapshot()

        self._complete_reveal(move.x, move.y, actor)
        self.reasoning = (
            f"{analysis['reasoning']} Agent {actor} revealed ({move.x}, {move.y}) "
            f"with estimated mine risk {move.risk:.2%}. {move.reason}"
        )
        return self.snapshot()


eel.init(".//UI")

SESSION = GameSession()


@eel.expose
def clickedOnTheCell(x, y):
    return SESSION.reveal_cell(x, y)


@eel.expose
def toggleFlag(x, y):
    return SESSION.toggle_flag(x, y)


@eel.expose
def requestSolverHint():
    return SESSION.solver_hint()


@eel.expose
def runAgentTurn():
    return SESSION.run_agent_turn()


@eel.expose
def getBoardState():
    return SESSION.snapshot()


@eel.expose
def makeBoard(boardSize, numMines, mode="classic"):
    return SESSION.make_board(boardSize, numMines, mode=mode)


if __name__ == "__main__":
    if EEL_IMPORT_ERROR is not None:
        raise SystemExit(EEL_IMPORT_ERROR)
    eel.start(
        "index.html",
        mode="default",
        port=8080,
        suppress_error=True,
    )
