from solver.types import SolverMove


class SolverSearchMixin:
    # Move selection layer: classic play plus adversarial search.

    def choose_move(self, grid, total_mines=None, adversarial=False):
        analysis = self.analyze(grid, total_mines=total_mines)
        safe_moves = analysis["safe_moves"]
        mine_moves = analysis["mine_moves"]
        probabilities = analysis["probabilities"]

        if adversarial:
            return self._choose_adversarial_move(
                grid, total_mines, analysis, safe_moves, mine_moves, probabilities
            )

        if safe_moves:
            chosen = self._pick_safe_move(grid, safe_moves, adversarial=False)
            return SolverMove(
                x=chosen[0],
                y=chosen[1],
                action="reveal",
                tier=analysis["tier"],
                risk=0.0,
                reason="Guaranteed safe by current constraints.",
            ), analysis

        if mine_moves:
            chosen = self._pick_flag_move(grid, mine_moves)
            return SolverMove(
                x=chosen[0],
                y=chosen[1],
                action="flag",
                tier=analysis["tier"],
                risk=1.0,
                reason="Guaranteed mine by current constraints.",
            ), analysis

        hidden_cells = [
            (x, y)
            for y in range(len(grid))
            for x in range(len(grid[0]))
            if grid[y][x] is None
        ]
        chosen = self._pick_probabilistic_move(
            grid, hidden_cells, probabilities, adversarial=adversarial
        )
        risk = probabilities.get(chosen, 0.5)
        reason = (
            "Lowest estimated mine probability available."
            if not adversarial
            else "Lowest-risk move with a conservative adversarial tie-break."
        )
        return SolverMove(
            x=chosen[0],
            y=chosen[1],
            action="reveal",
            tier=analysis["tier"],
            risk=risk,
            reason=reason,
        ), analysis

    def _choose_adversarial_move(
        self, grid, total_mines, analysis, safe_moves, mine_moves, probabilities
    ):
        # Search candidate actions and choose the one with the best expected payoff.
        if mine_moves:
            chosen = self._pick_flag_move(grid, mine_moves)
            return SolverMove(
                x=chosen[0],
                y=chosen[1],
                action="flag",
                tier=analysis["tier"],
                risk=1.0,
                reason="Forced mine found. Flagging it improves our position without risk.",
            ), analysis

        candidate_moves = self._candidate_moves(
            grid, safe_moves, mine_moves, probabilities, limit=self.candidate_limit
        )
        if not candidate_moves:
            hidden_cells = [
                (x, y)
                for y in range(len(grid))
                for x in range(len(grid[0]))
                if grid[y][x] is None
            ]
            chosen = self._pick_probabilistic_move(
                grid, hidden_cells, probabilities, adversarial=False
            )
            return SolverMove(
                x=chosen[0],
                y=chosen[1],
                action="reveal",
                tier=analysis["tier"],
                risk=probabilities.get(chosen, 0.5),
                reason="Fallback reveal: no candidate frontier moves were available.",
            ), analysis

        alpha = float("-inf")
        beta = float("inf")
        best_option = None
        best_score = float("-inf")

        for action, cell in candidate_moves:
            score = self._evaluate_adversarial_move(
                grid, total_mines, probabilities, action, cell, self.search_depth, alpha, beta
            )
            if score > best_score:
                best_score = score
                best_option = (action, cell)
            alpha = max(alpha, best_score)

        chosen_action, chosen_cell = best_option
        chosen_risk = 1.0 if chosen_action == "flag" else probabilities.get(chosen_cell, 0.5)
        return SolverMove(
            x=chosen_cell[0],
            y=chosen_cell[1],
            action=chosen_action,
            tier=analysis["tier"],
            risk=chosen_risk,
            reason=(
                "Selected by adversarial search to maximize our expected survival while "
                "minimizing the opponent's reply quality."
            ),
        ), analysis

    def _pick_safe_move(self, grid, safe_moves, adversarial=False):
        # Prefer informative safe moves in classic mode and quieter ones in adversarial mode.
        return min(
            safe_moves,
            key=lambda cell: (
                self._information_score(grid, cell)
                if adversarial
                else -self._information_score(grid, cell),
                cell[1],
                cell[0],
            ),
        )

    def _pick_flag_move(self, grid, mine_moves):
        # Prefer flags that sit in information-dense parts of the board.
        return max(
            mine_moves,
            key=lambda cell: (self._information_score(grid, cell), -cell[1], -cell[0]),
        )

    def _pick_probabilistic_move(self, grid, hidden_cells, probabilities, adversarial=False):
        # Choose the lowest-risk hidden cell, then break ties by board context.
        def move_score(cell):
            risk = probabilities.get(cell, 0.5)
            info = self._information_score(grid, cell)
            center_bias = self._center_bias(grid, cell)
            if adversarial:
                return (risk, info, center_bias, cell[1], cell[0])
            return (risk, -info, center_bias, cell[1], cell[0])

        return min(hidden_cells, key=move_score)

    def _candidate_moves(self, grid, safe_moves, mine_moves, probabilities, limit):
        # Limit the search tree to the most promising actions.
        if mine_moves:
            ordered_mines = sorted(
                mine_moves,
                key=lambda cell: (-self._information_score(grid, cell), cell[1], cell[0]),
            )
            return [("flag", cell) for cell in ordered_mines[:limit]]

        if safe_moves:
            ordered_safe = sorted(
                safe_moves,
                key=lambda cell: (
                    self._information_score(grid, cell),
                    self._center_bias(grid, cell),
                    cell[1],
                    cell[0],
                ),
            )
            return [("reveal", cell) for cell in ordered_safe[:limit]]

        hidden_cells = [
            (x, y)
            for y in range(len(grid))
            for x in range(len(grid[0]))
            if grid[y][x] is None
        ]
        ordered_hidden = sorted(
            hidden_cells,
            key=lambda cell: (
                probabilities.get(cell, 0.5),
                self._information_score(grid, cell),
                self._center_bias(grid, cell),
                cell[1],
                cell[0],
            ),
        )
        return [("reveal", cell) for cell in ordered_hidden[:limit]]

    def _evaluate_adversarial_move(
        self, grid, total_mines, probabilities, action, cell, depth, alpha, beta
    ):
        # Score one candidate move by expected outcome and the opponent's best reply.
        risk = 1.0 if action == "flag" else probabilities.get(cell, 0.5)
        if action == "flag":
            successor = self._simulate_flag(grid, cell)
            return 4.0 - self._negamax(successor, total_mines, depth - 1, -beta, -alpha)

        safe_successor = self._simulate_reveal(grid, cell, probabilities)
        safe_gain = self._reveal_gain(grid, safe_successor)
        safe_branch = safe_gain - self._negamax(
            safe_successor, total_mines, depth - 1, -beta, -alpha
        )
        mine_branch = -100.0
        return (1.0 - risk) * safe_branch + risk * mine_branch

    def _negamax(self, grid, total_mines, depth, alpha, beta):
        # Small adversarial search with alpha-beta pruning.
        analysis = self.analyze(grid, total_mines=total_mines)
        hidden_count = sum(1 for row in grid for value in row if value is None)
        if depth <= 0 or hidden_count == 0:
            return self._state_heuristic(grid, analysis)

        candidate_moves = self._candidate_moves(
            grid,
            analysis["safe_moves"],
            analysis["mine_moves"],
            analysis["probabilities"],
            limit=max(2, self.candidate_limit - 1),
        )
        if not candidate_moves:
            return self._state_heuristic(grid, analysis)

        best_value = float("-inf")
        for action, cell in candidate_moves:
            if action == "flag":
                successor = self._simulate_flag(grid, cell)
                value = 4.0 - self._negamax(successor, total_mines, depth - 1, -beta, -alpha)
            else:
                risk = analysis["probabilities"].get(cell, 0.5)
                successor = self._simulate_reveal(grid, cell, analysis["probabilities"])
                safe_gain = self._reveal_gain(grid, successor)
                value = (1.0 - risk) * (
                    safe_gain - self._negamax(successor, total_mines, depth - 1, -beta, -alpha)
                ) + risk * (-100.0)

            best_value = max(best_value, value)
            alpha = max(alpha, best_value)
            if alpha >= beta:
                break

        return best_value

    def _simulate_flag(self, grid, cell):
        # Create a successor state where the target cell is flagged.
        cloned = [row[:] for row in grid]
        cloned[cell[1]][cell[0]] = "F"
        return cloned

    def _simulate_reveal(self, grid, cell, probabilities):
        # Create an approximate successor state for search without the full hidden board.
        cloned = [row[:] for row in grid]
        estimated_value = self._estimated_reveal_value(grid, cell, probabilities)
        cloned[cell[1]][cell[0]] = estimated_value
        if estimated_value == 0:
            for nx, ny in self._neighbors(cell[0], cell[1], len(grid[0]), len(grid)):
                if cloned[ny][nx] is None and probabilities.get((nx, ny), 0.5) < 0.25:
                    cloned[ny][nx] = 0
        return cloned

    def _estimated_reveal_value(self, grid, cell, probabilities):
        # Approximate what number a reveal would show based on local mine probabilities.
        x, y = cell
        expected_mines = 0.0
        for nx, ny in self._neighbors(x, y, len(grid[0]), len(grid)):
            neighbor = grid[ny][nx]
            if neighbor == "F":
                expected_mines += 1.0
            elif neighbor is None:
                expected_mines += probabilities.get((nx, ny), 0.5)
        return int(max(0, min(8, round(expected_mines))))

    def _reveal_gain(self, before_grid, after_grid):
        # Reward moves that are expected to uncover more of the board.
        before_hidden = sum(1 for row in before_grid for value in row if value is None)
        after_hidden = sum(1 for row in after_grid for value in row if value is None)
        return 6.0 + float(before_hidden - after_hidden)

    def _state_heuristic(self, grid, analysis):
        # Score a search state using safety, certainty, and remaining uncertainty.
        hidden_count = sum(1 for row in grid for value in row if value is None)
        min_risk = 1.0
        hidden_probabilities = [
            probability
            for cell, probability in analysis["probabilities"].items()
            if grid[cell[1]][cell[0]] is None
        ]
        if hidden_probabilities:
            min_risk = min(hidden_probabilities)

        return (
            len(analysis["safe_moves"]) * 10.0
            + len(analysis["mine_moves"]) * 6.0
            + (1.0 - min_risk) * 14.0
            - hidden_count * 0.1
        )

    def _information_score(self, grid, cell):
        # Estimate how much board information a move is connected to.
        x, y = cell
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        numbered_neighbors = 0
        hidden_neighbors = 0
        for nx, ny in self._neighbors(x, y, cols, rows):
            if isinstance(grid[ny][nx], int):
                numbered_neighbors += 1
            elif grid[ny][nx] is None:
                hidden_neighbors += 1
        return numbered_neighbors * 3 + hidden_neighbors

    def _center_bias(self, grid, cell):
        # Small tie-break that prefers positions closer to the middle of the board.
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        center_x = (cols - 1) / 2.0
        center_y = (rows - 1) / 2.0
        return abs(cell[0] - center_x) + abs(cell[1] - center_y)
