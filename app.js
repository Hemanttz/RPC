// ===== PV Tool Training App — State & Logic (with Backend API) =====

const API = '';  // Same origin when served by Flask

// App state
const state = {
  currentScreen: 'login-screen',
  userId: null, sessionId: null, userEmail: '', userName: '',
  warehouse: '', deskcode: '', deskType: 'RETURN',
  inputCarton: '',
  outputCartons: { pass: '', fail: '', failnon: '', refinish: '', onhold: '' },
  outputCartonCounts: { pass: 0, fail: 0, failnon: 0, refinish: 0, onhold: 0 },
  trackingId: '', returnId: '',
  gtinScanned: false, brandTagNA: false,
  selectedIssue: 'no-issues', qcResult: '',
  currentProduct: null, currentLogId: null,
  productsDone: 0, totalProducts: 50,
  step: 0,
  sessionStartTime: null, productStartTime: null,
  timerInterval: null,
  // Image gallery state
  galleryImages: [],
  galleryIndex: 0
};

// ===== DATE FORMATTER =====
function formatDateTime(isoStr) {
  if (!isoStr) return '—';
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return '—';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  let hh = d.getHours();
  const min = String(d.getMinutes()).padStart(2, '0');
  const ampm = hh >= 12 ? 'pm' : 'am';
  hh = hh % 12 || 12;
  hh = String(hh).padStart(2, '0');
  return `${dd}/${mm}/${yyyy}, ${hh}:${min} ${ampm}`;
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

// ===== SCREEN NAVIGATION =====
function showScreen(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('app-shell').classList.remove('active');
  if (screenId === 'app-shell') {
    document.getElementById('app-shell').classList.add('active');
  } else {
    const el = document.getElementById(screenId);
    if (el) el.classList.add('active');
  }
  state.currentScreen = screenId;
}

// ===== TIMER =====
function startSessionTimer() {
  if (!state.sessionStartTime) {
    state.sessionStartTime = Date.now();
  }
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - state.sessionStartTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    const el = document.getElementById('session-timer');
    if (el) el.textContent = `⏱ ${m}:${s}`;
  }, 1000);
}

function updateProductCounter() {
  const el = document.getElementById('product-counter');
  if (el) el.textContent = `${state.productsDone}/${state.totalProducts}`;
}

// ===== STATE PERSISTENCE =====
function saveState() {
  if (state.userId) {
    const stateToSave = { ...state, timerInterval: null };
    localStorage.setItem('pv_state_' + state.userId, JSON.stringify(stateToSave));
  }
}

function loadState() {
  if (!state.userId) return false;
  const saved = localStorage.getItem('pv_state_' + state.userId);
  if (!saved) return false;
  try {
    const parsed = JSON.parse(saved);
    if (parsed.sessionId !== state.sessionId) {
      clearState();
      return false;
    }
    Object.assign(state, parsed);
    return true;
  } catch (e) {
    console.error('Failed to load state:', e);
    return false;
  }
}

function clearState() {
  if (state.userId) {
    localStorage.removeItem('pv_state_' + state.userId);
  }
}

function restoreUI() {
  if (!state.userId) return;

  showScreen(state.currentScreen);
  updateProductCounter();

  if (state.warehouse) {
    document.getElementById('location-info').classList.remove('hidden');
    document.getElementById('type-label').textContent = state.deskType;
    document.getElementById('change-desk-btn').classList.remove('hidden');
    document.getElementById('change-output-btn').classList.remove('hidden');
    
    document.getElementById('warehouse-select').value = state.warehouse;
    document.getElementById('deskcode-input').value = state.deskcode;
    const radio = document.querySelector(`input[name="desk-type"][value="${state.deskType}"]`);
    if (radio) radio.checked = true;
  }

  if (state.inputCarton) {
    document.getElementById('scan-carton-input').value = state.inputCarton;
    document.getElementById('carton-count').classList.remove('hidden');
    document.getElementById('close-carton-link').classList.remove('hidden');
    
    const { pass, fail, failnon, refinish, onhold } = state.outputCartons;
    if (pass && fail && failnon && refinish && onhold) {
      document.getElementById('scan-row').classList.remove('hidden');
    } else {
      document.getElementById('scan-row').classList.add('hidden');
    }
  } else {
    document.getElementById('scan-carton-input').value = '';
    document.getElementById('carton-count').classList.add('hidden');
    document.getElementById('close-carton-link').classList.add('hidden');
    document.getElementById('scan-row').classList.add('hidden');
  }

  const types = ['pass', 'fail', 'failnon', 'refinish', 'onhold'];
  types.forEach(t => {
    if (state.outputCartons[t]) {
      const closeBtn = document.getElementById('close-' + t + '-carton');
      if (closeBtn) closeBtn.classList.remove('hidden');
      
      let inputId = t + '-carton';
      if (t === 'pass') inputId = 'qc-pass-carton';
      if (t === 'fail') inputId = 'qc-fail-carton';
      if (t === 'failnon') inputId = 'qc-fail-non-carton';
      
      const input = document.getElementById(inputId);
      if (input) input.value = state.outputCartons[t];
      
      const countMap = { pass:'pass-count', fail:'fail-count', failnon:'failnon-count', refinish:'refinish-count', onhold:'onhold-count' };
      if (countMap[t]) {
        const cntEl = document.getElementById(countMap[t]);
        if (cntEl) cntEl.textContent = `(${state.outputCartonCounts ? state.outputCartonCounts[t] || 0 : 0})`;
      }
    } else {
      const closeBtn = document.getElementById('close-' + t + '-carton');
      if (closeBtn) closeBtn.classList.add('hidden');
      
      let inputId = t + '-carton';
      if (t === 'pass') inputId = 'qc-pass-carton';
      if (t === 'fail') inputId = 'qc-fail-carton';
      if (t === 'failnon') inputId = 'qc-fail-non-carton';
      
      const input = document.getElementById(inputId);
      if (input) input.value = '';
    }
  });

  if (state.currentProduct) {
    populateProduct(state.currentProduct);
    
    document.getElementById('product-img').src = state.galleryImages[state.galleryIndex];
    updateGalleryDots();
    
    document.getElementById('scan-tracking-input').value = state.trackingId;
    document.getElementById('scan-return-input').value = state.returnId;
    
    document.getElementById('product-area').classList.remove('hidden');
    document.getElementById('right-panel').classList.add('show');
    
    if (state.qcResult) {
      document.getElementById('other-checks-panel').classList.add('hidden');
      document.getElementById('gtin-panel').classList.add('hidden');
      document.getElementById('qc-result-panel').classList.remove('hidden');
      
      if (state.qcResult === 'pass') {
        document.getElementById('qc-pass-badge-top').classList.remove('hidden');
        document.getElementById('status-badge').textContent = 'RPC';
        document.getElementById('status-badge').style.background = '#4caf50';
      }
    } else if (state.gtinScanned || state.brandTagNA) {
      document.getElementById('gtin-panel').classList.add('hidden');
      document.getElementById('other-checks-panel').classList.remove('hidden');
      
      const gtinResult = state.gtinScanned ? 'GTIN PASS' : 'GTIN FAIL';
      document.getElementById('gtin-result-badge').textContent = gtinResult;
      document.getElementById('gtin-result-badge').className = 'gtin-badge ' + (state.gtinScanned ? 'pass' : 'fail');
      
      document.querySelectorAll('.issue-icon-btn').forEach(b => b.classList.remove('selected'));
      const activeBtn = document.querySelector(`.issue-icon-btn[data-issue="${state.selectedIssue}"]`);
      if (activeBtn) activeBtn.classList.add('selected');
      
      if (state.brandTagNA) {
        document.getElementById('extra-issue-icons').classList.remove('hidden');
      } else {
        document.getElementById('extra-issue-icons').classList.add('hidden');
      }
    } else {
      document.getElementById('gtin-panel').classList.remove('hidden');
      document.getElementById('other-checks-panel').classList.add('hidden');
      document.getElementById('qc-result-panel').classList.add('hidden');
    }
  } else {
    document.getElementById('product-area').classList.add('hidden');
    document.getElementById('right-panel').classList.remove('show');
    document.getElementById('qc-result-panel').classList.add('hidden');
    document.getElementById('qc-pass-badge-top').classList.add('hidden');
    document.getElementById('extra-issue-icons').classList.add('hidden');
    ['scan-tracking-input','scan-return-input','scan-gtin-input','scan-qc-input'].forEach(id => {
      const input = document.getElementById(id);
      if (input) input.value = '';
    });
  }

  setTimeout(() => {
    if (state.currentScreen === 'app-shell') {
      if (state.step === 2) {
        const el = document.getElementById('scan-carton-input');
        if (el) el.focus();
      } else if (state.step === 3) {
        const el = document.getElementById('scan-tracking-input');
        if (el) el.focus();
      } else if (state.step === 5) {
        if (state.gtinScanned || state.brandTagNA) {
          const el = document.getElementById('scan-qc-input');
          if (el) el.focus();
        } else {
          const el = document.getElementById('scan-gtin-input');
          if (el) el.focus();
        }
      } else if (state.step === 6) {
        const el = document.getElementById('scan-item-barcode-input');
        if (el) el.focus();
      }
    }
  }, 100);
}

