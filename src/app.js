import { fallbackAnalysis } from "./data.js";

const state = {
  analysis: fallbackAnalysis,
  search: "",
  selectedVariableId: fallbackAnalysis.variables[0]?.id ?? null,
  selectedFormulaId: fallbackAnalysis.formulas[0]?.id ?? null,
  tracedFormulaIds: [],
  tracedVariableIds: [],
  loading: false,
};

const variableListEl = document.querySelector("#variable-list");
const graphGridEl = document.querySelector("#graph-grid");
const graphLinesEl = document.querySelector("#graph-lines");
const detailTitleEl = document.querySelector("#detail-title");
const detailContentEl = document.querySelector("#detail-content");
const docInsightEl = document.querySelector("#doc-insight");
const searchInputEl = document.querySelector("#variable-search");
const sourceSelectEl = document.querySelector("#source-variable");
const targetSelectEl = document.querySelector("#target-variable");
const pathResultEl = document.querySelector("#path-result");
const pathButtonEl = document.querySelector("#find-path-button");
const pdfInputEl = document.querySelector("#pdf-input");
const analyzeButtonEl = document.querySelector("#analyze-button");
const statusBannerEl = document.querySelector("#status-banner");
const paperMetaEl = document.querySelector("#paper-meta");

function init() {
  bindEvents();
  syncStateWithAnalysis();
  render();
  requestAnimationFrame(drawConnections);
  window.addEventListener("resize", drawConnections);
  probeHealth();
}

function bindEvents() {
  searchInputEl.addEventListener("input", (event) => {
    state.search = event.target.value.trim().toLowerCase();
    renderVariableList();
  });

  pathButtonEl.addEventListener("click", () => {
    const source = sourceSelectEl.value;
    const target = targetSelectEl.value;
    if (!source || !target) {
      return;
    }

    const result = findVariablePath(source, target);
    state.tracedVariableIds = result.variablePath;
    state.tracedFormulaIds = result.formulaPath;
    pathResultEl.textContent = result.label;
    render();
  });

  analyzeButtonEl.addEventListener("click", analyzePdf);
}

async function probeHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return;
    }
    const health = await response.json();
    setStatus(`Backend ready. PDF parser: ${health.pdf_parser}. OCR: ${health.ocr}. LLM: ${health.llm}.`);
  } catch {
    setStatus("Backend is not reachable yet. Start the FastAPI server to analyze real PDFs.");
  }
}

async function analyzePdf() {
  const file = pdfInputEl.files?.[0];
  if (!file) {
    setStatus("Choose a PDF file first.", true);
    return;
  }

  state.loading = true;
  analyzeButtonEl.disabled = true;
  setStatus(`Uploading ${file.name} for parsing, OCR, and graph reconstruction...`);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/analyze", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Analysis failed");
    }

    state.analysis = payload;
    state.search = "";
    state.tracedFormulaIds = [];
    state.tracedVariableIds = [];
    searchInputEl.value = "";
    syncStateWithAnalysis();
    render();
    setStatus(`Analysis completed for ${payload.sourceFilename}. ${payload.warnings?.length ?? 0} warning(s).`);
  } catch (error) {
    setStatus(error.message || "Analysis failed.", true);
  } finally {
    state.loading = false;
    analyzeButtonEl.disabled = false;
  }
}

function syncStateWithAnalysis() {
  const variables = getVariables();
  const formulas = getFormulas();
  state.selectedVariableId = variables[0]?.id ?? null;
  state.selectedFormulaId = formulas[0]?.id ?? null;
  populateVariableSelectors();
}

function render() {
  renderMeta();
  renderVariableList();
  renderGraph();
  renderDetail();
  renderDocInsight();
  requestAnimationFrame(drawConnections);
}

function renderMeta() {
  const analysis = state.analysis;
  paperMetaEl.innerHTML = [
    `<span class="meta-pill">${escapeHtml(analysis.documentTitle)}</span>`,
    `<span class="meta-pill">${analysis.pageCount} pages</span>`,
    `<span class="meta-pill">${getFormulas().length} formulas</span>`,
    `<span class="meta-pill">${getVariables().length} variables</span>`,
    `<span class="meta-pill">${analysis.status}</span>`,
  ].join("");
}

