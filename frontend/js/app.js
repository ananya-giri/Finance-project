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
    scheduler: { title: 'Auto-Monitoring', sub: 'FR-004: Automated Report & Statement Watcher' }
  };

  if (titles[tabId]) {
    pageTitle.textContent = titles[tabId].title;
    pageSubtitle.textContent = titles[tabId].sub;
  }

  // Auto-refresh data on tab change
  if (tabId === 'dashboard') loadDashboard();
  if (tabId === 'documents') loadDocuments();
  if (tabId === 'scheduler') loadSchedulerStatus();
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
