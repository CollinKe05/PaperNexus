import { fallbackAnalysis } from "./data.js";

const TASK_STAGE_LABELS = {
  queued: "Queued",
  uploaded: "Uploaded",
  pymupdf_processing: "PyMuPDF processing",
  pymupdf_done: "PyMuPDF done",
  nougat_processing: "Nougat processing",
  semantic_analysis: "Semantic analysis",
  completed: "Completed",
  failed: "Failed",
};

const state = {
  analysis: fallbackAnalysis,
  search: "",
  selectedVariableId: fallbackAnalysis.variables[0]?.id ?? null,
  selectedFormulaId: fallbackAnalysis.formulas[0]?.id ?? null,
  activePdfPage: 1,
  tracedFormulaIds: [],
  tracedVariableIds: [],
  loading: false,
  activeTaskId: null,
  activeTaskStatus: "idle",
  activeTaskStage: "queued",
  activeTaskProgress: 0,
  quickMode: false,
  pollHandle: null,
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
const quickModeEl = document.querySelector("#quick-mode");
const analyzeButtonEl = document.querySelector("#analyze-button");
const statusBannerEl = document.querySelector("#status-banner");
const statusProgressBarEl = document.querySelector("#status-progress-bar");
const paperMetaEl = document.querySelector("#paper-meta");
const prevPageEl = document.querySelector("#prev-page");
const nextPageEl = document.querySelector("#next-page");
const pageIndicatorEl = document.querySelector("#page-indicator");
const pageFormulaLinksEl = document.querySelector("#page-formula-links");
const pdfPageImageEl = document.querySelector("#pdf-page-image");
const formulaOverlayEl = document.querySelector("#formula-overlay");
const openPdfLinkEl = document.querySelector("#open-pdf-link");

function init() {
  bindEvents();
  syncStateWithAnalysis(true);
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

  quickModeEl.addEventListener("change", () => {
    state.quickMode = quickModeEl.checked;
  });

  analyzeButtonEl.addEventListener("click", analyzePdf);
  prevPageEl.addEventListener("click", () => setActivePdfPage(state.activePdfPage - 1));
  nextPageEl.addEventListener("click", () => setActivePdfPage(state.activePdfPage + 1));
  pdfPageImageEl.addEventListener("error", () => {
    pdfPageImageEl.removeAttribute("src");
    if (state.activeTaskStatus !== "running") {
      setStatus("The current page preview is not available yet.", false, state.activeTaskProgress);
    }
  });
}

async function probeHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return;
    }
    const health = await response.json();
    setStatus(
      `Backend ready. PDF parser: ${health.pdf_parser}. Nougat: ${health.nougat}. OCR: ${health.ocr}. LLM: ${health.llm}.`,
      false,
      0
    );
  } catch {
    setStatus("Backend is not reachable yet. Start the FastAPI server to analyze real PDFs.", true, 0);
  }
}

async function analyzePdf() {
  const file = pdfInputEl.files?.[0];
  if (!file) {
    setStatus("Choose a PDF file first.", true, 0);
    return;
  }

  stopPollingTask();
  state.loading = true;
  state.activeTaskId = null;
  state.activeTaskStatus = "queued";
  state.activeTaskStage = "uploaded";
  state.activeTaskProgress = 0.02;
  state.quickMode = quickModeEl.checked;
  analyzeButtonEl.disabled = true;
  setStatus(`Uploading ${file.name}...`, false, state.activeTaskProgress);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("quick_mode", quickModeEl.checked ? "true" : "false");

  try {
    const response = await fetch("/api/analyze", { method: "POST", body: formData });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Analysis failed");
    }

    state.activeTaskId = payload.taskId;
    state.activeTaskStage = payload.stage;
    state.activeTaskStatus = payload.status;
    state.activeTaskProgress = 0.05;
    setStatus(buildTaskStatusText(payload.stage, payload.message), false, state.activeTaskProgress);
    startPollingTask(payload.taskId);
  } catch (error) {
    state.loading = false;
    analyzeButtonEl.disabled = false;
    setStatus(error.message || "Analysis failed.", true, 0);
  }
}

function startPollingTask(taskId) {
  stopPollingTask();
  pollTask(taskId);
  state.pollHandle = window.setInterval(() => pollTask(taskId), 1500);
}