function renderVariableList() {
  const variableMap = getVariableMap();
  const formulaMap = getFormulaMap();

  const filteredVariables = getVariables().filter((variable) => {
    if (!state.search) {
      return true;
    }

    const haystack = [variable.symbol, variable.name, variable.meaning, variable.role]
      .join(" ")
      .toLowerCase();

    return haystack.includes(state.search);
  });

  variableListEl.innerHTML = filteredVariables.length
    ? filteredVariables
        .map((variable) => {
          const isSelected = variable.id === state.selectedVariableId;
          const isTraced = state.tracedVariableIds.includes(variable.id);
          const relatedFormulaLinks = (variable.formulas || [])
            .map((formulaId) => {
              const formula = formulaMap.get(formulaId);
              return `<button class="inline-link" data-formula-link="${formulaId}">${escapeHtml(formula?.title ?? formulaId)}</button>`;
            })
            .join("");

          return `
            <article class="variable-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" data-variable-id="${variable.id}">
              <div class="variable-card-top">
                <div>
                  <p class="symbol">${escapeHtml(variable.symbol)}</p>
                  <h3>${escapeHtml(variable.name)}</h3>
                </div>
                <span class="type-badge">${escapeHtml(variable.type)}</span>
              </div>
              <p class="meaning">${escapeHtml(variable.meaning)}</p>
              <dl class="meta-grid">
                <div><dt>Unit</dt><dd>${escapeHtml(variable.unit || "-")}</dd></div>
                <div><dt>Role</dt><dd>${escapeHtml(variable.role)}</dd></div>
                <div><dt>Source</dt><dd>${escapeHtml(variable.source)}</dd></div>
                <div><dt>Memory</dt><dd>${escapeHtml(variable.memory)}</dd></div>
              </dl>
              <div class="reverse-trace">
                <span>Appears in</span>
                <div class="trace-links">${relatedFormulaLinks}</div>
              </div>
            </article>
          `;
        })
        .join("")
    : `<div class="empty-state">No variables matched the current search.</div>`;

  variableListEl.querySelectorAll("[data-variable-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      const clickedFormulaLink = event.target.closest("[data-formula-link]");
      if (clickedFormulaLink) {
        selectFormula(clickedFormulaLink.dataset.formulaLink);
        return;
      }

      selectVariable(card.dataset.variableId);
    });
  });
}

function renderGraph() {
  const variableMap = getVariableMap();

  graphGridEl.innerHTML = getFormulas().length
    ? getFormulas()
        .map((formula) => {
          const isSelected = formula.id === state.selectedFormulaId;
          const isTraced = state.tracedFormulaIds.includes(formula.id);
          const relatedVariables = (formula.inputs || [])
            .map((variableId) => {
              const variable = variableMap.get(variableId);
              const isActive = variableId === state.selectedVariableId || state.tracedVariableIds.includes(variableId);

              return `<button class="chip ${isActive ? "active" : ""}" data-variable-chip="${variableId}">${escapeHtml(variable?.symbol ?? variableId)}</button>`;
            })
            .join("");

          return `
            <article class="formula-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" data-formula-id="${formula.id}">
              <p class="formula-label">${escapeHtml(formula.id.toUpperCase())}</p>
              <h3>${escapeHtml(formula.title)}</h3>
              <p class="expression">${escapeHtml(formula.expression)}</p>
              <p class="formula-note">${escapeHtml(formula.physicalMeaning)}</p>
              <div class="chip-row">${relatedVariables}</div>
              <div class="paper-note">${escapeHtml(formula.paperNote)}</div>
            </article>
          `;
        })
        .join("")
    : `<div class="empty-state wide">No formulas were reconstructed for this PDF.</div>`;

  graphGridEl.querySelectorAll("[data-formula-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-variable-chip]");
      if (chip) {
        event.stopPropagation();
        selectVariable(chip.dataset.variableChip);
        return;
      }

      selectFormula(card.dataset.formulaId);
    });
  });
}