// ===== LOGIN (API) =====
function togglePassword() {
  const p = document.getElementById('login-password');
  const cb = document.getElementById('show-pass-cb');
  p.type = cb.checked ? 'text' : 'password';
}

async function doLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const errEl = document.getElementById('login-error');
  errEl.style.display = 'none';

  if (!email || !password) { errEl.textContent = 'Email and password required'; errEl.style.display = 'block'; return; }

  try {
    const res = await fetch(API + '/api/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.success) {
      state.userId = data.user.id;
      state.sessionId = data.session_id;
      state.userEmail = data.user.email;
      state.userName = data.user.name;
      state.totalProducts = data.total_products || 50;
      document.getElementById('nav-user-email').textContent = state.userEmail;
      
      startSessionTimer();
      updateProductCounter();
      
      if (loadState()) {
        restoreUI();
      } else {
        showScreen('app-shell');
        setTimeout(() => showWarehouseModal(), 300);
      }
    } else {
      errEl.textContent = data.error || 'Login failed';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Server not running. Start with: python server.py';
    errEl.style.display = 'block';
  }
}

async function doLogout() {
  try { await fetch(API + '/api/logout', { method: 'POST' }); } catch (e) {}
  if (state.timerInterval) clearInterval(state.timerInterval);
  clearState();
  state.userId = null; state.sessionId = null;
  showScreen('login-screen');
}

// ===== REGISTRATION (API) =====
async function doRegister() {
  const name = document.getElementById('reg-name').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value.trim();
  const msgEl = document.getElementById('reg-msg');

  if (!email || !password) { msgEl.textContent = 'Email and password required'; msgEl.style.color = '#d32f2f'; msgEl.style.display = 'block'; return; }

  try {
    const res = await fetch(API + '/api/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name })
    });
    const data = await res.json();
    if (data.success) {
      msgEl.textContent = 'Account created! You can now login.';
      msgEl.style.color = '#4caf50'; msgEl.style.display = 'block';
      setTimeout(() => showScreen('email-login-screen'), 1500);
    } else {
      msgEl.textContent = data.error || 'Registration failed';
      msgEl.style.color = '#d32f2f'; msgEl.style.display = 'block';
    }
  } catch (e) {
    msgEl.textContent = 'Server not running. Start with: python server.py';
    msgEl.style.color = '#d32f2f'; msgEl.style.display = 'block';
  }
}

async function uploadCSV(input) {
  const file = input.files[0];
  if (!file) return;
  const resultEl = document.getElementById('csv-result');
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(API + '/api/register/bulk', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.success) {
      let msg = `Created ${data.created} of ${data.total_in_csv} users.`;
      if (data.errors.length) msg += ` Errors: ${data.errors.join('; ')}`;
      resultEl.textContent = msg;
      resultEl.style.color = '#4caf50'; resultEl.style.display = 'block';
    } else {
      resultEl.textContent = data.error; resultEl.style.color = '#d32f2f'; resultEl.style.display = 'block';
    }
  } catch (e) {
    resultEl.textContent = 'Server not running.'; resultEl.style.color = '#d32f2f'; resultEl.style.display = 'block';
  }
  input.value = '';
}