function stopPollingTask() {
  if (state.pollHandle) {
    window.clearInterval(state.pollHandle);
    state.pollHandle = null;
  }
}

async function pollTask(taskId) {
  try {
    const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Task polling failed");
    }
    handleTaskPayload(payload);
  } catch (error) {
    stopPollingTask();
    state.loading = false;
    analyzeButtonEl.disabled = false;
    setStatus(error.message || "Task polling failed.", true, state.activeTaskProgress);
  }
}

function handleTaskPayload(payload) {
  state.activeTaskId = payload.taskId;
  state.activeTaskStatus = payload.status;
  state.activeTaskStage = payload.stage;
  state.activeTaskProgress = payload.progress || 0;

  if (payload.result) {
    applyAnalysisResult(payload.result);
  }

  if (payload.status === "failed") {
    stopPollingTask();
    state.loading = false;
    analyzeButtonEl.disabled = false;
    setStatus(payload.error || payload.message || "Analysis failed.", true, 1);
    return;
  }

  if (payload.status === "completed") {
    stopPollingTask();
    state.loading = false;
    analyzeButtonEl.disabled = false;
    setStatus(buildTaskStatusText(payload.stage, payload.message), false, 1);
    return;
  }

  setStatus(buildTaskStatusText(payload.stage, payload.message), false, payload.progress || 0);
}

function applyAnalysisResult(analysis) {
  const previousFilename = state.analysis?.sourceFilename;
  const isNewDocument = previousFilename !== analysis.sourceFilename;
  state.analysis = analysis;

  if (isNewDocument) {
    state.search = "";
    state.tracedFormulaIds = [];
    state.tracedVariableIds = [];
    pathResultEl.textContent = "";
    searchInputEl.value = "";
    syncStateWithAnalysis(true);
  } else {
    syncStateWithAnalysis(false);
  }

  render();
}

function syncStateWithAnalysis(forceReset = false) {
  const variables = getVariables();
  const formulas = getFormulas();
  const preferredFormula = pickPreferredFormula(formulas);
  const currentVariableExists = variables.some((item) => item.id === state.selectedVariableId);
  const currentFormulaExists = formulas.some((item) => item.id === state.selectedFormulaId);

  if (forceReset || !currentVariableExists) {
    state.selectedVariableId = variables[0]?.id ?? null;
  }
  if (forceReset || !currentFormulaExists) {
    state.selectedFormulaId = preferredFormula?.id ?? formulas[0]?.id ?? null;
  }

  const selectedFormula = formulas.find((item) => item.id === state.selectedFormulaId);
  const maxPage = Math.max(1, Number(state.analysis.pageCount) || 1);
  const suggestedPage = selectedFormula?.page || preferredFormula?.page || formulas[0]?.page || 1;
  state.activePdfPage = forceReset ? suggestedPage : clamp(state.activePdfPage || suggestedPage, 1, maxPage);
  populateVariableSelectors();
}

function render() {
  renderMeta();
  renderVariableList();
  renderGraph();
  renderDetail();
  renderDocInsight();
  renderPdfPreview();
  requestAnimationFrame(drawConnections);
}

function renderMeta() {
  const analysis = state.analysis;
  const modeLabel = analysis.status === "fallback" ? "heuristic mode" : "interactive mode";
  const stageLabel = state.activeTaskId ? TASK_STAGE_LABELS[state.activeTaskStage] || state.activeTaskStage : "demo";
  paperMetaEl.innerHTML = [
    `<span class="meta-pill">${escapeHtml(analysis.documentTitle)}</span>`,
    `<span class="meta-pill">${analysis.pageCount} pages</span>`,
    `<span class="meta-pill">${getFormulas().length} formulas</span>`,
    `<span class="meta-pill">${getVariables().length} variables</span>`,
    `<span class="meta-pill">${escapeHtml(analysis.status)}</span>`,
    `<span class="meta-pill">${escapeHtml(modeLabel)}</span>`,
    `<span class="meta-pill">${escapeHtml(stageLabel)}</span>`,
  ].join("");
}

