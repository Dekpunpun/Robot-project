/* ---------------------------------------------------------------------------
 * GAME
 * ------------------------------------------------------------------------- */

const state = {
  history: [],      // [{ role, content }] — model-facing transcript
  presented: [],    // evidence ids already shown to the suspect
  unlocked: [],     // evidence ids visible on the board
  pressure: 0,
  composure: "steady",
  turns: 0,         // questions asked — the score cares how fast you got there
  lit: 0,           // meter cells currently on, so a gain can be animated
  over: false,
  busy: false,
  started: false,
};

const el = (id) => document.getElementById(id);

/* ------------------------------ title screen ----------------------------- */

function startGame() {
  if (state.started) return;
  state.started = true;

  SFX.unlock();
  SFX.start();
  el("titleScreen").classList.add("gone");
  el("chatInput").focus();
  checkConnection();
}

/* Match on code as well as key: some input paths (and remapped layouts) leave
   `key` empty, and a title screen that ignores Enter looks broken. */
document.addEventListener("keydown", (e) => {
  const isStart =
    ["Enter", " ", "Spacebar"].includes(e.key) ||
    ["Enter", "NumpadEnter", "Space"].includes(e.code);
  if (!state.started && isStart) {
    e.preventDefault();
    startGame();
  }
});
el("titleScreen").addEventListener("click", startGame);

/* ---------------------------------- boot --------------------------------- */

function init() {
  state.history = [];
  state.presented = [];
  state.unlocked = CASE.evidence.filter((e) => e.available).map((e) => e.id);
  state.pressure = 0;
  state.composure = "steady";
  state.turns = 0;
  state.lit = 0;
  state.over = false;
  state.busy = false;

  el("caseTitle").textContent = CASE.title;
  el("suspectName").textContent = CASE.suspect.name;
  el("suspectRole").textContent = CASE.suspect.role;

  Portrait.mount(el("portrait"));
  Portrait.mount(el("titlePortrait"));
  Portrait.reset();

  renderCaseFile();
  renderEvidence();
  renderMeter();

  el("chatLog").innerHTML = "";
  addMessage("suspect", CASE.opener);
  state.history.push({ role: "assistant", content: CASE.opener });

  el("chatInput").disabled = false;
  el("sendBtn").disabled = false;
}

/* Fail loudly at boot rather than silently on the player's first question. */
async function checkConnection() {
  if (location.protocol === "file:") {
    addMessage(
      "evidence",
      `<b>Opened straight from disk.</b> The browser will block every call to the model
       (LM Studio sends no CORS headers). Serve the game instead:
       <code>node server.mjs</code> — then open <code>http://localhost:5173</code>.`
    );
    SFX.error();
    return;
  }

  try {
    const models = await LLM.listModels();
    if (!models.some((id) => !/embed|rerank/i.test(id))) {
      addMessage(
        "evidence",
        `<b>No chat model loaded.</b> The server is up but only has embedding models.
         Load a chat model in LM Studio, then reload this page.`
      );
      SFX.error();
    }
  } catch (err) {
    addMessage(
      "evidence",
      `<b>Can't reach the model.</b> ${escapeHtml(err.message)}<br />
       Start LM Studio's local server, then reload. Questions will fail until then.`
    );
    SFX.error();
  }
}

/* -------------------------------- rendering ------------------------------ */

function renderCaseFile() {
  el("casefileBody").innerHTML = `
    <div class="cf-block">
      <h3>Victim</h3>
      <p class="cf-name">${CASE.victim.name}</p>
      <p class="cf-sub">${CASE.victim.detail}</p>
    </div>

    <div class="cf-block">
      <h3>Scene</h3>
      <p>${CASE.scene}</p>
    </div>

    <div class="cf-block">
      <h3>Timeline</h3>
      <ul class="timeline">
        ${CASE.timeline
          .map((t) => `<li><span class="t-time">${t.time}</span><span>${t.text}</span></li>`)
          .join("")}
      </ul>
    </div>

    <div class="cf-block">
      <h3>Established Facts</h3>
      <ul class="facts">${CASE.facts.map((f) => `<li>${f}</li>`).join("")}</ul>
    </div>

    <div class="cf-block">
      <h3>In the Room</h3>
      <p class="cf-name">${CASE.suspect.name}</p>
      <p class="cf-sub">${CASE.suspect.role}</p>
    </div>
  `;
}

