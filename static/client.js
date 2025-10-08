// ====== Socket.IO : forcer WebSocket + reconnect propre ======
const socket = io({
  transports: ['websocket'],
  upgrade: false,
  path: '/socket.io',
});
socket.on('connect_error', () => {
  setTimeout(() => socket.connect(), 1000);
});
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !socket.connected) {
    socket.connect();
  }
});

// ====== Sélecteurs ======
const $timer = document.getElementById("timer");
const $prompt = document.getElementById("prompt");
const $form = document.getElementById("formArea");
const $start = document.getElementById("startBtn");
const $submit = document.getElementById("submitBtn");
const $hint = document.getElementById("hintBtn");

const $chatLog = document.getElementById("chatLog");
const $chatInput = document.getElementById("chatInput");
const $chatSend = document.getElementById("chatSend");
const $authBtn = document.getElementById("authBtn");
const $playerName = document.getElementById("playerName");
const $playerCode = document.getElementById("playerCode");

let AUTH = false;
let NAME = "";
let timerInterval = null;

// ====== Chat util ======
function appendChat(m) {
  const d = document.createElement("div");
  d.textContent = (m.system ? "ℹ️ " : "") + m.msg;
  $chatLog?.prepend(d);
}

// ====== Timer local ======
function formatMMSS(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}
function startLocalTimer(initial) {
  if (!$timer) return;
  if (timerInterval) clearInterval(timerInterval);
  let rem = Math.max(0, parseInt(initial, 10) || 0);
  $timer.textContent = `⏳ ${formatMMSS(rem)}`;
  timerInterval = setInterval(() => {
    rem = Math.max(0, rem - 1);
    $timer.textContent = `⏳ ${formatMMSS(rem)}`;
    if (rem <= 0) { clearInterval(timerInterval); timerInterval = null; }
  }, 1000);
}

// ====== Auth ======
$authBtn?.addEventListener("click", () => {
  const name = ($playerName?.value || "").trim() || "Agent";
  const pcode = ($playerCode?.value || "").trim().toUpperCase();
  if (!pcode) return alert("Entre ton code joueur.");
  socket.emit("auth", { room: ROOM, name, player_code: pcode });
});
socket.on("auth_result", ({ ok, msg }) => {
  appendChat({ system: true, msg });
  if (ok) {
    AUTH = true;
    NAME = ($playerName?.value || "Agent").trim() || "Agent";
    [$start, $submit, $hint, $chatInput, $chatSend].forEach((el) => { if (el) el.disabled = false; });
    document.getElementById("authBox")?.remove();
  }
});

// ====== UI boutons ======
$start?.addEventListener("click", () => socket.emit("start", { room: ROOM }));
$hint?.addEventListener("click", () => socket.emit("hint", { room: ROOM }));

$chatSend?.addEventListener("click", sendChat);
$chatInput?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); sendChat(); } });
function sendChat() {
  const text = ($chatInput?.value || "").trim();
  if (!text) return;
  socket.emit("chat_message", { room: ROOM, name: NAME || "Agent", text });
  $chatInput.value = "";
}
socket.on("chat", appendChat);

