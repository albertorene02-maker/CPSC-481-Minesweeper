# CPSC-481-Minesweeper

# run these commands in powershell to start program (change first line to your file path)

cd "C: "file path" "
python -m pip uninstall -y setuptools
python -m pip install "setuptools<81"
python -m pip install --force-reinstall eel==0.14.0
python -c "import pkg_resources; import eel; print('eel import worked')"
python minesweeperGUI.py

# Course: CPSC 481 — Artificial Intelligence, California State University, Fullerton

Name
Alberto Molina
Arai Leyva
Dylan Ruiz