function renderEvidence(freshId) {
  const body = el("evidenceBody");
  const visible = CASE.evidence.filter((e) => state.unlocked.includes(e.id));
  const locked = CASE.evidence.length - visible.length;

  body.innerHTML =
    visible
      .map((e) => {
        const used = state.presented.includes(e.id);
        return `
        <article class="ev ${used ? "used" : ""} ${e.id === freshId ? "new" : ""}">
          <div class="ev-head">
            <span class="ev-icon">${e.icon}</span>
            <h3>${e.name}</h3>
          </div>
          <p class="ev-summary">${e.summary}</p>
          <p class="ev-detail">${e.detail}</p>
          <button class="btn btn-present" data-present="${e.id}" ${used ? "disabled" : ""}>
            ${used ? "Presented" : "Present"}
          </button>
        </article>`;
      })
      .join("") +
    (locked
      ? `<p class="ev-locked">${locked} item${locked > 1 ? "s" : ""} still with forensics.
         Apply pressure and they'll come through.</p>`
      : "");
}

/* A bar of discrete cells — a smoothly sliding fill would give the game away
   as a modern one. The newest cell flashes so a gain reads at a glance. */
const CELLS = 20;

function renderMeter() {
  const p = Math.min(100, Math.round(state.pressure));
  const lit = Math.round((p / 100) * CELLS);
  const level = p >= 70 ? "high" : p >= 35 ? "mid" : "low";
  const track = el("meterCells");

  if (track.children.length !== CELLS) {
    track.innerHTML = Array.from({ length: CELLS }, () => "<span class='cell'></span>").join("");
  }

  Array.from(track.children).forEach((cell, i) => {
    const on = i < lit;
    cell.className = `cell${on ? " on" : ""}${on && i >= state.lit ? " fresh" : ""}`;
    if (on) cell.dataset.level = level;
    else delete cell.dataset.level;
  });

  state.lit = lit;
  el("meterValue").textContent = `${p}%`;

  const status = el("suspectStatus");
  status.textContent = { steady: "composed", rattled: "rattled", cracking: "cracking" }[state.composure];
  status.className = `status ${state.composure}`;
  Portrait.set(state.composure);
}

function addMessage(who, text) {
  const log = el("chatLog");
  const wrap = document.createElement("div");
  wrap.className = `msg msg-${who}`;

  if (who === "suspect") {
    wrap.innerHTML = `<div class="avatar">${CASE.suspect.portraitInitials}</div>
                      <div class="bubble">${escapeHtml(text)}</div>`;
  } else if (who === "evidence") {
    wrap.innerHTML = `<div class="bubble">${text}</div>`;
  } else {
    wrap.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  }

  log.appendChild(wrap);
  log.scrollTop = log.scrollHeight;
  return wrap;
}

/* Dialogue arrives a character at a time with a blip, the way a text box in a
   console game does. Clicking the log skips to the end of the line. */
let skipTyping = null;

function typeMessage(text) {
  return new Promise((resolve) => {
    const node = addMessage("suspect", "");
    const bubble = node.querySelector(".bubble");
    const log = el("chatLog");
    const caret = document.createElement("span");
    caret.className = "caret";

    let i = 0;

    const finish = () => {
      clearInterval(timer);
      bubble.textContent = text;
      skipTyping = null;
      log.scrollTop = log.scrollHeight;
      resolve(node);
    };

    const timer = setInterval(() => {
      if (i >= text.length) return finish();
      const ch = text[i++];
      bubble.textContent = text.slice(0, i);
      bubble.appendChild(caret);
      if (i % 2 === 0 && !/\s/.test(ch)) SFX.speak();
      log.scrollTop = log.scrollHeight;
    }, 24);

    skipTyping = finish;
  });
}

el("chatLog").addEventListener("click", () => skipTyping?.());

/* A local model can take a minute or more per turn. Three static dots are
   indistinguishable from a hang, so count the seconds out loud. */