// ====== State (serveur → client) ======
socket.on("state", (st) => {
  // Titre équipe
  const title = document.querySelector("header h2");
  if (title && st.room_label) title.textContent = `Équipe ${st.room_label}`;

  if (st.finished) {
    $prompt.innerHTML = st.success
      ? `<h3>✅ Victoire !</h3><p>Temps écoulé. Voulez-vous rejouer ?</p>`
      : `<h3>⛔ Mission terminée.</h3><p>Temps écoulé. Voulez-vous rejouer ?</p>`;

    // Bouton REJOUER explicite (fonctionne même après refresh)
    $form.innerHTML = `<button id="replayBtn" class="btn">🔁 Rejouer</button>`;
    const $replay = document.getElementById("replayBtn");

    // Option 1 : recharge l’URL avec ?reset=1
    $replay?.addEventListener("click", () => {
      const base = window.location.href.replace(/\?.*$/, "");
      window.location.href = base + "?reset=1";
    });

    if ($hint) $hint.textContent = "Indice";
    if ($start) $start.disabled = false; // “Démarrer” sert aussi de Rejouer (serveur gère)
    if (timerInterval){ clearInterval(timerInterval); timerInterval = null; }
    return;
  }

  // Chrono local
  startLocalTimer(st.remaining || 0);

  // Prompt
  const p = st.prompt || {};
  const instruction = (p.instruction || "").replace(/\n/g, "<br>");
  $prompt.innerHTML = `<h3>${p.title || "Salle"}</h3><p>${instruction}</p>`;

  // Indices
  if ($hint) {
    const left = ((st.hints?.total) || 0) - ((st.hints?.used) || 0);
    $hint.textContent = `Indice (${left >= 0 ? left : 0} rest.)`;
  }

  // -------- Rendu des 4 salles (version atelier) --------
  $form.innerHTML = ""; // reset UI

  // Salle 1 — Tri (select pour chaque item)
  if (p.type === "waste_v2") {
    let html = `<div class="card-grid">`;
    (p.objects || []).forEach(o => {
      html += `<div class="card">
        <div style="font-size:42px">${o.icon || ""}</div>
        <div style="font-weight:700;margin-top:4px">${o.label}</div>
        <select data-obj="${o.id}" class="binSelect" style="margin-top:6px;width:100%">
          <option value="">— Choisir un bac —</option>
          ${(p.bins || []).map(b => `<option value="${b.id}">${b.label}</option>`).join("")}
        </select>
      </div>`;
    });
    html += `</div>
      <div class="muted" style="margin-top:8px">Bacs :</div>
      <div class="card-grid" style="grid-template-columns:repeat(3,minmax(120px,1fr))">
        ${(p.bins || []).map(b => `
          <div class="card">
            <div style="font-size:32px">${b.icon || ""}</div>
            <div style="font-weight:700;margin-top:4px">${b.label}</div>
          </div>`).join("")}
      </div>`;
    $form.innerHTML = html;
  }

  // Salle 2 — Devinette Abeille (champ texte sans solution dans placeholder)
  if (p.type === "riddle_v2") {
    $form.innerHTML = `
      <div class="row"><input id="riddleAnswer" placeholder="Votre réponse…"></div>
      <div class="muted">2 minutes pour débattre et répondre.</div>
    `;
  }

  // Salle 3 — Énergie 180 MW (slider fossile = 0 par défaut ; à l’équipe de bouger)
  if (p.type === "energy_180") {
    const min = p.min ?? 0;
    const max = p.max ?? 60;
    const step = p.step ?? 1;
    const fossilStart = 0; // remis à zéro

    $form.innerHTML = `
      <div class="row muted">
        Éolien: ${p.eolien} MW — Solaire: ${p.solaire} MW — Hydro: ${p.hydro} MW
      </div>
      <div class="row">Gaz fossile
        <input type="range" id="fossil" min="${min}" max="${max}" step="${step}" value="${fossilStart}" oninput="updateEnergy()">
        <span id="fossilV">${fossilStart}</span> MW
      </div>
      <div class="row"><span class="tag">Total: <span id="totalMW">0</span> MW</span> <span id="okTag" class="tag" style="display:none">✅ Total atteint — tu peux valider</span></div>
      <p class="muted">Objectif: atteindre 180 MW et minimiser le fossile.</p>
    `;

    window.updateEnergy = function () {
      const f = +document.getElementById("fossil").value;
      document.getElementById("fossilV").textContent = f;
      const sum = (p.eolien || 0) + (p.solaire || 0) + (p.hydro || 0) + f;
      document.getElementById("totalMW").textContent = sum;
      document.getElementById("okTag").style.display = (sum === 180) ? "inline-block" : "none";
    };
    updateEnergy();
  }

  // Salle 4 — Gaïa (champ texte sans solution affichée)
  if (p.type === "gaia_v2") {
    $form.innerHTML = `
      <div class="row"><input id="gaiaAnswer" placeholder="Votre réponse (ex: 14 mars 2025)"></div>
      <div class="muted">Additionnez, divisez, convertissez en date du calendrier.</div>
    `;
  }
});

// ====== Submit ======
$submit?.addEventListener("click", () => {
  // Prélever les saisies selon la salle visible
  const selects = document.querySelectorAll(".binSelect"); // Salle 1
  const riddle = document.getElementById("riddleAnswer"); // Salle 2
  const fos = document.getElementById("fossil");          // Salle 3
  const gaia = document.getElementById("gaiaAnswer");     // Salle 4

  let payload = {};

  if (selects && selects.length) {
    const assign = {};
    selects.forEach(sel => { assign[sel.dataset.obj] = sel.value; });
    payload = { assign };
  }
  if (riddle) {
    payload = { answer: (riddle.value || "").trim() };
  }
  if (fos) {
    payload = { fossil: +fos.value };
  }
  if (gaia) {
    payload = { date: (gaia.value || "").trim() };
  }

  socket.emit("submit", { room: ROOM, payload });
});

