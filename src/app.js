import { fallbackAnalysis } from "./data.js";

const TASK_STAGE_LABELS = {
  en: {
    queued: "Queued",
    uploaded: "Uploaded",
    pymupdf_processing: "PyMuPDF processing",
    pymupdf_done: "PyMuPDF done",
    nougat_processing: "Nougat processing",
    semantic_analysis: "Semantic analysis",
    completed: "Completed",
    failed: "Failed",
  },
  zh: {
    queued: "已排队",
    uploaded: "已上传",
    pymupdf_processing: "PyMuPDF 处理中",
    pymupdf_done: "PyMuPDF 已完成",
    nougat_processing: "Nougat 处理中",
    semantic_analysis: "语义分析中",
    completed: "已完成",
    failed: "失败",
  },
};

const UI_STRINGS = {
  en: {
    languageLabel: "Language",
    heroEyebrow: "Interactive Paper Graph",
    uploadKicker: "Pipeline",
    uploadTitle: "Upload a PDF for semantic parsing + precise formula grounding",
    uploadCopy: "The backend runs formula region detection, optional OCR, and semantic dependency parsing.",
    quickMode: "Quick mode: only run PyMuPDF first, then open the reader immediately",
    analyzeButton: "Analyze PDF",
    waitingUpload: "Waiting for a PDF upload.",
    sidebarKicker: "Dynamic Parameter Sidebar",
    variablesTitle: "Variables",
    variableSearch: "Search symbol / meaning",
    connectionTitle: "Connection Finder",
    connectionCopy: "Pick any two variables to reveal the shortest semantic path through the formula graph.",
    highlightPath: "Highlight Path",
    graphKicker: "Formula Graph Area",
    graphTitle: "Dependency Topology",
    legendDependency: "dependency",
    legendSelected: "selected",
    legendTraced: "traced",
    legendPageLinked: "page-linked",
    detailKicker: "Micro-Formula Detail View",
    selectFormula: "Select a formula",
    docInsightTitle: "Document Insight",
    pdfKicker: "PDF Preview",
    pdfTitle: "Page + Region Linked Reading",
    prev: "Prev",
    next: "Next",
    openOriginal: "Open original",
    pageFormulasTitle: "Formulas on this page",
    noPdfLoaded: "No PDF loaded",
    backendReady: "Backend ready. PDF parser: {pdf_parser}. Nougat: {nougat}. OCR: {ocr}. LLM: {llm}.",
    backendMissing: "Backend is not reachable yet. Start the FastAPI server to analyze real PDFs.",
    choosePdfFirst: "Choose a PDF file first.",
    uploading: "Uploading {name}...",
    pagePreviewMissing: "The current page preview is not available yet.",
    noVariablesMatch: "No variables matched the current search.",
    noFormulas: "No formulas were reconstructed for this PDF.",
    uploadToInspect: "Upload a paper to inspect a formula.",
    symbolsInFormula: "Symbols in this formula",
    chunkedExplanation: "Chunked explanation",
    howToUse: "How to use",
    pipeline: "Pipeline",
    warnings: "Warnings",
    formulaCandidates: "Formula candidates",
    noWarnings: "No warnings.",
    noCandidates: "No candidates detected.",
    noFormulasOnPage: "No formula node is currently linked to this page.",
    pageIndicator: "Page {page} / {maxPage}",
    sourcePage: "Source page",
    semantic: "Semantic",
    memoryHook: "Memory hook",
    paperAnchors: "Paper anchors",
    anchors: "Anchors",
    appearsIn: "Appears in",
    unit: "Unit",
    role: "Role",
    source: "Source",
    memory: "Memory",
    jumpToPage: "Jump to page {page}",
    taskLanguageMismatch: "UI language is {selected}. Current explanations are {current}. Re-run analysis to regenerate explanations in the selected language.",
    taskLanguageCurrent: "Current explanation language: {current}.",
    usageTip1: "Upload returns immediately and the page begins polling task progress in the background.",
    usageTip2: "PyMuPDF produces the first visible graph first; Nougat enhancement may continue after you can already read the paper.",
    usageTip3: "Click a formula card in the center, then inspect its rendered equation and linked variables on the right.",
    usageTip4: "Use the page badge or Jump button to move the PDF preview to the linked page.",
    usageTipFallback: "Fallback mode means this result was reconstructed without full LLM semantics, so labels and relations are less reliable.",
    usageTipWarnings: "If a formula looks incomplete, check the warnings before trusting the semantic explanation.",
    noPath: "No semantic path found in the current graph.",
    alreadySelected: "{symbol} is already selected.",
    statusModeHeuristic: "heuristic mode",
    statusModeInteractive: "interactive mode",
    stageDemo: "demo",
    pageBadge: "Page {page}",
    pageShort: "p.{page}",
    detailsJoiner: " - ",
    formulaShort: "{id} - {title}",
    unknown: "unknown",
  },
  zh: {},
};

