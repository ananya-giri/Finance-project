// State
let currentTab = 'dashboard';
let companiesData = [];
let selectedFile = null;

// DOM Elements
const sidebarNav = document.querySelectorAll('.nav-item');
const tabPanels = document.querySelectorAll('.tab-panel');
const pageTitle = document.getElementById('page-title');
const pageSubtitle = document.getElementById('page-subtitle');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupDropZone();
  checkApiHealth();
  loadDashboard();
  loadSchedulerStatus();
  loadRagStatus();
});

// Navigation Handling
function setupNavigation() {
  sidebarNav.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const tab = link.getAttribute('data-tab');
      switchTab(tab);
    });
  });

  const quickIngest = document.getElementById('quick-ingest-btn');
  if (quickIngest) {
    quickIngest.addEventListener('click', () => switchTab('ingest'));
  }

  // Global search enter key
  const search = document.getElementById('global-search');
  if (search) {
    search.addEventListener('keyup', (e) => {
      if (e.key === 'Enter' && search.value.trim()) {
        const val = search.value.trim().toUpperCase();
        document.getElementById('metrics-ticker').value = val;
        switchTab('metrics');
        loadMetrics();
      }
    });
  }
}

function switchTab(tabId) {
  currentTab = tabId;
  sidebarNav.forEach(item => {
    if (item.getAttribute('data-tab') === tabId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  tabPanels.forEach(panel => {
    if (panel.id === `tab-${tabId}`) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
  });

  const titles = {
    dashboard: { title: 'Dashboard', sub: 'Financial Intelligence Overview' },
    ingest: { title: 'Historical Ingestion', sub: 'FR-001: 5-Year Financial Data Collection' },
    documents: { title: 'Document Upload', sub: 'FR-002: Statements, Presentations & Transcripts' },
    metrics: { title: 'Financial Metrics', sub: 'FR-003: 10 Core Structured Financial Metrics' },
    scheduler: { title: 'Auto-Monitoring', sub: 'FR-004: Automated Report & Statement Watcher' },
    'market-intelligence': { title: 'External Market Intelligence', sub: 'FR-005 to FR-009: Macro Indicators, Geopolitics, Regulations, News & Impact Classifier' },
    rag: { title: 'Knowledge Base & RAG', sub: 'FR-010 to FR-014: Persistent Vector Storage, Semantic Search & Grounded Recommendations' }
  };

  if (titles[tabId]) {
    pageTitle.textContent = titles[tabId].title;
    pageSubtitle.textContent = titles[tabId].sub;
  }

  // Auto-refresh data on tab change
  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'documents') loadDocuments();
  if (tabId === 'scheduler') loadSchedulerStatus();
  if (tabId === 'market-intelligence') loadMarketIntelligence();
  if (tabId === 'rag') loadRagStatus();
}


// Check Health
async function checkApiHealth() {
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      statusDot.className = 'status-dot online';
      statusText.textContent = 'API Connected';
    } else {
      throw new Error();
    }
  } catch (err) {
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'API Offline';
  }
}

// -------------------------------------------------------------
// DASHBOARD & FR-001
// -------------------------------------------------------------
async function loadDashboard() {
  const tbody = document.getElementById('companies-tbody');
  tbody.innerHTML = '<tr><td colspan="8" class="empty-row"><div class="spinner"></div> Loading companies...</td></tr>';

  try {
    const res = await fetch('/api/companies');
    companiesData = await res.json();

    // Stats
    document.getElementById('stat-companies').textContent = companiesData.length;
    const fiveYearCount = companiesData.filter(c => c.has_five_year_history).length;
    document.getElementById('stat-fiveyear').textContent = `${fiveYearCount} / ${companiesData.length}`;

    // Docs count
    const docsRes = await fetch('/api/documents');
    const docs = await docsRes.json();
    document.getElementById('stat-documents').textContent = docs.length;

    // Scheduler count
    const schedRes = await fetch('/api/scheduler/status');
    const sched = await schedRes.json();
    document.getElementById('stat-watcher').textContent = sched.scheduler_active ? 'Active' : 'Idle';

    if (companiesData.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="empty-state">
            <p>No companies ingested yet.</p>
            <button class="btn btn-primary btn-sm" onclick="switchTab('ingest')">Ingest First Company (FR-001)</button>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = companiesData.map(c => `
      <tr>
        <td><span class="ticker-tag">${c.ticker}</span></td>
        <td><strong>${c.name}</strong></td>
        <td>${c.sector || '—'}</td>
        <td>${c.years_of_data_available} yrs</td>
        <td>
          <span class="status-badge ${c.has_five_year_history ? 'complete' : 'pending'}">
            ${c.has_five_year_history ? '✓ 5-Yr Verified' : `${c.years_of_data_available}/5 yrs`}
          </span>
        </td>
        <td>${c.latest_fiscal_period || '—'}</td>
        <td>${c.auto_sync_enabled ? '<span style="color:var(--accent-green)">Enabled</span>' : '<span style="color:var(--text-muted)">Disabled</span>'}</td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="viewMetricsFor('${c.ticker}')">Metrics</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color:var(--accent-rose);text-align:center;padding:20px;">Failed to load companies: ${err.message}</td></tr>`;
  }
}

function viewMetricsFor(ticker) {
  document.getElementById('metrics-ticker').value = ticker;
  switchTab('metrics');
  loadMetrics();
}

// FR-001 Ingest Historical Data
async function ingestHistoricalData() {
  const tickerInput = document.getElementById('ingest-ticker');
  const yearsInput = document.getElementById('ingest-years');
  const btn = document.getElementById('ingest-btn');
  const resBox = document.getElementById('ingest-result');

  const ticker = tickerInput.value.trim().toUpperCase();
  const years = parseInt(yearsInput.value) || 5;

  if (!ticker) {
    showToast('Please enter a stock ticker symbol');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Ingesting Financials...';
  resBox.className = 'result-box hidden';

  try {
    const res = await fetch('/api/companies/ingest-historical', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticker: ticker, minimum_years: years })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Ingestion failed');

    resBox.className = 'result-box success';
    resBox.innerHTML = `
      <strong>Success! Historical Data Ingested for ${data.ticker} (${data.company_name})</strong><br>
      • Years of Data: <strong>${data.years_of_data_available} years</strong><br>
      • 5-Year Requirement Satisfied: <strong>${data.has_five_year_history ? 'YES (FR-001 Compliant)' : 'Partial'}</strong><br>
      • Statements Ingested: <strong>${data.statements_ingested}</strong> (Income, Balance, Cash Flow)<br>
      • Metric Periods Computed: <strong>${data.metrics_computed}</strong> periods<br>
      • Latest Period: <strong>${data.latest_fiscal_period}</strong>
    `;

    showToast(`Successfully ingested ${data.ticker}`);
    loadDashboard();
  } catch (err) {
    resBox.className = 'result-box error';
    resBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
    showToast(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Start Ingestion';
  }
}

function setTicker(t) {
  document.getElementById('ingest-ticker').value = t;
}

// -------------------------------------------------------------
// FR-002: DOCUMENT UPLOAD & INGESTION
// -------------------------------------------------------------
function setupDropZone() {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('doc-file');
  const selectedName = document.getElementById('file-selected-name');

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFile(fileInput.files[0]);
    }
  });

  function handleFile(file) {
    selectedFile = file;
    selectedName.classList.remove('hidden');
    selectedName.innerHTML = `<span>File: <strong>${file.name}</strong> (${(file.size / 1024).toFixed(1)} KB)</span> <button class="btn btn-ghost btn-sm" onclick="clearFile()">×</button>`;
  }
}