function renderDetail() {
  const formula = getFormulaMap().get(state.selectedFormulaId);
  const variableMap = getVariableMap();
  if (!formula) {
    detailTitleEl.textContent = "Select a formula";
    detailContentEl.innerHTML = `<div class="empty-state">Upload a paper to inspect a formula.</div>`;
    return;
  }

  detailTitleEl.textContent = `${formula.id.toUpperCase()} · ${formula.title}`;
  const highlightedVariables = new Set([state.selectedVariableId, ...state.tracedVariableIds]);

  detailContentEl.innerHTML = `
    <section class="detail-hero">
      <p class="detail-expression">${escapeHtml(formula.expression)}</p>
      <p class="detail-summary">${escapeHtml(formula.physicalMeaning)}</p>
      <p class="detail-memory"><strong>Memory hook:</strong> ${escapeHtml(formula.memory)}</p>
    </section>
    <section class="detail-section">
      <h3>Chunked explanation</h3>
      ${(formula.chunks || [])
        .map((chunk) => {
          const chips = (chunk.variableIds || [])
            .map((variableId) => {
              const variable = variableMap.get(variableId);
              const active = highlightedVariables.has(variableId);
              return `<button class="chip ${active ? "active" : ""}" data-detail-variable="${variableId}">${escapeHtml(variable?.symbol ?? variableId)}</button>`;
            })
            .join("");

          return `
            <article class="chunk-card">
              <div class="chunk-top">
                <h4>${escapeHtml(chunk.label)}</h4>
                <div class="chip-row">${chips}</div>
              </div>
              <p>${escapeHtml(chunk.text)}</p>
            </article>
          `;
        })
        .join("")}
    </section>
    <section class="detail-section">
      <h3>Bound variables</h3>
      <div class="bound-variable-list">
        ${(formula.inputs || [])
          .map((variableId) => {
            const variable = variableMap.get(variableId);
            const active = variableId === state.selectedVariableId;
            return `
              <button class="bound-variable ${active ? "active" : ""}" data-detail-variable="${variableId}">
                <span>${escapeHtml(variable?.symbol ?? variableId)}</span>
                <small>${escapeHtml(variable?.meaning ?? "")}</small>
              </button>
            `;
          })
          .join("")}
      </div>
    </section>
    <section class="detail-section">
      <h3>Extraction preview</h3>
      <p class="detail-summary">${escapeHtml(state.analysis.extractedText?.slice(0, 1000) || "No extracted text available.")}</p>
    </section>
  `;

  detailContentEl.querySelectorAll("[data-detail-variable]").forEach((button) => {
    button.addEventListener("click", () => selectVariable(button.dataset.detailVariable));
  });
}

function renderDocInsight() {
  const insight = state.analysis.documentInsight || { overview: "", pipeline: [] };
  const warnings = state.analysis.warnings || [];
  const formulaCandidates = state.analysis.formulaCandidates || [];
  docInsightEl.innerHTML = `
    <p>${escapeHtml(insight.overview || "No document insight available.")}</p>
    <ol class="insight-list">
      ${(insight.pipeline || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ol>
    <h4>Warnings</h4>
    <ul class="insight-list">
      ${warnings.length ? warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") : "<li>No warnings.</li>"}
    </ul>
    <h4>Formula candidates</h4>
    <ul class="insight-list">
      ${formulaCandidates.length ? formulaCandidates.slice(0, 8).map((item) => `<li>${escapeHtml(item)}</li>`).join("") : "<li>No candidates detected.</li>"}
    </ul>
  `;
}

function populateVariableSelectors() {
  const options = getVariables()
    .map((variable) => `<option value="${variable.id}">${escapeHtml(variable.symbol)} · ${escapeHtml(variable.name)}</option>`)
    .join("");

  sourceSelectEl.innerHTML = options;
  targetSelectEl.innerHTML = options;

  const variables = getVariables();
  sourceSelectEl.value = variables[0]?.id || "";
  targetSelectEl.value = variables[variables.length - 1]?.id || variables[0]?.id || "";
}

