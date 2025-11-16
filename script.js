// =======================
// CONFIGURAÇÃO GERAL
// =======================
const API_BASE = "https://seu-backend-no-render.onrender.com"; // troque pelo URL real do Render

const els = {
  leagueSelect: document.getElementById("leagueSelect"),
  homeSelect: document.getElementById("homeTeamSelect"),
  awaySelect: document.getElementById("awayTeamSelect"),
  analyzeButton: document.getElementById("analyzeButton"),

  homeName: document.getElementById("homeName"),
  homePos: document.getElementById("homePos"),
  homeLogo: document.getElementById("homeLogo"),

  awayName: document.getElementById("awayName"),
  awayPos: document.getElementById("awayPos"),
  awayLogo: document.getElementById("awayLogo"),

  probHomeSeg: document.getElementById("probHomeSeg"),
  probDrawSeg: document.getElementById("probDrawSeg"),
  probAwaySeg: document.getElementById("probAwaySeg"),
  probHomeLabel: document.getElementById("probHomeLabel"),
  probDrawLabel: document.getElementById("probDrawLabel"),
  probAwayLabel: document.getElementById("probAwayLabel"),

  mainTipTag: document.getElementById("mainTipTag"),
  mainTipText: document.getElementById("mainTipText"),

  over15Bar: document.getElementById("over15Bar"),
  over25Bar: document.getElementById("over25Bar"),
  bttsBar: document.getElementById("bttsBar"),
  over15Value: document.getElementById("over15Value"),
  over25Value: document.getElementById("over25Value"),
  bttsValue: document.getElementById("bttsValue"),
  goalsNote: document.getElementById("goalsNote"),

  cornersAvgBar: document.getElementById("cornersAvgBar"),
  corners85Bar: document.getElementById("corners85Bar"),
  corners95Bar: document.getElementById("corners95Bar"),
  cornersAvgValue: document.getElementById("cornersAvgValue"),
  corners85Value: document.getElementById("corners85Value"),
  corners95Value: document.getElementById("corners95Value"),
  cornersNote: document.getElementById("cornersNote"),

  cardsAvgBar: document.getElementById("cardsAvgBar"),
  cardsHomeBar: document.getElementById("cardsHomeBar"),
  cardsAwayBar: document.getElementById("cardsAwayBar"),
  cardsAvgValue: document.getElementById("cardsAvgValue"),
  cardsHomeValue: document.getElementById("cardsHomeValue"),
  cardsAwayValue: document.getElementById("cardsAwayValue"),
  cardsNote: document.getElementById("cardsNote"),

  alertsList: document.getElementById("alertsList"),
  h2hHistoryList: document.getElementById("h2hHistoryList"),

  palpitesBody: document.getElementById("palpitesBody"),
  palpitesList: document.getElementById("palpitesList"),
  multiplasBody: document.getElementById("multiplasBody"),
  multiplasList: document.getElementById("multiplasList"),
  multiCount: document.getElementById("multiCount"),
  multiOdd: document.getElementById("multiOdd")
};

let state = {
  leagues: [],
  teamsByLeague: {},
  currentH2H: null,
  multiplasSelecionadas: []
};

// =======================
// HELPERS
// =======================
function pct(num) {
  if (num == null || isNaN(num)) return "-";
  return `${num.toFixed(0)}%`;
}

function setBar(barEl, value) {
  if (!barEl) return;
  const v = Math.max(0, Math.min(100, value || 0));
  barEl.style.width = `${v}%`;
}

function setNumberBar(barEl, value, maxBase = 100) {
  if (!barEl) return;
  const ratio = Math.min(1, (value || 0) / maxBase);
  barEl.style.width = `${(ratio * 100).toFixed(0)}%`;
}

// =======================
// COLLAPSIBLES
// =======================
document.querySelectorAll(".toggle-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const targetId = btn.getAttribute("data-target");
    const body = document.getElementById(targetId);
    if (!body) return;
    const isOpen = body.classList.toggle("open");
    body.style.display = isOpen ? "block" : "none";
    btn.textContent = isOpen ? "–" : "+";
  });
});

// começa FECHADO
if (els.palpitesBody) {
  els.palpitesBody.classList.remove("open");
  els.palpitesBody.style.display = "none";
}
if (els.multiplasBody) {
  els.multiplasBody.classList.remove("open");
  els.multiplasBody.style.display = "none";
}