function renderVariableList() {
  const formulaMap = getFormulaMap();
  const filteredVariables = getVariables().filter((variable) => {
    if (!state.search) {
      return true;
    }

    const haystack = [variable.symbol, variable.name, variable.meaning, variable.role].join(" ").toLowerCase();
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
              const page = formula?.page ? ` (p.${formula.page})` : "";
              return `<button class="inline-link" data-formula-link="${formulaId}">${escapeHtml(formula?.title ?? formulaId)}${page}</button>`;
            })
            .join("");

          return `
            <article class="variable-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" data-variable-id="${variable.id}">
              <div class="variable-card-top">
                <div>
                  <div class="symbol symbol-math" data-math data-display="false">${escapeHtml(toLatexSymbol(variable.symbol))}</div>
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
              ${renderAnchorList(variable.anchors, "Anchors")}
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

  renderMathIn(variableListEl);
}

function renderGraph() {
  const variableMap = getVariableMap();

  graphGridEl.innerHTML = getFormulas().length
    ? getFormulas()
        .map((formula) => {
          const isSelected = formula.id === state.selectedFormulaId;
          const isTraced = state.tracedFormulaIds.includes(formula.id);
          const isPageLinked = formula.page === state.activePdfPage;
          const relatedVariables = (formula.inputs || [])
            .map((variableId) => {
              const variable = variableMap.get(variableId);
              const isActive = variableId === state.selectedVariableId || state.tracedVariableIds.includes(variableId);
              return `<button class="chip ${isActive ? "active" : ""}" data-variable-chip="${variableId}">${escapeHtml(variable?.symbol ?? variableId)}</button>`;
            })
            .join("");
          const pageBadge = formula.page ? `<button class="page-badge" data-formula-page="${formula.page}">Page ${formula.page}</button>` : "";

          return `
            <article class="formula-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""} ${isPageLinked ? "page-linked" : ""}" data-formula-id="${formula.id}">
              <div class="formula-top-row">
                <p class="formula-label">${escapeHtml(formula.id.toUpperCase())}</p>
                ${pageBadge}
              </div>
              <h3>${escapeHtml(formula.title)}</h3>
              <div class="expression math-block" data-formula-math="${formula.id}"></div>
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

      const pageLink = event.target.closest("[data-formula-page]");
      if (pageLink) {
        event.stopPropagation();
        setActivePdfPage(Number(pageLink.dataset.formulaPage));
        return;
      }

      selectFormula(card.dataset.formulaId);
    });
  });

  renderFormulaMathIn(graphGridEl);
}

function renderDetail() {
  const formula = getFormulaMap().get(state.selectedFormulaId);
  const variableMap = getVariableMap();
  if (!formula) {
    detailTitleEl.textContent = "Select a formula";
    detailContentEl.innerHTML = `<div class="empty-state">Upload a paper to inspect a formula.</div>`;
    return;
  }

  detailTitleEl.textContent = `${formula.id.toUpperCase()} - ${formula.title}`;
  const highlightedVariables = new Set([state.selectedVariableId, ...state.tracedVariableIds]);
  const semantic = formula.semantic || { lhsSymbols: [], rhsSymbols: [], operators: [], complexity: 0 };

  detailContentEl.innerHTML = `
    <section class="detail-hero">
      <div class="detail-expression math-block math-block-large" data-formula-math="${formula.id}"></div>
      <p class="detail-summary">${escapeHtml(formula.physicalMeaning)}</p>
      <p class="detail-memory"><strong>Memory hook:</strong> ${escapeHtml(formula.memory)}</p>
      <p class="detail-summary"><strong>Source page:</strong> ${formula.page || "unknown"}</p>
      <p class="detail-summary"><strong>Semantic:</strong> LHS [${escapeHtml((semantic.lhsSymbols || []).join(", "))}] RHS [${escapeHtml((semantic.rhsSymbols || []).join(", "))}] Ops [${escapeHtml((semantic.operators || []).join(" "))}]</p>
      ${formula.page ? `<button class="mini-button" data-jump-page="${formula.page}">Jump to page ${formula.page}</button>` : ""}
      ${renderAnchorList(formula.anchors, "Paper anchors")}
    </section>
    <section class="detail-section">
      <h3>Symbols in this formula</h3>
      <div class="bound-variable-list">
        ${(formula.inputs || [])
          .map((variableId) => {
            const variable = variableMap.get(variableId);
            if (!variable) {
              return "";
            }
            const active = highlightedVariables.has(variableId);
            return `
              <button class="bound-variable ${active ? "active" : ""}" data-bound-variable="${variableId}">
                <span class="symbol symbol-math" data-math data-display="false">${escapeHtml(toLatexSymbol(variable.symbol))}</span>
                <strong>${escapeHtml(variable.name)}</strong>
                <small>${escapeHtml(variable.meaning)}</small>
              </button>
            `;
          })
          .join("")}
      </div>
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
  `;

  detailContentEl.querySelectorAll("[data-detail-variable]").forEach((button) => {
    button.addEventListener("click", () => selectVariable(button.dataset.detailVariable));
  });

  detailContentEl.querySelectorAll("[data-jump-page]").forEach((button) => {
    button.addEventListener("click", () => setActivePdfPage(Number(button.dataset.jumpPage)));
  });

  detailContentEl.querySelectorAll("[data-bound-variable]").forEach((button) => {
    button.addEventListener("click", () => selectVariable(button.dataset.boundVariable));
  });

  renderMathIn(detailContentEl);
  renderFormulaMathIn(detailContentEl);
}