function selectVariable(variableId) {
  state.selectedVariableId = variableId;
  const relatedFormulaId = getVariableMap().get(variableId)?.formulas?.[0];
  if (relatedFormulaId) {
    state.selectedFormulaId = relatedFormulaId;
  }
  render();
}

function selectFormula(formulaId) {
  state.selectedFormulaId = formulaId;
  const firstVariableId = getFormulaMap().get(formulaId)?.inputs?.[0];
  if (firstVariableId) {
    state.selectedVariableId = firstVariableId;
  }
  render();
}

function drawConnections() {
  const cards = [...graphGridEl.querySelectorAll("[data-formula-id]")];
  if (!cards.length) {
    graphLinesEl.innerHTML = "";
    return;
  }

  const stageRect = graphGridEl.getBoundingClientRect();
  const cardMap = new Map(
    cards.map((card) => [
      card.dataset.formulaId,
      {
        x: card.offsetLeft + card.offsetWidth / 2,
        y: card.offsetTop + card.offsetHeight / 2,
      },
    ])
  );

  graphLinesEl.setAttribute("viewBox", `0 0 ${Math.ceil(stageRect.width)} ${Math.ceil(stageRect.height)}`);

  graphLinesEl.innerHTML = getFormulas()
    .flatMap((formula) =>
      (formula.dependsOn || []).map((dependencyId) => {
        const from = cardMap.get(dependencyId);
        const to = cardMap.get(formula.id);
        if (!from || !to) {
          return "";
        }

        const isTraced = state.tracedFormulaIds.includes(formula.id) && state.tracedFormulaIds.includes(dependencyId);
        const isSelected = formula.id === state.selectedFormulaId || dependencyId === state.selectedFormulaId;
        const midX = (from.x + to.x) / 2;
        const path = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
        return `<path class="graph-path ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" d="${path}" />`;
      })
    )
    .join("");
}

function findVariablePath(sourceId, targetId) {
  if (sourceId === targetId) {
    return {
      variablePath: [sourceId],
      formulaPath: [],
      label: `${getVariableMap().get(sourceId)?.symbol} is already selected.`,
    };
  }

  const adjacency = new Map(getVariables().map((variable) => [variable.id, []]));
  for (const formula of getFormulas()) {
    for (const variableId of formula.inputs || []) {
      const links = adjacency.get(variableId) ?? [];
      for (const peerId of formula.inputs || []) {
        if (peerId !== variableId) {
          links.push({ next: peerId, via: formula.id });
        }
      }
      adjacency.set(variableId, links);
    }
  }

  const queue = [{ id: sourceId, variablePath: [sourceId], formulaPath: [] }];
  const visited = new Set([sourceId]);

  while (queue.length) {
    const current = queue.shift();
    const edges = adjacency.get(current.id) ?? [];

    for (const edge of edges) {
      if (visited.has(edge.next)) {
        continue;
      }

      const variablePath = [...current.variablePath, edge.next];
      const formulaPath = [...current.formulaPath, edge.via];
      if (edge.next === targetId) {
        const label = variablePath
          .map((variableId, index) => {
            const symbol = getVariableMap().get(variableId)?.symbol ?? variableId;
            const formulaId = formulaPath[index];
            return formulaId ? `${symbol} --${formulaId.toUpperCase()}--> ` : symbol;
          })
          .join("");
        return { variablePath, formulaPath, label };
      }

      visited.add(edge.next);
      queue.push({ id: edge.next, variablePath, formulaPath });
    }
  }

  return { variablePath: [sourceId, targetId], formulaPath: [], label: "No semantic path found in the current graph." };
}

function getVariables() {
  return state.analysis.variables || [];
}

function getFormulas() {
  return state.analysis.formulas || [];
}

function getVariableMap() {
  return new Map(getVariables().map((item) => [item.id, item]));
}

function getFormulaMap() {
  return new Map(getFormulas().map((item) => [item.id, item]));
}

function setStatus(message, isError = false) {
  statusBannerEl.textContent = message;
  statusBannerEl.classList.toggle("error", isError);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

init();