UI_STRINGS.zh = { ...UI_STRINGS.en, languageLabel: "语言", heroEyebrow: "论文交互图谱", uploadKicker: "流程", uploadTitle: "上传 PDF，进行语义解析和公式定位", uploadCopy: "后端会运行公式区域检测、可选 OCR 和语义依赖解析。", quickMode: "快速模式：先只跑 PyMuPDF，立即打开阅读界面", analyzeButton: "解析 PDF", waitingUpload: "等待上传 PDF。", sidebarKicker: "动态变量侧栏", variablesTitle: "变量", variableSearch: "搜索符号 / 含义", connectionTitle: "连接查找", connectionCopy: "任选两个变量，查看它们在公式图中的最短语义路径。", highlightPath: "高亮路径", graphKicker: "公式图区", graphTitle: "依赖拓扑", legendDependency: "依赖", legendSelected: "选中", legendTraced: "追踪", legendPageLinked: "页关联", detailKicker: "公式详情", selectFormula: "选择一个公式", docInsightTitle: "文档洞察", pdfKicker: "PDF 预览", pdfTitle: "页码与区域联动阅读", prev: "上一页", next: "下一页", openOriginal: "打开原文", pageFormulasTitle: "本页公式", noPdfLoaded: "未加载 PDF", backendReady: "后端已就绪。PDF 解析器：{pdf_parser}。Nougat：{nougat}。OCR：{ocr}。LLM：{llm}。", backendMissing: "暂时无法连接后端。请先启动 FastAPI 服务。", choosePdfFirst: "请先选择一个 PDF 文件。", uploading: "正在上传 {name}...", pagePreviewMissing: "当前页预览暂时不可用。", noVariablesMatch: "没有变量匹配当前搜索。", noFormulas: "当前 PDF 没有重建出公式。", uploadToInspect: "上传论文后可查看公式详情。", symbolsInFormula: "该公式中的符号", chunkedExplanation: "分块解释", howToUse: "使用方式", pipeline: "流程", warnings: "警告", formulaCandidates: "公式候选", noWarnings: "没有警告。", noCandidates: "没有检测到候选公式。", noFormulasOnPage: "当前页没有关联的公式节点。", pageIndicator: "第 {page} / {maxPage} 页", sourcePage: "来源页", semantic: "语义", memoryHook: "记忆钩子", paperAnchors: "论文锚点", anchors: "锚点", appearsIn: "出现于", unit: "单位", role: "角色", source: "来源", memory: "记忆", jumpToPage: "跳到第 {page} 页", taskLanguageMismatch: "界面语言是 {selected}，当前解释内容是 {current}。请重新解析以生成所选语言的解释。", taskLanguageCurrent: "当前解释语言：{current}。", usageTip1: "上传会立即返回，页面会在后台轮询解析进度。", usageTip2: "PyMuPDF 会先产出第一版可见图谱；Nougat 增强可能在你开始阅读后继续完成。", usageTip3: "先点中间的公式卡片，再在右侧查看渲染公式和变量解释。", usageTip4: "可用页码徽标或 Jump 按钮跳到对应 PDF 页面。", usageTipFallback: "Fallback 模式表示当前结果未使用完整 LLM 语义分析，因此标签和依赖关系可靠性更低。", usageTipWarnings: "如果某条公式看起来不完整，先查看警告再决定是否采信解释。", noPath: "当前图里没有找到语义路径。", alreadySelected: "{symbol} 已经被选中。", statusModeHeuristic: "启发式模式", statusModeInteractive: "交互模式", stageDemo: "演示", pageBadge: "第 {page} 页", pageShort: "第{page}页", detailsJoiner: " - ", formulaShort: "{id} - {title}", unknown: "未知" };