function showTyping() {
  const node = addMessage("suspect", "");
  node.classList.add("typing");
  node.querySelector(".bubble").innerHTML =
    `<i></i><i></i><i></i><span class="wait"></span>`;

  const label = node.querySelector(".wait");
  const started = Date.now();

  const tick = () => {
    const s = Math.round((Date.now() - started) / 1000);
    if (s < 4) return;
    label.textContent = s < 25 ? `THINKING ${s}s` : `STILL THINKING ${s}s`;
  };

  const timer = setInterval(tick, 1000);
  node.stopTimer = () => clearInterval(timer);
  return node;
}

/* Always clear the interval — a bare .remove() would leak it. */
function clearTyping(node) {
  node.stopTimer?.();
  node.remove();
}

function shake() {
  const board = el("board");
  board.classList.remove("shake");
  void board.offsetWidth; // restart the animation
  board.classList.add("shake");
  setTimeout(() => board.classList.remove("shake"), 600);
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

/* ------------------------------ model plumbing --------------------------- */

/* The model appends a hidden control line. Pull it off before display. */
function parseReply(raw) {
  const tell = raw.match(/\[\[\s*TELL[^\]]*\]\]/i);
  let composure = null;
  let pressure = null;

  if (tell) {
    /* Match the whole value, not the first alternative — a model that echoes
       the template back ("composure=steady|rattled|cracking") has told us
       nothing, and must not be read as a choice of "steady". */
    const c = tell[0].match(/composure\s*=\s*([a-z|]+)/i);
    const p = tell[0].match(/pressure\s*=\s*\+?(-?\d+)/i);
    if (c && !c[1].includes("|") && ["steady", "rattled", "cracking"].includes(c[1].toLowerCase())) {
      composure = c[1].toLowerCase();
    }
    if (p) pressure = Math.max(0, Math.min(30, parseInt(p[1], 10)));
  }

  const text = raw
    .replace(/<think>[\s\S]*?<\/think>/gi, "")  // reasoning models that inline their scratchpad
    .replace(/<think>[\s\S]*$/i, "")            // ...or never close the tag
    .replace(/\[\[[^\]]*\]\]/g, "")             // control line, and any stray bracket noise
    .replace(/\*[^*]*\*/g, "")                  // stage directions if the model slips
    .replace(/^["“]|["”]$/g, "")                // wrapping quotes around the whole line
    .trim();

  return { text: text || "…", composure, pressure };
}

async function askSuspect(playerLine, { evidenceId = null } = {}) {
  if (state.busy || state.over) return;
  state.busy = true;
  state.turns++;
  el("sendBtn").disabled = true;

  state.history.push({ role: "user", content: playerLine });
  const typing = showTyping();

  try {
    const messages = [
      { role: "system", content: buildSystemPrompt(state) },
      ...state.history,
    ];
    const raw = await LLM.chat(messages);
    const { text, composure, pressure } = parseReply(raw);

    clearTyping(typing);
    state.history.push({ role: "assistant", content: text });

    const before = state.pressure;
    applyPressure(pressure, evidenceId);
    state.composure = deriveComposure(composure);

    /* Land the hit first, then let him speak through it. */
    if (state.pressure > before) {
      Portrait.hit();
      shake();
      SFX.hurt();
    }
    renderMeter();

    await typeMessage(text);
    checkUnlocks();
  } catch (err) {
    clearTyping(typing);
    SFX.error();

    /* Roll the turn back so the player can simply try again: drop the unanswered
       question, and put the evidence back on the board unspent. */
    state.history.pop();
    state.turns--;
    if (evidenceId) {
      state.presented = state.presented.filter((id) => id !== evidenceId);
      renderEvidence();
    }

    addMessage(
      "evidence",
      `<b>Connection failed.</b> ${escapeHtml(err.message)}<br />
       Check the LLM settings (⚙) — the prototype expects an OpenAI-compatible
       server at <code>${escapeHtml(LLM.get().baseUrl)}</code>.
       Nothing was spent; try again.`
    );
  } finally {
    state.busy = false;
    el("sendBtn").disabled = state.over;
    el("chatInput").focus();
  }
}

/* Model-reported pressure is the signal; presented evidence sets a floor so a
   stubborn model can't stall the game outright. */
function applyPressure(reported, evidenceId) {
  let gain = reported ?? 0;

  if (evidenceId) {
    const ev = CASE.evidence.find((e) => e.id === evidenceId);
    gain = Math.max(gain, Math.round(ev.pressure * 0.6));
  }

  state.pressure = Math.min(100, state.pressure + gain);
}

