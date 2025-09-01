// ---- config ----
const API = ""; // same-origin
const boardEl = document.getElementById("board");
const turnEl = document.getElementById("turn");
const sidInput = document.getElementById("sidInput");
const errEl = document.getElementById("err");
const okEl = document.getElementById("ok");
const statusEl = document.getElementById("status");
const autoBlack = document.getElementById("autoBlack");

document.getElementById("reloadBtn").onclick = () => loadState();
document.getElementById("newBtn").onclick = () => newSession();

let S = null;                  // server state {board, turn, fen}
let selected = null;           // "e2"
let legalTargets = new Set();  // Set<"e4">

const files = ["a","b","c","d","e","f","g","h"];
const sqId = (f,r)=> files[f] + (8-r);
const toFR = (sq)=> ({ f: files.indexOf(sq[0]), r: 8 - parseInt(sq[1]) });

async function api(path, opts={}) {
  errEl.textContent = ""; okEl.textContent = "";
  const res = await fetch(API + path, { headers: { "content-type":"application/json" }, ...opts });
  if (!res.ok) {
    const txt = await res.text();
    errEl.textContent = `${res.status} ${path} ${txt}`;
    throw new Error(`${res.status} ${path}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

async function ensureSession() {
  let sid = sidInput.value.trim();
  if (sid) return sid;
  const created = await api(`/sessions`, { method: "POST", body: JSON.stringify({ ruleset: "chess" }) });
  sidInput.value = created.id;
  okEl.textContent = `Created session ${created.id}`;
  return created.id;
}

async function loadState() {
  selected = null; legalTargets.clear();
  const sid = await ensureSession();
  S = await api(`/sessions/${sid}/state`);
  drawBoard();
  turnEl.textContent = `Turn: ${S.turn} | FEN: ${S.fen}`;
  statusEl.textContent = S.status ? `Status: ${S.status}` : "";
  if (S.turn === "b" && autoBlack.checked) await aiTurn();
}

function drawBoard() {
  boardEl.innerHTML = "";
  for (let r=0;r<8;r++){
    for (let f=0;f<8;f++){
      const sq = sqId(f,r);
      const div = document.createElement("div");
      div.className = `sq ${(f+r)%2? "dark":"light"}${selected===sq?" sel":""}${legalTargets.has(sq)?" hl":""}`;
      div.dataset.sq = sq;
      div.onclick = onSquareClick;
      div.textContent = pieceToGlyph(S.board[r][f]);
      boardEl.appendChild(div);
    }
  }
}

function pieceToGlyph(p) {
  const map = { p:"♟", r:"♜", n:"♞", b:"♝", q:"♛", k:"♚", P:"♙", R:"♖", N:"♘", B:"♗", Q:"♕", K:"♔" };
  return map[p] || "";
}

async function onSquareClick(ev) {
  const sq = ev.currentTarget.dataset.sq;
  const fr = toFR(sq);
  const piece = S.board[fr.r][fr.f];

  const isWhitePiece = piece && piece === piece.toUpperCase();
  if (S.turn === "w" && isWhitePiece && selected !== sq) {
    selected = sq;
    legalTargets = new Set(await getLegalTargets(sq));
    return drawBoard();
  }

  if (selected && legalTargets.has(sq)) {
    const uci = selected + sq;
    await submitMove(uci);
    return;
  }

  selected = null; legalTargets.clear(); drawBoard();
}

async function getLegalTargets(fromSq) {
  const sid = sidInput.value.trim();
  const data = await api(`/sessions/${sid}/legal?from=${fromSq}`);
  return data.to || [];
}

async function submitMove(uci) {
  const sid = sidInput.value.trim();
  await api(`/sessions/${sid}/move`, { method:"POST", body: JSON.stringify({ uci }) });
  await loadState();
}

async function aiTurn() {
  const data = await api(`/chess/ai/next`, { method:"POST", body: JSON.stringify({ fen: S.fen }) });
  await submitMove(data.uci);
}

loadState().catch(err => console.error(err));