// =======================
// FETCH LIGAS / TIMES / H2H
// =======================
async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return await resp.json();
}

async function carregarLigas() {
  if (!els.leagueSelect) return;
  try {
    const data = await fetchJSON(`${API_BASE}/api/leagues`);
    state.leagues = data.leagues || [];
    els.leagueSelect.innerHTML = '<option value="">Selecione...</option>';
    state.leagues.forEach((lg) => {
      const opt = document.createElement("option");
      opt.value = lg.id;
      opt.textContent = lg.name;
      els.leagueSelect.appendChild(opt);
    });
  } catch (err) {
    console.error("Erro ao carregar ligas", err);
    els.leagueSelect.innerHTML =
      '<option value="">Erro ao carregar ligas</option>';
  }
}

async function carregarTimesDaLiga(leagueId) {
  if (!leagueId || !els.homeSelect || !els.awaySelect) return;

  els.homeSelect.disabled = true;
  els.awaySelect.disabled = true;
  els.homeSelect.innerHTML = '<option value="">Carregando...</option>';
  els.awaySelect.innerHTML = '<option value="">Carregando...</option>';

  try {
    const data = await fetchJSON(
      `${API_BASE}/api/teams?league_id=${encodeURIComponent(leagueId)}`
    );
    const teams = data.teams || [];
    state.teamsByLeague[leagueId] = teams;

    const optsHtml =
      '<option value="">Selecione...</option>' +
      teams
        .map(
          (t) => `<option value="${t.id}">${t.name}</option>`
        )
        .join("");

    els.homeSelect.innerHTML = optsHtml;
    els.awaySelect.innerHTML = optsHtml;
    els.homeSelect.disabled = false;
    els.awaySelect.disabled = false;
  } catch (err) {
    console.error("Erro ao carregar times", err);
    els.homeSelect.innerHTML =
      '<option value="">Erro ao carregar times</option>';
    els.awaySelect.innerHTML =
      '<option value="">Erro ao carregar times</option>';
  }
}

async function analisarConfronto() {
  if (!els.leagueSelect || !els.homeSelect || !els.awaySelect) return;

  const leagueId = els.leagueSelect.value;
  const homeId = els.homeSelect.value;
  const awayId = els.awaySelect.value;

  if (!leagueId || !homeId || !awayId) {
    alert("Selecione liga, mandante e visitante.");
    return;
  }

  try {
    if (els.analyzeButton) {
      els.analyzeButton.disabled = true;
      els.analyzeButton.textContent = "Analisando...";
    }

    const url = `${API_BASE}/api/h2h?league_id=${encodeURIComponent(
      leagueId
    )}&home_id=${encodeURIComponent(homeId)}&away_id=${encodeURIComponent(
      awayId
    )}`;

    const data = await fetchJSON(url);
    state.currentH2H = data;

    preencherPainelH2H(data);
  } catch (err) {
    console.error("Erro na análise H2H", err);
    alert("Erro ao analisar confronto. Veja o log no Render.");
  } finally {
    if (els.analyzeButton) {
      els.analyzeButton.disabled = false;
      els.analyzeButton.textContent = "Analisar Confronto";
    }
  }
}