/* The meter is the source of truth for how cornered the suspect is. A model
   will happily report "cracking" on the first piece of evidence, which reads as
   a collapse the player hasn't earned — so its self-report may only ever pull
   composure one step above what the pressure actually supports. */
const LEVELS = ["steady", "rattled", "cracking"];

function deriveComposure(reported) {
  const floor = state.pressure >= 70 ? 2 : state.pressure >= 35 ? 1 : 0;
  const ceiling = Math.min(LEVELS.length - 1, floor + 1);
  const claimed = reported ? LEVELS.indexOf(reported) : -1;
  return LEVELS[Math.min(Math.max(claimed, floor), ceiling)];
}

function checkUnlocks() {
  let fresh = null;

  for (const ev of CASE.evidence) {
    if (state.unlocked.includes(ev.id) || !ev.unlock) continue;

    const byPressure = ev.unlock.pressure != null && state.pressure >= ev.unlock.pressure;
    const byEvidence =
      ev.unlock.afterPresenting && state.presented.includes(ev.unlock.afterPresenting);

    if (byPressure || byEvidence) {
      state.unlocked.push(ev.id);
      fresh = ev.id;
      addMessage(
        "evidence",
        `<b>Forensics.</b> New item on the board: <b>${escapeHtml(ev.name)}</b> — ${escapeHtml(ev.summary)}`
      );
    }
  }

  if (fresh) {
    renderEvidence(fresh);
    SFX.unlock_();
  }
}

/* --------------------------------- actions ------------------------------- */

function presentEvidence(id) {
  if (state.busy || state.over || state.presented.includes(id)) return;
  const ev = CASE.evidence.find((e) => e.id === id);

  state.presented.push(id);
  renderEvidence();
  SFX.present();

  addMessage("evidence", `<b>You place it on the table.</b> ${escapeHtml(ev.name)} — ${escapeHtml(ev.summary)}`);
  askSuspect(
    `[EVIDENCE PRESENTED: ${ev.name} — ${ev.detail} This contradicts: ${ev.contradicts}]`,
    { evidenceId: id }
  );
}

function openAccusation() {
  if (state.over) return;
  SFX.select();
  const held = CASE.conviction.requires.filter((id) => state.presented.includes(id)).length;
  el("accuseText").innerHTML =
    `You are about to close the case on <b>${escapeHtml(CASE.suspect.name)}</b>. ` +
    `A verdict only sticks if the evidence you've put to ${CASE.suspect.pronouns.split("/")[0]} supports it. ` +
    `<br /><br /><span class="hint">EVIDENCE ${state.presented.length}/${CASE.evidence.length} &middot; PRESSURE ${Math.round(state.pressure)}%</span>` +
    (held < CASE.conviction.requires.length
      ? `<br /><span class="hint">SOMETHING ISN'T NAILED DOWN</span>`
      : "");
  el("accuseModal").classList.remove("hidden");
}

/* A letter grade, arcade style: did you convict, and how cleanly? */
function gradeRun(rightVerdict, hasProof) {
  if (!rightVerdict) return { letter: "F", caption: "CASE GONE COLD" };
  if (!hasProof) return { letter: "D", caption: "THROWN OUT ON APPEAL" };
  if (state.turns <= 10) return { letter: "S", caption: "SURGICAL" };
  if (state.turns <= 16) return { letter: "A", caption: "SOLID POLICE WORK" };
  if (state.turns <= 24) return { letter: "B", caption: "GOT THERE IN THE END" };
  return { letter: "C", caption: "A LONG NIGHT" };
}