function renderDocInsight() {
  const insight = state.analysis.documentInsight || { overview: "", pipeline: [] };
  const warnings = state.analysis.warnings || [];
  const formulaCandidates = state.analysis.formulaCandidates || [];
  const usageTips = buildUsageTips(state.analysis);
  docInsightEl.innerHTML = `
    <p>${escapeHtml(insight.overview || "No document insight available.")}</p>
    <h4>How to use</h4>
    <ul class="insight-list">${usageTips.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <h4>Pipeline</h4>
    <ol class="insight-list">${(insight.pipeline || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
    <h4>Warnings</h4>
    <ul class="insight-list">${warnings.length ? warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") : "<li>No warnings.</li>"}</ul>
    <h4>Formula candidates</h4>
    <ul class="insight-list">${formulaCandidates.length ? formulaCandidates.slice(0, 10).map((item) => `<li>${escapeHtml(item)}</li>`).join("") : "<li>No candidates detected.</li>"}</ul>
  `;
}

function renderPdfPreview() {
  const maxPage = Math.max(1, Number(state.analysis.pageCount) || 1);
  state.activePdfPage = clamp(state.activePdfPage, 1, maxPage);

  pageIndicatorEl.textContent = `Page ${state.activePdfPage} / ${maxPage}`;
  prevPageEl.disabled = state.activePdfPage <= 1;
  nextPageEl.disabled = state.activePdfPage >= maxPage;

  const pdfUrl = state.analysis.pdfUrl || "";
  openPdfLinkEl.href = pdfUrl || "#";
  openPdfLinkEl.style.pointerEvents = pdfUrl ? "auto" : "none";
  openPdfLinkEl.style.opacity = pdfUrl ? "1" : "0.4";

  const filename = extractFilename(pdfUrl);
  if (filename) {
    const imageSrc = `/api/pdf-page-image/${encodeURIComponent(filename)}/${state.activePdfPage}?scale=2`;
    if (pdfPageImageEl.getAttribute("src") !== imageSrc) {
      pdfPageImageEl.setAttribute("src", imageSrc);
    }
  } else {
    pdfPageImageEl.removeAttribute("src");
  }

  renderFormulaOverlay();

  const formulasOnPage = getFormulas().filter((formula) => formula.page === state.activePdfPage);
  pageFormulaLinksEl.innerHTML = formulasOnPage.length
    ? formulasOnPage
        .map(
          (formula) =>
            `<button class="inline-link ${formula.id === state.selectedFormulaId ? "active" : ""}" data-page-formula="${formula.id}">${escapeHtml(
              formula.id.toUpperCase()
            )} - ${escapeHtml(formula.title)}</button>`
        )
        .join("")
    : "<p class='muted'>No formula node is currently linked to this page.</p>";

  pageFormulaLinksEl.querySelectorAll("[data-page-formula]").forEach((button) => {
    button.addEventListener("click", () => selectFormula(button.dataset.pageFormula));
  });
}