const CLEAN_TASK_STAGE_LABELS = {
  en: TASK_STAGE_LABELS.en,
  zh: {
    queued: "排队中",
    uploaded: "已上传",
    pymupdf_processing: "PyMuPDF 解析中",
    pymupdf_done: "PyMuPDF 已完成",
    nougat_processing: "Nougat 处理中",
    semantic_analysis: "语义分析中",
    completed: "已完成",
    failed: "失败",
  },
};

const CLEAN_UI_STRINGS = {
  en: UI_STRINGS.en,
  zh: {
    ...UI_STRINGS.en,
    languageLabel: "语言",
    heroEyebrow: "论文交互图谱",
    uploadKicker: "解析流程",
    uploadTitle: "上传 PDF，生成带公式锚点与语义解释的论文阅读页",
    uploadCopy: "后端会执行公式区域检测、可选 OCR 与语义依赖分析。",
    quickMode: "快速模式：先只运行 PyMuPDF，尽快打开阅读页",
    analyzeButton: "解析 PDF",
    waitingUpload: "等待上传 PDF。",
    sidebarKicker: "变量侧栏",
    variablesTitle: "变量",
    variableSearch: "搜索符号 / 含义",
    connectionTitle: "关系查询",
    connectionCopy: "选择两个变量，查看它们在当前公式图中的最短路径。",
    highlightPath: "高亮路径",
    graphKicker: "公式图区域",
    graphTitle: "依赖拓扑",
    legendDependency: "依赖",
    legendSelected: "已选中",
    legendTraced: "已追踪",
    legendPageLinked: "页内关联",
    detailKicker: "公式详情",
    selectFormula: "选择一个公式",
    docInsightTitle: "文档说明",
    pdfKicker: "PDF 预览",
    pdfTitle: "页码与区域联动阅读",
    prev: "上一页",
    next: "下一页",
    openOriginal: "打开原 PDF",
    pageFormulasTitle: "本页公式",
    noPdfLoaded: "未加载 PDF",
    backendReady: "后端可用。PDF 解析器：{pdf_parser}。Nougat：{nougat}。OCR：{ocr}。LLM：{llm}。",
    backendMissing: "暂时无法连接后端。请先启动 FastAPI 服务。",
    choosePdfFirst: "请先选择一个 PDF 文件。",
    uploading: "正在上传 {name}...",
    pagePreviewMissing: "当前页预览暂不可用。",
    noVariablesMatch: "没有匹配当前搜索条件的变量。",
    noFormulas: "当前 PDF 没有重建出公式。",
    uploadToInspect: "上传论文后即可查看公式详情。",
    symbolsInFormula: "本公式中的符号",
    chunkedExplanation: "分块解释",
    howToUse: "使用方式",
    pipeline: "解析流程",
    warnings: "警告",
    formulaCandidates: "公式候选",
    noWarnings: "没有警告。",
    noCandidates: "没有检测到公式候选。",
    noFormulasOnPage: "当前页面没有关联到公式节点。",
    pageIndicator: "第 {page} / {maxPage} 页",
    sourcePage: "来源页",
    semantic: "语义结构",
    memoryHook: "记忆点",
    paperAnchors: "论文锚点",
    anchors: "锚点",
    appearsIn: "出现于",
    unit: "单位",
    role: "角色",
    source: "来源",
    memory: "记忆",
    jumpToPage: "跳到第 {page} 页",
    taskLanguageMismatch: "界面语言为 {selected}，当前解释语言为 {current}。请重新解析以生成所选语言的解释。",
    taskLanguageCurrent: "当前解释语言：{current}。",
    usageTip1: "上传后会立即返回任务，并在后台持续轮询解析进度。",
    usageTip2: "PyMuPDF 会先生成首版可读结果，Nougat 作为后台增强补充公式。",
    usageTip3: "点击中间公式卡片，再在右侧查看渲染后的公式与变量解释。",
    usageTip4: "点击页码标签或跳转按钮，可将 PDF 预览切到对应页面。",
    usageTipFallback: "Fallback 模式表示当前结果未经过完整 LLM 语义分析，标签和关系可信度较低。",
    usageTipWarnings: "如果某个公式看起来不完整，请先查看警告后再信任解释。",
    noPath: "当前图中没有找到语义路径。",
    alreadySelected: "{symbol} 已经被选中。",
    statusModeHeuristic: "启发式模式",
    statusModeInteractive: "交互模式",
    stageDemo: "演示",
    pageBadge: "第 {page} 页",
    pageShort: "p.{page}",
    formulaShort: "{id} - {title}",
    unknown: "未知",
  },
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
  selectedLanguage: window.localStorage.getItem("papernexus-language") || fallbackAnalysis.language || "en",
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
const languageSelectEl = document.querySelector("#language-select");
const analyzeButtonEl = document.querySelector("#analyze-button");
const statusBannerEl = document.querySelector("#status-banner");
const statusProgressBarEl = document.querySelector("#status-progress-bar");
const usageGuideTitleEl = document.querySelector("#usage-guide-title");
const usageGuideEl = document.querySelector("#usage-guide");
const paperMetaEl = document.querySelector("#paper-meta");
const prevPageEl = document.querySelector("#prev-page");
const nextPageEl = document.querySelector("#next-page");
const pageIndicatorEl = document.querySelector("#page-indicator");
const pageFormulaLinksEl = document.querySelector("#page-formula-links");
const pdfPageImageEl = document.querySelector("#pdf-page-image");
const formulaOverlayEl = document.querySelector("#formula-overlay");
const openPdfLinkEl = document.querySelector("#open-pdf-link");

function init() {
  languageSelectEl.value = normalizeLanguage(state.selectedLanguage);
  bindEvents();
  renderStaticText();
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
  languageSelectEl.addEventListener("change", () => {
    state.selectedLanguage = normalizeLanguage(languageSelectEl.value);
    window.localStorage.setItem("papernexus-language", state.selectedLanguage);
    renderStaticText();
    render();
    probeHealth();
  });

  analyzeButtonEl.addEventListener("click", analyzePdf);
  prevPageEl.addEventListener("click", () => setActivePdfPage(state.activePdfPage - 1));
  nextPageEl.addEventListener("click", () => setActivePdfPage(state.activePdfPage + 1));
  pdfPageImageEl.addEventListener("error", () => {
    pdfPageImageEl.removeAttribute("src");
    if (state.activeTaskStatus !== "running") {
      setStatus(t("pagePreviewMissing"), false, state.activeTaskProgress);
    }
  });
}

function renderStaticText() {
  setText("#hero-eyebrow", t("heroEyebrow"));
  setText("#language-label", t("languageLabel"));
  setText("#upload-kicker", t("uploadKicker"));
  setText("#upload-title", t("uploadTitle"));
  setText("#upload-copy-text", t("uploadCopy"));
  setText("#quick-mode-label", t("quickMode"));
  setText("#analyze-button", t("analyzeButton"));
  if (usageGuideTitleEl) {
    usageGuideTitleEl.textContent = t("howToUse");
  }
  if (!state.activeTaskId && !state.loading) {
    setStatus(t("waitingUpload"), false, 0);
  }
  setText("#sidebar-kicker", t("sidebarKicker"));
  setText("#variables-title", t("variablesTitle"));
  searchInputEl.placeholder = t("variableSearch");
  setText("#connection-title", t("connectionTitle"));
  setText("#connection-copy", t("connectionCopy"));
  setText("#find-path-button", t("highlightPath"));
  setText("#graph-kicker", t("graphKicker"));
  setText("#graph-title", t("graphTitle"));
  setText("#legend-dependency", t("legendDependency"));
  setText("#legend-selected", t("legendSelected"));
  setText("#legend-traced", t("legendTraced"));
  setText("#legend-page-linked", t("legendPageLinked"));
  setText("#detail-kicker", t("detailKicker"));
  setText("#doc-insight-title", t("docInsightTitle"));
  setText("#pdf-kicker", t("pdfKicker"));
  setText("#pdf-title", t("pdfTitle"));
  setText("#prev-page", t("prev"));
  setText("#next-page", t("next"));
  setText("#open-pdf-link", t("openOriginal"));
  setText("#page-formulas-title", t("pageFormulasTitle"));
}

async function probeHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      return;
    }
    const health = await response.json();
    setStatus(
      t("backendReady", health),
      false,
      0
    );
  } catch {
    setStatus(t("backendMissing"), true, 0);
  }
}

