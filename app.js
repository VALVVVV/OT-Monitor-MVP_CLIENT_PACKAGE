let documents = [];

const sources = [
  {
    id: 1,
    name: "Минтруд России",
    url: "https://mintrud.gov.ru/docs",
    section: "Нормативные документы / документы Минтруда",
    frequency: "вручную / демо-запуск",
    lastCheck: "—",
    status: "Активен"
  },
  {
    id: 2,
    name: "МЧС России",
    url: "https://mchs.gov.ru/dokumenty/vse-dokumenty",
    section: "Документы МЧС",
    frequency: "вручную / демо-запуск",
    lastCheck: "—",
    status: "Активен"
  },
  {
    id: 3,
    name: "Минздрав России",
    url: "https://minzdrav.gov.ru/documents",
    section: "Документы Минздрава",
    frequency: "вручную / демо-запуск",
    lastCheck: "—",
    status: "Активен"
  }
];

const schedules = [
  {
    source: "Минтруд России",
    frequency: "ручной запуск",
    lastCheck: "—",
    nextCheck: "не настроена",
    launchMethod: "run_demo_check.bat",
    status: "Ручной режим"
  },
  {
    source: "МЧС России",
    frequency: "ручной запуск",
    lastCheck: "—",
    nextCheck: "не настроена",
    launchMethod: "run_demo_check.bat",
    status: "Ручной режим"
  },
  {
    source: "Минздрав России",
    frequency: "ручной запуск",
    lastCheck: "—",
    nextCheck: "не настроена",
    launchMethod: "run_demo_check.bat",
    status: "Ручной режим"
  }
];

const searchQueries = [
  {
    source: "Минтруд России",
    topic: "Обучение по охране труда",
    mode: "Мягкий отбор",
    rule: "Без отбора по ключевым словам",
    comment: "Документы собираются без жёсткого отбора по ключевым словам, чтобы не пропустить важные публикации. На следующем этапе правила отбора можно будет уточнить, а не нужные документы инженер сможет пометить как «Неактуально / не относится»."
  },
  {
    source: "Минздрав России",
    topic: "Медицинские осмотры",
    mode: "Мягкий отбор",
    rule: "Без отбора по ключевым словам",
    comment: "Документы по медосмотрам и медицине лучше сначала показывать шире, а лишнее инженер сможет убрать решением."
  },
  {
    source: "МЧС России",
    topic: "Огнетушители",
    mode: "Мягкий отбор",
    rule: "Без отбора по ключевым словам",
    comment: "Сейчас важно не пропустить документы по пожарной безопасности, ГО и ЧС. Отбор МЧС должен быть мягким, даже если в ленту попадут лишние документы."
  }
];

const sourceRulesTableData = [
  {
    source: "Минтруд России",
    url: "https://mintrud.gov.ru/docs",
    section: "Охрана труда",
    mode: "Отбор по рабочим разделам",
    ruleComment:
      "Показываются документы со страницы Минтруда, если они относятся к подходящим разделам с приказами и соглашениями. Система берёт документы из рабочих разделов источника, чтобы не перегружать список лишними публикациями. После этого инженер вручную отмечает неактуальные или не относящиеся документы.",
    status: "Активен"
  },
  {
    source: "МЧС России",
    url: "https://mchs.gov.ru/dokumenty/vse-dokumenty",
    section: "Пожарная безопасность, ГО и ЧС",
    mode: "Широкий отбор по дате",
    ruleComment:
      "Показываются документы из раздела МЧС «Все документы» начиная с 1 июня 2026 года. Система показывает новые документы источника по дате публикации. Дальше инженер вручную отмечает лишние документы как неактуальные или не относящиеся.",
    status: "Активен"
  },
  {
    source: "Минздрав России",
    url: "https://minzdrav.gov.ru/documents",
    section: "Медицина",
    mode: "Широкий отбор по дате",
    ruleComment:
      "Показываются документы Минздрава начиная с 1 мая 2026 года. Система показывает новые документы по дате публикации, чтобы не пропустить важные изменения. После этого инженер вручную отмечает лишние документы.",
    status: "Активен"
  }
];

let checkLog = [];

const decisionStatuses = [
  "Новое",
  "Проверка актуальности",
  "Принято в работу",
  "Неактуально / не относится",
  "Закрыто"
];

const documentList = document.getElementById("document-list");
const selectedDocument = document.getElementById("selected-document");
const lastCheckValue = document.getElementById("last-check");
const newDocsCount = document.getElementById("new-docs");
const inReviewCount = document.getElementById("in-review");
const inWorkCount = document.getElementById("in-work");
const consultationCount = document.getElementById("consultation-docs");
const closedCount = document.getElementById("closed-docs");
const checkButton = document.getElementById("check-now");
const checkNotification = document.getElementById("check-notification");
const defaultCheckButtonText = checkButton ? checkButton.textContent : "Проверить сейчас";
const sourceRulesList = document.getElementById("source-rules-list");
const decisionLogTable = document.getElementById("decision-log");
const checkLogTable = document.getElementById("check-log");
const toggleDocumentsListButton = document.getElementById("toggle-documents-list");
const resetDocumentsFilterButton = document.getElementById("reset-documents-filter");
const currentDocumentsFilterLabel = document.getElementById("current-documents-filter");
const filterStatusNewButton = document.getElementById("filter-status-new");
const filterStatusReviewButton = document.getElementById("filter-status-review");
const filterStatusWorkButton = document.getElementById("filter-status-work");
const filterStatusNotRelevantButton = document.getElementById("filter-status-not-relevant");
const filterStatusClosedButton = document.getElementById("filter-status-closed");
const checkModeValue = document.getElementById("check-mode-value");
const scheduleLastCheckValue = document.getElementById("schedule-last-check");
const toggleScheduleSettingsButton = document.getElementById("toggle-schedule-settings");
const scheduleSettingsPanel = document.getElementById("schedule-settings-panel");
const scheduleFrequencySelect = document.getElementById("schedule-frequency");
const scheduleTimeInput = document.getElementById("schedule-time");
const saveScheduleSettingsButton = document.getElementById("save-schedule-settings");
const scheduleSettingsMessage = document.getElementById("schedule-settings-message");
const sectionToggleButtons = document.querySelectorAll(".section-toggle");
const toggleReviewModeButton = document.getElementById("toggle-review-mode");
const downloadReviewReportButton = document.getElementById("download-review-report");
const downloadReviewCommentsButton = document.getElementById("download-review-comments");
const reviewModeTip = document.getElementById("review-mode-tip");
const reviewModeTipText = document.querySelector(".review-mode-tip-text");
const reviewCommentsCounter = document.getElementById("review-comments-counter");
const addGeneralReviewCommentButton = document.getElementById("add-general-review-comment");
const reviewCommentModal = document.getElementById("review-comment-modal");
const reviewZoneTitle = document.getElementById("review-zone-title");
const reviewCommentText = document.getElementById("review-comment-text");
const reviewFormMessage = document.getElementById("review-form-message");
const saveReviewCommentButton = document.getElementById("save-review-comment");
const cancelReviewCommentButton = document.getElementById("cancel-review-comment");
const defaultReviewModeTipText = reviewModeTipText ? reviewModeTipText.textContent : "";
let selectedDocId = null;
let showAllDocuments = false;
let activeStatusFilter = null;
let reviewMode = false;
let activeReviewZone = null;
let reviewCommentsCount = 0;
let reviewCommentJustSaved = false;
const collapsedDocumentsCount = 5;
const reviewCommentDocumentZones = new Set([
  "document_card",
  "document_statuses",
  "engineer_comment",
  "documents_list"
]);
const scheduleInterfaceState = {
  frequency: "Только вручную",
  time: "09:00",
  isExpanded: false,
  message: ""
};