function clearFile() {
  selectedFile = null;
  document.getElementById('doc-file').value = '';
  document.getElementById('file-selected-name').classList.add('hidden');
}

async function uploadDocument() {
  const ticker = document.getElementById('doc-ticker').value.trim().toUpperCase();
  const docType = document.getElementById('doc-type').value;
  const title = document.getElementById('doc-title').value.trim();
  const period = document.getElementById('doc-period').value.trim();
  const periodType = document.getElementById('doc-period-type').value;
  const btn = document.getElementById('upload-btn');
  const resBox = document.getElementById('upload-result');

  if (!ticker) {
    showToast('Please provide a ticker symbol');
    return;
  }
  if (!selectedFile) {
    showToast('Please select a file to upload');
    return;
  }

  const formData = new FormData();
  formData.append('ticker', ticker);
  formData.append('doc_type', docType);
  if (title) formData.append('title', title);
  if (period) formData.append('fiscal_period', period);
  formData.append('period_type', periodType);
  formData.append('file', selectedFile);

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Uploading...';
  resBox.className = 'result-box hidden';

  try {
    const res = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    resBox.className = 'result-box success';
    resBox.innerHTML = `
      <strong>Document Successfully Ingested (FR-002)!</strong><br>
      • ID: <strong>#${data.document_id}</strong><br>
      • Category: <strong>${data.type_label}</strong><br>
      • Title: <strong>${data.title}</strong><br>
      • Text Extracted: <strong>${data.text_length} chars</strong><br>
      • Structured Metrics Recalculated: <strong>${data.metrics_updated ? 'YES' : 'N/A'}</strong>
    `;

    showToast(`Uploaded: ${data.title}`);
    clearFile();
    loadDocuments();
  } catch (err) {
    resBox.className = 'result-box error';
    resBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
    showToast(`Upload error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Upload Document';
  }
}

async function loadDocuments() {
  const container = document.getElementById('docs-list');
  try {
    const res = await fetch('/api/documents');
    const docs = await res.json();

    if (docs.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <p>No documents uploaded yet.</p>
        </div>`;
      return;
    }

    container.innerHTML = docs.map(d => `
      <div class="doc-card">
        <div class="doc-info">
          <span class="doc-title">${d.title}</span>
          <div class="doc-meta">
            <span class="doc-badge">${d.doc_type}</span>
            <span>Ticker: <strong>${d.ticker}</strong></span>
            <span>Period: ${d.fiscal_period || '—'}</span>
            <span>Size: ${(d.file_size_bytes / 1024).toFixed(1)} KB</span>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-rose);padding:16px;">Failed to load documents: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------
// FR-003: STRUCTURED FINANCIAL METRICS
// -------------------------------------------------------------
async function loadMetrics() {
  const ticker = document.getElementById('metrics-ticker').value.trim().toUpperCase();
  const periodType = document.getElementById('metrics-period').value;

  if (!ticker) {
    showToast('Please enter a company ticker');
    return;
  }

  const emptyCard = document.getElementById('metrics-empty');
  const summaryCard = document.getElementById('metrics-summary-card');
  const tableCard = document.getElementById('metrics-table-card');

  emptyCard.classList.remove('hidden');
  emptyCard.innerHTML = '<div class="spinner-center"><div class="spinner"></div></div>';
  summaryCard.classList.add('hidden');
  tableCard.classList.add('hidden');

  try {
    // 1. Fetch Timeline
    const res = await fetch(`/api/metrics/${ticker}?period_type=${periodType}`);
    const metrics = await res.json();
    if (!res.ok) throw new Error(metrics.detail || 'Failed to fetch metrics');

    // 2. Fetch Executive Summary
    const sumRes = await fetch(`/api/metrics/${ticker}/summary`);
    const summary = await sumRes.json();

    emptyCard.classList.add('hidden');
    summaryCard.classList.remove('hidden');
    tableCard.classList.remove('hidden');

    renderSummary(summary);
    renderTimelineTable(metrics);
  } catch (err) {
    emptyCard.classList.remove('hidden');
    emptyCard.innerHTML = `
      <div class="empty-state" style="color:var(--accent-rose)">
        <p><strong>Failed to load metrics for ${ticker}:</strong> ${err.message}</p>
        <button class="btn btn-primary btn-sm" onclick="setTicker('${ticker}'); switchTab('ingest');">Ingest ${ticker} First</button>
      </div>`;
  }
}

function renderSummary(s) {
  document.getElementById('metrics-summary-title').textContent = `${s.ticker} — ${s.company_name} (${s.years_covered} Years Ingested)`;
  const healthBadge = document.getElementById('metrics-health-badge');
  healthBadge.className = `health-badge ${s.status === 'HEALTHY' ? 'healthy' : 'moderate'}`;
  healthBadge.textContent = s.status;

  const m = s.latest_metrics || {};
  const kpis = [
    { label: 'Revenue', val: formatCurrency(m.revenue), sub: `CAGR: ${s.revenue_5yr_cagr_pct ? s.revenue_5yr_cagr_pct + '%' : '—'}` },
    { label: 'EBITDA', val: formatCurrency(m.ebitda), sub: `Period: ${m.period}` },
    { label: 'Operating Margin', val: m.operating_margin_pct ? `${m.operating_margin_pct}%` : '—', sub: 'EBIT / Revenue' },
    { label: 'Net Profit', val: formatCurrency(m.net_profit), sub: 'Bottom Line' },
    { label: 'Free Cash Flow', val: formatCurrency(m.free_cash_flow), sub: 'Operating CF - CapEx' },
    { label: 'Debt Ratio', val: m.debt_ratio ? m.debt_ratio.toFixed(2) : '—', sub: 'Total Debt / Assets' },
    { label: 'EPS', val: m.eps ? `$${m.eps.toFixed(2)}` : '—', sub: 'Earnings Per Share' },
    { label: 'ROE', val: m.roe_pct ? `${m.roe_pct}%` : '—', sub: 'Return on Equity' }
  ];

  document.getElementById('metrics-summary-body').innerHTML = kpis.map(k => `
    <div class="kpi-tile">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.val}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join('');
}

function renderTimelineTable(metrics) {
  const thead = document.getElementById('metrics-thead');
  const tbody = document.getElementById('metrics-tbody');

  // Columns: Metric Name | Period 1 | Period 2 | ...
  const periods = metrics.map(m => m.fiscal_period);
  thead.innerHTML = `
    <tr>
      <th>FR-003 Metric</th>
      ${periods.map(p => `<th>${p}</th>`).join('')}
    </tr>
  `;

  const rows = [
    { label: 'Revenue', fn: m => formatCurrency(m.revenue) },
    { label: 'EBITDA', fn: m => formatCurrency(m.ebitda) },
    { label: 'EBIT', fn: m => formatCurrency(m.ebit) },
    { label: 'Net Profit', fn: m => formatCurrency(m.net_profit) },
    { label: 'Operating Margin', fn: m => m.operating_margin ? `${(m.operating_margin * 100).toFixed(1)}%` : '—' },
    { label: 'Cash Flow (Op)', fn: m => formatCurrency(m.operating_cash_flow) },
    { label: 'Free Cash Flow', fn: m => formatCurrency(m.free_cash_flow) },
    { label: 'Debt Ratio', fn: m => m.debt_ratio ? m.debt_ratio.toFixed(2) : '—' },
    { label: 'EPS', fn: m => m.eps ? `$${m.eps.toFixed(2)}` : '—' },
    { label: 'ROE', fn: m => m.roe ? `${(m.roe * 100).toFixed(1)}%` : '—' },
    { label: 'ROA', fn: m => m.roa ? `${(m.roa * 100).toFixed(1)}%` : '—' }
  ];

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><strong>${r.label}</strong></td>
      ${metrics.map(m => `<td>${r.fn(m)}</td>`).join('')}
    </tr>
  `).join('');
}

function formatCurrency(num) {
  if (num === null || num === undefined) return '—';
  const abs = Math.abs(num);
  const sign = num < 0 ? '-' : '';
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  return `${sign}$${abs.toLocaleString()}`;
}

// -------------------------------------------------------------
// FR-004: SCHEDULER & AUTO-MONITORING
// -------------------------------------------------------------
async function loadSchedulerStatus() {
  const container = document.getElementById('scheduler-status-body');
  const logsContainer = document.getElementById('audit-logs-list');

  try {
    const res = await fetch('/api/scheduler/status');
    const data = await res.json();

    container.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>Watcher Engine Status:</span>
          <span class="status-badge ${data.scheduler_active ? 'complete' : 'pending'}">
            ${data.scheduler_active ? '● Running (Background Daemon)' : '○ Inactive'}
          </span>
        </div>
        <div style="display:flex;justify-content:space-between;">
          <span style="color:var(--text-muted)">Poll Interval:</span>
          <strong>Every ${data.poll_interval_minutes} minutes</strong>
        </div>
        <div style="display:flex;justify-content:space-between;">
          <span style="color:var(--text-muted)">Monitored Companies:</span>
          <strong>${data.monitored_companies_count} companies</strong>
        </div>
        <div style="display:flex;justify-content:space-between;">
          <span style="color:var(--text-muted)">Last Check:</span>
          <span>${data.last_check_timestamp ? new Date(data.last_check_timestamp).toLocaleTimeString() : 'Pending'}</span>
        </div>
        <div style="display:flex;justify-content:space-between;">
          <span style="color:var(--text-muted)">Next Scheduled Check:</span>
          <span>${data.next_scheduled_run ? new Date(data.next_scheduled_run).toLocaleTimeString() : 'Immediate'}</span>
        </div>
      </div>
    `;

    // Render Recent Audit Logs
    const logsRes = await fetch('/api/scheduler/logs?limit=15');
    const logs = await logsRes.json();

    if (logs.length === 0) {
      logsContainer.innerHTML = `
        <div class="empty-state">
          <p>No audit events yet.</p>
        </div>`;
      return;
    }

    logsContainer.innerHTML = logs.map(l => `
      <div class="log-item">
        <div class="log-dot ${l.status.toLowerCase()}"></div>
        <div class="log-details">
          <div><strong>${l.ticker || 'SYSTEM'}:</strong> ${l.details}</div>
          <div class="log-time">${new Date(l.created_at).toLocaleString()} • Event: ${l.event_type}</div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-rose)">Failed to load scheduler: ${err.message}</div>`;
  }
}

async function triggerManualCheck() {
  const resBox = document.getElementById('check-result');
  resBox.className = 'result-box hidden';
  showToast('Running automated report check...');

  try {
    const res = await fetch('/api/scheduler/check-now', { method: 'POST' });
    const data = await res.json();

    resBox.className = 'result-box success';
    resBox.innerHTML = `<strong>Check Complete:</strong> Scanned ${data.results.length} companies. Audit log updated.`;
    loadSchedulerStatus();
  } catch (err) {
    resBox.className = 'result-box error';
    resBox.innerHTML = `<strong>Check Failed:</strong> ${err.message}`;
  }
}

function showSimulatePanel() {
  const panel = document.getElementById('simulate-panel');
  panel.classList.toggle('hidden');
}

async function simulateNewReport() {
  const ticker = document.getElementById('sim-ticker').value.trim().toUpperCase();
  const reportType = document.getElementById('sim-type').value;
  const quarter = document.getElementById('sim-quarter').value.trim();
  const resBox = document.getElementById('simulate-result');

  if (!ticker) {
    showToast('Enter ticker to simulate report for');
    return;
  }

  try {
    let url = `/api/scheduler/simulate-new-report?ticker=${ticker}&report_type=${reportType}`;
    if (quarter) url += `&quarter=${encodeURIComponent(quarter)}`;

    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Simulation failed');

    resBox.className = 'result-box success';
    resBox.innerHTML = `
      <strong>FR-004 Event Fired!</strong><br>
      • Ticker: <strong>${data.ticker}</strong><br>
      • Report: <strong>${data.report_type}</strong> (${data.fiscal_period})<br>
      • Updated Metrics: <strong>${data.metrics_updated.length} metrics automatically recomputed</strong><br>
      • Audit Log Written.
    `;
    showToast(`Simulated new ${reportType} for ${data.ticker}`);
    loadSchedulerStatus();
    loadDashboard();
  } catch (err) {
    resBox.className = 'result-box error';
    resBox.innerHTML = `<strong>Error:</strong> ${err.message}`;
  }
}

// Toast Utility
function showToast(msg) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================================
// MARKET INTELLIGENCE CLIENT LOGIC (FR-005 to FR-009)
// ============================================================================

let currentIntelSubtab = 'indicators';
let cachedIndicators = [];
let cachedEvents = [];
let cachedNews = [];
let currentIndicatorCategory = 'ALL';
let currentGeoType = 'ALL';
let currentGeoSeverity = 'ALL';

function switchIntelSubtab(subtabId) {
  currentIntelSubtab = subtabId;
  document.querySelectorAll('.intel-subnav-btn').forEach(btn => {
    if (btn.getAttribute('data-subtab') === subtabId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  document.querySelectorAll('.intel-subview').forEach(view => {
    if (view.id === `subview-${subtabId}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  if (subtabId === 'indicators') loadIndicators(currentIndicatorCategory);
  if (subtabId === 'geopolitical') loadMarketEvents(currentGeoType, currentGeoSeverity);
  if (subtabId === 'news') loadMarketNews();
  if (subtabId === 'classifier') loadImpactMatrix();
}

async function loadMarketIntelligence() {
  try {
    const res = await fetch('/api/market-intelligence/overview');
    if (res.ok) {
      const data = await res.json();
      const elInd = document.getElementById('intel-stat-indicators');
      const elEv = document.getElementById('intel-stat-events');
      const elNews = document.getElementById('intel-stat-news');
      const elAlerts = document.getElementById('intel-stat-alerts');

      if (elInd) elInd.textContent = data.total_indicators_tracked || '28';
      if (elEv) elEv.textContent = data.total_events || '—';
      if (elNews) elNews.textContent = data.latest_critical_events ? data.total_events : '—';

      const critCount = (data.severity_distribution?.CRITICAL || 0) + (data.severity_distribution?.HIGH || 0);
      if (elAlerts) elAlerts.textContent = critCount;
    }
  } catch (err) {
    console.warn('Overview fetch error:', err);
  }

  // Load active subtab
  switchIntelSubtab(currentIntelSubtab);
}

// -------------------------------------------------------------
// FR-005 & FR-006: ECONOMIC INDICATORS
// -------------------------------------------------------------
async function loadIndicators(category = 'ALL') {
  currentIndicatorCategory = category;
  const grid = document.getElementById('indicators-grid');
  if (!grid) return;

  grid.innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading economic indicators...</div>';

  try {
    let url = '/api/market-intelligence/indicators';
    if (category && category !== 'ALL') {
      url += `?category=${encodeURIComponent(category)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load indicators');
    const data = await res.json();
    cachedIndicators = data;

    renderIndicatorsGrid(data);
  } catch (err) {
    grid.innerHTML = `<div class="empty-state"><p class="text-rose">Error loading indicators: ${err.message}</p></div>`;
  }
}

function renderIndicatorsGrid(indicators) {
  const grid = document.getElementById('indicators-grid');
  if (!grid) return;

  if (!indicators || indicators.length === 0) {
    grid.innerHTML = '<div class="empty-state"><p>No indicators match this filter.</p></div>';
    return;
  }

  grid.innerHTML = indicators.map(ind => {
    const change = ind.change_24h || 0;
    const changePct = ind.change_pct_24h || 0;
    const isUp = change > 0;
    const isDown = change < 0;
    const changeClass = isUp ? 'up' : (isDown ? 'down' : 'neutral');
    const sign = isUp ? '+' : '';
    const arrow = isUp ? '▲' : (isDown ? '▼' : '—');

    const sparkSvg = generateSparklineSvg(ind.historical_sparkline, isUp);

    // Format formatted value
    let formattedVal = ind.current_value;
    if (ind.category === 'EXCHANGE_RATE' || ind.unit === 'USD') {
      formattedVal = Number(ind.current_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    } else if (ind.category === 'STOCK_INDEX') {
      formattedVal = Number(ind.current_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else {
      formattedVal = Number(ind.current_value).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 });
    }

    return `
      <div class="indicator-card">
        <div>
          <div class="indicator-card-header">
            <div>
              <span class="indicator-symbol-tag">${ind.symbol}</span>
              <div class="indicator-name" style="margin-top: 6px;">${ind.name}</div>
            </div>
            <span class="indicator-cat-badge badge-impact badge-impact-${ind.category.toLowerCase().split('_')[0]}">
              ${ind.category.replace('_', ' ')}
            </span>
          </div>

          <div class="indicator-value-row">
            <div>
              <span class="indicator-value">${formattedVal}</span>
              <span class="indicator-unit">${ind.unit}</span>
            </div>
            <div class="indicator-change-pill ${changeClass}">
              <span>${arrow}</span>
              <span>${sign}${changePct}%</span>
            </div>
          </div>

          <div class="sparkline-container">
            ${sparkSvg}
          </div>
        </div>

        <div class="indicator-card-footer">
          <span>${ind.source}</span>
          <span>${ind.frequency}</span>
        </div>
      </div>
    `;
  }).join('');
}

function filterIndicatorsCategory(cat) {
  document.querySelectorAll('#indicator-category-pills .cat-pill').forEach(btn => {
    if (btn.getAttribute('data-cat') === cat) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  loadIndicators(cat);
}

function filterIndicatorsSearch() {
  const query = document.getElementById('indicator-search').value.toLowerCase().trim();
  if (!query) {
    renderIndicatorsGrid(cachedIndicators);
    return;
  }
  const filtered = cachedIndicators.filter(i =>
    i.name.toLowerCase().includes(query) ||
    i.symbol.toLowerCase().includes(query) ||
    i.category.toLowerCase().includes(query)
  );
  renderIndicatorsGrid(filtered);
}

async function syncIndicators() {
  showToast('Collecting live economic indicators (FR-005)...');
  try {
    const res = await fetch('/api/market-intelligence/indicators/sync', { method: 'POST' });
    const data = await res.json();
    showToast(`Updated ${data.total_indicators || '28'} economic indicators!`);
    loadIndicators(currentIndicatorCategory);
    loadMarketIntelligence();
  } catch (err) {
    showToast(`Sync failed: ${err.message}`);
  }
}

// Sparkline SVG generator
function generateSparklineSvg(sparklineJson, isPositive) {
  if (!sparklineJson) return '';
  let pts = [];
  try {
    pts = JSON.parse(sparklineJson);
  } catch (e) {
    return '';
  }
  if (!pts || pts.length < 2) return '';

  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const width = 240;
  const height = 36;
  const padding = 3;

  const strokeColor = isPositive ? '#10b981' : '#f43f5e';
  const fillColor = isPositive ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)';

  const points = pts.map((val, idx) => {
    const x = padding + (idx / (pts.length - 1)) * (width - padding * 2);
    const y = height - padding - ((val - min) / range) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${width - padding},${height} L ${padding},${height} Z`;

  return `
    <svg class="sparkline-svg" viewBox="0 0 ${width} ${height}">
      <path d="${areaD}" fill="${fillColor}" />
      <path d="${pathD}" fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  `;
}

// -------------------------------------------------------------
// FR-007: GEOPOLITICAL & REGULATORY EVENTS
// -------------------------------------------------------------
async function loadMarketEvents(eventType = 'ALL', severity = 'ALL') {
  currentGeoType = eventType;
  currentGeoSeverity = severity;

  const container = document.getElementById('geopolitical-events-list');
  if (!container) return;

  container.innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading geopolitical & regulatory events...</div>';

  try {
    let url = '/api/market-intelligence/events?limit=50';
    if (eventType && eventType !== 'ALL') url += `&event_type=${encodeURIComponent(eventType)}`;
    if (severity && severity !== 'ALL') url += `&severity=${encodeURIComponent(severity)}`;

    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load events');
    const events = await res.json();
    cachedEvents = events;

    renderMarketEvents(events);
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p class="text-rose">Error loading events: ${err.message}</p></div>`;
  }
}

function renderMarketEvents(events) {
  const container = document.getElementById('geopolitical-events-list');
  if (!container) return;

  if (!events || events.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No geopolitical or regulatory events found for this filter.</p></div>';
    return;
  }

  container.innerHTML = events.map(ev => {
    const sevClass = `severity-${ev.severity.toLowerCase()}`;
    const impactClass = `badge-impact-${ev.impact_category.toLowerCase()}`;

    let sectors = [];
    try { sectors = JSON.parse(ev.affected_sectors || '[]'); } catch (e) {}

    let tickers = [];
    try { tickers = JSON.parse(ev.affected_tickers || '[]'); } catch (e) {}

    const evDate = new Date(ev.event_date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });

    return `
      <div class="event-card ${sevClass}">
        <div class="event-card-header">
          <div class="event-title">${ev.title}</div>
          <div class="event-badges">
            <span class="badge-impact ${impactClass}">${ev.impact_category}</span>
            <span class="badge-severity badge-${sevClass}">${ev.severity}</span>
          </div>
        </div>

        <p class="event-summary">${ev.summary}</p>

        <div class="event-footer">
          <div class="event-tags-wrap">
            <span class="text-muted" style="font-size: 0.72rem;">Type: <strong>${ev.event_type.replace('_', ' ')}</strong></span>
            ${sectors.map(s => `<span class="sector-tag">${s}</span>`).join('')}
            ${tickers.map(t => `<span class="ticker-tag">${t}</span>`).join('')}
          </div>
          <div>
            <span>${ev.source}</span> • <span>${evDate}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterGeoType(type) {
  document.querySelectorAll('#geo-type-pills .cat-pill').forEach(btn => {
    if (btn.getAttribute('data-type') === type) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  loadMarketEvents(type, currentGeoSeverity);
}

function filterGeoSeverity(sev) {
  currentGeoSeverity = sev;
  loadMarketEvents(currentGeoType, sev);
}

// -------------------------------------------------------------
// FR-008: MARKET NEWS & ANALYST REPORTS
// -------------------------------------------------------------
async function loadMarketNews() {
  const container = document.getElementById('market-news-list');
  if (!container) return;

  container.innerHTML = '<div class="loading-state"><div class="spinner"></div> Loading financial news and market reports...</div>';

  try {
    const res = await fetch('/api/market-intelligence/news?limit=40');
    if (!res.ok) throw new Error('Failed to load news');
    const news = await res.json();
    cachedNews = news;
    renderMarketNews(news);
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p class="text-rose">Error loading news: ${err.message}</p></div>`;
  }
}

function renderMarketNews(news) {
  const container = document.getElementById('market-news-list');
  if (!container) return;

  if (!news || news.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>No news articles currently stored. Click "Fetch Live News" above.</p></div>';
    return;
  }

  container.innerHTML = news.map(item => {
    const evDate = new Date(item.event_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    const impactClass = `badge-impact-${item.impact_category.toLowerCase()}`;
    const sentimentPill = item.sentiment === 'POSITIVE'
      ? '<span class="indicator-change-pill up" style="padding: 2px 6px;">Positive</span>'
      : (item.sentiment === 'NEGATIVE'
        ? '<span class="indicator-change-pill down" style="padding: 2px 6px;">Negative</span>'
        : '<span class="indicator-change-pill neutral" style="padding: 2px 6px;">Neutral</span>');

    return `
      <div class="news-card">
        <div>
          <div class="news-card-meta">
            <span><strong>${item.source}</strong> • ${evDate}</span>
            <div style="display: flex; gap: 4px; align-items: center;">
              ${sentimentPill}
              <span class="badge-impact ${impactClass}">${item.impact_category}</span>
            </div>
          </div>
          <h3 class="news-title">${item.title}</h3>
          <p class="news-summary">${item.summary}</p>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 0.75rem;">
          <span class="text-muted">Impact: ${item.severity}</span>
          ${item.source_url ? `<a href="${item.source_url}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-cyan); text-decoration: none;">Read Report &rarr;</a>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function filterNewsSearch() {
  const q = document.getElementById('news-search').value.toLowerCase().trim();
  if (!q) {
    renderMarketNews(cachedNews);
    return;
  }
  const filtered = cachedNews.filter(n =>
    n.title.toLowerCase().includes(q) ||
    n.summary.toLowerCase().includes(q) ||
    n.source.toLowerCase().includes(q)
  );
  renderMarketNews(filtered);
}

async function syncMarketNews() {
  showToast('Fetching latest financial news & analyst reports (FR-008)...');
  try {
    const res = await fetch('/api/market-intelligence/news/sync', { method: 'POST' });
    const data = await res.json();
    showToast(`Collected ${data.articles_collected || 'latest'} news items!`);
    loadMarketNews();
    loadMarketIntelligence();
  } catch (err) {
    showToast(`News fetch error: ${err.message}`);
  }
}

async function syncAllMarketIntelligence() {
  const btn = document.getElementById('btn-sync-all-intel');
  if (btn) btn.disabled = true;
  showToast('Running comprehensive market intelligence sync (FR-005 to FR-008)...');

  try {
    await Promise.all([
      fetch('/api/market-intelligence/indicators/sync', { method: 'POST' }),
      fetch('/api/market-intelligence/news/sync', { method: 'POST' })
    ]);
    showToast('Market intelligence live sync complete!');
    loadMarketIntelligence();
  } catch (err) {
    showToast(`Intel sync error: ${err.message}`);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// -------------------------------------------------------------
// FR-009: IMPACT CATEGORY MATRIX & CLASSIFIER SANDBOX
// -------------------------------------------------------------
const IMPACT_DESCRIPTIONS = {
  FINANCIAL: 'Interest rate shifts, inflation, liquidity, treasury yields, banking capital rules, and forex volatility.',
  REGULATORY: 'Antitrust rulings, disclosure mandates (SEC, EPA, CSDDD), compliance fines, and legal directives.',
  POLITICAL: 'Elections, government transitions, diplomatic friction, bilateral conflicts, and sovereign policy.',
  ENVIRONMENTAL: 'Carbon emissions limits, green transition capex, EPA standards, climate disclosure, and weather shocks.',
  SUPPLY_CHAIN: 'Tariffs, trade restrictions, export controls, port bottlenecks, chip shortages, and shipping disruptions.',
  COMPETITIVE: 'Hyperscaler rivalry, AI model breakthroughs, disruptive pricing wars, M&A, and market share displacement.'
};

async function loadImpactMatrix() {
  const grid = document.getElementById('impact-matrix-grid');
  if (!grid) return;

  try {
    const res = await fetch('/api/market-intelligence/impact-matrix');
    if (!res.ok) throw new Error('Failed to load matrix');
    const matrix = await res.json();

    const categories = ['FINANCIAL', 'REGULATORY', 'POLITICAL', 'ENVIRONMENTAL', 'SUPPLY_CHAIN', 'COMPETITIVE'];

    grid.innerHTML = categories.map(cat => {
      const stats = matrix[cat] || { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, TOTAL: 0 };
      const total = stats.TOTAL || 0;
      const desc = IMPACT_DESCRIPTIONS[cat] || '';

      const critPct = total ? (stats.CRITICAL / total) * 100 : 0;
      const highPct = total ? (stats.HIGH / total) * 100 : 0;
      const medPct = total ? (stats.MEDIUM / total) * 100 : 0;
      const lowPct = total ? (stats.LOW / total) * 100 : 0;

      return `
        <div class="impact-category-card">
          <div class="impact-cat-head">
            <span class="impact-cat-name">
              <span class="badge-impact badge-impact-${cat.toLowerCase()}">${cat}</span>
            </span>
            <span class="impact-cat-count">${total}</span>
          </div>

          <p class="impact-cat-desc">${desc}</p>

          <div class="severity-meter-bar">
            <div class="meter-seg meter-critical" style="width: ${critPct}%" title="Critical: ${stats.CRITICAL}"></div>
            <div class="meter-seg meter-high" style="width: ${highPct}%" title="High: ${stats.HIGH}"></div>
            <div class="meter-seg meter-medium" style="width: ${medPct}%" title="Medium: ${stats.MEDIUM}"></div>
            <div class="meter-seg meter-low" style="width: ${lowPct}%" title="Low: ${stats.LOW}"></div>
          </div>

          <div class="severity-legend">
            <span>🔴 Crit: ${stats.CRITICAL}</span>
            <span>🟠 High: ${stats.HIGH}</span>
            <span>🔵 Med: ${stats.MEDIUM}</span>
            <span>⚪ Low: ${stats.LOW}</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div class="empty-state"><p class="text-rose">Error loading impact matrix: ${err.message}</p></div>`;
  }
}

const SAMPLE_SCENARIOS = {
  tariff: 'United States Trade Representative announces finalization of 100% tariffs on imported electric vehicles, 50% on solar cells and advanced semiconductors, and 25% on critical battery minerals effective immediately.',
  export: 'Multilateral export control agreement bars sales of advanced semiconductor manufacturing equipment, gate-all-around EDA software, and sub-3nm chip technologies to foreign foundries.',
  tax: 'Global minimum corporate tax framework Pillar Two reaches 55 ratifying member states, imposing a 15% top-up tax on multinational tech conglomerates earning over €750M in annual revenue.',
  fed: 'Federal Reserve Open Market Committee signals neutral interest rate adjustments, holding federal funds rate while 10-year Treasury yield spikes 18 basis points amidst durable goods inflation concerns.',
  epa: 'Environmental Protection Agency issues binding greenhouse gas emissions limits for fossil-fueled power stations, mandating 90% carbon capture utilization by 2032.',
  ai: 'Hyperscaler cloud competitors launch next-generation automated reasoning models, slashing cloud token pricing by 65% and sparking widespread enterprise infrastructure displacement.'
};

function setClassifierSample(type) {
  const text = SAMPLE_SCENARIOS[type];
  if (text) {
    document.getElementById('classifier-input-text').value = text;
  }
}

async function runClassifier() {
  const input = document.getElementById('classifier-input-text').value.trim();
  const btn = document.getElementById('btn-run-classifier');
  const card = document.getElementById('classifier-result-card');

  if (!input) {
    showToast('Please enter text to classify.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Classifying Impact...';

  try {
    const res = await fetch('/api/market-intelligence/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: input })
    });

    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Classification failed');
    }

    const data = await res.json();
    card.classList.remove('hidden');

    const impactClass = `badge-impact-${data.impact_category.toLowerCase()}`;
    const sevClass = `badge-severity-${data.severity.toLowerCase()}`;
    const confPct = Math.round(data.confidence_score * 100);

    card.innerHTML = `
      <div class="classifier-result-header">
        <div>
          <span style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">FR-009 Classification Result</span>
          <div class="classifier-result-title">${data.title}</div>
        </div>
        <div style="display: flex; gap: 6px;">
          <span class="badge-impact ${impactClass}">${data.impact_category}</span>
          <span class="badge-severity ${sevClass}">${data.severity}</span>
        </div>
      </div>

      <div class="classifier-grid">
        <div class="classifier-meta-block">
          <div class="classifier-meta-label">Primary Impact Domain</div>
          <div class="classifier-meta-val" style="color: var(--accent-purple); font-size: 1.1rem;">${data.impact_category}</div>
          <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">${data.impact_description}</div>
        </div>

        <div class="classifier-meta-block">
          <div class="classifier-meta-label">Confidence & Sentiment</div>
          <div class="classifier-meta-val">${confPct}% Confidence</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Sentiment: <strong>${data.sentiment}</strong></div>
        </div>

        <div class="classifier-meta-block">
          <div class="classifier-meta-label">Detected Event Type</div>
          <div class="classifier-meta-val">${data.detected_event_type.replace('_', ' ')}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Severity: <strong>${data.severity}</strong></div>
        </div>
      </div>

      <div style="margin-bottom: 14px;">
        <span style="font-size: 0.75rem; color: var(--text-muted); margin-right: 8px;">Affected Sectors:</span>
        ${data.affected_sectors.map(s => `<span class="sector-tag" style="margin-right: 4px;">${s}</span>`).join('')}
        ${data.affected_tickers.length > 0 ? `
          <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 12px; margin-right: 8px;">Tickers:</span>
          ${data.affected_tickers.map(t => `<span class="ticker-tag" style="margin-right: 4px;">${t}</span>`).join('')}
        ` : ''}
      </div>

      <div class="actions-box">
        <div class="actions-box-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          Automated Risk Mitigation & Recommendations
        </div>
        <ul class="actions-list">
          ${data.suggested_actions.map(a => `<li>${a}</li>`).join('')}
        </ul>
      </div>
    `;

    showToast(`Classified as ${data.impact_category} (${data.severity} Severity)`);
  } catch (err) {
    showToast(`Classifier error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Classify Impact Category (FR-009)';
  }
}

// -------------------------------------------------------------
// EVENT CREATION MODAL (FR-007)
// -------------------------------------------------------------
function openCreateEventModal() {
  document.getElementById('create-event-modal').classList.remove('hidden');
}

function closeCreateEventModal() {
  document.getElementById('create-event-modal').classList.add('hidden');
}

async function submitCreateEvent() {
  const title = document.getElementById('modal-ev-title').value.trim();
  const event_type = document.getElementById('modal-ev-type').value;
  const impact_category = document.getElementById('modal-ev-category').value;
  const summary = document.getElementById('modal-ev-summary').value.trim();
  const source = document.getElementById('modal-ev-source').value.trim() || 'Intelligence Network';
  const source_url = document.getElementById('modal-ev-url').value.trim() || null;
  const severity = document.getElementById('modal-ev-severity').value;
  const sectorsRaw = document.getElementById('modal-ev-sectors').value.trim();
  const tickersRaw = document.getElementById('modal-ev-tickers').value.trim();

  if (!title || !summary) {
    showToast('Please provide both Title and Summary.');
    return;
  }

  const affected_sectors = sectorsRaw ? sectorsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
  const affected_tickers = tickersRaw ? tickersRaw.split(',').map(t => t.trim().toUpperCase()).filter(Boolean) : [];

  const payload = {
    title,
    summary,
    event_type,
    impact_category: impact_category || null,
    severity,
    sentiment: 'NEUTRAL',
    source,
    source_url,
    affected_sectors,
    affected_tickers
  };

  try {
    const res = await fetch('/api/market-intelligence/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Event creation failed');
    }

    const created = await res.json();
    showToast(`Event registered: ${created.title.substring(0, 30)}...`);
    closeCreateEventModal();

    // Reset form
    document.getElementById('modal-ev-title').value = '';
    document.getElementById('modal-ev-summary').value = '';
    document.getElementById('modal-ev-source').value = '';
    document.getElementById('modal-ev-url').value = '';
    document.getElementById('modal-ev-sectors').value = '';
    document.getElementById('modal-ev-tickers').value = '';

    // Refresh views
    loadMarketEvents(currentGeoType, currentGeoSeverity);
    loadImpactMatrix();
    loadMarketIntelligence();
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
}

// ============================================================================
// FUNCTION 2.3: KNOWLEDGE MANAGEMENT & RAG (FR-010 to FR-014)
// ============================================================================

async function loadRagStatus() {
  try {
    const res = await fetch('/api/rag/status');
    if (!res.ok) throw new Error('Failed to fetch RAG status');
    const data = await res.json();

    const statDocs = document.getElementById('rag-stat-docs');
    const statChunks = document.getElementById('rag-stat-chunks');
    if (statDocs) statDocs.textContent = `${data.indexed_documents_count} / ${data.total_documents_count}`;
    if (statChunks) statChunks.textContent = data.total_chunks_stored;

    // Populate Ticker Filter dropdowns if companies or indexed tickers exist
    const tickerFilter = document.getElementById('rag-filter-ticker');
    const recomTicker = document.getElementById('rag-recom-ticker');

    // Fetch tracked companies if not already loaded
    if (companiesData.length === 0) {
      const compRes = await fetch('/api/companies');
      if (compRes.ok) companiesData = await compRes.json();
    }

    const allTickers = Array.from(new Set([
      ...companiesData.map(c => c && c.ticker).filter(Boolean),
      ...(data.indexed_tickers || []).filter(Boolean)
    ])).sort();

    if (tickerFilter) {
      const currentFilterVal = tickerFilter.value;
      tickerFilter.innerHTML = '<option value="ALL">All Companies</option>' +
        allTickers.map(t => `<option value="${t}" ${t === currentFilterVal ? 'selected' : ''}>${t}</option>`).join('');
    }

    if (recomTicker) {
      const currentRecomVal = recomTicker.value;
      recomTicker.innerHTML = '<option value="ALL">Auto-Detect from Query</option>' +
        allTickers.map(t => `<option value="${t}" ${t === currentRecomVal ? 'selected' : ''}>${t}</option>`).join('');
    }
  } catch (err) {
    console.error('loadRagStatus error:', err);
  }
}

let isSyncingRagDocs = false;

async function syncAllRagDocs() {
  if (isSyncingRagDocs) return;

  const btn = document.getElementById('btn-sync-all-rag');
  const feedback = document.getElementById('rag-index-feedback');

  isSyncingRagDocs = true;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Indexing Documents...';
  }

  if (feedback) {
    feedback.classList.remove('hidden');
    feedback.className = 'rag-feedback-banner loading';
    feedback.innerHTML = `
      <div class="rag-feedback-header">
        <div class="rag-feedback-title">
          <div class="spinner"></div>
          <span>Synchronizing Knowledge Base Vector Store (FR-010)</span>
        </div>
        <span class="rag-stat-pill">Model: <strong>BAAI/bge-small-en-v1.5</strong></span>
      </div>
      <div class="rag-feedback-message">
        Examining unstructured documents, computing SHA-256 hashes, generating sentence-boundary semantic chunks, and verifying embeddings...
      </div>
    `;
  }

  try {
    const res = await fetch('/api/rag/index-all', { method: 'POST' });
    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      throw new Error(`Server returned non-JSON response (${res.status} ${res.statusText})`);
    }

    if (!res.ok) {
      throw new Error(data.detail || data.message || `HTTP ${res.status} ${res.statusText}`);
    }

    const isAllUpToDate = data.status === 'UP_TO_DATE' || (data.newly_indexed === 0 && data.failed_count === 0);

    if (feedback) {
      if (isAllUpToDate) {
        feedback.className = 'rag-feedback-banner up-to-date';
        feedback.innerHTML = `
          <div class="rag-feedback-header">
            <div class="rag-feedback-title" style="color: #34d399;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
              <span>All Documents Verified & Up to Date (FR-010)</span>
            </div>
            <span class="rag-stat-pill" style="border-color: rgba(16,185,129,0.35); color:#34d399;">SHA-256 Verified</span>
          </div>
          <div class="rag-feedback-message">
            ${data.message || `All ${data.total_documents} documents in the knowledge base match their persistent vector signatures. No new indexing was necessary.`}
          </div>
          <div class="rag-feedback-stats">
            <span class="rag-stat-pill">Examined: <strong>${data.total_documents}</strong></span>
            <span class="rag-stat-pill">Newly Indexed: <strong>0</strong></span>
            <span class="rag-stat-pill">Unchanged: <strong>${data.unchanged_count}</strong></span>
            <span class="rag-stat-pill">Failures: <strong>${data.failed_count || 0}</strong></span>
            <span class="rag-stat-pill">Total Persistent Chunks: <strong>${data.total_chunks_stored}</strong></span>
          </div>
        `;
        showToast(`Vector store up to date: all ${data.total_documents} documents verified (${data.total_chunks_stored} chunks).`);
      } else {
        feedback.className = 'rag-feedback-banner success';
        feedback.innerHTML = `
          <div class="rag-feedback-header">
            <div class="rag-feedback-title" style="color: #10b981;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
              <span>Vector Indexing Completed (FR-010)</span>
            </div>
            <span class="rag-stat-pill" style="border-color: rgba(16,185,129,0.45); color:#6ee7b7;">Indexed</span>
          </div>
          <div class="rag-feedback-message">
            ${data.message || `Successfully indexed ${data.newly_indexed} document(s) into persistent vector storage.`}
          </div>
          <div class="rag-feedback-stats">
            <span class="rag-stat-pill">Examined: <strong>${data.total_documents}</strong></span>
            <span class="rag-stat-pill">Newly Indexed: <strong>${data.newly_indexed}</strong></span>
            <span class="rag-stat-pill">Unchanged: <strong>${data.unchanged_count}</strong></span>
            <span class="rag-stat-pill">Failures: <strong>${data.failed_count || 0}</strong></span>
            <span class="rag-stat-pill">Total Persistent Chunks: <strong>${data.total_chunks_stored}</strong></span>
          </div>
        `;
        showToast(`Indexed ${data.newly_indexed} document(s) into ${data.total_chunks_stored} persistent vector chunks.`);
      }
    }

    await loadRagStatus();
  } catch (err) {
    if (feedback) {
      feedback.className = 'rag-feedback-banner error';
      feedback.innerHTML = `
        <div class="rag-feedback-header">
          <div class="rag-feedback-title" style="color: #f43f5e;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span>FR-010 Indexing Failed</span>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="syncAllRagDocs()" style="font-size:0.75rem; padding:3px 8px;">Retry</button>
        </div>
        <div class="rag-feedback-message">
          ${err.message}
        </div>
      `;
    }
    showToast(`Indexing error: ${err.message}`);
  } finally {
    isSyncingRagDocs = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
        Index All Documents (FR-010)
      `;
    }
  }
}

async function runSemanticSearch() {
  const query = document.getElementById('rag-search-query').value.trim();
  const ticker = document.getElementById('rag-filter-ticker').value;
  const docType = document.getElementById('rag-filter-doctype').value;
  const industry = document.getElementById('rag-filter-industry').value.trim();
  const geography = document.getElementById('rag-filter-geography').value.trim();
  const minSim = parseFloat(document.getElementById('rag-filter-similarity').value) || 0.35;
  const minConf = parseFloat(document.getElementById('rag-filter-confidence').value) || null;

  const btn = document.getElementById('btn-run-rag-search');
  const resultsContainer = document.getElementById('rag-search-results');
  const summaryBox = document.getElementById('rag-search-summary');

  if (!query) {
    showToast('Please enter a semantic search query or financial question');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Searching...';
  resultsContainer.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Scanning 384-dimensional persistent vector space...</p></div>';

  try {
    const payload = {
      query,
      ticker: ticker !== 'ALL' ? ticker : null,
      doc_type: docType !== 'ALL' ? docType : null,
      industry: industry || null,
      geography: geography || null,
      min_confidence: minConf,
      min_similarity: minSim,
      top_k: 6
    };

    const res = await fetch('/api/rag/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Search failed');

    summaryBox.classList.remove('hidden');
    summaryBox.innerHTML = `Found <strong>${data.results_count}</strong> distinct evidence chunks across <strong>${data.distinct_documents_count}</strong> documents (Relevance ≥ ${(minSim * 100).toFixed(0)}%).`;

    if (data.results_count === 0) {
      resultsContainer.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <p>No distinct evidence passages matched query and active metadata filters.</p>
          <span style="font-size:0.75rem; color:var(--text-muted);">Try lowering the Min Similarity threshold or clearing metadata filters.</span>
        </div>`;
      return;
    }

    resultsContainer.innerHTML = data.evidence.map((ev, idx) => `
      <div class="evidence-item-card">
        <div class="evidence-top">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="ticker-tag">${ev.ticker}</span>
            <span class="provenance-tag">${ev.doc_type}</span>
            <span style="font-size:0.8rem; font-weight:600; color:var(--text-primary);">${ev.title}</span>
          </div>
          <div class="similarity-badge">
            ${(ev.similarity_score * 100).toFixed(1)}% Sim
          </div>
        </div>
        <div class="evidence-text">
          "${ev.text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}"
        </div>
        <div class="evidence-meta-footer">
          <span><strong>Source:</strong> ${ev.file_name}</span>
          <span><strong>Period:</strong> ${ev.fiscal_period || 'N/A'}</span>
          <span><strong>Chunk:</strong> #${ev.chunk_index}</span>
          <span><strong>Industry:</strong> ${ev.metadata.industry || 'Corporate'}</span>
          <span><strong>Geography:</strong> ${ev.metadata.geography || 'Global'}</span>
          <span><strong>Confidence:</strong> ${(ev.metadata.confidence_score * 100).toFixed(0)}%</span>
        </div>
      </div>
    `).join('');

    showToast(`Retrieved ${data.results_count} evidence chunks`);
  } catch (err) {
    resultsContainer.innerHTML = `<div style="color:var(--accent-rose); padding:16px;">Error: ${err.message}</div>`;
    showToast(`Search error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Search';
  }
}

async function generateRecommendation() {
  const query = document.getElementById('rag-recom-query').value.trim();
  const ticker = document.getElementById('rag-recom-ticker').value;
  const threshold = parseFloat(document.getElementById('rag-recom-threshold').value) || 0.68;

  const btn = document.getElementById('btn-generate-recom');
  const outCard = document.getElementById('rag-recom-output');

  if (!query) {
    showToast('Please provide a financial analysis prompt');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Synthesizing Grounded Insights (FR-014)...';
  outCard.classList.remove('hidden');
  outCard.innerHTML = '<div class="empty-state"><div class="spinner"></div><p>Retrieving evidence, cross-referencing citations, and evaluating factual grounding...</p></div>';

  try {
    const payload = {
      query,
      ticker: ticker !== 'ALL' ? ticker : null,
      min_similarity: threshold,
      top_k: 4
    };

    const res = await fetch('/api/rag/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Recommendation generation failed');

    const isGrounded = data.status === 'GROUNDED';

    outCard.innerHTML = `
      <div class="grounded-banner ${isGrounded ? 'success' : 'insufficient'}">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          ${isGrounded
            ? '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline>'
            : '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>'}
        </svg>
        <div>
          <div>${isGrounded ? 'VERIFIED GROUNDED RECOMMENDATION (FR-014)' : 'EXPLICIT INSUFFICIENT EVIDENCE RESULT (FR-014)'}</div>
          <div style="font-size:0.75rem; font-weight:normal; opacity:0.85;">
            ${isGrounded
              ? `Supported by ${data.evidence_count} source citations | Avg Similarity: ${(data.average_similarity * 100).toFixed(1)}%`
              : data.insufficient_evidence_reason}
          </div>
        </div>
      </div>

      <div class="recom-body">${data.recommendation.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>

      ${isGrounded && data.key_findings.length > 0 ? `
        <div style="margin-top:14px;">
          <h4 style="font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.05em; margin-bottom:8px;">
            Key Factual Findings
          </h4>
          <ul class="findings-list">
            ${data.key_findings.map(f => `<li>${f}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      ${isGrounded && data.citations.length > 0 ? `
        <div style="margin-top:16px;">
          <h4 style="font-size:0.85rem; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.05em; margin-bottom:8px;">
            Verified Provenance & Source Citations (${data.citations.length})
          </h4>
          <div class="citations-container">
            ${data.citations.map(c => `
              <div class="citation-card">
                <div class="citation-card-head">
                  <span style="color:var(--accent-indigo); font-weight:700;">[${c.citation_id}] ${c.title}</span>
                  <span class="similarity-badge">${(c.similarity_score * 100).toFixed(1)}% Match</span>
                </div>
                <div class="citation-excerpt">"${c.excerpt}"</div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">
                  Doc #${c.document_id} • ${c.file_name} • ${c.fiscal_period || 'N/A'} • Chunk #${c.chunk_index} • Conf: ${(c.confidence_score * 100).toFixed(0)}%
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    `;

    showToast(isGrounded ? 'Grounded recommendation generated' : 'Insufficient evidence warning reported');
  } catch (err) {
    outCard.innerHTML = `<div style="color:var(--accent-rose); padding:16px;">Error: ${err.message}</div>`;
    showToast(`Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>
      Generate Grounded Recommendation (FR-014)
    `;
  }
}