// ===== BANNER NOTIFICATIONS =====
function showBanner(type, message) {
  const banner = document.getElementById('app-banner');
  banner.className = 'banner show ' + type;
  document.getElementById('banner-msg').textContent = message;
  banner.querySelector('.banner-icon').textContent = type === 'success' ? '✅' : '⚠️';
}
function closeBanner() { document.getElementById('app-banner').classList.remove('show'); }

// ===== SIDEBAR VIEW SWITCHING =====
function showView(view) {
  const qcView = document.querySelector('.main-content > .relative');
  const dashView = document.getElementById('dashboard-view');
  const exportView = document.getElementById('export-view');
  const addProductsView = document.getElementById('add-products-view');
  const rightPanel = document.getElementById('right-panel');

  document.querySelectorAll('.sidebar-icon').forEach(i => i.classList.remove('active'));

  // Hide all views first
  if (qcView) qcView.classList.add('hidden');
  dashView.classList.add('hidden');
  exportView.classList.add('hidden');
  addProductsView.classList.add('hidden');
  rightPanel.classList.remove('show');

  if (view === 'dashboard') {
    dashView.classList.remove('hidden');
    document.querySelectorAll('.sidebar-icon')[1].classList.add('active');
    loadDashboard();
  } else if (view === 'export') {
    exportView.classList.remove('hidden');
    document.querySelectorAll('.sidebar-icon')[2].classList.add('active');
  } else if (view === 'add-products') {
    addProductsView.classList.remove('hidden');
    document.querySelectorAll('.sidebar-icon')[3].classList.add('active');
    loadProductCount();
  } else {
    // QC view
    if (qcView) qcView.classList.remove('hidden');
    document.querySelectorAll('.sidebar-icon')[0].classList.add('active');
  }
}

// ===== DASHBOARD (API) =====
async function loadDashboard() {
  try {
    const [statsRes, dashRes] = await Promise.all([
      fetch(API + '/api/stats'), fetch(API + '/api/dashboard')
    ]);
    const statsData = await statsRes.json();
    const dashData = await dashRes.json();

    // My stats
    const s = statsData.stats || {};
    document.getElementById('stat-total').textContent = s.total_products || 0;
    document.getElementById('stat-avg').textContent = (s.avg_time || 0) + 's';
    document.getElementById('stat-fastest').textContent = (s.fastest_time || 0) + 's';
    document.getElementById('stat-total-time').textContent = (s.total_time || 0) + 's';

    // Leaderboard
    const tbody = document.getElementById('leaderboard-body');
    tbody.innerHTML = '';
    (dashData.users || []).forEach((u, i) => {
      const acc = u.pv_accuracy || 0;
      const accClass = acc >= 80 ? 'pass-badge' : (acc >= 50 ? 'warn-badge' : 'fail-badge');
      tbody.innerHTML += `<tr>
        <td>${i + 1}</td><td>${u.name}</td><td>${u.email}</td>
        <td>${u.warehouse || '—'}</td>
        <td>${u.total_products}</td>
        <td>${formatDateTime(u.carton_scan_start)}</td>
        <td>${formatDateTime(u.carton_scan_end)}</td>
        <td>${formatDuration(u.total_scan_duration)}</td>
        <td><span class="${accClass}">${acc}%</span></td>
      </tr>`;
    });

    // History
    const hbody = document.getElementById('history-body');
    hbody.innerHTML = '';
    (statsData.history || []).forEach((h, i) => {
      hbody.innerHTML += `<tr>
        <td>${i + 1}</td><td>${h.user_name || '—'}</td><td>${h.product_name}</td><td>${h.brand}</td><td>${h.category}</td>
        <td>${h.time_seconds}s</td><td>${h.gtin_result}</td><td>${h.issue_selected}</td>
        <td><span class="${h.qc_result === 'pass' ? 'pass-badge' : 'fail-badge'}">${h.qc_result.toUpperCase()}</span></td>
      </tr>`;
    });
  } catch (e) { console.error('Dashboard load error:', e); }
}

// ===== EXPORT DATA =====
function getExportFilters() {
  return {
    date_from: document.getElementById('export-date-from').value || '',
    date_to: document.getElementById('export-date-to').value || '',
    name: document.getElementById('export-name').value.trim(),
    carton_code: document.getElementById('export-carton-code').value.trim(),
    warehouse: document.getElementById('export-warehouse').value,
  };
}

async function filterExportData() {
  const f = getExportFilters();
  const params = new URLSearchParams();
  if (f.date_from) params.set('date_from', f.date_from);
  if (f.date_to) params.set('date_to', f.date_to);
  if (f.name) params.set('name', f.name);
  if (f.carton_code) params.set('carton_code', f.carton_code);
  if (f.warehouse) params.set('warehouse', f.warehouse);

  const btn = document.getElementById('btn-export-filter');
  btn.textContent = 'Loading…';
  btn.disabled = true;

  try {
    const res = await fetch(API + '/api/export?' + params.toString());
    const json = await res.json();
    const rows = json.data || [];

    const info = document.getElementById('export-result-info');
    const countEl = document.getElementById('export-result-count');
    info.style.display = 'block';
    countEl.textContent = `${rows.length} record${rows.length !== 1 ? 's' : ''} found`;

    const tbody = document.getElementById('export-body');
    tbody.innerHTML = '';
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="14" style="text-align:center;color:#999;padding:20px">No records found for the selected filters.</td></tr>';
    } else {
      rows.forEach((r, i) => {
        const accClass = r.accuracy_result === 'Correct' ? 'pass-badge' : 'fail-badge';
        tbody.innerHTML += `<tr>
          <td>${i + 1}</td>
          <td>${r.name || '—'}</td>
          <td>${r.warehouse || '—'}</td>
          <td>${r.carton_code || '—'}</td>
          <td>${r.product_name || '—'}</td>
          <td>${r.brand || '—'}</td>
          <td>${r.category || '—'}</td>
          <td>${formatDateTime(r.started_at)}</td>
          <td>${formatDateTime(r.completed_at)}</td>
          <td>${r.time_seconds || 0}s</td>
          <td>${r.gtin_result || '—'}</td>
          <td>${r.issue_selected || '—'}</td>
          <td><span class="${r.qc_result === 'pass' ? 'pass-badge' : 'fail-badge'}">${(r.qc_result || '').toUpperCase()}</span></td>
          <td><span class="${accClass}">${r.accuracy_result || '—'}</span></td>
        </tr>`;
      });
    }
  } catch (e) {
    console.error('Export filter error:', e);
  }

  btn.textContent = 'Filter';
  btn.disabled = false;
}

