import { documentInsight, formulas, variables } from "./data.js";

const state = {
  search: "",
  selectedVariableId: variables[0]?.id ?? null,
  selectedFormulaId: formulas[0]?.id ?? null,
  tracedFormulaIds: [],
  tracedVariableIds: [],
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

const variableMap = new Map(variables.map((item) => [item.id, item]));
const formulaMap = new Map(formulas.map((item) => [item.id, item]));

function init() {
  populateVariableSelectors();
  renderDocInsight();
  bindEvents();
  render();
  requestAnimationFrame(drawConnections);
  window.addEventListener("resize", drawConnections);
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
}

function render() {
  renderVariableList();
  renderGraph();
  renderDetail();
  requestAnimationFrame(drawConnections);
}

function renderVariableList() {
  const filteredVariables = variables.filter((variable) => {
    if (!state.search) {
      return true;
    }

    const haystack = [variable.symbol, variable.name, variable.meaning, variable.role]
      .join(" ")
      .toLowerCase();

    return haystack.includes(state.search);
  });

  variableListEl.innerHTML = filteredVariables
    .map((variable) => {
      const isSelected = variable.id === state.selectedVariableId;
      const isTraced = state.tracedVariableIds.includes(variable.id);
      const relatedFormulaLinks = variable.formulas
        .map((formulaId) => {
          const formula = formulaMap.get(formulaId);
          return `<button class="inline-link" data-formula-link="${formulaId}">${formula?.title ?? formulaId}</button>`;
        })
        .join("");

      return `
        <article class="variable-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" data-variable-id="${variable.id}">
          <div class="variable-card-top">
            <div>
              <p class="symbol">${variable.symbol}</p>
              <h3>${variable.name}</h3>
            </div>
            <span class="type-badge">${variable.type}</span>
          </div>
          <p class="meaning">${variable.meaning}</p>
          <dl class="meta-grid">
            <div><dt>Unit</dt><dd>${variable.unit}</dd></div>
            <div><dt>Role</dt><dd>${variable.role}</dd></div>
            <div><dt>Source</dt><dd>${variable.source}</dd></div>
            <div><dt>Memory</dt><dd>${variable.memory}</dd></div>
          </dl>
          <div class="reverse-trace">
            <span>Appears in</span>
            <div class="trace-links">${relatedFormulaLinks}</div>
          </div>
        </article>
      `;
    })
    .join("");

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
  graphGridEl.innerHTML = formulas
    .map((formula) => {
      const isSelected = formula.id === state.selectedFormulaId;
      const isTraced = state.tracedFormulaIds.includes(formula.id);
      const relatedVariables = formula.inputs
        .map((variableId) => {
          const variable = variableMap.get(variableId);
          const isActive = variableId === state.selectedVariableId || state.tracedVariableIds.includes(variableId);

          return `<button class="chip ${isActive ? "active" : ""}" data-variable-chip="${variableId}">${variable?.symbol ?? variableId}</button>`;
        })
        .join("");

      return `
        <article class="formula-card ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" data-formula-id="${formula.id}">
          <p class="formula-label">${formula.id.toUpperCase()}</p>
          <h3>${formula.title}</h3>
          <p class="expression">${formula.expression}</p>
          <p class="formula-note">${formula.physicalMeaning}</p>
          <div class="chip-row">${relatedVariables}</div>
          <div class="paper-note">${formula.paperNote}</div>
        </article>
      `;
    })
    .join("");

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
  const formula = formulaMap.get(state.selectedFormulaId);
  if (!formula) {
    detailTitleEl.textContent = "Select a formula";
    detailContentEl.innerHTML = "";
    return;
  }

  detailTitleEl.textContent = `${formula.id.toUpperCase()} · ${formula.title}`;

  const highlightedVariables = new Set([state.selectedVariableId, ...state.tracedVariableIds]);

  detailContentEl.innerHTML = `
    <section class="detail-hero">
      <p class="detail-expression">${formula.expression}</p>
      <p class="detail-summary">${formula.physicalMeaning}</p>
      <p class="detail-memory"><strong>Memory hook:</strong> ${formula.memory}</p>
    </section>
    <section class="detail-section">
      <h3>Chunked explanation</h3>
      ${formula.chunks
        .map((chunk) => {
          const chips = chunk.variableIds
            .map((variableId) => {
              const variable = variableMap.get(variableId);
              const active = highlightedVariables.has(variableId);
              return `<button class="chip ${active ? "active" : ""}" data-detail-variable="${variableId}">${variable?.symbol ?? variableId}</button>`;
            })
            .join("");

          return `
            <article class="chunk-card">
              <div class="chunk-top">
                <h4>${chunk.label}</h4>
                <div class="chip-row">${chips}</div>
              </div>
              <p>${chunk.text}</p>
            </article>
          `;
        })
        .join("")}
    </section>
    <section class="detail-section">
      <h3>Bound variables</h3>
      <div class="bound-variable-list">
        ${formula.inputs
          .map((variableId) => {
            const variable = variableMap.get(variableId);
            const active = variableId === state.selectedVariableId;
            return `
              <button class="bound-variable ${active ? "active" : ""}" data-detail-variable="${variableId}">
                <span>${variable?.symbol ?? variableId}</span>
                <small>${variable?.meaning ?? ""}</small>
              </button>
            `;
          })
          .join("")}
      </div>
    </section>
  `;

  detailContentEl.querySelectorAll("[data-detail-variable]").forEach((button) => {
    button.addEventListener("click", () => selectVariable(button.dataset.detailVariable));
  });
}

function renderDocInsight() {
  docInsightEl.innerHTML = `
    <p>${documentInsight.overview}</p>
    <ol class="insight-list">
      ${documentInsight.pipeline.map((item) => `<li>${item}</li>`).join("")}
    </ol>
  `;
}

function populateVariableSelectors() {
  const options = variables
    .map((variable) => `<option value="${variable.id}">${variable.symbol} · ${variable.name}</option>`)
    .join("");

  sourceSelectEl.innerHTML = options;
  targetSelectEl.innerHTML = options;

  sourceSelectEl.value = "p";
  targetSelectEl.value = "j";
}

function selectVariable(variableId) {
  state.selectedVariableId = variableId;
  const relatedFormulaId = variableMap.get(variableId)?.formulas[0];
  if (relatedFormulaId) {
    state.selectedFormulaId = relatedFormulaId;
  }
  render();
}

function selectFormula(formulaId) {
  state.selectedFormulaId = formulaId;
  const firstVariableId = formulaMap.get(formulaId)?.inputs[0];
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

  const lines = formulas
    .flatMap((formula) =>
      formula.dependsOn.map((dependencyId) => {
        const from = cardMap.get(dependencyId);
        const to = cardMap.get(formula.id);
        if (!from || !to) {
          return "";
        }

        const isTraced =
          state.tracedFormulaIds.includes(formula.id) && state.tracedFormulaIds.includes(dependencyId);
        const isSelected = formula.id === state.selectedFormulaId || dependencyId === state.selectedFormulaId;
        const midX = (from.x + to.x) / 2;
        const path = `M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`;

        return `<path class="graph-path ${isSelected ? "selected" : ""} ${isTraced ? "traced" : ""}" d="${path}" />`;
      })
    )
    .join("");

  graphLinesEl.innerHTML = lines;
}

function findVariablePath(sourceId, targetId) {
  if (sourceId === targetId) {
    return {
      variablePath: [sourceId],
      formulaPath: [],
      label: `${variableMap.get(sourceId)?.symbol} is already selected.`,
    };
  }

  const adjacency = new Map();

  for (const variable of variables) {
    adjacency.set(variable.id, []);
  }

  for (const formula of formulas) {
    for (const variableId of formula.inputs) {
      const links = adjacency.get(variableId) ?? [];
      for (const peerId of formula.inputs) {
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
            const symbol = variableMap.get(variableId)?.symbol ?? variableId;
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

  return {
    variablePath: [sourceId, targetId],
    formulaPath: [],
    label: "No semantic path found in the current mock graph.",
  };
}

init();
