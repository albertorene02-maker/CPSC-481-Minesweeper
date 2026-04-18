var size = 0;
var bombs = 0;
var gameState = null;
var selectedDifficulty = "easy";
var selectedMode = "classic";

function difficultyConfig(mode) {
  if (mode === "easy") {
    return { size: 10, bombs: 15, zoomOut: false };
  }
  if (mode === "medium") {
    return { size: 18, bombs: 45, zoomOut: false };
  }
  if (mode === "hard") {
    return { size: 24, bombs: 100, zoomOut: true };
  }
  return { size: 30, bombs: 200, zoomOut: true };
}

async function startNew(mode) {
  selectedDifficulty = mode;
  const config = difficultyConfig(mode);
  size = config.size;
  bombs = config.bombs;

  const board = document.getElementById("board");
  board.classList.toggle("zoomOut", config.zoomOut);

  const state = await eel.makeBoard(size, bombs, selectedMode)();
  applyState(state);
}

function setMode(mode) {
  selectedMode = mode;
  document.getElementById("modeLabel").innerText =
    mode === "adversarial" ? "Adversarial Agents" : "Classic";
  startNew(selectedDifficulty);
}

function applyState(state) {
  gameState = state;
  renderBoard(state.board);
  renderStatus(state);
}

function renderBoard(boardState) {
  let toAdd = "";
  for (let y = 0; y < boardState.length; y++) {
    for (let x = 0; x < boardState[y].length; x++) {
      const cell = boardState[y][x];
      const name = `${y}-${x}`;
      const classes = ["cell"];
      let value = " ";

      if (cell === null) {
        classes.push("empty");
      } else if (cell === "F") {
        classes.push("flagged", "empty");
      } else if (cell === "B") {
        classes.push("bomb");
      } else if (cell === 0) {
        classes.push("on");
      } else {
        classes.push("on", "number");
        value = `${cell}`;
      }

      toAdd += `<input class="${classes.join(
        " "
      )}" type="button" onmousedown="handleCell(this, event)" name="${name}" value="${value}" />`;
    }
    toAdd += "</br>";
  }
  document.getElementById("board").innerHTML = toAdd;
}

function renderStatus(state) {
  const title = document.getElementById("h1");
  title.classList.remove("won");
  title.classList.remove("lost");
  if (state.gameOver) {
    if (state.winner) {
      title.innerText =
        state.mode === "adversarial"
          ? state.winner === "Tie"
            ? "Tie Game"
            : `Winner: Agent ${state.winner}`
          : "You Win";
      if ((state.mode === "adversarial" && state.winner !== "Tie") || state.winner === "Human") {
        title.classList.add("won");
      }
    } else {
      title.innerText = "Game Over";
      title.classList.add("lost");
    }
  } else {
    title.innerText = "Minesweeper";
  }

  document.getElementById("status").innerText = state.statusText;
  document.getElementById("reasoning").innerText = state.reasoning || "No solver output yet.";
  document.getElementById("turn").innerText =
    state.mode === "adversarial"
      ? `Current turn: Agent ${state.currentPlayer}`
      : "Current turn: Human";
}

async function handleCell(element, event) {
  if (!gameState || gameState.gameOver) {
    return;
  }

  const x = parseInt(element.name.split("-")[1]);
  const y = parseInt(element.name.split("-")[0]);

  if (event.button === 0 && !element.classList.contains("flagged")) {
    const state = await eel.clickedOnTheCell(x, y)();
    applyState(state);
  } else if (event.button === 2) {
    event.preventDefault();
    const state = await eel.toggleFlag(x, y)();
    applyState(state);
  }
}

async function solverHint() {
  const state = await eel.requestSolverHint()();
  applyState(state);
}

async function runAgentTurn() {
  const state = await eel.runAgentTurn()();
  applyState(state);
}

var themes = ["pink", "green", "dark", "red", "yellow", "armin", "brown"];
function changeTheme(name) {
  const body = document.getElementById("body");
  body.className = "";

  if (themes.includes(name)) {
    body.classList.add(name);
  } else {
    body.classList.add("pink");
  }
}

changeTheme("pink");
setMode("classic");
