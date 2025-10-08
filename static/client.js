const socket = io();

const $timer = document.getElementById("timer");
const $prompt = document.getElementById("prompt");
const $form = document.getElementById("formArea");
const $start = document.getElementById("startBtn");
const $submit = document.getElementById("submitBtn");
const $hint = document.getElementById("hintBtn");
const $replay = document.getElementById("replayBtn");
const $chatLog = document.getElementById("chatLog");
const $chatInput = document.getElementById("chatInput");
const $chatSend = document.getElementById("chatSend");
const $authBtn = document.getElementById("authBtn");
const $playerName = document.getElementById("playerName");
const $playerCode = document.getElementById("playerCode");

let AUTH = false;
let NAME = "";
let timerInterval = null;

function appendChat(m){
  const d = document.createElement("div");
  d.textContent = (m.system ? "ℹ️ " : "") + m.msg;
  $chatLog.prepend(d);
}

// --------- Timer local (décrément 1s) ----------
function formatMMSS(sec){
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}
function startLocalTimer(initial){
  if (!$timer) return;
  if (timerInterval) clearInterval(timerInterval);
  let rem = Math.max(0, parseInt(initial,10) || 0);
  $timer.textContent = `⏳ ${formatMMSS(rem)}`;
  timerInterval = setInterval(()=>{
    rem = Math.max(0, rem - 1);
    $timer.textContent = `⏳ ${formatMMSS(rem)}`;
    if (rem <= 0) { clearInterval(timerInterval); timerInterval = null; }
  }, 1000);
}

// --------- Auth ----------
$authBtn?.addEventListener("click", ()=>{
  const name = ($playerName?.value || "").trim() || "Agent";
  const pcode = ($playerCode?.value || "").trim().toUpperCase();
  if(!pcode) return alert("Entre ton code joueur.");
  socket.emit("auth", { room: ROOM, name, player_code: pcode });
});
socket.on("auth_result", ({ok, msg})=>{
  appendChat({system:true, msg});
  if(ok){
    AUTH = true;
    NAME = ($playerName?.value || "Agent").trim() || "Agent";
    [$start, $submit, $hint, $chatInput, $chatSend].forEach(el=>{ if(el){ el.disabled = false; }});
    document.getElementById("authBox")?.remove();
  }
});

// --------- UI boutons ----------
$start?.addEventListener("click", ()=> socket.emit("start", { room: ROOM }));
$hint?.addEventListener("click", ()=> socket.emit("hint", { room: ROOM }));
$replay?.addEventListener("click", ()=> socket.emit("replay", { room: ROOM }));
$chatSend?.addEventListener("click", sendChat);
$chatInput?.addEventListener("keydown", (e)=>{ if(e.key==="Enter"){ e.preventDefault(); sendChat(); }});
function sendChat(){
  const text = ($chatInput?.value || "").trim();
  if(!text) return;
  socket.emit("chat_message", { room: ROOM, name: NAME || "Agent", text });
  $chatInput.value="";
}
socket.on("chat", appendChat);

