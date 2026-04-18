from collections import Counter, defaultdict


class SolverAnalysisMixin:
    # Tiered analysis: local rules, CSP inference, then probability fallback.

    def analyze(self, grid, total_mines=None):
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        known_mines = {
            (x, y)
            for y in range(rows)
            for x in range(cols)
            if grid[y][x] == "F"
        }
        safe_moves, inferred_mines = self._run_deterministic_rules(grid, known_mines)
        known_mines |= inferred_mines

        probabilities = {}
        for y in range(rows):
            for x in range(cols):
                if grid[y][x] == "F":
                    probabilities[(x, y)] = 1.0
                elif grid[y][x] is not None:
                    probabilities[(x, y)] = 0.0

        if safe_moves or inferred_mines:
            for cell in safe_moves:
                probabilities[cell] = 0.0
            for cell in inferred_mines:
                probabilities[cell] = 1.0
            return {
                "tier": "deterministic",
                "safe_moves": sorted(safe_moves),
                "mine_moves": sorted(inferred_mines),
                "probabilities": probabilities,
                "reasoning": self._build_reasoning(
                    "Tier 1", safe_moves, inferred_mines, None
                ),
            }

        constraints, frontier, hidden_cells = self._build_constraints(grid, known_mines)
        unconstrained = hidden_cells - frontier - known_mines
        component_probabilities = {}
        guaranteed_safe = set()
        guaranteed_mines = set()
        frontier_note = None

        # Each independent frontier component can be solved separately.
        for variables, component_constraints in self._split_components(frontier, constraints):
            if len(variables) > self.max_frontier_size:
                frontier_note = (
                    f"CSP frontier too large ({len(variables)} cells), using "
                    "probabilistic fallback for that region."
                )
                continue

            solutions, mine_counts = self._enumerate_component(
                list(variables), component_constraints
            )
            if solutions == 0:
                continue

            for cell in variables:
                probability = mine_counts[cell] / float(solutions)
                component_probabilities[cell] = probability
                if probability == 0.0:
                    guaranteed_safe.add(cell)
                elif probability == 1.0:
                    guaranteed_mines.add(cell)

        probabilities.update(component_probabilities)
        if guaranteed_safe or guaranteed_mines:
            for cell in guaranteed_safe:
                probabilities[cell] = 0.0
            for cell in guaranteed_mines:
                probabilities[cell] = 1.0
            return {
                "tier": "csp",
                "safe_moves": sorted(guaranteed_safe),
                "mine_moves": sorted(guaranteed_mines),
                "probabilities": probabilities,
                "reasoning": self._build_reasoning(
                    "Tier 2", guaranteed_safe, guaranteed_mines, frontier_note
                ),
            }

        background_probability = self._background_probability(
            grid, total_mines, known_mines, component_probabilities, unconstrained
        )
        for cell in unconstrained:
            probabilities[cell] = background_probability

        remaining_hidden = [
            (x, y)
            for y in range(rows)
            for x in range(cols)
            if grid[y][x] is None
        ]
        if not remaining_hidden:
            return {
                "tier": "complete",
                "safe_moves": [],
                "mine_moves": [],
                "probabilities": probabilities,
                "reasoning": "Board is already fully resolved.",
            }

        for cell in remaining_hidden:
            probabilities.setdefault(cell, background_probability)

        return {
            "tier": "probabilistic",
            "safe_moves": [],
            "mine_moves": [],
            "probabilities": probabilities,
            "reasoning": self._build_reasoning(
                "Tier 3", set(), set(), frontier_note or "No forced moves exist."
            ),
        }

    def _run_deterministic_rules(self, grid, known_mines):
        # Apply the basic one-cell Minesweeper rules until nothing new appears.
        safe_moves = set()
        inferred_mines = set()
        changed = True
        while changed:
            changed = False
            for y in range(len(grid)):
                for x in range(len(grid[0])):
                    value = grid[y][x]
                    if not isinstance(value, int) or value < 0:
                        continue

                    hidden_neighbors = []
                    flagged_neighbors = 0
                    for nx, ny in self._neighbors(x, y, len(grid[0]), len(grid)):
                        if (nx, ny) in known_mines or (nx, ny) in inferred_mines:
                            flagged_neighbors += 1
                        elif grid[ny][nx] is None:
                            hidden_neighbors.append((nx, ny))

                    remaining = value - flagged_neighbors
                    if remaining == 0 and hidden_neighbors:
                        before = len(safe_moves)
                        safe_moves.update(hidden_neighbors)
                        changed |= len(safe_moves) != before
                    elif remaining == len(hidden_neighbors) and hidden_neighbors:
                        before = len(inferred_mines)
                        inferred_mines.update(hidden_neighbors)
                        changed |= len(inferred_mines) != before
        safe_moves -= inferred_mines
        return safe_moves, inferred_mines

    def _build_constraints(self, grid, known_mines):
        # Turn revealed numbered cells into CSP constraints over nearby hidden cells.
        constraints = []
        frontier = set()
        hidden_cells = set()
        rows = len(grid)
        cols = len(grid[0]) if rows else 0

        for y in range(rows):
            for x in range(cols):
                if grid[y][x] is None:
                    hidden_cells.add((x, y))

        for y in range(rows):
            for x in range(cols):
                value = grid[y][x]
                if not isinstance(value, int) or value < 0:
                    continue

                unknown_neighbors = set()
                flagged_neighbors = 0
                for nx, ny in self._neighbors(x, y, cols, rows):
                    if (nx, ny) in known_mines or grid[ny][nx] == "F":
                        flagged_neighbors += 1
                    elif grid[ny][nx] is None:
                        unknown_neighbors.add((nx, ny))

                remaining = value - flagged_neighbors
                if unknown_neighbors and remaining >= 0:
                    frontier |= unknown_neighbors
                    constraints.append((frozenset(unknown_neighbors), remaining))

        return constraints, frontier, hidden_cells

    def _split_components(self, frontier, constraints):
        # Group the frontier into independent CSP regions to keep search manageable.
        if not frontier:
            return []

        adjacency = defaultdict(set)
        relevant_constraints = []
        for cells, count in constraints:
            component_cells = cells & frontier
            if not component_cells:
                continue
            relevant_constraints.append((component_cells, count))
            for cell in component_cells:
                adjacency[cell] |= component_cells - {cell}

        seen = set()
        components = []
        for cell in frontier:
            if cell in seen:
                continue
            stack = [cell]
            variables = set()
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                variables.add(current)
                stack.extend(adjacency[current] - seen)

            component_constraints = []
            for cells, count in relevant_constraints:
                overlap = cells & variables
                if overlap:
                    component_constraints.append((tuple(sorted(overlap)), count))
            components.append((variables, component_constraints))
        return components

    def _enumerate_component(self, variables, constraints):
        # Enumerate valid mine assignments for one frontier component.
        var_index = {cell: i for i, cell in enumerate(variables)}
        normalized_constraints = []
        var_to_constraints = defaultdict(list)

        for idx, (cells, count) in enumerate(constraints):
            indexes = tuple(var_index[cell] for cell in cells)
            normalized_constraints.append(
                {
                    "indexes": indexes,
                    "target": count,
                    "assigned_sum": 0,
                    "remaining": len(indexes),
                }
            )
            for var in indexes:
                var_to_constraints[var].append(idx)

        ordered_vars = sorted(
            range(len(variables)),
            key=lambda idx: len(var_to_constraints[idx]),
            reverse=True,
        )
        assignment = [-1] * len(variables)
        solutions = 0
        mine_counts = Counter()

        def backtrack(depth):
            nonlocal solutions
            if depth == len(ordered_vars):
                for constraint in normalized_constraints:
                    if constraint["assigned_sum"] != constraint["target"]:
                        return
                solutions += 1
                for idx, value in enumerate(assignment):
                    if value == 1:
                        mine_counts[variables[idx]] += 1
                return

            var = ordered_vars[depth]
            for value in (0, 1):
                assignment[var] = value
                touched = []
                valid = True
                for constraint_idx in var_to_constraints[var]:
                    constraint = normalized_constraints[constraint_idx]
                    constraint["assigned_sum"] += value
                    constraint["remaining"] -= 1
                    touched.append(constraint)
                    lower_bound = constraint["assigned_sum"]
                    upper_bound = constraint["assigned_sum"] + constraint["remaining"]
                    if lower_bound > constraint["target"] or upper_bound < constraint["target"]:
                        valid = False
                        break

                if valid:
                    backtrack(depth + 1)

                for constraint in touched:
                    constraint["assigned_sum"] -= value
                    constraint["remaining"] += 1

            assignment[var] = -1

        backtrack(0)
        return solutions, mine_counts

    def _background_probability(
        self, grid, total_mines, known_mines, component_probabilities, unconstrained
    ):
        # Estimate mine risk for cells not covered by any current CSP frontier.
        if not unconstrained:
            return 0.5

        if total_mines is None:
            return 0.5

        expected_frontier_mines = sum(component_probabilities.values())
        remaining_mines = total_mines - len(known_mines) - expected_frontier_mines
        remaining_mines = max(0.0, remaining_mines)
        return min(1.0, remaining_mines / float(len(unconstrained)))

    def _build_reasoning(self, tier_name, safe_moves, mine_moves, note):
        # Build short UI-facing text describing which solver layer made the choice.
        segments = [f"{tier_name} reasoning active."]
        if safe_moves:
            segments.append(f"Safe cells identified: {len(safe_moves)}.")
        if mine_moves:
            segments.append(f"Mine cells identified: {len(mine_moves)}.")
        if note:
            segments.append(note)
        return " ".join(segments)

    def _neighbors(self, x, y, cols, rows):
        # Yield valid neighboring coordinates around one cell.
        for nx in range(max(0, x - 1), min(cols, x + 2)):
            for ny in range(max(0, y - 1), min(rows, y + 2)):
                if nx == x and ny == y:
                    continue
                yield nx, ny