function downloadExportCSV() {
  const f = getExportFilters();
  const params = new URLSearchParams();
  if (f.date_from) params.set('date_from', f.date_from);
  if (f.date_to) params.set('date_to', f.date_to);
  if (f.name) params.set('name', f.name);
  if (f.carton_code) params.set('carton_code', f.carton_code);
  if (f.warehouse) params.set('warehouse', f.warehouse);

  // Trigger browser download
  window.location.href = API + '/api/export/csv?' + params.toString();
}

// ===== WAREHOUSE MODAL =====
function showWarehouseModal() { document.getElementById('warehouse-modal').classList.add('show'); }
function closeWarehouseModal() { document.getElementById('warehouse-modal').classList.remove('show'); }

function proceedWarehouse() {
  const warehouse = document.getElementById('warehouse-select').value;
  const deskcode = document.getElementById('deskcode-input').value;
  const deskType = document.querySelector('input[name="desk-type"]:checked').value;
  if (!warehouse) { alert('Please select a warehouse'); return; }
  if (!deskcode) { alert('Please enter a deskcode'); return; }
  state.warehouse = warehouse; state.deskcode = deskcode; state.deskType = deskType; state.step = 2;
  document.getElementById('location-info').classList.remove('hidden');
  document.getElementById('type-label').textContent = deskType;
  document.getElementById('change-desk-btn').classList.remove('hidden');
  document.getElementById('change-output-btn').classList.remove('hidden');
  closeWarehouseModal();
  showBanner('success', 'SUCCESS');

  // Save warehouse to server session
  fetch(API + '/api/warehouse', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ warehouse: warehouse })
  }).catch(() => {});

  saveState();
  setTimeout(() => document.getElementById('scan-carton-input').focus(), 300);
}

// ===== CARTON SCANNING =====
function handleCartonScan(event) {
  if (event.key !== 'Enter') return;
  const input = document.getElementById('scan-carton-input');
  const barcode = input.value.trim();
  if (!barcode) return;
  if (barcode === 'C366855613') {
    showBanner('error', 'WMS API error: Carton barcode already associated. code: 10028');
    return;
  }
  state.inputCarton = barcode;
  document.getElementById('carton-count').classList.remove('hidden');
  document.getElementById('close-carton-link').classList.remove('hidden');
  showBanner('success', 'SUCCESS');
  state.step = 3;
  
  const { pass, fail, failnon, refinish, onhold } = state.outputCartons;
  if (pass && fail && failnon && refinish && onhold) {
    document.getElementById('scan-row').classList.remove('hidden');
  }

  // Persist carton code to server session for export
  fetch(API + '/api/carton_code', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ carton_code: barcode })
  }).catch(() => {});

  saveState();
  setTimeout(() => document.getElementById('scan-tracking-input').focus(), 300);
}

function closeCarton() {
  state.inputCarton = '';
  document.getElementById('scan-carton-input').value = '';
  document.getElementById('carton-count').classList.add('hidden');
  document.getElementById('close-carton-link').classList.add('hidden');
  document.getElementById('scan-row').classList.add('hidden');
  document.getElementById('product-area').classList.add('hidden');
  document.getElementById('right-panel').classList.remove('show');
  saveState();
}

// ===== OUTPUT CARTON MODAL =====
function showOutputCartonModal() {
  document.getElementById('output-carton-modal').classList.add('show');
}
function closeOutputCartonModal() { document.getElementById('output-carton-modal').classList.remove('show'); }

function closeOutputCarton(type) {
  state.outputCartons[type] = '';
  if (!state.outputCartonCounts) state.outputCartonCounts = { pass: 0, fail: 0, failnon: 0, refinish: 0, onhold: 0 };
  state.outputCartonCounts[type] = 0;
  
  let inputId = type + '-carton';
  if (type === 'pass') inputId = 'qc-pass-carton';
  if (type === 'fail') inputId = 'qc-fail-carton';
  if (type === 'failnon') inputId = 'qc-fail-non-carton';
  
  const input = document.getElementById(inputId);
  if (input) input.value = '';
  
  const closeBtn = document.getElementById('close-' + type + '-carton');
  if (closeBtn) closeBtn.classList.add('hidden');
  
  const countMap = { pass:'pass-count', fail:'fail-count', failnon:'failnon-count', refinish:'refinish-count', onhold:'onhold-count' };
  const cntEl = document.getElementById(countMap[type]);
  if (cntEl) cntEl.textContent = '(0)';
  
  saveState();
}

function handleOutputCartonScan(event, type) {
  if (event.key !== 'Enter') return;
  const inputMap = { pass:'qc-pass-carton', fail:'qc-fail-carton', failnon:'qc-fail-non-carton', refinish:'refinish-carton', onhold:'onhold-carton' };
  const input = document.getElementById(inputMap[type]);
  const barcode = input.value.trim();
  if (!barcode) return;
  if (type === 'refinish' && barcode.startsWith('STNC')) {
    showOutputBanner('error', 'WMS API error: Carton already registered. code: 10023');
    return;
  }
  state.outputCartons[type] = barcode;
  document.getElementById('close-' + type + '-carton').classList.remove('hidden');
  const countMap = { pass:'pass-count', fail:'fail-count', failnon:'failnon-count' };
  if (countMap[type]) document.getElementById(countMap[type]).textContent = '(0)';
  showOutputBanner('success', 'Carton Registered Successfully');
  saveState();
}

function showOutputBanner(type, msg) {
  const banner = document.getElementById('output-modal-banner');
  banner.className = 'modal-banner show ' + type;
  document.getElementById('output-banner-msg').textContent = msg;
  banner.querySelector('.banner-icon').textContent = type === 'success' ? '✅' : '⚠️';
}
function closeOutputBanner() { document.getElementById('output-modal-banner').classList.remove('show'); }

function updateOutputCartons() {
  const { pass, fail, failnon, refinish, onhold } = state.outputCartons;
  if (!pass || !fail || !failnon || !refinish || !onhold) {
    showOutputBanner('error', 'Please scan all 5 output cartons before updating.');
    return;
  }

  closeOutputCartonModal(); closeOutputBanner();
  if (state.inputCarton) {
    document.getElementById('scan-row').classList.remove('hidden');
    setTimeout(() => document.getElementById('scan-tracking-input').focus(), 300);
  }
}