// --------- State (serveur → client) ----------
socket.on("state", (st)=>{
  if (st.finished) {
    const res = st.success ? "✅ Victoire !" : "⛔ Mission terminée.";
    const score = st.score ?? 0;
    $prompt.innerHTML = `<h3>${res}</h3><p>Score final : <strong>${score}</strong></p>`;
    $form.innerHTML = "";
    if ($hint) $hint.textContent = "Indice";
    if (timerInterval){ clearInterval(timerInterval); timerInterval = null; }
  } else {
    // Démarre/Resynchronise le chrono local
    startLocalTimer(st.remaining || 0);

    const p = st.prompt || {};
    const instruction = (p.instruction || "").replace(/\n/g, "<br>");
    $prompt.innerHTML = `<h3>${p.title || "Salle"}</h3><p>${instruction}</p>`;

    // rendu des salles
    if (p.type === "tri") {
      // S1
      let html = `<div class="card-grid">`;
      (p.items||[]).forEach(o=>{
        html += `<div class="card">
          <div style="font-size:42px">${o.icon||""}</div>
          <div style="font-weight:700;margin-top:4px">${o.name}</div>
          <select data-obj="${o.id}" class="binSelect" style="margin-top:6px;width:100%">
            <option value="">— Choisir un bac —</option>
            ${(p.bins||[]).map(b=>`<option value="${b.id}">${b.name}</option>`).join("")}
          </select>
        </div>`;
      });
      html += `</div>
        <div class="muted" style="margin-top:8px">Bacs :</div>
        <div class="card-grid" style="grid-template-columns:repeat(3,minmax(120px,1fr))">
          ${(p.bins||[]).map(b=>`<div class="card"><div style="font-size:32px">${b.icon}</div><div style="font-weight:700;margin-top:4px">${b.name}</div></div>`).join("")}
        </div>`;
      $form.innerHTML = html;
    }
    else if (p.type === "riddle") {
      $form.innerHTML = `<input id="answer" placeholder="Réponse">`;
    }
    else if (p.type === "energy") {
      $form.innerHTML = `
        <div class="row"><span class="tag">Total: <span id="tot">0</span> MW</span></div>
        <div class="row">Éolien <input type="number" id="eol" min="${p.min}" max="${p.max}" value="0" oninput="updateTot()"> </div>
        <div class="row">Solaire <input type="number" id="sol" min="${p.min}" max="${p.max}" value="0" oninput="updateTot()"> </div>
        <div class="row">Hydraulique <input type="number" id="hyd" min="${p.min}" max="${p.max}" value="0" oninput="updateTot()"> </div>
        <div class="row">Gaz <input type="number" id="gaz" min="${p.min}" max="${p.max}" value="0" oninput="updateTot()"> </div>
        <p class="muted">Objectif : total = 180 MW, gaz ≤ 30.</p>`;
      window.updateTot = function(){
        const e = +document.getElementById("eol").value||0;
        const s = +document.getElementById("sol").value||0;
        const h = +document.getElementById("hyd").value||0;
        const g = +document.getElementById("gaz").value||0;
        document.getElementById("tot").textContent = e+s+h+g;
      };
      updateTot();
    }
    else if (p.type === "gaia") {
      $form.innerHTML = `<input id="date" placeholder="ex: 14 mars 2025">`;
    } else {
      $form.innerHTML = "";
    }
  }

  if ($hint) {
    const left = ((st.hints?.total) || 0) - ((st.hints?.used) || 0);
    $hint.textContent = `Indice (${left >= 0 ? left : 0} rest.)`;
  }
});

// --------- Submit ----------
$submit?.addEventListener("click", ()=>{
  const selects = document.querySelectorAll(".binSelect"); // S1
  const ans = document.getElementById("answer");           // S2
  const eol = document.getElementById("eol");              // S3
  const sol = document.getElementById("sol");
  const hyd = document.getElementById("hyd");
  const gaz = document.getElementById("gaz");
  const dt = document.getElementById("date");              // S4

  let payload = {};
  if (selects && selects.length){
    const assign = {};
    // mapping: bin_id -> item_id  (on lit la valeur choisie pour chaque objet et on inverse)
    // ici plus simple: on parcourt les selects, on lit l'option choisie (bin)
    // => on construit {bin: item}
    selects.forEach(sel=>{
      const item = sel.dataset.obj;
      const bin = sel.value;
      if (bin) payload[bin] = item;
    });
    payload = { assign: payload };
  }
  if (ans) payload = { answer: (ans.value||"").trim() };
  if (eol && sol && hyd && gaz) {
    payload = { mix: {
      eolien: +(eol.value||0), solaire: +(sol.value||0),
      hydro: +(hyd.value||0), gaz: +(gaz.value||0)
    }};
  }
  if (dt) payload = { date: (dt.value||"").trim() };

  socket.emit("submit", { room: ROOM, payload });
});
