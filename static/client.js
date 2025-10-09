// static/client.js
const socket = io();

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
const $replay = document.getElementById("replayBtn"); // dans le header si présent

let AUTH = false;
let NAME = "";
let timerInterval = null;

function appendChat(m){
  const d = document.createElement("div");
  d.textContent = (m.system ? "ℹ️ " : "") + m.msg;
  $chatLog?.prepend(d);
}

// ---------- Timer local ----------
function fmt(sec){
  const m = String(Math.floor(sec/60)).padStart(2,"0");
  const s = String(sec%60).padStart(2,"0");
  return `${m}:${s}`;
}
function startLocalTimer(initial){
  if (!$timer) return;
  if (timerInterval) clearInterval(timerInterval);
  let rem = Math.max(0, parseInt(initial,10) || 0);
  $timer.textContent = `⏳ ${fmt(rem)}`;
  timerInterval = setInterval(()=>{
    rem = Math.max(0, rem-1);
    $timer.textContent = `⏳ ${fmt(rem)}`;
    if (rem <= 0){
    clearInterval(timerInterval);
    timerInterval = null;
    showTimeoutPopup(); // ← affiche la popup quand le temps est écoulé
}
  },1000);
}
function showTimeoutPopup() {
  const modal = document.getElementById("timeoutModal");
  if(!modal) { console.error("❌ Popup non trouvée"); return; }
  modal.style.display = "flex"; // afficher la popup

  // Désactiver boutons de la salle
  [$submit, $hint, $start].forEach(el=>{ if(el) el.disabled=true; });

  // Bouton Rejouer
  document.getElementById("closeModal").onclick = function() {
    modal.style.display = "none";
    socket.emit("replay", { room: ROOM }); // Rejouer
  };
}

// ---------- Auth ----------
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

    // === Afficher la popup de contexte ===
    const modal = document.getElementById("contextModal");
    modal.style.display = "flex";

    document.getElementById("closeContext").onclick = () => {
      modal.style.display = "none";
  };
  }
});

// ---------- Chat ----------
$chatSend?.addEventListener("click", sendChat);
$chatInput?.addEventListener("keydown", (e)=>{ if(e.key==="Enter"){ e.preventDefault(); sendChat(); }});
function sendChat(){
  const text = ($chatInput?.value || "").trim();
  if(!text) return;
  socket.emit("chat_message", { room: ROOM, name: NAME || "Agent", text });
  $chatInput.value="";
}
socket.on("chat", appendChat);

// ---------- Boutons top ----------
$start?.addEventListener("click", ()=> socket.emit("start", { room: ROOM }));
$hint?.addEventListener("click", ()=> socket.emit("hint", { room: ROOM }));
$replay?.addEventListener("click", ()=> socket.emit("replay", { room: ROOM }));

// ---------- Render state ----------
socket.on("state", (st)=>{
  if (st.finished) {
    $prompt.innerHTML = st.success
      ? `<h3>✅ Mission accomplie !</h3><p>Vous avez <strong>sauvez</strong> la planete.</p>`
      : `<h3>⛔ Mission terminée.</h3><p>Vous avez <strong>ruinez</strong>la planete.</p>`;
    $form.innerHTML = `
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button id="replayLocal" class="btn">🔁 Rejouer</button>
      </div>`;
    document.getElementById("replayLocal")?.addEventListener("click", ()=>{
      socket.emit("replay", { room: ROOM });
    });
    if (timerInterval){ clearInterval(timerInterval); timerInterval=null; }
    return;
  }

  // chrono
  startLocalTimer(st.remaining || 0);

  const p = st.prompt || {};
  const instruction = (p.instruction || "").replace(/\n/g,"<br>");
  $prompt.innerHTML = `<h3>${p.title || "Salle"}</h3><p>${instruction}</p>`;

  if ($hint) {
    const left = ((st.hints?.total)||0) - ((st.hints?.used)||0);
    $hint.textContent = `Indice (${left>=0?left:0} rest.)`;
  }

  // UI par type
  if (p.type === "waste_v2") {
    let html = `<div class="card-grid">`;
    (p.objects||[]).forEach(o=>{
      html += `<div class="card">
        <div class="big">${o.icon||""}</div>
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
      ${(p.bins||[]).map(b=>`
        <div class="card">
          <div class="big">${b.icon||""}</div>
          <div style="font-weight:700;margin-top:4px">${b.name}</div>
        </div>`).join("")}
    </div>`;
    $form.innerHTML = html;
  }
  else if (p.type === "riddle") {
    $form.innerHTML = `<input id="answer" placeholder="Votre réponse">`;
  }
  else if (p.type === "energy_v2") {
    $form.innerHTML = `
      <div class="row">Éolien (max ${p.maxE}) <input type="range" id="eolien" min="${p.min}" max="${p.maxE}" value="${p.start?.eolien??0}" oninput="updateMix()"> <span id="eolienV">${p.start?.eolien??0}</span> MW</div>
      <div class="row">Solaire (max ${p.maxS}) <input type="range" id="solaire" min="${p.min}" max="${p.maxS}" value="${p.start?.solaire??0}" oninput="updateMix()"> <span id="solaireV">${p.start?.solaire??0}</span> MW</div>
      <div class="row">Hydraulique (max ${p.maxH}) <input type="range" id="hydro" min="${p.min}" max="${p.maxH}" value="${p.start?.hydro??0}" oninput="updateMix()"> <span id="hydroV">${p.start?.hydro??0}</span> MW</div>
      <div class="row">Fossile (max ${p.maxF}) <input type="range" id="fossile" min="${p.min}" max="${p.maxF}" value="${p.start?.fossile??0}" oninput="updateMix()"> <span id="fossileV">${p.start?.fossile??0}</span> MW</div>
      <div class="row"><span class="tag">Total: <span id="mixTotal">0</span> MW</span></div>`;
    window.updateMix = function(){
      const e = +document.getElementById("eolien").value;
      const s = +document.getElementById("solaire").value;
      const h = +document.getElementById("hydro").value;
      const f = +document.getElementById("fossile").value;
      document.getElementById("eolienV").textContent=e;
      document.getElementById("solaireV").textContent=s;
      document.getElementById("hydroV").textContent=h;
      document.getElementById("fossileV").textContent=f;
      document.getElementById("mixTotal").textContent = e+s+h+f;
    };
    updateMix();
  }
  else if (p.type === "gaia") {
    $form.innerHTML = `<input id="gaiaAnswer">`;
  } else {
    $form.innerHTML = "";
  }
});

// ---------- Submit ----------
$submit?.addEventListener("click", ()=>{
  const ans = document.getElementById("answer");   // salle 2
  const date = document.getElementById("gaiaAnswer");    // salle 4
  const selects = document.querySelectorAll(".binSelect"); // salle 1
  const e = document.getElementById("eolien");     // salle 3
  const s = document.getElementById("solaire");
  const h = document.getElementById("hydro");
  const f = document.getElementById("fossile");

  let payload = {};

  if (selects && selects.length){
    const assign = {};
    selects.forEach(sel => { if(sel.value) assign[sel.value] = sel.dataset.obj; });
    payload = { assign };
  }
  if (ans) payload = { answer: ans.value.trim() };
  if (e && s && h && f){
    payload = { mix: {
      eolien: +e.value, solaire: +s.value, hydro: +h.value, fossile: +f.value
    }};
  }
  if (date) payload = { date: date.value.trim() };

  socket.emit("submit", { room: ROOM, payload });
});