// ===== IMAGE ENLARGE MODAL =====
function openImageModal() {
  const src = document.getElementById('product-img').src;
  document.getElementById('enlarged-img').src = src;
  document.getElementById('image-modal').classList.add('show');
}
function closeImageModal() {
  document.getElementById('image-modal').classList.remove('show');
}
function modalPrevImage() {
  galleryPrev();
  document.getElementById('enlarged-img').src = state.galleryImages[state.galleryIndex];
}
function modalNextImage() {
  galleryNext();
  document.getElementById('enlarged-img').src = state.galleryImages[state.galleryIndex];
}

// ===== TRACKING ID SCANNING (SKU-based lookup from API) =====
async function handleTrackingScan(event) {
  if (event.key !== 'Enter') return;
  const input = document.getElementById('scan-tracking-input');
  const trackingId = input.value.trim();
  if (!trackingId) return;
  state.trackingId = trackingId;

  // Look up product by Tracking ID
  try {
    const skuRes = await fetch(API + '/api/product/by-tracking-id/' + encodeURIComponent(trackingId));
    const skuData = await skuRes.json();

    if (!skuData.product) {
      showBanner('error', 'Product not found for Tracking ID: ' + trackingId + '. Please scan the correct Tracking ID.');
      return;
    }

    state.currentProduct = skuData.product;

    // Get product count info
    const countRes = await fetch(API + '/api/product/next');
    const countData = await countRes.json();
    state.productsDone = countData.products_done || 0;
    state.totalProducts = countData.total_products || 150;
    updateProductCounter();

    // Start PV tracking
    const pvRes = await fetch(API + '/api/pv/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: skuData.product.id })
    });
    const pvData = await pvRes.json();
    state.currentLogId = pvData.log_id;
    state.productStartTime = Date.now();

    // Populate product details
    populateProduct(skuData.product);
    showBanner('success', 'SUCCESS');
  } catch (e) {
    // Fallback to static product if server unavailable
    populateProductStatic();
    showBanner('success', 'SUCCESS (offline mode)');
  }

  state.step = 5;
  document.getElementById('product-area').classList.remove('hidden');
  document.getElementById('right-panel').classList.add('show');
  document.getElementById('gtin-panel').classList.remove('hidden');
  document.getElementById('other-checks-panel').classList.add('hidden');
  document.getElementById('qc-result-panel').classList.add('hidden');
  saveState();
  setTimeout(() => document.getElementById('scan-gtin-input').focus(), 500);
}

function populateProduct(p) {
  // Set up image gallery with 3 images
  const getImageUrl = (img) => img && img.startsWith('http') ? img : '/static/products/' + img;
  state.galleryImages = [
    getImageUrl(p.image_filename),
    p.image_filename_2 ? getImageUrl(p.image_filename_2) : getImageUrl(p.image_filename),
    p.image_filename_3 ? getImageUrl(p.image_filename_3) : getImageUrl(p.image_filename)
  ];
  state.galleryIndex = 0;
  document.getElementById('product-img').src = state.galleryImages[0];
  updateGalleryDots();

  document.getElementById('display-return-id').textContent = '10' + String(Math.floor(Math.random() * 9000000000 + 1000000000));
  document.getElementById('prod-brand').textContent = p.brand;
  document.getElementById('prod-name').textContent = p.brand + ' ' + p.name;
  document.getElementById('prod-barcode').textContent = p.item_barcode;
  document.getElementById('prod-sku').textContent = p.myntra_sku;
  document.getElementById('prod-style').textContent = p.style_id;
  document.getElementById('prod-article').textContent = p.article_no;
  document.getElementById('prod-size').textContent = p.size;
  document.getElementById('prod-mrp').textContent = '₹' + p.mrp;
  document.getElementById('prod-color').textContent = p.color;
  // Description
  const descEl = document.getElementById('prod-desc');
  if (descEl) descEl.textContent = p.description || '—';
  // Update return details
  const rdSpans = document.querySelectorAll('.return-detail-item span');
  if (rdSpans[1]) rdSpans[1].textContent = p.return_type;
  if (rdSpans[2]) rdSpans[2].textContent = p.return_mode;

  // Update brand tag eligibility notice
  const eligEl = document.getElementById('brand-tag-eligibility');
  if (eligEl) {
    if (p.eligible_brand_tag === 1) {
      eligEl.textContent = '✅ ITEM IS ELIGIBLE FOR BRAND TAG REPLACEMENT';
      eligEl.className = 'notice eligible';
    } else {
      eligEl.textContent = '⊘ ITEM IS NOT ELIGIBLE FOR BRAND TAG REPLACEMENT';
      eligEl.className = 'notice not-eligible';
    }
  }
}

// ===== IMAGE GALLERY NAVIGATION =====
function galleryPrev() {
  if (state.galleryImages.length === 0) return;
  state.galleryIndex = (state.galleryIndex - 1 + state.galleryImages.length) % state.galleryImages.length;
  document.getElementById('product-img').src = state.galleryImages[state.galleryIndex];
  updateGalleryDots();
}

function galleryNext() {
  if (state.galleryImages.length === 0) return;
  state.galleryIndex = (state.galleryIndex + 1) % state.galleryImages.length;
  document.getElementById('product-img').src = state.galleryImages[state.galleryIndex];
  updateGalleryDots();
}

function updateGalleryDots() {
  const dots = document.querySelectorAll('#gallery-dots .gallery-dot');
  dots.forEach((dot, i) => {
    dot.classList.toggle('active', i === state.galleryIndex);
  });
}

function populateProductStatic() {
  // Keep existing hardcoded product as fallback
}

// ===== GTIN SCANNING =====
function handleGtinScan(event) {
  if (event.key !== 'Enter') return;
  const inputVal = document.getElementById('scan-gtin-input').value.trim();
  if (!inputVal) return;
  
  if (state.currentProduct && inputVal !== state.currentProduct.myntra_sku) {
    showBanner('error', 'Incorrect GTIN/SKU. Please scan the correct SKU for this item.');
    return;
  }

  state.gtinScanned = true;
  showOtherChecks('GTIN PASS');
  saveState();
}