function preencherPainelH2H(data) {
  if (!data) return;

  const {
    home,
    away,
    probabilities,
    goals,
    corners,
    cards,
    tip,
    alerts,
    h2h
  } = data;

  const tipData = tip || {};

  if (home && els.homeName) {
    els.homeName.textContent = home.name;
    if (els.homePos) {
      els.homePos.textContent = `Posição: ${home.position ?? "-"}`;
    }
    if (els.homeLogo) {
      els.homeLogo.textContent = (home.name || "?").slice(0, 2).toUpperCase();
    }
  }

  if (away && els.awayName) {
    els.awayName.textContent = away.name;
    if (els.awayPos) {
      els.awayPos.textContent = `Posição: ${away.position ?? "-"}`;
    }
    if (els.awayLogo) {
      els.awayLogo.textContent = (away.name || "?").slice(0, 2).toUpperCase();
    }
  }

  // PROBABILIDADES
  const pHome = probabilities?.home ?? 0;
  const pDraw = probabilities?.draw ?? 0;
  const pAway = probabilities?.away ?? 0;
  const total = Math.max(1, pHome + pDraw + pAway);

  const wHome = (pHome / total) * 100;
  const wDraw = (pDraw / total) * 100;
  const wAway = (pAway / total) * 100;

  if (els.probHomeSeg) {
    els.probHomeSeg.style.width = `${wHome.toFixed(1)}%`;
    els.probHomeSeg.textContent = `${pct(pHome)}`;
  }
  if (els.probDrawSeg) {
    els.probDrawSeg.style.width = `${wDraw.toFixed(1)}%`;
    els.probDrawSeg.textContent = `${pct(pDraw)}`;
  }
  if (els.probAwaySeg) {
    els.probAwaySeg.style.width = `${wAway.toFixed(1)}%`;
    els.probAwaySeg.textContent = `${pct(pAway)}`;
  }

  if (els.probHomeLabel) els.probHomeLabel.textContent = `1: ${pct(pHome)}`;
  if (els.probDrawLabel) els.probDrawLabel.textContent = `X: ${pct(pDraw)}`;
  if (els.probAwayLabel) els.probAwayLabel.textContent = `2: ${pct(pAway)}`;

  // TIP PRINCIPAL
  if (els.mainTipTag) els.mainTipTag.textContent = tipData.label || "Melhor aposta";
  if (els.mainTipText) els.mainTipText.textContent = tipData.text || "";

  // GOALS
  if (goals) {
    setBar(els.over15Bar, goals.over15 ?? 0);
    setBar(els.over25Bar, goals.over25 ?? 0);
    setBar(els.bttsBar, goals.btts ?? 0);
    if (els.over15Value) els.over15Value.textContent = pct(goals.over15 ?? 0);
    if (els.over25Value) els.over25Value.textContent = pct(goals.over25 ?? 0);
    if (els.bttsValue) els.bttsValue.textContent = pct(goals.btts ?? 0);
    if (els.goalsNote) els.goalsNote.textContent = goals.note || "–";
  }

  // CORNERS
  if (corners) {
    setNumberBar(els.cornersAvgBar, corners.avg ?? 0, 14);
    setBar(els.corners85Bar, corners.over85 ?? 0);
    setBar(els.corners95Bar, corners.over95 ?? 0);
    if (els.cornersAvgValue) {
      els.cornersAvgValue.textContent =
        corners.avg != null ? corners.avg.toFixed(1) : "-";
    }
    if (els.corners85Value) {
      els.corners85Value.textContent = pct(corners.over85 ?? 0);
    }
    if (els.corners95Value) {
      els.corners95Value.textContent = pct(corners.over95 ?? 0);
    }
    if (els.cornersNote) els.cornersNote.textContent = corners.note || "–";
  }

  // CARDS
  if (cards) {
    setNumberBar(els.cardsAvgBar, cards.avg ?? 0, 8);
    setNumberBar(els.cardsHomeBar, cards.home ?? 0, 6);
    setNumberBar(els.cardsAwayBar, cards.away ?? 0, 6);
    if (els.cardsAvgValue) {
      els.cardsAvgValue.textContent =
        cards.avg != null ? cards.avg.toFixed(1) : "-";
    }
    if (els.cardsHomeValue) {
      els.cardsHomeValue.textContent =
        cards.home != null ? cards.home.toFixed(1) : "-";
    }
    if (els.cardsAwayValue) {
      els.cardsAwayValue.textContent =
        cards.away != null ? cards.away.toFixed(1) : "-";
    }
    if (els.cardsNote) els.cardsNote.textContent = cards.note || "–";
  }

  // ALERTAS
  if (els.alertsList) {
    els.alertsList.innerHTML = "";
    (alerts || []).forEach((al) => {
      const li = document.createElement("li");
      const tag = document.createElement("span");
      tag.classList.add("alert-tag");
      if (al.type === "high") {
        tag.classList.add("alert-tag-high");
        tag.textContent = "ALTA";
      } else {
        tag.classList.add("alert-tag-info");
        tag.textContent = "INFO";
      }
      const text = document.createElement("span");
      text.textContent = al.text;
      li.appendChild(tag);
      li.appendChild(text);
      els.alertsList.appendChild(li);
    });
  }

  // HISTÓRICO
  if (els.h2hHistoryList) {
    els.h2hHistoryList.innerHTML = "";
    (h2h?.matches || []).forEach((m) => {
      const li = document.createElement("li");
      li.classList.add("history-item");

      const left = document.createElement("span");
      left.textContent = `${m.date} · ${m.home} ${m.score} ${m.away}`;

      const right = document.createElement("span");
      right.classList.add("history-meta");
      right.textContent = `${m.competition} · ${m.market || ""}`;

      li.appendChild(left);
      li.appendChild(right);
      els.h2hHistoryList.appendChild(li);
    });
  }
}