function mapApiDecisionToUiEntry(item) {
  return {
    id: item.id,
    docId: item.document_id,
    title: item.document_title || "Без названия",
    datetime: formatCheckLogDatetime(item.decided_at),
    status: normalizeDocumentStatus(item.status),
    comment: item.comment || "",
    responsible: item.responsible || "Инженер по ОТ"
  };
}

async function loadDecisionLogFromApi() {
  const response = await fetch("/api/decisions", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();

  if (!payload.ok || !Array.isArray(payload.decisions)) {
    throw new Error("Некорректный ответ /api/decisions");
  }

  return payload.decisions.map(mapApiDecisionToUiEntry);
}

async function saveDecisionToApi(documentId, status, comment) {
  const response = await fetch(`/api/documents/${documentId}/decision`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      status,
      comment,
      responsible: "Инженер по ОТ"
    })
  });

  const payload = await response.json();

  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || `HTTP ${response.status}`);
  }

  return payload;
}

let decisionLog = [];

const sourceNames = {
  mintrud: "Минтруд России",
  mchs: "МЧС России",
  minzdrav: "Минздрав России"
};

function mapApiDocumentToUiDocument(item) {
  const discoveredDate = String(item.discovered_at || "").slice(0, 10);

  return {
    id: item.id,
    title: item.title || "Без названия",
    source: sourceNames[item.source_id] || item.source_id || "Не указан",
    section: item.section || item.topic || "Общее",
    summary: item.summary || "Краткое описание отсутствует.",
    status: item.status || "Новое",
    foundDate: item.publication_date || discoveredDate,
    originalUrl: item.original_url || "",
    fileUrl: item.file_url || "",
    savedFilePath: item.saved_file_path || "",
    downloadStatus: item.download_status || "not_requested",
    engineerComment: item.engineer_comment || "",
    internalTypes: [],
    aiNote: "",
    draftRecommendation: "",
    draftWarning: ""
  };
}

async function downloadDocumentFileFromApi(documentId) {
  const response = await fetch(`/api/documents/${documentId}/download`, {
    method: "POST"
  });

  const payload = await response.json();

  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || `HTTP ${response.status}`);
  }

  return payload;
}

