# Adversarial Multi-Agent Minesweeper Solver

A Minesweeper AI where two agents compete on the same shared board. Each agent uses a three-tier CSP solver under the hood, but in Battle mode the objective shifts from "minimize my mine risk" to "which move leaves my opponent in the hardest possible position?" Agents evaluate candidate moves using Minimax with Alpha-Beta pruning to look ahead and exploit opponent vulnerability.

This is a CPSC 481 (Artificial Intelligence) capstone project at California State University, Fullerton.


# run these commands in powershell to start program (change first line to your file path)

```bash
cd "C: "file path" "
python -m pip uninstall -y setuptools
python -m pip install "setuptools<81"
python -m pip install --force-reinstall eel==0.14.0
python -c "import pkg_resources; import eel; print('eel import worked')"
python minesweeperGUI.py
```
Browser will open to game, you can set difficulty, or classic game mode vs adversarial adgent mode.

## Team

**Course:** CPSC 481 — Artificial Intelligence, California State University, Fullerton

| Name |
|------|
| Alberto Molina |
| Arai Leyva |
| Dylan Ruiz |