function brandTagNotAvailable() {
  state.brandTagNA = true;
  showOtherChecks('GTIN FAIL');
  document.getElementById('extra-issue-icons').classList.remove('hidden');
  document.getElementById('gtin-result-badge').textContent = 'GTIN FAIL';
  document.getElementById('gtin-result-badge').className = 'gtin-badge fail';
  saveState();
}

async function returnNotReceived() {
  state.selectedIssue = 'return-not-received';
  state.qcResult = 'fail';
  const gtinResult = state.gtinScanned ? 'PASS' : (state.brandTagNA ? 'FAIL' : 'FAIL');
  const assignedCarton = 'QC Fail Carton (STN)';

  // Complete PV via API
  if (state.currentLogId) {
    try {
      const res = await fetch(API + '/api/pv/complete', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          log_id: state.currentLogId,
          gtin_result: gtinResult,
          issue_selected: 'return-not-received',
          qc_result: 'fail'
        })
      });
      const data = await res.json();
      if (data.time_seconds) {
        showBanner('success', `Q1 — Time: ${data.time_seconds}s`);
      }
    } catch (e) { console.error(e); }
  }

  state.productsDone++;
  updateProductCounter();

  // Show result panel
  document.getElementById('gtin-panel').classList.add('hidden');
  document.getElementById('other-checks-panel').classList.add('hidden');
  document.getElementById('qc-result-panel').classList.remove('hidden');

  const statusEl = document.getElementById('result-status-display');
  statusEl.textContent = '❌ Marked As QC Fail';
  statusEl.className = 'result-status fail';
  document.getElementById('qc-pass-badge-top').classList.add('hidden');

  const cartonEl = document.getElementById('assigned-carton-name');
  const keepInCartonEl = cartonEl.closest('.keep-in-carton');
  cartonEl.textContent = assignedCarton;
  keepInCartonEl.classList.remove('carton-pass', 'carton-fail', 'carton-refinish');
  keepInCartonEl.classList.add('carton-fail');

  state.step = 6;
  saveState();
}

function showOtherChecks(gtinResult) {
  document.getElementById('gtin-panel').classList.add('hidden');
  document.getElementById('other-checks-panel').classList.remove('hidden');
  document.getElementById('gtin-result-badge').textContent = gtinResult;
  document.getElementById('gtin-result-badge').className = 'gtin-badge ' + (gtinResult.includes('PASS') ? 'pass' : 'fail');
  document.querySelectorAll('.issue-icon-btn').forEach(b => b.classList.remove('selected'));
  const noBtn = document.querySelector('[data-issue="no-issues"]');
  if (noBtn) noBtn.classList.add('selected');
  state.selectedIssue = 'no-issues';
}

function goBackToGtin() {
  document.getElementById('other-checks-panel').classList.add('hidden');
  document.getElementById('gtin-panel').classList.remove('hidden');
  document.getElementById('extra-issue-icons').classList.add('hidden');
  state.gtinScanned = false;
  state.brandTagNA = false;
  saveState();
}

function selectIssue(btn) {
  document.querySelectorAll('.issue-icon-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  state.selectedIssue = btn.dataset.issue;
  saveState();
}

// ===== CARTON MAPPING LOGIC =====
function getAssignedCarton(issue, radioValue) {
  // Check brand tag eligibility from current product
  const isEligible = state.currentProduct && state.currentProduct.eligible_brand_tag === 1;

  // Radio button selections (wrong product, damaged, fake) → QC Fail
  if (radioValue === 'wrong-product' || radioValue === 'damaged' || radioValue === 'fake') {
    return { carton: 'QC Fail Carton (STN)', qcResult: 'fail' };
  }

  // Standard mappings
  const cartonMap = {
    'no-issues':       { carton: 'QC Pass Carton (STN)', qcResult: 'pass' },
    'missing-part':    { carton: 'QC Fail Carton (STN)', qcResult: 'fail' },
    'defective':       { carton: 'QC Fail Carton (STN)', qcResult: 'fail' },
    'pattern-shade':   { carton: 'QC Fail Carton (STN)', qcResult: 'fail' },
    'stain-dirty':     { carton: 'Refinish Carton', qcResult: 'fail' },
    'stitching':       { carton: 'Refinish Carton', qcResult: 'fail' },
    'wrinkled':        { carton: 'Refinish Carton', qcResult: 'fail' },
    'sod-product':     { carton: 'QC Fail Carton (Non-STN)', qcResult: 'fail' },
    'sod-size':        { carton: 'QC Fail Carton (Non-STN)', qcResult: 'fail' },
  };

  // Exception rules based on brand tag eligibility
  if (issue === 'product-size') {
    return isEligible
      ? { carton: 'Refinish Carton', qcResult: 'fail' }
      : { carton: 'QC Fail Carton (STN)', qcResult: 'fail' };
  }
  if (issue === 'tag-mismatch') {
    return isEligible
      ? { carton: 'Refinish Carton', qcResult: 'fail' }
      : { carton: 'QC Fail Carton (STN)', qcResult: 'fail' };
  }
  if (issue === 'bt-shaded') {
    return isEligible
      ? { carton: 'Refinish Carton', qcResult: 'fail' }
      : { carton: 'QC Fail Carton (STN)', qcResult: 'fail' };
  }

  // "Return item not received" (from the button click) → QC Fail
  if (issue === 'return-not-received') {
    return { carton: 'QC Fail Carton (STN)', qcResult: 'fail' };
  }

  return cartonMap[issue] || { carton: 'On Hold Carton', qcResult: 'fail' };
}

// ===== QC CODE SCANNING (completes PV, records time) =====
async function handleQcScan(event) {
  if (event.key !== 'Enter') return;
  if (!document.getElementById('scan-qc-input').value.trim()) return;

  // Get selected radio value (wrong-product, damaged, fake) if any
  const selectedRadio = document.querySelector('input[name="issue-type"]:checked');
  const radioValue = selectedRadio ? selectedRadio.value : null;

  // Determine carton assignment
  const assignment = getAssignedCarton(state.selectedIssue, radioValue);
  state.qcResult = assignment.qcResult;
  const assignedCarton = assignment.carton;

  const gtinResult = state.gtinScanned ? 'PASS' : (state.brandTagNA ? 'FAIL' : 'PASS');

  // Complete PV via API
  if (state.currentLogId) {
    try {
      const res = await fetch(API + '/api/pv/complete', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          log_id: state.currentLogId,
          gtin_result: gtinResult,
          issue_selected: state.selectedIssue,
          qc_result: state.qcResult
        })
      });
      const data = await res.json();
      if (data.time_seconds) {
        showBanner('success', `Q1 — Time: ${data.time_seconds}s`);
      }
    } catch (e) { console.error(e); }
  }

  state.productsDone++;
  updateProductCounter();

  document.getElementById('other-checks-panel').classList.add('hidden');
  document.getElementById('gtin-panel').classList.add('hidden');
  document.getElementById('qc-result-panel').classList.remove('hidden');

  // Update result status display
  const statusEl = document.getElementById('result-status-display');
  if (state.qcResult === 'pass') {
    statusEl.textContent = '✅ Marked As QC Pass';
    statusEl.className = 'result-status pass';
    document.getElementById('qc-pass-badge-top').classList.remove('hidden');
    document.getElementById('status-badge').textContent = 'RPC';
    document.getElementById('status-badge').style.background = '#4caf50';
    if (!state.currentLogId) showBanner('success', 'Q1');
  } else if (assignedCarton.includes('Refinish')) {
    statusEl.textContent = '🔧 Marked As Refinish';
    statusEl.className = 'result-status refinish';
    document.getElementById('qc-pass-badge-top').classList.add('hidden');
  } else {
    statusEl.textContent = '❌ Marked As QC Fail';
    statusEl.className = 'result-status fail';
    document.getElementById('qc-pass-badge-top').classList.add('hidden');
  }

  // Update assigned carton name and color
  const cartonEl = document.getElementById('assigned-carton-name');
  const keepInCartonEl = cartonEl.closest('.keep-in-carton');
  cartonEl.textContent = assignedCarton;

  // Set carton box color
  keepInCartonEl.classList.remove('carton-pass', 'carton-fail', 'carton-refinish');
  if (assignedCarton.includes('Pass')) {
    keepInCartonEl.classList.add('carton-pass');
  } else if (assignedCarton.includes('Refinish')) {
    keepInCartonEl.classList.add('carton-refinish');
  } else {
    keepInCartonEl.classList.add('carton-fail');
  }

  state.step = 6;
  saveState();
}