function renderFormulaOverlay() {
  const formulasOnPage = getFormulas().filter((formula) => formula.page === state.activePdfPage && formula.bbox);
  formulaOverlayEl.innerHTML = formulasOnPage
    .map((formula) => {
      const bbox = formula.bbox;
      const active = formula.id === state.selectedFormulaId ? "active" : "";
      return `<button class="formula-region ${active}" data-region-formula="${formula.id}" style="left:${bbox.x0 * 100}%;top:${bbox.y0 * 100}%;width:${(bbox.x1 - bbox.x0) * 100}%;height:${(bbox.y1 - bbox.y0) * 100}%;"></button>`;
    })
    .join("");

  formulaOverlayEl.querySelectorAll("[data-region-formula]").forEach((button) => {
    button.addEventListener("click", () => selectFormula(button.dataset.regionFormula));
  });
}

function populateVariableSelectors() {
  const options = getVariables()
    .map((variable) => `<option value="${variable.id}">${escapeHtml(variable.symbol)} - ${escapeHtml(variable.name)}</option>`)
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
    const page = getFormulaMap().get(relatedFormulaId)?.page;
    if (page) {
      state.activePdfPage = page;
    }
  }
  render();
}

function selectFormula(formulaId) {
  state.selectedFormulaId = formulaId;
  const formula = getFormulaMap().get(formulaId);
  const firstVariableId = formula?.inputs?.[0];
  if (firstVariableId) {
    state.selectedVariableId = firstVariableId;
  }
  if (formula?.page) {
    state.activePdfPage = formula.page;
  }
  render();
}

function setActivePdfPage(page) {
  const maxPage = Math.max(1, Number(state.analysis.pageCount) || 1);
  state.activePdfPage = clamp(page, 1, maxPage);

  const firstFormulaOnPage = getFormulas().find((formula) => formula.page === state.activePdfPage);
  if (firstFormulaOnPage) {
    state.selectedFormulaId = firstFormulaOnPage.id;
    state.selectedVariableId = firstFormulaOnPage.inputs?.[0] || state.selectedVariableId;
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
        const isPageLinked = formula.page === state.activePdfPage;
        const midX = (from.x + to.x) / 2;
        const path = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;
        return `<path class="graph-path ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""} ${isPageLinked ? "page-linked" : ""}" d="${path}" />`;
      })
    )
    .join("");
}