function resolveAccusation(verdict) {
  el("accuseModal").classList.add("hidden");
  state.over = true;
  el("chatInput").disabled = true;
  el("sendBtn").disabled = true;

  const c = CASE.conviction;
  const hasProof =
    c.requires.every((id) => state.presented.includes(id)) && state.pressure >= c.minPressure;
  const rightVerdict = verdict === c.verdict;

  const [subj, obj] = CASE.suspect.pronouns.split("/");
  let title, text;

  if (rightVerdict && hasProof) {
    title = "Case Closed";
    text =
      `The charge holds. You put ${CASE.suspect.name} at the scene after ${subj} swore ${subj} was ` +
      `home, and you tied the killing to a motive worth killing over. The confession was a ` +
      `formality by the time it came.`;
  } else if (rightVerdict) {
    const missing = c.requires
      .filter((id) => !state.presented.includes(id))
      .map((id) => CASE.evidence.find((e) => e.id === id).name);
    title = "Right Suspect, Thin Case";
    text =
      `You named the killer — and the prosecutor threw it straight back at you. ` +
      (missing.length
        ? `You never put this in front of ${obj}: ${missing.join(", ")}.`
        : `You never applied enough pressure to make any of it stick.`);
  } else {
    title = "Wrong Call";
    text =
      `You clear ${CASE.suspect.name}, and the file goes cold on a shelf. ` +
      `The one person who could have told you what happened in Lab B walks out of the Thorne.`;
  }

  const { letter, caption } = gradeRun(rightVerdict, hasProof);

  el("resultTitle").textContent = title;
  el("resultRank").innerHTML =
    `${letter}<small>${caption} &middot; ${state.turns} QUESTIONS &middot; ` +
    `${state.presented.length}/${CASE.evidence.length} EVIDENCE</small>`;
  el("resultText").textContent = text;
  el("resultSolution").innerHTML = `<h3>What actually happened</h3><p>${escapeHtml(CASE.solution)}</p>`;
  el("resultModal").classList.remove("hidden");

  rightVerdict && hasProof ? SFX.win() : SFX.lose();
}

/* --------------------------------- wiring -------------------------------- */

el("chatForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = el("chatInput");
  const text = input.value.trim();
  if (!text || state.busy || state.over) return;
  input.value = "";
  SFX.ask();
  addMessage("player", text);
  askSuspect(text);
});

el("chatInput").addEventListener("keydown", (e) => {
  if (e.key.length === 1) SFX.type();
});

el("evidenceBody").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-present]");
  if (btn) presentEvidence(btn.dataset.present);
});

el("accuseBtn").addEventListener("click", openAccusation);

el("muteBtn").addEventListener("click", () => {
  const muted = SFX.toggle();
  el("muteBtn").classList.toggle("off", muted);
  el("muteBtn").title = muted ? "Sound off" : "Sound on";
});

document.querySelectorAll("[data-verdict]").forEach((btn) =>
  btn.addEventListener("click", () => resolveAccusation(btn.dataset.verdict))
);

document.querySelectorAll("[data-close]").forEach((btn) =>
  btn.addEventListener("click", () => {
    SFX.select();
    btn.closest(".modal").classList.add("hidden");
  })
);

el("restartBtn").addEventListener("click", () => {
  el("resultModal").classList.add("hidden");
  SFX.start();
  init();
  el("chatInput").focus();
});

/* ------------------------------- settings -------------------------------- */

el("settingsBtn").addEventListener("click", () => {
  const cfg = LLM.get();
  SFX.select();
  el("cfgBaseUrl").value = cfg.baseUrl;
  el("cfgModel").value = cfg.model;
  el("cfgKey").value = cfg.apiKey;
  el("cfgStatus").textContent = "";
  el("settingsModal").classList.remove("hidden");
});

el("cfgSave").addEventListener("click", () => {
  LLM.save({
    baseUrl: el("cfgBaseUrl").value.trim().replace(/\/$/, ""),
    model: el("cfgModel").value.trim(),
    apiKey: el("cfgKey").value.trim(),
  });
  SFX.select();
  el("settingsModal").classList.add("hidden");
});

el("cfgDetect").addEventListener("click", async () => {
  LLM.save({ baseUrl: el("cfgBaseUrl").value.trim().replace(/\/$/, "") });
  el("cfgStatus").textContent = "checking...";
  try {
    const models = (await LLM.listModels()).filter((id) => !/embed|rerank/i.test(id));
    el("cfgStatus").textContent = models.length
      ? `found: ${models.slice(0, 3).join(", ")}`
      : "server reachable, no chat models loaded";
    if (models.length && !el("cfgModel").value) el("cfgModel").value = models[0];
  } catch (err) {
    el("cfgStatus").textContent = `unreachable — ${err.message}`;
  }
});

init();