// ===== BARCODE PRINT =====
function showBarcodePage() {
  document.getElementById('app-shell').classList.remove('active');
  // Update barcode with current product info
  if (state.currentProduct) {
    const p = state.currentProduct;
    document.querySelector('.sku-number').innerHTML = p.myntra_sku.slice(0, -2) + ' <span style="font-size:64px; margin-left:12px;">' + p.myntra_sku.slice(-2) + '</span>';
    document.querySelector('.size-info').innerHTML = `<span>${p.size}</span><span>${p.article_no}</span>`;
    document.querySelector('.id-info').innerHTML = `<span>${p.style_id}</span><span>${p.item_barcode}</span>`;
    
    // Generate real barcode using JsBarcode
    if (typeof JsBarcode !== 'undefined') {
      JsBarcode("#print-barcode-svg", p.item_barcode, {
        format: "CODE128",
        displayValue: false,
        height: 100,
        width: 3,
        margin: 0,
        lineColor: "#000"
      });
    }
  }
  showScreen('barcode-screen');
  setTimeout(() => window.print(), 500);
}
function closeBarcodePage() { showScreen('app-shell'); }

// ===== ITEM BARCODE SCAN (next product) =====
async function handleItemBarcodeScan(event) {
  if (event.key !== 'Enter') return;
  const input = document.getElementById('scan-item-barcode-input');
  if (!input.value.trim()) return;

  // Increment output carton count
  const cartonName = document.getElementById('assigned-carton-name').textContent;
  const keyMap = {
    'QC Pass Carton (STN)': 'pass',
    'QC Fail Carton (STN)': 'fail',
    'QC Fail Carton (Non-STN)': 'failnon',
    'Refinish Carton': 'refinish',
    'On Hold Carton': 'onhold'
  };
  const type = keyMap[cartonName];
  if (type) {
    if (!state.outputCartonCounts) state.outputCartonCounts = { pass: 0, fail: 0, failnon: 0, refinish: 0, onhold: 0 };
    state.outputCartonCounts[type]++;
    const countMap = { pass:'pass-count', fail:'fail-count', failnon:'failnon-count', refinish:'refinish-count', onhold:'onhold-count' };
    const cntEl = document.getElementById(countMap[type]);
    if (cntEl) cntEl.textContent = `(${state.outputCartonCounts[type]})`;
  }

  showBanner('success', 'Item processed! Ready for next item.');
  // Reset UI for next product
  document.getElementById('product-area').classList.add('hidden');
  document.getElementById('right-panel').classList.remove('show');
  document.getElementById('qc-result-panel').classList.add('hidden');
  document.getElementById('qc-pass-badge-top').classList.add('hidden');
  document.getElementById('extra-issue-icons').classList.add('hidden');
  ['scan-tracking-input','scan-return-input','scan-gtin-input','scan-qc-input'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  input.value = '';
  state.currentProduct = null; state.currentLogId = null;
  state.gtinScanned = false; state.brandTagNA = false;
  state.galleryImages = []; state.galleryIndex = 0;
  state.qcResult = ''; state.selectedIssue = 'no-issues';
  state.step = 3;
  saveState();
  setTimeout(() => document.getElementById('scan-tracking-input').focus(), 300);
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('warehouse-select').value = 'bilaspur';

  // Allow Enter key to submit login
  ['login-email', 'login-password'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
  });

  // Allow Enter key to submit registration
  ['reg-name', 'reg-email', 'reg-password'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') doRegister(); });
  });

  // Restore session if user is still logged in (survives page refresh)
  fetch(API + '/api/me')
    .then(res => { if (!res.ok) throw new Error('Not logged in'); return res.json(); })
    .then(data => {
      if (data.logged_in) {
        state.userId = data.user.id;
        state.sessionId = data.session_id;
        state.userEmail = data.user.email;
        state.userName = data.user.name;
        state.totalProducts = data.total_products || 50;
        document.getElementById('nav-user-email').textContent = state.userEmail;
        
        startSessionTimer();
        updateProductCounter();
        
        if (loadState()) {
          restoreUI();
        } else {
          showScreen('app-shell');
          setTimeout(() => showWarehouseModal(), 300);
        }
      }
    })
    .catch(() => { /* Not logged in, stay on login screen */ });

  // Setup drag-and-drop for CSV upload
  const dropZone = document.getElementById('csv-drop-zone');
  if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file && file.name.endsWith('.csv')) {
        const input = document.getElementById('product-csv-upload');
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        handleProductCSVSelect(input);
      } else {
        alert('Please drop a CSV file.');
      }
    });
  }
});