// =======================
// PALPITES DO DIA / MÚLTIPLAS
// =======================
async function carregarPalpitesDia() {
  if (!els.palpitesList) return;

  try {
    const data = await fetchJSON(`${API_BASE}/api/palpites-dia`);
    const tips = data.tips || [];
    els.palpitesList.innerHTML = "";

    tips.forEach((t) => {
      const li = document.createElement("li");
      li.classList.add("tip-item");

      const col1 = document.createElement("div");
      const main = document.createElement("div");
      main.classList.add("tip-market");
      main.textContent = t.title;
      const meta = document.createElement("div");
      meta.classList.add("tip-league");
      meta.textContent = `${t.league} · ${t.time}`;
      col1.appendChild(main);
      col1.appendChild(meta);

      const col2 = document.createElement("div");
      col2.classList.add("tip-odd");
      col2.textContent = `Odd: ${t.odd != null ? t.odd.toFixed(2) : "-"}`;

      const col3 = document.createElement("div");
      const badge = document.createElement("span");
      badge.classList.add("tip-badge");
      badge.textContent = t.tag || "Palpite do Dia";
      col3.appendChild(badge);

      li.appendChild(col1);
      li.appendChild(col2);
      li.appendChild(col3);

      // clique para adicionar/remover na múltipla
      li.addEventListener("click", () => toggleNaMultipla(t));
      els.palpitesList.appendChild(li);
    });
  } catch (err) {
    console.error("Erro ao carregar palpites do dia", err);
  }
}

function toggleNaMultipla(tip) {
  const key = `${tip.league}-${tip.matchId}-${tip.market}`;
  const idx = state.multiplasSelecionadas.findIndex((x) => x.key === key);

  if (idx >= 0) {
    // já está na múltipla -> remove
    state.multiplasSelecionadas.splice(idx, 1);
  } else {
    // adiciona
    state.multiplasSelecionadas.push({
      key,
      title: tip.title,
      league: tip.league,
      time: tip.time,
      odd: tip.odd || 1,
      tag: tip.tag || "Palpite do Dia"
    });
  }

  atualizarMultipla();
}

function atualizarMultipla() {
  if (!els.multiplasList || !els.multiCount || !els.multiOdd) return;

  els.multiplasList.innerHTML = "";

  const itens = state.multiplasSelecionadas;
  if (!itens.length) {
    els.multiCount.textContent = "0";
    els.multiOdd.textContent = "-";
    return;
  }

  let totalOdd = 1;

  itens.forEach((t) => {
    const li = document.createElement("li");
    li.classList.add("multi-item");

    const col1 = document.createElement("div");
    const main = document.createElement("div");
    main.classList.add("tip-market");
    main.textContent = t.title;
    const meta = document.createElement("div");
    meta.classList.add("tip-league");
    meta.textContent = `${t.league} · ${t.time}`;
    col1.appendChild(main);
    col1.appendChild(meta);

    const col2 = document.createElement("div");
    col2.classList.add("tip-odd");
    col2.textContent = `Odd: ${(t.odd || 1).toFixed(2)}`;

    const col3 = document.createElement("div");
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.classList.add("multi-remove-btn");
    removeBtn.textContent = "X";
    removeBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const idx = state.multiplasSelecionadas.findIndex(
        (x) => x.key === t.key
      );
      if (idx >= 0) {
        state.multiplasSelecionadas.splice(idx, 1);
        atualizarMultipla();
      }
    });
    col3.appendChild(removeBtn);

    li.appendChild(col1);
    li.appendChild(col2);
    li.appendChild(col3);

    els.multiplasList.appendChild(li);

    totalOdd *= t.odd || 1;
  });

  els.multiCount.textContent = String(itens.length);
  els.multiOdd.textContent = totalOdd.toFixed(2);
}

// =======================
// INIT
// =======================
function init() {
  carregarLigas();
  carregarPalpitesDia();

  if (els.leagueSelect) {
    els.leagueSelect.addEventListener("change", (e) => {
      const leagueId = e.target.value;
      carregarTimesDaLiga(leagueId);
    });
  }

  if (els.analyzeButton) {
    els.analyzeButton.addEventListener("click", analisarConfronto);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