function findVariablePath(sourceId, targetId) {
  if (sourceId === targetId) {
    return { variablePath: [sourceId], formulaPath: [], label: `${getVariableMap().get(sourceId)?.symbol} is already selected.` };
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

function setStatus(message, isError = false, progress = 0) {
  statusBannerEl.textContent = message;
  statusBannerEl.classList.toggle("error", isError);
  statusProgressBarEl.style.width = `${Math.max(0, Math.min(100, Math.round(progress * 100)))}%`;
}

function buildTaskStatusText(stage, message) {
  const stageLabel = TASK_STAGE_LABELS[stage] || stage;
  return `${stageLabel}: ${message}`;
}

function extractFilename(pdfUrl) {
  if (!pdfUrl) {
    return "";
  }
  const parts = pdfUrl.split("/");
  return parts[parts.length - 1] || "";
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderAnchorList(anchors = [], title = "Anchors") {
  if (!anchors?.length) {
    return "";
  }

  return `
    <div class="anchor-block">
      <p class="anchor-title">${escapeHtml(title)}</p>
      <ul class="anchor-list">
        ${anchors.map((anchor) => `<li>${escapeHtml(anchor)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function pickPreferredFormula(formulas = []) {
  if (!formulas.length) {
    return null;
  }
  return [...formulas].sort((a, b) => formulaPriorityScore(b) - formulaPriorityScore(a))[0];
}

function formulaPriorityScore(formula) {
  const semantic = formula?.semantic || {};
  return (
    (formula?.anchors?.length || 0) * 4 +
    (formula?.page ? 1 : 0) * 2 +
    (formula?.inputs?.length || 0) +
    (semantic?.complexity || 0)
  );
}

function buildUsageTips(analysis) {
  const tips = [
    "Upload returns immediately and the page begins polling task progress in the background.",
    "PyMuPDF produces the first visible graph first; Nougat enhancement may continue after you can already read the paper.",
    "Click a formula card in the center, then inspect its rendered equation and linked variables on the right.",
    "Use the page badge or Jump button to move the PDF preview to the linked page.",
  ];

  if (analysis.status === "fallback") {
    tips.push("Fallback mode means this result was reconstructed without full LLM semantics, so labels and relations are less reliable.");
  }

  if ((analysis.warnings || []).length) {
    tips.push("If a formula looks incomplete, check the warnings before trusting the semantic explanation.");
  }

  return tips;
}

function renderMathIn(root) {
  if (!root || !window.katex) {
    return;
  }

  root.querySelectorAll("[data-math]").forEach((node) => {
    const source = node.dataset.mathSource || node.textContent || "";
    node.dataset.mathSource = source;

    try {
      window.katex.render(source, node, {
        throwOnError: false,
        displayMode: node.dataset.display === "true",
        strict: "ignore",
        trust: true,
      });
      node.classList.add("math-ready");
      node.classList.remove("math-fallback");
    } catch {
      node.textContent = source;
      node.classList.add("math-fallback");
      node.classList.remove("math-ready");
    }
  });
}

function renderFormulaMathIn(root) {
  if (!root || !window.katex) {
    return;
  }

  const formulaMap = getFormulaMap();
  const variableMap = getVariableMap();

  root.querySelectorAll("[data-formula-math]").forEach((node) => {
    const formulaId = node.dataset.formulaMath;
    const formula = formulaMap.get(formulaId);
    if (!formula) {
      return;
    }

    const source = buildAnnotatedFormulaSource(formula, variableMap);
    try {
      window.katex.render(source, node, {
        throwOnError: false,
        displayMode: true,
        strict: "ignore",
        trust: true,
      });
      node.classList.add("math-ready");
      node.classList.remove("math-fallback");
      bindFormulaSymbolInteractions(node);
    } catch {
      node.textContent = formula.expression || "";
      node.classList.add("math-fallback");
      node.classList.remove("math-ready");
    }
  });
}

function bindFormulaSymbolInteractions(root) {
  root.querySelectorAll(".pn-symbol").forEach((element) => {
    const tokenClass = [...element.classList].find((name) => name.startsWith("pn-symbol-"));
    const variableId = tokenClass?.replace("pn-symbol-", "");
    if (!variableId) {
      return;
    }

    element.classList.toggle("is-active", variableId === state.selectedVariableId);
    element.addEventListener("click", (event) => {
      event.stopPropagation();
      selectVariable(variableId);
    });
  });
}

function buildAnnotatedFormulaSource(formula, variableMap) {
  let annotated = formula.expression || "";
  const variableIds = uniqueList([formula.output, ...(formula.inputs || [])]);
  const replacements = variableIds
    .map((variableId) => {
      const variable = variableMap.get(variableId);
      if (!variable?.symbol) {
        return null;
      }
      return {
        variableId,
        variants: uniqueList(buildSymbolVariants(variable.symbol)).sort((a, b) => b.length - a.length),
      };
    })
    .filter(Boolean);

  for (const item of replacements) {
    for (const variant of item.variants) {
      annotated = replaceFormulaToken(annotated, variant, item.variableId);
    }
  }

  return annotated;
}

function replaceFormulaToken(source, token, variableId) {
  if (!token) {
    return source;
  }

  return source.split(token).join(`\\htmlClass{pn-symbol pn-symbol-${variableId}}{${token}}`);
}

function buildSymbolVariants(symbol) {
  const raw = String(symbol || "").trim();
  if (!raw) {
    return [];
  }

  const latex = toLatexSymbol(raw);
  const variants = [raw, latex];
  if (raw.includes("_")) {
    variants.push(raw.replace(/_([A-Za-z0-9]+)/g, "_{$1}"));
    variants.push(latex.replace(/_([A-Za-z0-9]+)/g, "_{$1}"));
  }
  return variants;
}

function toLatexSymbol(symbol) {
  const raw = String(symbol || "").trim();
  if (!raw) {
    return "";
  }
  if (raw.includes("\\") || raw.includes("{") || raw.includes("}")) {
    return raw;
  }

  const greekMap = {
    alpha: "\\alpha",
    beta: "\\beta",
    gamma: "\\gamma",
    delta: "\\delta",
    epsilon: "\\epsilon",
    eta: "\\eta",
    theta: "\\theta",
    lambda: "\\lambda",
    mu: "\\mu",
    pi: "\\pi",
    rho: "\\rho",
    sigma: "\\sigma",
    tau: "\\tau",
    phi: "\\phi",
    psi: "\\psi",
    omega: "\\omega",
  };

  return greekMap[raw] || raw;
}

function uniqueList(items = []) {
  return [...new Set(items.filter(Boolean))];
}

init();