// ===== ADD PRODUCTS — Admin CSV Upload Functions =====

let selectedProductCSV = null;

function toggleAdminPassword() {
  const p = document.getElementById('admin-password');
  p.type = p.type === 'password' ? 'text' : 'password';
}

function handleProductCSVSelect(input) {
  const file = input.files[0];
  if (!file) return;
  selectedProductCSV = file;
  document.getElementById('upload-file-info').classList.remove('hidden');
  document.getElementById('upload-file-name').textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
}

function clearProductCSV() {
  selectedProductCSV = null;
  document.getElementById('product-csv-upload').value = '';
  document.getElementById('upload-file-info').classList.add('hidden');
  document.getElementById('upload-file-name').textContent = '—';
}

async function loadProductCount() {
  try {
    const res = await fetch(API + '/api/admin/products/count');
    const data = await res.json();
    document.getElementById('ap-product-count').textContent = data.total_products || 0;
  } catch (e) {
    document.getElementById('ap-product-count').textContent = '—';
  }
}

async function uploadProductCSV() {
  const username = document.getElementById('admin-username').value.trim();
  const password = document.getElementById('admin-password').value.trim();
  const resultEl = document.getElementById('upload-result');
  const btn = document.getElementById('btn-upload-products');

  // Validate inputs
  if (!username || !password) {
    showUploadResult('error', 'Authentication Required', 'Please enter admin username and password.');
    return;
  }
  if (!selectedProductCSV) {
    showUploadResult('error', 'No File Selected', 'Please select a CSV file to upload.');
    return;
  }

  // Disable button
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Uploading...';

  try {
    const formData = new FormData();
    formData.append('admin_username', username);
    formData.append('admin_password', password);
    formData.append('file', selectedProductCSV);

    const res = await fetch(API + '/api/admin/products/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (data.success) {
      let body = '<span class="result-stat created">✓ ' + data.created + ' products created</span>';
      body += '<span class="result-stat total">📦 Total in CSV: ' + data.total_in_csv + '</span>';
      if (data.errors && data.errors.length > 0) {
        body += '<span class="result-stat errors">⚠ ' + data.errors.length + ' errors</span>';
        body += '<div class="result-errors-list">';
        data.errors.forEach(e => { body += '<div>• ' + e + '</div>'; });
        body += '</div>';
      }
      body += '<br><br>New total products in database: <strong>' + data.new_total_products + '</strong>';
      showUploadResult('success', 'Products Added Successfully!', body);
      document.getElementById('ap-product-count').textContent = data.new_total_products;
      clearProductCSV();
    } else {
      showUploadResult('error', 'Upload Failed', data.error || 'Unknown error occurred.');
    }
  } catch (e) {
    showUploadResult('error', 'Server Error', 'Could not connect to server. Make sure the server is running (python server.py).');
  }

  // Re-enable button
  btn.disabled = false;
  btn.innerHTML = '<span class="btn-icon">⬆</span> Upload & Add Products';
}

function showUploadResult(type, title, bodyHtml) {
  const el = document.getElementById('upload-result');
  el.className = 'add-products-result ' + type;
  el.classList.remove('hidden');
  document.getElementById('upload-result-icon').textContent = type === 'success' ? '✅' : '❌';
  document.getElementById('upload-result-title').textContent = title;
  document.getElementById('upload-result-body').innerHTML = bodyHtml;
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function deleteProductByTrackingId() {
  const username = document.getElementById('admin-username').value.trim();
  const password = document.getElementById('admin-password').value.trim();
  const trackingId = document.getElementById('delete-tracking-id').value.trim();
  
  const resultEl = document.getElementById('delete-result');
  const resultTitle = document.getElementById('delete-result-title');
  const resultBody = document.getElementById('delete-result-body');
  const resultIcon = document.getElementById('delete-result-icon');
  
  if (!username || !password) {
    resultEl.className = 'add-products-result error';
    resultEl.classList.remove('hidden');
    resultIcon.textContent = '❌';
    resultTitle.textContent = 'Authentication Required';
    resultTitle.style.color = '#c62828';
    resultBody.innerHTML = 'Please enter admin username and password.';
    return;
  }
  if (!trackingId) {
    resultEl.className = 'add-products-result error';
    resultEl.classList.remove('hidden');
    resultIcon.textContent = '❌';
    resultTitle.textContent = 'Tracking ID Required';
    resultTitle.style.color = '#c62828';
    resultBody.innerHTML = 'Please enter a Tracking ID.';
    return;
  }
  
  try {
    const res = await fetch(API + '/api/admin/products/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_username: username, admin_password: password, tracking_id: trackingId })
    });
    const data = await res.json();
    
    resultEl.classList.remove('hidden');
    if (data.success) {
      resultEl.className = 'add-products-result success';
      resultEl.style.background = '#e8f5e9';
      resultEl.style.borderColor = '#a5d6a7';
      resultIcon.textContent = '✅';
      resultTitle.textContent = 'Delete Successful';
      resultTitle.style.color = '#2e7d32';
      resultBody.innerHTML = data.message;
      resultBody.style.color = '#1b5e20';
      document.getElementById('ap-product-count').textContent = data.new_total_products;
      document.getElementById('delete-tracking-id').value = '';
    } else {
      resultEl.className = 'add-products-result error';
      resultEl.style.background = '#ffebee';
      resultEl.style.borderColor = '#ef9a9a';
      resultIcon.textContent = '❌';
      resultTitle.textContent = 'Delete Failed';
      resultTitle.style.color = '#c62828';
      resultBody.innerHTML = data.error || 'Unknown error occurred.';
      resultBody.style.color = '#b71c1c';
    }
  } catch (e) {
    resultEl.className = 'add-products-result error';
    resultEl.classList.remove('hidden');
    resultIcon.textContent = '❌';
    resultTitle.textContent = 'Server Error';
    resultTitle.style.color = '#c62828';
    resultBody.innerHTML = 'Could not connect to server.';
  }
}