async function loadDocumentsFromApi() {
  const response = await fetch("/api/documents", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();

  if (!payload.ok || !Array.isArray(payload.documents)) {
    throw new Error("Некорректный ответ /api/documents");
  }

  return payload.documents.map(mapApiDocumentToUiDocument);
}

function formatCheckLogDatetime(isoDatetime) {
  if (!isoDatetime) {
    return "-";
  }

  const date = new Date(isoDatetime);
  if (Number.isNaN(date.getTime())) {
    return isoDatetime;
  }

  const dateStr = String(date.getDate()).padStart(2, "0");
  const monthStr = String(date.getMonth() + 1).padStart(2, "0");
  const yearStr = date.getFullYear();
  const hoursStr = String(date.getHours()).padStart(2, "0");
  const minsStr = String(date.getMinutes()).padStart(2, "0");
  const secsStr = String(date.getSeconds()).padStart(2, "0");
  return `${dateStr}.${monthStr}.${yearStr} ${hoursStr}:${minsStr}:${secsStr}`;
}

function mapApiCheckToUiEntry(item) {
  const resultLabels = {
    running: "Выполняется",
    success: "Успешно",
    partial: "Частично",
    error: "Ошибка"
  };

  return {
    datetime: formatCheckLogDatetime(item.finished_at || item.started_at),
    source: sourceNames[item.source_id] || item.source_id || "Неизвестный источник",
    result: resultLabels[item.result] || "Ошибка",
    found: Number.isFinite(Number(item.found_count)) ? Number(item.found_count) : 0,
    newDocs: Number.isFinite(Number(item.added_count)) ? Number(item.added_count) : 0,
    error: item.error_message && item.error_message.trim()
      ? item.error_message
      : "-"
  };
}

async function loadCheckLogFromApi() {
  const response = await fetch("/api/checks", { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const payload = await response.json();

  if (!payload.ok || !Array.isArray(payload.checks)) {
    throw new Error("Некорректный ответ /api/checks");
  }

  return payload.checks.map(mapApiCheckToUiEntry);
}

function normalizeDocumentStatus(status) {
  const statusValue = String(status || "").trim().toLowerCase();

  if (["новое", "new"].includes(statusValue)) {
    return "Новое";
  }

  if (
    [
      "на проверке",
      "проверка актуальности",
      "in_progress",
      "in review",
      "review",
      "требует консультации",
      "consultation",
      "needs consultation",
      "needs_consultation"
    ].includes(statusValue)
  ) {
    return "Проверка актуальности";
  }

  if (["принято в работу", "in_work", "in work"].includes(statusValue)) {
    return "Принято в работу";
  }

  if (
    ["не относится", "неактуально / не относится", "не актуально / не относится", "not relevant"]
      .includes(statusValue)
  ) {
    return "Неактуально / не относится";
  }

  if (["закрыто", "closed", "done"].includes(statusValue)) {
    return "Закрыто";
  }

  return status || "Новое";
}

function getStatusBadgeClass(status) {
  const normalizedStatus = normalizeDocumentStatus(status);

  if (normalizedStatus === "Новое") {
    return "status-new";
  }

  if (normalizedStatus === "Проверка актуальности") {
    return "status-review";
  }

  if (normalizedStatus === "Принято в работу") {
    return "status-work";
  }

  if (normalizedStatus === "Неактуально / не относится") {
    return "status-not-relevant";
  }

  if (normalizedStatus === "Закрыто") {
    return "status-closed";
  }

  return "status-default";
}

function renderStatusBadge(status, extraClass = "") {
  const normalizedStatus = normalizeDocumentStatus(status);
  const className = ["status-badge", getStatusBadgeClass(normalizedStatus), extraClass]
    .filter(Boolean)
    .join(" ");

  return `<span class="${className}">${normalizedStatus}</span>`;
}

function getDocumentIconPath(doc) {
  const source = (doc?.source || "").toLowerCase();
  const section = (doc?.section || "").toLowerCase();

  if (
    source.includes("мчс") ||
    section.includes("пожарная безопасность") ||
    section.includes("го и чс")
  ) {
    return "assets/icons/mchs_fire.png";
  }

  if (source.includes("минтруд") || section.includes("охрана труда")) {
    return "assets/icons/labor_safety.png";
  }

  if (source.includes("минздрав") || section.includes("медицина")) {
    return "assets/icons/medical_kit.png";
  }

  return "";
}

function renderDocumentIcon(doc, extraClass = "") {
  const iconPath = getDocumentIconPath(doc);

  if (!iconPath) {
    return "";
  }

  return `<img class="document-topic-icon ${extraClass}" src="${iconPath}" alt="" aria-hidden="true">`;
}

function getLatestCheckDatetime() {
  if (!Array.isArray(checkLog) || checkLog.length === 0) {
    return "—";
  }

  return checkLog[0].datetime || "—";
}

function getLatestCheckDatetimeForSource(sourceName) {
  if (!Array.isArray(checkLog) || checkLog.length === 0) {
    return "—";
  }

  const matchedEntry = checkLog.find(entry => entry.source === sourceName);
  return matchedEntry && matchedEntry.datetime ? matchedEntry.datetime : "—";
}


function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatSourceCheckMessage(payload) {
  if (!payload || !Array.isArray(payload.source_results)) {
    return payload && payload.message
      ? escapeHtml(payload.message)
      : "Проверка завершена.";
  }

  const resultLabels = {
    success: "успешно",
    partial: "частично",
    error: "ошибка",
    running: "выполняется"
  };

  const sourceLines = payload.source_results.map(result => {
    const sourceName = sourceNames[result.source_id]
      || result.source
      || result.source_id
      || "Неизвестный источник";

    const resultLabel = resultLabels[result.result] || result.result;
    const foundCount = Number(result.found_count) || 0;
    const addedCount = Number(result.added_count) || 0;

    let line = `${escapeHtml(sourceName)}: ${escapeHtml(resultLabel)}`
      + `; найдено ${foundCount}; новых ${addedCount}`;

    if (result.error_message) {
      line += `; ошибка: ${escapeHtml(result.error_message)}`;
    }

    return line;
  });

  const heading = payload.message
    ? escapeHtml(payload.message)
    : "Проверка завершена.";

  return `${heading}<br>${sourceLines.join("<br>")}`;
}

function showCheckMessage(message) {
  checkNotification.innerHTML = `
    <div class="check-result-header">
      <h2>Результат последней проверки</h2>
    </div>
    <div class="notification-text">${message}</div>
  `;
  checkNotification.classList.add("visible");
}

function hideCheckMessageLater() {
  // Итог последней проверки остаётся видимым до следующего запуска.
}

async function reloadRuntimeData() {
  try {
    const loadedDocuments = await loadDocumentsFromApi();
    documents = loadedDocuments;
  } catch (error) {
    documents = [];
    console.warn("Не удалось загрузить документы из SQLite API.", error);
    showCheckMessage(
      "Не удалось загрузить документы из базы данных. "
      + "Проверьте, запущен ли сервер."
    );
  }

  try {
    checkLog = await loadCheckLogFromApi();
  } catch (error) {
    checkLog = [];
    console.warn("Не удалось загрузить журнал проверок из SQLite API.", error);
  }

  try {
    decisionLog = await loadDecisionLogFromApi();
  } catch (error) {
    decisionLog = [];
    console.warn("Не удалось загрузить журнал решений из SQLite API.", error);
  }
  renderStats();
  renderDocumentList();
  renderSourceRulesTable();
  renderCheckControlPanel();
  renderDecisionLog();
  renderCheckLog();

  if (selectedDocId) {
    const selectedDoc = documents.find(doc => String(doc.id) === String(selectedDocId));
    if (selectedDoc) {
      renderSelectedDocument(selectedDoc);
    }
  }
}

function renderDecisionLog() {
  decisionLogTable.innerHTML = "";
  if (decisionLog.length === 0) {
    const emptyRow = document.createElement("tr");
    emptyRow.innerHTML = '<td colspan="5" class="empty-log">Сохранённых решений пока нет.</td>';
    decisionLogTable.appendChild(emptyRow);
    return;
  }

  decisionLog.forEach(entry => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${entry.datetime}</td>
      <td>${entry.title}</td>
      <td>${renderStatusBadge(entry.status)}</td>
      <td>${entry.comment || "—"}</td>
      <td>${entry.responsible}</td>
    `;
    decisionLogTable.appendChild(row);
  });
}


function renderStats() {
  const newCount = documents.filter(doc => normalizeDocumentStatus(doc.status) === "Новое").length;
  const reviewCount = documents.filter(
    doc => normalizeDocumentStatus(doc.status) === "Проверка актуальности"
  ).length;
  const workCount = documents.filter(
    doc => normalizeDocumentStatus(doc.status) === "Принято в работу"
  ).length;
  const consultation = documents.filter(
    doc => normalizeDocumentStatus(doc.status) === "Неактуально / не относится"
  ).length;
  const closed = documents.filter(doc => normalizeDocumentStatus(doc.status) === "Закрыто").length;

  lastCheckValue.textContent = getLatestCheckDatetime();
  newDocsCount.textContent = newCount;
  inReviewCount.textContent = reviewCount;
  inWorkCount.textContent = workCount;
  consultationCount.textContent = consultation;
  closedCount.textContent = closed;
}

function shouldHideFromMainWorkingList(status) {
  const normalizedStatus = normalizeDocumentStatus(status);
  return normalizedStatus === "Неактуально / не относится" || normalizedStatus === "Закрыто";
}

function getWorkingDocuments() {
  return documents.filter(doc => !shouldHideFromMainWorkingList(doc.status));
}

function getDocumentsByStatus(status) {
  return documents.filter(doc => normalizeDocumentStatus(doc.status) === status);
}

function getDocumentsForCurrentFilter() {
  if (!activeStatusFilter) {
    return getWorkingDocuments();
  }

  return getDocumentsByStatus(activeStatusFilter);
}

function parseDocumentDisplayDate(value) {
  const dateValue = String(value || "").trim();
  if (!dateValue) {
    return null;
  }

  if (/^\d{4}-\d{2}-\d{2}/.test(dateValue)) {
    const parsedIsoDate = new Date(dateValue);
    return Number.isNaN(parsedIsoDate.getTime()) ? null : parsedIsoDate.getTime();
  }

  const ruDateMatch = dateValue.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (ruDateMatch) {
    const [, day, month, year] = ruDateMatch;
    const parsedRuDate = new Date(`${year}-${month}-${day}T00:00:00`);
    return Number.isNaN(parsedRuDate.getTime()) ? null : parsedRuDate.getTime();
  }

  const parsedDate = new Date(dateValue);
  return Number.isNaN(parsedDate.getTime()) ? null : parsedDate.getTime();
}

function getDocumentDisplayTimestamp(doc) {
  const dateFields = [
    doc.found_date,
    doc.foundDate,
    doc.discovered_at,
    doc.created_at,
    doc.date
  ];

  for (const value of dateFields) {
    const parsedTimestamp = parseDocumentDisplayDate(value);
    if (parsedTimestamp !== null) {
      return parsedTimestamp;
    }
  }

  return null;
}

function getCurrentFilterLabel() {
  if (!activeStatusFilter) {
    return "Рабочий список";
  }

  if (activeStatusFilter === "Неактуально / не относится" || activeStatusFilter === "Закрыто") {
    return `Архив: ${activeStatusFilter}`;
  }

  return `Фильтр: ${activeStatusFilter}`;
}

function generateReviewCommentId() {
  return `review_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

function updateReviewCommentsCounter() {
  if (!reviewCommentsCounter) {
    return;
  }

  reviewCommentsCounter.textContent = `Сохранено замечаний: ${reviewCommentsCount}`;
}

async function loadReviewCommentsSummary() {
  try {
    const response = await fetch("/api/review-comments", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    reviewCommentsCount = Number.isFinite(Number(payload.count)) ? Number(payload.count) : 0;
  } catch (error) {
    reviewCommentsCount = 0;
    console.warn("Не удалось загрузить количество замечаний.", error);
  }

  updateReviewCommentsCounter();
}

function showReviewModeStatus(message) {
  if (!reviewModeTipText) {
    return;
  }

  reviewModeTipText.textContent = message;

  setTimeout(() => {
    if (reviewModeTipText && reviewMode) {
      reviewModeTipText.textContent = defaultReviewModeTipText;
    }
  }, 3000);
}

function hasUnsavedReviewDraft() {
  return Boolean(reviewCommentModal && !reviewCommentModal.hidden && reviewCommentText && reviewCommentText.value.trim());
}

function confirmCloseUnsavedReviewComment() {
  if (reviewCommentJustSaved || !hasUnsavedReviewDraft()) {
    return true;
  }

  return window.confirm("Замечание не сохранено. Закрыть без сохранения?");
}

function closeReviewCommentModal(force = false) {
  if (!force && !confirmCloseUnsavedReviewComment()) {
    return false;
  }

  activeReviewZone = null;
  reviewCommentJustSaved = false;

  if (reviewCommentModal) {
    reviewCommentModal.hidden = true;
  }

  if (reviewFormMessage) {
    reviewFormMessage.textContent = "";
    reviewFormMessage.classList.remove("visible", "error");
  }

  if (reviewCommentText) {
    reviewCommentText.value = "";
  }

  return true;
}

function openReviewCommentModal(zoneSource) {
  if (!zoneSource || !reviewCommentModal || !reviewZoneTitle || !reviewCommentText) {
    return;
  }

  if (!reviewCommentModal.hidden) {
    const canCloseCurrentDraft = closeReviewCommentModal();
    if (!canCloseCurrentDraft) {
      return;
    }
  }

  const zoneElement = zoneSource.dataset ? zoneSource : { dataset: zoneSource };
  activeReviewZone = {
    zoneId: zoneElement.dataset.reviewZone || "",
    zoneTitle: zoneElement.dataset.reviewTitle || "Без названия"
  };

  reviewZoneTitle.textContent = activeReviewZone.zoneTitle;
  reviewCommentText.value = "";
  reviewCommentJustSaved = false;

  if (reviewFormMessage) {
    reviewFormMessage.textContent = "";
    reviewFormMessage.classList.remove("visible", "error");
  }

  reviewCommentModal.hidden = false;
  reviewCommentText.focus();
}

function setupReviewZoneButtons() {
  const reviewZones = document.querySelectorAll("[data-review-zone]");

  reviewZones.forEach(zone => {
    zone.classList.add("review-zone");

    if (zone.dataset.reviewButtonReady === "true") {
      const existingButton = zone.querySelector(".review-zone-button");
      const existingActions = zone.querySelector(".review-zone-actions");
      if (existingActions) {
        existingActions.hidden = !reviewMode;
      }
      if (existingButton) {
        existingButton.hidden = !reviewMode;
      }
      return;
    }

    const actionsContainer = document.createElement("div");
    actionsContainer.className = "review-zone-actions";
    actionsContainer.hidden = !reviewMode;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "review-zone-button";
    button.textContent = "Добавить замечание";
    button.hidden = !reviewMode;
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      openReviewCommentModal(zone);
    });

    actionsContainer.appendChild(button);

    if (zone.classList.contains("review-zone-anchor")) {
      zone.appendChild(actionsContainer);
    } else {
      zone.prepend(actionsContainer);
    }

    zone.dataset.reviewButtonReady = "true";
  });
}

function syncReviewModeUi() {
  setupReviewZoneButtons();

  document.body.classList.toggle("review-mode-active", reviewMode);

  if (toggleReviewModeButton) {
    toggleReviewModeButton.classList.toggle("active", reviewMode);
    toggleReviewModeButton.setAttribute("aria-pressed", String(reviewMode));
    toggleReviewModeButton.textContent = reviewMode
      ? "Отключить режим замечаний"
      : "Включить режим замечаний";
  }

  if (reviewModeTip) {
    reviewModeTip.hidden = !reviewMode;
  }

  if (downloadReviewCommentsButton) {
    downloadReviewCommentsButton.hidden = !reviewMode;
  }

  if (downloadReviewReportButton) {
    downloadReviewReportButton.hidden = !reviewMode;
  }

  document.querySelectorAll(".review-zone-button").forEach(button => {
    button.hidden = !reviewMode;
  });

  document.querySelectorAll(".review-zone-actions").forEach(container => {
    container.hidden = !reviewMode;
  });

  if (!reviewMode) {
    closeReviewCommentModal(true);
  }
}

async function submitReviewComment() {
  if (!activeReviewZone || !reviewCommentText || !saveReviewCommentButton) {
    return;
  }

  const commentText = reviewCommentText.value.trim();
  if (!commentText) {
    if (reviewFormMessage) {
      reviewFormMessage.textContent = "Напишите замечание перед сохранением.";
      reviewFormMessage.classList.add("visible", "error");
    }
    return;
  }

  const selectedDocumentData = documents.find(doc => doc.id === selectedDocId) || null;
  const shouldAttachDocument = reviewCommentDocumentZones.has(activeReviewZone.zoneId);
  const payload = {
    id: generateReviewCommentId(),
    created_at: new Date().toISOString(),
    page: "main",
    zone_id: activeReviewZone.zoneId,
    zone_title: activeReviewZone.zoneTitle,
    comment_text: commentText,
    status: "Новое",
    current_filter: getCurrentFilterLabel(),
    document_id: shouldAttachDocument && selectedDocumentData ? selectedDocumentData.id : null,
    document_title: shouldAttachDocument && selectedDocumentData ? selectedDocumentData.title : null
  };

  saveReviewCommentButton.disabled = true;

  try {
    const response = await fetch("/api/review-comments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();
    if (!response.ok || !result.ok) {
      throw new Error(result && result.message ? result.message : "Не удалось сохранить замечание.");
    }

    reviewCommentsCount = Number.isFinite(Number(result.saved_count))
      ? Number(result.saved_count)
      : reviewCommentsCount + 1;
    updateReviewCommentsCounter();
    reviewCommentJustSaved = true;
    closeReviewCommentModal(true);
    if (result.warning === "report_file_locked") {
      showReviewModeStatus(
        `Замечание сохранено. Всего замечаний: ${reviewCommentsCount}. Если отчёт открыт в Word, закройте его перед следующим обновлением локальной копии. Скачать новый отчёт всё равно можно кнопкой «Скачать замечания в Word».`
      );
    } else {
      showReviewModeStatus(`Замечание сохранено. Всего замечаний: ${reviewCommentsCount}.`);
    }
  } catch (error) {
    if (reviewFormMessage) {
      reviewFormMessage.textContent = error.message || "Не удалось сохранить замечание.";
      reviewFormMessage.classList.add("visible", "error");
    }
  } finally {
    saveReviewCommentButton.disabled = false;
  }
}

function renderDocumentList() {
  documentList.innerHTML = "";
  const documentsForList = getDocumentsForCurrentFilter();
  // Сортируем только копию для отображения: новые документы сверху.
  const sortedDocumentsForList = [...documentsForList].sort((leftDoc, rightDoc) => {
    const leftTimestamp = getDocumentDisplayTimestamp(leftDoc);
    const rightTimestamp = getDocumentDisplayTimestamp(rightDoc);

    if (leftTimestamp === null && rightTimestamp === null) {
      return 0;
    }

    if (leftTimestamp === null) {
      return 1;
    }

    if (rightTimestamp === null) {
      return -1;
    }

    return rightTimestamp - leftTimestamp;
  });
  const visibleDocuments = showAllDocuments
    ? sortedDocumentsForList
    : sortedDocumentsForList.slice(0, collapsedDocumentsCount);
  const selectedVisibleDoc = visibleDocuments.find(doc => doc.id === selectedDocId);

  if (visibleDocuments.length === 0) {
    documentList.innerHTML = `
      <div class="card empty-state">
        ${activeStatusFilter
          ? `По фильтру «${getCurrentFilterLabel()}» сейчас нет документов.`
          : "В рабочем списке сейчас нет документов для показа."}
      </div>
    `;
    selectedDocument.innerHTML = `
      <div class="card empty-state">
        Выберите другой фильтр или дождитесь новых документов.
      </div>
    `;
    renderDocumentsListToggle();
    renderStatusFilterControls();
    syncReviewModeUi();
    return;
  }

  if (!selectedVisibleDoc) {
    selectedDocId = visibleDocuments[0].id;
    renderSelectedDocument(visibleDocuments[0]);
  }

  visibleDocuments.forEach(doc => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "card document-card";
    if (doc.id === selectedDocId) {
      card.classList.add("selected");
    }
    card.innerHTML = `
      <h3 class="document-card-title" title="${doc.title}">${doc.title}</h3>
      <div class="meta source-label source-label-with-icon">
        ${renderDocumentIcon(doc, "document-topic-icon-small")}
        <span>${doc.source} • ${doc.section}</span>
      </div>
      ${renderStatusBadge(doc.status, "document-status-badge")}
    `;
    card.addEventListener("click", () => selectDocument(doc, card));
    documentList.appendChild(card);
  });

  renderDocumentsListToggle();
  renderStatusFilterControls();
  syncReviewModeUi();
}

function renderDocumentsListToggle() {
  if (!toggleDocumentsListButton) {
    return;
  }

  const filteredDocuments = getDocumentsForCurrentFilter();
  const needsToggle = showAllDocuments || filteredDocuments.length > collapsedDocumentsCount;

  if (!needsToggle) {
    toggleDocumentsListButton.hidden = true;
    return;
  }

  toggleDocumentsListButton.hidden = false;
  toggleDocumentsListButton.textContent = showAllDocuments
    ? "Свернуть список"
    : "Показать все документы";
}

function renderStatusFilterControls() {
  if (currentDocumentsFilterLabel) {
    currentDocumentsFilterLabel.textContent = getCurrentFilterLabel();
  }

  if (resetDocumentsFilterButton) {
    resetDocumentsFilterButton.hidden = !activeStatusFilter;
  }

  const filterButtons = [
    { element: filterStatusNewButton, status: "Новое" },
    { element: filterStatusReviewButton, status: "Проверка актуальности" },
    { element: filterStatusWorkButton, status: "Принято в работу" },
    { element: filterStatusNotRelevantButton, status: "Неактуально / не относится" },
    { element: filterStatusClosedButton, status: "Закрыто" }
  ];

  filterButtons.forEach(({ element, status }) => {
    if (!element) {
      return;
    }
    element.classList.toggle("active", activeStatusFilter === status);
  });
}

function selectDocument(doc, cardElement) {
  selectedDocId = doc.id;
  const currentActive = document.querySelector(".document-card.selected");
  if (currentActive) {
    currentActive.classList.remove("selected");
  }
  cardElement.classList.add("selected");
  renderSelectedDocument(doc);
}

function renderSelectedDocument(doc) {
  const savedDecision = {
    status: normalizeDocumentStatus(doc.status),
    comment: doc.engineerComment || ""
  };
  doc.status = savedDecision.status;
  selectedDocument.innerHTML = `
    <h3>${doc.title}</h3>
    <div class="detail-row">
      <span>Источник</span>
      <strong class="source-label source-label-with-icon">
        ${renderDocumentIcon(doc, "document-topic-icon-detail")}
        <span>${doc.source}</span>
      </strong>
    </div>
    <div class="detail-row">
      <span>Дата обнаружения</span>
      <strong>${doc.foundDate || "—"}</strong>
    </div>
    <div class="detail-row">
      <span>Ссылка на первоисточник</span>
      <p><a href="${doc.originalUrl || '#'}" target="_blank" rel="noopener noreferrer">${doc.originalUrl || "—"}</a></p>
    </div>
    <div class="detail-row">
      <span>Файл документа</span>
      <div>
        ${
          doc.savedFilePath
            ? `<p><a href="/${doc.savedFilePath}" target="_blank" rel="noopener noreferrer">Открыть сохранённый файл</a></p>`
            : `<p>${doc.fileUrl ? "Файл ещё не скачан" : "Ссылка на файл отсутствует"}</p>`
        }
        <button
          id="download-document-file"
          type="button"
          ${doc.fileUrl ? "" : "disabled"}
        >
          ${doc.savedFilePath ? "Скачать повторно" : "Скачать файл"}
        </button>
        <p id="download-message" class="save-message"></p>
      </div>
    </div>
    <div class="detail-row">
      <span>Раздел</span>
      <strong>${doc.section}</strong>
    </div>
    <div class="detail-row">
      <span>Краткая суть</span>
      <p>${doc.summary}</p>
    </div>
    <div class="detail-row">
      <span>Типы внутренних документов для проверки</span>
      <ul>${doc.internalTypes.map(type => `<li>${type}</li>`).join("")}</ul>
    </div>
    <div class="info-block">
      <strong>Будущий ИИ/RAG</strong>
      <p>${doc.aiNote || "В будущем ИИ/RAG сможет извлечь ключевые требования и связать их с внутренними документами компании."}</p>
    </div>
    <div class="draft-warning-block">
      <strong>Черновик рекомендации</strong>
      <p>${doc.draftRecommendation || "Предварительно проанализировать документ и подготовить вариант рекомендаций."}</p>
      <p class="draft-warning-text">${doc.draftWarning || "Черновик, требует проверки инженером."}</p>
    </div>
    <div class="detail-row" data-review-zone="document_statuses" data-review-title="Статусы документа">
      <span>Статус</span>
      ${renderStatusBadge(doc.status, "detail-status-badge")}
    </div>
    <div class="decision-card">
      <div class="section-header">
        <h3>Решение инженера</h3>
      </div>
      <div class="detail-row">
        <span>Статус обработки</span>
        <select id="engineer-status">
          ${decisionStatuses.map(status => `
            <option value="${status}" ${status === savedDecision.status ? "selected" : ""}>${status}</option>
          `).join("")}
        </select>
      </div>
      <div class="detail-row" data-review-zone="engineer_comment" data-review-title="Комментарий инженера">
        <span>Комментарий инженера</span>
        <textarea id="engineer-comment" rows="4">${savedDecision.comment || ""}</textarea>
      </div>
      <button id="save-decision" type="button">Сохранить решение</button>
      <p id="decision-message" class="save-message"></p>
    </div>
  `;

  const downloadButton = document.getElementById("download-document-file");

  if (downloadButton) {
    downloadButton.addEventListener("click", async () => {
      const messageElement = document.getElementById("download-message");

      downloadButton.disabled = true;
      messageElement.textContent = "Скачивание файла...";

      try {
        const payload = await downloadDocumentFileFromApi(doc.id);
        const updatedDocument = payload.document;

        doc.savedFilePath = updatedDocument.saved_file_path || "";
        doc.downloadStatus = updatedDocument.download_status || "not_requested";

        messageElement.textContent = payload.message || "Файл скачан";
        renderSelectedDocument(doc);
      } catch (error) {
        messageElement.textContent = `Ошибка: ${error.message}`;
        downloadButton.disabled = false;
      }
    });
  }

  const saveButton = document.getElementById("save-decision");
  saveButton.addEventListener("click", async () => {
    const status = normalizeDocumentStatus(document.getElementById("engineer-status").value);
    const comment = document.getElementById("engineer-comment").value.trim();
    await saveDecisionToApi(doc.id, status, comment);
    decisionLog = await loadDecisionLogFromApi();
    renderDecisionLog();
    doc.status = status;
    doc.engineerComment = comment;
    if (activeStatusFilter && activeStatusFilter !== status) {
      if (shouldHideFromMainWorkingList(activeStatusFilter) && !shouldHideFromMainWorkingList(status)) {
        activeStatusFilter = status;
      }
    }
    selectedDocId = doc.id;
    renderStats();
    renderDocumentList();
    renderSelectedDocument(doc);

    const message = document.getElementById("decision-message");
    message.textContent = "Решение инженера сохранено.";
    message.classList.add("visible");

    setTimeout(() => {
      message.classList.remove("visible");
    }, 3000);
  });

  syncReviewModeUi();
}

function renderSourceRulesTable() {
  if (!sourceRulesList) {
    return;
  }

  sourceRulesList.innerHTML = "";
  sourceRulesTableData.forEach(query => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>
        <div class="sources-table-source">
          ${renderDocumentIcon(query, "document-topic-icon-table")}
          <span>${query.source}</span>
        </div>
      </td>
      <td><a href="${query.url}" target="_blank" rel="noopener noreferrer">${query.url}</a></td>
      <td>${query.section}</td>
      <td>${query.mode}</td>
      <td>${query.ruleComment}</td>
      <td><span class="status-badge status-default">${query.status}</span></td>
    `;
    sourceRulesList.appendChild(row);
  });
}

function renderCheckControlPanel() {
  if (checkModeValue) {
    checkModeValue.textContent = "ручной";
  }

  if (scheduleLastCheckValue) {
    scheduleLastCheckValue.textContent = getLatestCheckDatetime();
  }

  if (toggleScheduleSettingsButton) {
    toggleScheduleSettingsButton.textContent = scheduleInterfaceState.isExpanded
      ? "Настроить периодичность ▲"
      : "Настроить периодичность ▼";
  }

  if (scheduleSettingsPanel) {
    scheduleSettingsPanel.hidden = !scheduleInterfaceState.isExpanded;
  }

  if (scheduleFrequencySelect) {
    scheduleFrequencySelect.value = scheduleInterfaceState.frequency;
  }

  if (scheduleTimeInput) {
    scheduleTimeInput.value = scheduleInterfaceState.time;
  }

  if (scheduleSettingsMessage) {
    scheduleSettingsMessage.textContent = scheduleInterfaceState.message;
    scheduleSettingsMessage.classList.toggle("visible", Boolean(scheduleInterfaceState.message));
  }
}

function toggleCollapsibleSection(button) {
  const targetId = button.dataset.target;
  if (!targetId) {
    return;
  }

  const body = document.getElementById(targetId);
  if (!body) {
    return;
  }

  const section = button.closest(".collapsible-section");
  const isExpanded = button.getAttribute("aria-expanded") === "true";
  const nextExpanded = !isExpanded;
  const icon = button.querySelector(".section-toggle-icon");

  button.setAttribute("aria-expanded", String(nextExpanded));
  body.hidden = !nextExpanded;

  if (section) {
    section.classList.toggle("expanded", nextExpanded);
    section.classList.toggle("collapsed", !nextExpanded);
  }

  if (icon) {
    icon.textContent = nextExpanded ? "▼" : "▶";
  }
}

function renderCheckLog() {
  checkLogTable.innerHTML = "";
  checkLog.forEach(entry => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${entry.datetime}</td>
      <td>${entry.source}</td>
      <td><span class="result-badge result-${entry.result === 'Успешно' ? 'success' : 'error'}">${entry.result}</span></td>
      <td>${entry.found}</td>
      <td>${entry.newDocs}</td>
      <td>${entry.error}</td>
    `;
    checkLogTable.appendChild(row);
  });
}

function formatCurrentDatetime() {
  const now = new Date();
  const dateStr = String(now.getDate()).padStart(2, '0');
  const monthStr = String(now.getMonth() + 1).padStart(2, '0');
  const yearStr = now.getFullYear();
  const hoursStr = String(now.getHours()).padStart(2, '0');
  const minsStr = String(now.getMinutes()).padStart(2, '0');
  return `${dateStr}.${monthStr}.${yearStr} ${hoursStr}:${minsStr}`;
}

function addCheckLogEntry(entry) {
  checkLog.unshift(entry);
}

function documentExists(title) {
  return documents.some(doc => doc.title === title);
}

function runDemoSearchCheck() {
  const demoTopics = [
    "Обучение по охране труда",
    "Медицинские осмотры",
    "Огнетушители"
  ];
  const datetime = formatCurrentDatetime();
  demoTopics.forEach(topic => {
    const query = searchQueries.find(q => q.topic === topic);
    if (!query) {
      return;
    }

    const newDocs = topic === "Огнетушители" ? 0 : 1;
    const found = 1;
    addCheckLogEntry({
      datetime,
      source: `${query.source} — ${query.topic}`,
      result: "Успешно",
      found,
      newDocs,
      error: "-"
    });
  });

  const addedDocuments = addDemoDocumentsIfMissing(datetime);
  if (addedDocuments > 0) {
    renderDocumentList();
    renderStats();
  }
  renderCheckLog();

  return addedDocuments;
}

function addDemoDocumentsIfMissing(datetime) {
  const demoDocs = [
    {
      id: 6,
      title: "Демонстрационное изменение по обучению охране труда",
      source: "Минтруд России",
      section: "Охрана труда",
      summary: "Во время демонстрационной проверки найден документ, который может повлиять на порядок обучения и инструктажей по охране труда.",
      status: "Новое",
      foundDate: datetime.split(' ')[0],
      originalUrl: "https://example.ru/demo-search-document-1",
      savedFilePath: "files/saved_documents/demo_search_learning.pdf",
      aiNote: "ИИ/RAG поможет будущему модулю выявлять ключевые требования по обучению и связывать их с журналами и протоколами.",
      draftRecommendation: "Проверить связанные журналы обучения и определить, нужно ли обновление инструкций.",
      draftWarning: "Черновик, требует проверки инженером.",
      internalTypes: [
        "Журнал инструктажа по охране труда",
        "Журнал учета посещаемости и проведения занятий по охране труда",
        "Протоколы по охране труда"
      ]
    },
    {
      id: 7,
      title: "Демонстрационное изменение по медицинским осмотрам",
      source: "Минздрав России",
      section: "Медицина",
      summary: "Во время демонстрационной проверки найден документ, который может повлиять на порядок направления работников на медицинские осмотры.",
      status: "Новое",
      foundDate: datetime.split(' ')[0],
      originalUrl: "https://example.ru/demo-search-document-2",
      savedFilePath: "files/saved_documents/demo_search_medical.pdf",
      aiNote: "ИИ/RAG сможет в будущем связать ключевые требования медосмотров с внутренними таблицами и направлениями.",
      draftRecommendation: "Оценить необходимость обновления направлений и таблиц медкомиссий.",
      draftWarning: "Черновик, требует проверки инженером.",
      internalTypes: [
        "Журнал учета выдачи направлений",
        "Таблица медкомиссий и санитарного минимума"
      ]
    }
  ];

  let addedCount = 0;
  demoDocs.forEach(doc => {
    if (!documentExists(doc.title)) {
      documents.unshift(doc);
      addedCount += 1;
    }
  });

  return addedCount;
}

async function showCheckNotification() {
  checkButton.disabled = true;
  checkButton.textContent = "Проверка идёт...";
  showCheckMessage("Проверка запущена. Подождите, идёт обновление данных.");

  try {
    const response = await fetch("/api/run-demo-check", {
      method: "POST"
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }

    if (payload && payload.stdout) {
      console.log("run_demo_check stdout:\n", payload.stdout);
    }
    if (payload && payload.stderr) {
      console.warn("run_demo_check stderr:\n", payload.stderr);
    }

    if (!response.ok) {
      const message = payload && payload.message
        ? payload.message
        : "Не удалось запустить backend-проверку.";
      showCheckMessage(message);
      hideCheckMessageLater();
      return;
    }

    await reloadRuntimeData();

    showCheckMessage(formatSourceCheckMessage(payload));
  } catch (error) {
    console.warn("Ошибка при запуске /api/run-demo-check", error);
    showCheckMessage("Не удалось выполнить проверку. Подробности см. в консоли.");
  } finally {
    checkButton.disabled = false;
    checkButton.textContent = defaultCheckButtonText;
    hideCheckMessageLater();
  }
}

function setupActions() {
  checkButton.addEventListener("click", async () => {
    await showCheckNotification();
  });

  if (toggleDocumentsListButton) {
    toggleDocumentsListButton.addEventListener("click", () => {
      showAllDocuments = !showAllDocuments;
      renderDocumentList();
    });
  }

  const statusFilterButtons = [
    { element: filterStatusNewButton, status: "Новое" },
    { element: filterStatusReviewButton, status: "Проверка актуальности" },
    { element: filterStatusWorkButton, status: "Принято в работу" },
    { element: filterStatusNotRelevantButton, status: "Неактуально / не относится" },
    { element: filterStatusClosedButton, status: "Закрыто" }
  ];

  statusFilterButtons.forEach(({ element, status }) => {
    if (!element) {
      return;
    }

    element.addEventListener("click", () => {
      activeStatusFilter = activeStatusFilter === status ? null : status;
      showAllDocuments = false;
      renderDocumentList();
    });
  });

  if (resetDocumentsFilterButton) {
    resetDocumentsFilterButton.addEventListener("click", () => {
      activeStatusFilter = null;
      showAllDocuments = false;
      renderDocumentList();
    });
  }

  if (toggleScheduleSettingsButton) {
    toggleScheduleSettingsButton.addEventListener("click", () => {
      scheduleInterfaceState.isExpanded = !scheduleInterfaceState.isExpanded;
      renderCheckControlPanel();
    });
  }

  if (saveScheduleSettingsButton) {
    saveScheduleSettingsButton.addEventListener("click", () => {
      scheduleInterfaceState.frequency = scheduleFrequencySelect
        ? scheduleFrequencySelect.value
        : scheduleInterfaceState.frequency;
      scheduleInterfaceState.time = scheduleTimeInput
        ? scheduleTimeInput.value || "09:00"
        : scheduleInterfaceState.time;
      scheduleInterfaceState.message =
        "Настройка сохранена в интерфейсе MVP. Автоматический запуск пока не подключён.";
      renderCheckControlPanel();
    });
  }

  if (sectionToggleButtons.length > 0) {
    sectionToggleButtons.forEach(button => {
      button.addEventListener("click", () => {
        toggleCollapsibleSection(button);
      });
    });
  }

  if (toggleReviewModeButton) {
    toggleReviewModeButton.addEventListener("click", async () => {
      if (reviewMode) {
        const canDisable = closeReviewCommentModal();
        if (!canDisable) {
          return;
        }
        reviewMode = false;
      } else {
        reviewMode = true;
        await loadReviewCommentsSummary();
      }
      syncReviewModeUi();
    });
  }

  if (downloadReviewCommentsButton) {
    downloadReviewCommentsButton.addEventListener("click", () => {
      window.location.href = "/api/review-comments/export";
    });
  }

  if (downloadReviewReportButton) {
    downloadReviewReportButton.addEventListener("click", () => {
      window.location.href = "/api/review-comments/report-rtf";
    });
  }

  if (saveReviewCommentButton) {
    saveReviewCommentButton.addEventListener("click", async () => {
      await submitReviewComment();
    });
  }

  if (cancelReviewCommentButton) {
    cancelReviewCommentButton.addEventListener("click", () => {
      closeReviewCommentModal();
    });
  }

  if (reviewCommentModal) {
    reviewCommentModal.addEventListener("click", event => {
      if (event.target === reviewCommentModal || event.target.classList.contains("review-modal-backdrop")) {
        closeReviewCommentModal();
      }
    });
  }

  if (addGeneralReviewCommentButton) {
    addGeneralReviewCommentButton.addEventListener("click", () => {
      openReviewCommentModal({
        reviewZone: "general_page",
        reviewTitle: "Общее замечание по странице"
      });
    });
  }
}

// Инициализируем интерфейс. Сначала пробуем взять документы из SQLite API,
// а при любой ошибке остаёмся на встроенном демонстрационном наборе.
async function initializeApp() {
  await reloadRuntimeData();
  await loadReviewCommentsSummary();
  setupActions();
  syncReviewModeUi();
}

initializeApp();
console.log("ОТ-Монитор запущен");