async function analyzePdf() {
  const file = pdfInputEl.files?.[0];
  if (!file) {
    setStatus(t("choosePdfFirst"), true, 0);
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
  setStatus(t("uploading", { name: file.name }), false, state.activeTaskProgress);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("quick_mode", quickModeEl.checked ? "true" : "false");
  formData.append("language", state.selectedLanguage);

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
  renderUsageGuide();
  renderVariableList();
  renderGraph();
  renderDetail();
  renderDocInsight();
  renderPdfPreview();
  requestAnimationFrame(drawConnections);
}

function renderMeta() {
  const analysis = state.analysis;
  const modeLabel = analysis.status === "fallback" ? t("statusModeHeuristic") : t("statusModeInteractive");
  const stageLabel = state.activeTaskId ? getStageLabel(state.activeTaskStage) : t("stageDemo");
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

function renderUsageGuide() {
  if (!usageGuideEl) {
    return;
  }
  const tips = buildUsageTips(state.analysis);
  usageGuideEl.innerHTML = `<ul>${tips.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderVariableList() {
  const formulaMap = getFormulaMap();
  const selectedVariable = getVariableMap().get(state.selectedVariableId);
  const filteredVariables = getVariables().filter((variable) => {
    if (!state.search) {
      return true;
    }

    const haystack = [variable.symbol, variable.name, variable.meaning, variable.role].join(" ").toLowerCase();
    return haystack.includes(state.search);
  });

  const summaryHtml = selectedVariable
    ? `
      <section class="variable-summary">
        <div class="variable-summary-head">
          <div class="symbol symbol-math" data-math data-display="false">${escapeHtml(toLatexSymbol(selectedVariable.symbol))}</div>
          <div>
            <h3>${escapeHtml(selectedVariable.name)}</h3>
            <p class="muted">${escapeHtml(selectedVariable.role)} · ${escapeHtml(selectedVariable.type)}</p>
          </div>
        </div>
        <p class="meaning compact-meaning">${escapeHtml(selectedVariable.meaning)}</p>
        <div class="summary-meta-row">
          <span><strong>${escapeHtml(t("unit"))}:</strong> ${escapeHtml(selectedVariable.unit || "-")}</span>
          <span><strong>${escapeHtml(t("source"))}:</strong> ${escapeHtml(selectedVariable.source)}</span>
        </div>
      </section>
    `
    : "";

  const tableHtml = filteredVariables.length
    ? `
      <div class="variable-table-wrap">
        <table class="variable-table">
          <thead>
            <tr>
              <th>${escapeHtml(t("variablesTitle"))}</th>
              <th>${escapeHtml(t("role"))}</th>
              <th>${escapeHtml(t("sourcePage"))}</th>
            </tr>
          </thead>
          <tbody>
            ${filteredVariables
              .map((variable) => {
                const isSelected = variable.id === state.selectedVariableId;
                const firstFormula = (variable.formulas || []).map((formulaId) => formulaMap.get(formulaId)).find(Boolean);
                const pageLabel = firstFormula?.page ? t("pageShort", { page: firstFormula.page }) : "-";
                return `
                  <tr class="${isSelected ? "is-selected" : ""}" data-variable-row="${variable.id}">
                    <td>
                      <div class="table-symbol-row">
                        <span class="symbol symbol-math" data-math data-display="false">${escapeHtml(toLatexSymbol(variable.symbol))}</span>
                        <div class="table-symbol-copy">
                          <strong>${escapeHtml(variable.name)}</strong>
                          <small>${escapeHtml(variable.unit || "-")}</small>
                        </div>
                      </div>
                    </td>
                    <td>${escapeHtml(variable.role)}</td>
                    <td>${escapeHtml(pageLabel)}</td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </div>
    `
    : `<div class="empty-state">${escapeHtml(t("noVariablesMatch"))}</div>`;

  const relatedFormulaLinks = selectedVariable
    ? (selectedVariable.formulas || [])
        .map((formulaId) => {
          const formula = formulaMap.get(formulaId);
          const page = formula?.page ? ` (${t("pageShort", { page: formula.page })})` : "";
          return `<button class="inline-link" data-formula-link="${formulaId}">${escapeHtml(formula?.title ?? formulaId)}${escapeHtml(page)}</button>`;
        })
        .join("")
    : "";

  const anchorHtml = selectedVariable?.anchors?.length ? renderAnchorList(selectedVariable.anchors, t("anchors")) : "";

  variableListEl.innerHTML = `
    ${summaryHtml}
    ${tableHtml}
    ${selectedVariable ? `<div class="variable-summary-tail"><span>${escapeHtml(t("appearsIn"))}</span><div class="trace-links">${relatedFormulaLinks}</div>${anchorHtml}</div>` : ""}
  `;

  variableListEl.querySelectorAll("[data-variable-row]").forEach((row) => {
    row.addEventListener("click", () => selectVariable(row.dataset.variableRow));
  });
  variableListEl.querySelectorAll("[data-formula-link]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      selectFormula(button.dataset.formulaLink);
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
          const pageBadge = formula.page ? `<button class="page-badge" data-formula-page="${formula.page}">${escapeHtml(t("pageBadge", { page: formula.page }))}</button>` : "";

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
    : `<div class="empty-state wide">${escapeHtml(t("noFormulas"))}</div>`;

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
    detailTitleEl.textContent = t("selectFormula");
    detailContentEl.innerHTML = `<div class="empty-state">${escapeHtml(t("uploadToInspect"))}</div>`;
    return;
  }

  detailTitleEl.textContent = `${formula.id.toUpperCase()} - ${formula.title}`;
  const highlightedVariables = new Set([state.selectedVariableId, ...state.tracedVariableIds]);
  const semantic = formula.semantic || { lhsSymbols: [], rhsSymbols: [], operators: [], complexity: 0 };

  detailContentEl.innerHTML = `
    <section class="detail-hero">
      <div class="detail-expression math-block math-block-large" data-formula-math="${formula.id}"></div>
      <p class="detail-summary">${escapeHtml(formula.physicalMeaning)}</p>
      <p class="detail-memory"><strong>${escapeHtml(t("memoryHook"))}:</strong> ${escapeHtml(formula.memory)}</p>
      <p class="detail-summary"><strong>${escapeHtml(t("sourcePage"))}:</strong> ${formula.page || escapeHtml(t("unknown"))}</p>
      <p class="detail-summary"><strong>${escapeHtml(t("semantic"))}:</strong> LHS [${escapeHtml((semantic.lhsSymbols || []).join(", "))}] RHS [${escapeHtml((semantic.rhsSymbols || []).join(", "))}] Ops [${escapeHtml((semantic.operators || []).join(" "))}]</p>
      ${formula.page ? `<button class="mini-button" data-jump-page="${formula.page}">${escapeHtml(t("jumpToPage", { page: formula.page }))}</button>` : ""}
      ${renderAnchorList(formula.anchors, t("paperAnchors"))}
    </section>
    <section class="detail-section">
      <h3>${escapeHtml(t("symbolsInFormula"))}</h3>
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
      <h3>${escapeHtml(t("chunkedExplanation"))}</h3>
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
  const languageNote =
    normalizeLanguage(state.analysis.language || "en") !== normalizeLanguage(state.selectedLanguage)
      ? t("taskLanguageMismatch", {
          selected: getLanguageDisplayNameSafe(state.selectedLanguage),
          current: getLanguageDisplayNameSafe(state.analysis.language || "en"),
        })
      : t("taskLanguageCurrent", { current: getLanguageDisplayNameSafe(state.analysis.language || "en") });
  docInsightEl.innerHTML = `
    <p>${escapeHtml(insight.overview || "")}</p>
    <p class="muted">${escapeHtml(languageNote)}</p>
    <h4>${escapeHtml(t("pipeline"))}</h4>
    <ol class="insight-list">${(insight.pipeline || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
    <h4>${escapeHtml(t("warnings"))}</h4>
    <ul class="insight-list">${warnings.length ? warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") : `<li>${escapeHtml(t("noWarnings"))}</li>`}</ul>
    <h4>${escapeHtml(t("formulaCandidates"))}</h4>
    <ul class="insight-list">${formulaCandidates.length ? formulaCandidates.slice(0, 10).map((item) => `<li>${escapeHtml(item)}</li>`).join("") : `<li>${escapeHtml(t("noCandidates"))}</li>`}</ul>
  `;
}

function renderPdfPreview() {
  const maxPage = Math.max(1, Number(state.analysis.pageCount) || 1);
  state.activePdfPage = clamp(state.activePdfPage, 1, maxPage);

  pageIndicatorEl.textContent = t("pageIndicator", { page: state.activePdfPage, maxPage });
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
    : `<p class='muted'>${escapeHtml(t("noFormulasOnPage"))}</p>`;

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
    return {
      variablePath: [sourceId],
      formulaPath: [],
      label: t("alreadySelected", { symbol: getVariableMap().get(sourceId)?.symbol || sourceId }),
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

  return { variablePath: [sourceId, targetId], formulaPath: [], label: t("noPath") };
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
  const stageLabel = getStageLabel(stage);
  return `${stageLabel}: ${message}`;
}

function getStageLabel(stage) {
  const labels = CLEAN_TASK_STAGE_LABELS[normalizeLanguage(state.selectedLanguage)] || CLEAN_TASK_STAGE_LABELS.en;
  return labels[stage] || stage;
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

function t(key, values = {}) {
  const strings = CLEAN_UI_STRINGS[normalizeLanguage(state.selectedLanguage)] || CLEAN_UI_STRINGS.en;
  return interpolate(strings[key] || CLEAN_UI_STRINGS.en[key] || key, values);
}

function interpolate(template, values = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
}

function normalizeLanguage(language) {
  return String(language || "").toLowerCase().startsWith("zh") ? "zh" : "en";
}

function getLanguageDisplayName(language) {
  return normalizeLanguage(language) === "zh" ? "中文" : "English";
}

function getLanguageDisplayNameSafe(language) {
  return normalizeLanguage(language) === "zh" ? "中文" : "English";
}

function setText(selector, value) {
  const node = document.querySelector(selector);
  if (node) {
    node.textContent = value;
  }
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
    t("usageTip1"),
    t("usageTip2"),
    t("usageTip3"),
    t("usageTip4"),
  ];

  if (analysis.status === "fallback") {
    tips.push(t("usageTipFallback"));
  }

  if ((analysis.warnings || []).length) {
    tips.push(t("usageTipWarnings"));
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
