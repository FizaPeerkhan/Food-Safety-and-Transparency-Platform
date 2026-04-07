// API Configuration
const API_URL = 'http://127.0.0.1:5000';
let currentIngredients = '';

// ==================== UTILITY FUNCTIONS ====================
function showToast(message, type = 'success', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `position:fixed; bottom:24px; right:24px; z-index:10000; display:flex; flex-direction:column; gap:10px; pointer-events:none;`;
    document.body.appendChild(container);
  }
  
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
  const colors = { success: '#1e9e5e', error: '#ef4444', warning: '#f59e0b', info: '#3b82f6' };
  
  const toast = document.createElement('div');
  toast.style.cssText = `display:flex; align-items:center; gap:12px; padding:14px 20px; border-radius:14px; background:#1f2937; color:white; font-size:0.875rem; font-weight:500; box-shadow:0 8px 28px rgba(0,0,0,0.2); pointer-events:auto; animation:slideIn 0.3s ease both; border-left:4px solid ${colors[type]}; max-width:380px;`;
  toast.innerHTML = `<span style="color:${colors[type]}; font-size:1.1rem;">${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Add animation style
if (!document.querySelector('#toast-style')) {
  const style = document.createElement('style');
  style.id = 'toast-style';
  style.textContent = `@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`;
  document.head.appendChild(style);
}

// ==================== AUTHENTICATION FUNCTIONS ====================

async function checkAuthState() {
  try {
    const response = await fetch(`${API_URL}/api/me`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    const adminInfo = document.getElementById('adminInfo');
    const userInfo = document.getElementById('userInfo');
    const authButtons = document.getElementById('authButtons');
    const mobileAuthLinks = document.getElementById('mobileAuthLinks');
    
    if (data.authenticated) {
      const user = data.user;
      
      if (user.role === 'admin') {
        if (adminInfo) adminInfo.style.display = 'flex';
        if (userInfo) userInfo.style.display = 'none';
        if (authButtons) authButtons.style.display = 'none';
        if (mobileAuthLinks) {
          mobileAuthLinks.innerHTML = '<a href="#" onclick="logout()" class="nav-link">👑 Logout</a>';
        }
        if (document.getElementById('adminName')) {
          document.getElementById('adminName').textContent = user.username;
        }
      } else {
        if (adminInfo) adminInfo.style.display = 'none';
        if (userInfo) userInfo.style.display = 'flex';
        if (authButtons) authButtons.style.display = 'none';
        if (mobileAuthLinks) {
          mobileAuthLinks.innerHTML = '<a href="#" onclick="logout()" class="nav-link">Logout</a>';
        }
        if (document.getElementById('userName')) {
          document.getElementById('userName').textContent = user.username;
        }
        if (document.getElementById('userAvatar')) {
          document.getElementById('userAvatar').textContent = user.username?.charAt(0).toUpperCase() || 'U';
        }
      }
    } else {
      if (adminInfo) adminInfo.style.display = 'none';
      if (userInfo) userInfo.style.display = 'none';
      if (authButtons) authButtons.style.display = 'flex';
      if (mobileAuthLinks) {
        mobileAuthLinks.innerHTML = '<a href="login.html" class="nav-link">Login</a><a href="signup.html" class="nav-link">Sign Up</a>';
      }
    }
  } catch (error) {
    console.error('Auth check failed:', error);
    const authButtons = document.getElementById('authButtons');
    if (authButtons) authButtons.style.display = 'flex';
  }
}

async function logout() {
  try {
    await fetch(`${API_URL}/api/logout`, {
      method: 'POST',
      credentials: 'include'
    });
  } catch (error) {
    console.error('Logout error:', error);
  }
  window.location.href = 'index.html';
}

// ==================== NAVIGATION ====================
function initNav() {
  const nav = document.querySelector('.nav');
  const burger = document.querySelector('.nav-burger');
  const mobile = document.querySelector('.nav-mobile');
  
  if (nav) window.addEventListener('scroll', () => nav.classList.toggle('scrolled', window.scrollY > 12));
  if (burger && mobile) {
    burger.addEventListener('click', () => {
      mobile.classList.toggle('open');
      const spans = burger.querySelectorAll('span');
      const isOpen = mobile.classList.contains('open');
      if (spans[0]) spans[0].style.transform = isOpen ? 'rotate(45deg) translate(5px,5px)' : '';
      if (spans[1]) spans[1].style.opacity = isOpen ? '0' : '1';
      if (spans[2]) spans[2].style.transform = isOpen ? 'rotate(-45deg) translate(5px,-5px)' : '';
    });
  }
  
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === path) link.classList.add('active');
  });
}

// ==================== DASHBOARD ====================
const DASHBOARD_PRODUCTS = [
  { id: 'p1', name: 'Classic Milk', brand: 'DairyPure', category: 'Dairy', riskLevel: 'low', riskScore: 12, status: 'safe', image: '🥛', ingredients: ['Whole Milk', 'Vitamin D3'] },
  { id: 'p2', name: 'Refined Honey', brand: 'GoldenHive', category: 'Sweetener', riskLevel: 'medium', riskScore: 54, status: 'flagged', image: '🍯', ingredients: ['Honey', 'High Fructose Corn Syrup'] },
  { id: 'p3', name: 'Extra Virgin Olive Oil', brand: 'MediterraOil', category: 'Oils', riskLevel: 'low', riskScore: 8, status: 'safe', image: '🫒', ingredients: ['Cold-Pressed Olive Oil'] },
  { id: 'p4', name: 'Instant Noodles', brand: 'QuickBite', category: 'Processed', riskLevel: 'high', riskScore: 81, status: 'adulterated', image: '🍜', ingredients: ['Wheat Flour', 'Palm Oil', 'MSG', 'TBHQ'] },
  { id: 'p5', name: 'Organic Turmeric', brand: 'SpiceRoot', category: 'Spices', riskLevel: 'medium', riskScore: 47, status: 'flagged', image: '🌿', ingredients: ['Turmeric', 'Metanil Yellow (trace)'] }
];

function initDashboard() {
  if (!document.getElementById('dashboard-page')) return;
  
  const grid = document.getElementById('product-grid');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const searchInput = document.getElementById('dash-search');
  let flaggedReports = [];
  
  function getRiskColor(level) { 
    return { low: 'var(--green-500)', medium: 'var(--amber-500)', high: 'var(--red-500)' }[level]; 
  }
  
  function getStatusBadge(status) {
    const map = { 
      safe: { cls: 'badge-safe', label: 'Safe' }, 
      flagged: { cls: 'badge-caution', label: 'Flagged' }, 
      adulterated: { cls: 'badge-danger', label: 'Adulterated' },
      'Under Review': { cls: 'badge-caution', label: 'Under Review' },
      'Resolved': { cls: 'badge-safe', label: 'Resolved' }
    };
    return map[status] || { cls: 'badge-info', label: status || 'Unknown' };
  }
  
  async function fetchFlaggedReports() {
    try {
      const response = await fetch(`${API_URL}/flagged-products`);
      const data = await response.json();
      if (data.products) {
        flaggedReports = data.products;
        renderProducts();
      }
    } catch (error) {
      console.error('Error fetching flagged reports:', error);
    }
  }
  
  function renderProducts(filter = 'all', query = '') {
    if (!grid) return;
    let displayProducts = [...DASHBOARD_PRODUCTS];
    
    flaggedReports.forEach(report => {
      displayProducts.push({
        id: `report_${report.id}`,
        name: report.product_name,
        brand: report.brand,
        category: report.category || 'Reported',
        riskLevel: report.severity === 'high' ? 'high' : (report.severity === 'medium' ? 'medium' : 'low'),
        riskScore: report.severity === 'high' ? 85 : (report.severity === 'medium' ? 55 : 30),
        status: report.status === 'Under Review' ? 'flagged' : (report.status === 'Resolved' ? 'safe' : 'adulterated'),
        image: '⚠️',
        ingredients: [report.issue_type || 'Reported Issue'],
        isReport: true,
        reportId: report.id,
        description: report.description
      });
    });
    
    let list = displayProducts;
    if (filter !== 'all') list = list.filter(p => p.status === filter || p.riskLevel === filter);
    if (query) list = list.filter(p => p.name.toLowerCase().includes(query) || p.brand.toLowerCase().includes(query));
    
    grid.innerHTML = list.map(p => {
      const badge = getStatusBadge(p.status);
      const color = getRiskColor(p.riskLevel);
      const isReport = p.isReport ? true : false;
      
      return `<div class="prod-card card" data-id="${p.id}" data-is-report="${isReport}" data-report-id="${p.reportId || ''}" style="cursor: pointer;">
        <div class="prod-card-accent" style="background: linear-gradient(135deg, ${color}22, ${color}08);"></div>
        <div class="prod-card-body">
          <div class="prod-card-top">
            <span class="prod-card-emoji">${p.image}</span>
            <span class="badge ${badge.cls}">${badge.label}</span>
          </div>
          <div>
            <h3 class="prod-card-name">${escapeHtml(p.name)}</h3>
            <p class="prod-card-brand">${escapeHtml(p.brand)} · ${p.category}</p>
          </div>
          <div class="prod-card-meter">
            <div class="risk-meter risk-${p.riskLevel}">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-size:.75rem;">Risk Score</span>
                <span style="font-family:monospace;">${p.riskScore}/100</span>
              </div>
              <div class="risk-meter-bar">
                <div class="risk-meter-fill" style="width:${p.riskScore}%;background:${color};"></div>
              </div>
            </div>
          </div>
          <div class="prod-card-pills">
            ${p.ingredients.slice(0,2).map(i => `<span class="ingredient-pill pill-neutral">${escapeHtml(i)}</span>`).join('')}
          </div>
          ${isReport ? `<div style="margin-top:8px; font-size:0.7rem; color:var(--red-500);">⚠️ User Reported</div>` : ''}
        </div>
      </div>`;
    }).join('');
    
    document.querySelectorAll('.prod-card').forEach(card => {
      card.addEventListener('click', () => {
        const isReport = card.dataset.isReport === 'true';
        if (isReport) {
          const reportId = card.dataset.reportId;
          const report = flaggedReports.find(r => r.id == reportId);
          if (report) showReportDetails(report);
        } else {
          window.location.href = `check-product.html?id=${card.dataset.id}`;
        }
      });
    });
  }
  
  function showReportDetails(report) {
    const evidenceHtml = report.evidence_path ? `
      <div style="margin-top:12px;">
        <strong>Evidence Image:</strong><br>
        <img src="/${report.evidence_path}" style="max-width:100%; border-radius:8px; margin-top:8px;" onclick="window.open(this.src)" />
      </div>
    ` : '';
    
    const modalHtml = `
      <div id="reportModal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;">
        <div style="background:white;border-radius:24px;max-width:500px;width:90%;max-height:80vh;overflow-y:auto;padding:24px;">
          <h3 style="margin-bottom:16px;color:var(--red-500);">⚠️ User Report</h3>
          <div style="margin-bottom:12px;">
            <strong>Product:</strong> ${escapeHtml(report.product_name)}<br>
            <strong>Brand:</strong> ${escapeHtml(report.brand)}<br>
            <strong>Issue:</strong> ${escapeHtml(report.issue_type || 'Not specified')}<br>
            <strong>Severity:</strong> <span style="color:${report.severity === 'high' ? 'red' : (report.severity === 'medium' ? 'orange' : 'green')}">${report.severity}</span><br>
            <strong>Status:</strong> ${escapeHtml(report.status)}<br>
            <strong>Reported by:</strong> ${escapeHtml(report.reporter_name || 'Anonymous')}
          </div>
          ${evidenceHtml}
          <div style="margin-bottom:12px;padding:12px;background:#f7fafc;border-radius:8px;">
            <strong>Description:</strong><br>
            ${escapeHtml(report.description)}
          </div>
          <button class="btn btn-primary" style="width:100%;" onclick="document.getElementById('reportModal')?.remove()">Close</button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
  }
  
  let currentFilter = 'all', currentQuery = '';
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderProducts(currentFilter, currentQuery);
    });
  });
  
  if (searchInput) {
    searchInput.addEventListener('input', e => { 
      currentQuery = e.target.value.toLowerCase().trim(); 
      renderProducts(currentFilter, currentQuery); 
    });
  }
  
  fetchFlaggedReports();
  renderProducts();
}

// ==================== CHECK PRODUCT PAGE ====================
function initCheckProduct() {
  if (!document.getElementById('check-page')) return;
  
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.dataset.tab;
      panels.forEach(p => p.style.display = p.id === `tab-${target}` ? 'block' : 'none');
    });
  });
  
  const searchBtn = document.getElementById('search-btn');
  const searchInput = document.getElementById('product-search-input');
  const resultArea = document.getElementById('search-result');
  
  async function doSearch() {
    const query = searchInput?.value.trim();
    if (!query) { showToast('Please enter a product name', 'warning'); return; }
    resultArea.innerHTML = '<div style="text-align:center;padding:40px;">⏳ Searching database...</div>';
    
    try {
      const response = await fetch(`${API_URL}/search?name=${encodeURIComponent(query)}`);
      const data = await response.json();
      if (data.error) { resultArea.innerHTML = `<div class="card" style="padding:32px;"><p style="color:var(--red-500);">${data.error}</p></div>`; showToast(data.error, 'error'); return; }
      currentIngredients = data.product.ingredients_text;
      renderSearchResult(data, resultArea);
      showToast(`✅ Found "${data.product.product_name}"`, 'success');
    } catch (error) {
      resultArea.innerHTML = `<div class="card" style="padding:32px;"><p style="color:var(--red-500);">❌ Cannot connect to server. Make sure Flask is running on port 5000</p></div>`;
      showToast('Cannot connect to backend server', 'error');
    }
  }
  
  if (searchBtn) searchBtn.addEventListener('click', doSearch);
  if (searchInput) searchInput.addEventListener('keypress', e => { if (e.key === 'Enter') doSearch(); });
  
  document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => { if (searchInput) { searchInput.value = chip.dataset.val; doSearch(); } });
  });
  
  initUploadTab();
  initClaimsTab();
}

function renderSearchResult(data, container) {
  const riskIcon = { High: '🔴', Moderate: '🟡', Low: '🟢' }[data.overall_risk] || '⚪';
  const riskColor = data.overall_risk === 'High' ? 'var(--red-500)' : (data.overall_risk === 'Moderate' ? 'var(--amber-500)' : 'var(--green-500)');
  const riskScore = data.overall_risk === 'High' ? 85 : (data.overall_risk === 'Moderate' ? 55 : 20);
  
  const hiSet = new Set((data.high_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
  const moSet = new Set((data.moderate_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
  
  let ingredientTags = '';
  let ingredientsList = [];
  
  if (data.all_ingredients && data.all_ingredients.length > 0) {
    ingredientsList = data.all_ingredients;
  } else {
    const rawIngredients = data.product.ingredients_text.split(',').map(x => ({ name: x.trim() }));
    ingredientsList = rawIngredients;
  }
  
  ingredientsList.forEach(i => {
    const name = i.name || i;
    const isHigh = hiSet.has(name.toLowerCase());
    const isMod = moSet.has(name.toLowerCase());
    const isInfo = i.risk_level === 'Info' || i.is_debunked === true;
    
    let tagClass = 'ingredient-tag';
    if (isInfo) tagClass += ' tag-info';
    else if (isHigh) tagClass += ' tag-high';
    else if (isMod) tagClass += ' tag-moderate';
    else tagClass += ' tag-safe';
    
    const title = i.explanation || i.category || '';
    ingredientTags += `<span class="${tagClass}" title="${escapeHtml(title)}">${escapeHtml(name)}</span>`;
  });
  
  let highRiskHtml = '';
  if (data.high_risk_ingredients?.length) {
    highRiskHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--red-500);">🔴 High Risk Ingredients</p>${data.high_risk_ingredients.map(i => `<div style="padding:12px;background:#fff5f5;border-left:3px solid #e53e3e;border-radius:8px;margin-bottom:8px;"><strong>⚠️ ${escapeHtml(i.ingredient)}</strong><br><span style="font-size:0.85rem;">${escapeHtml(i.explanation || i.reason)}</span><br><small style="color:#c53030;">Avoid if you have: ${escapeHtml(i.caution_for)}</small></div>`).join('')}</div>`;
  }
  
  let moderateRiskHtml = '';
  if (data.moderate_risk_ingredients?.length) {
    moderateRiskHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--amber-500);">🟡 Moderate Risk Ingredients</p>${data.moderate_risk_ingredients.map(i => `<div style="padding:12px;background:#fffaf0;border-left:3px solid #ed8936;border-radius:8px;margin-bottom:8px;"><strong>⚠️ ${escapeHtml(i.ingredient)}</strong><br><span style="font-size:0.85rem;">${escapeHtml(i.explanation || i.reason)}</span></div>`).join('')}</div>`;
  }
  
  let allergenHtml = '';
  if (data.allergens?.length) {
    allergenHtml = `<div style="margin-top:20px;background:#fff3cd;border:1px solid #fcd34d;border-radius:8px;padding:12px;"><strong>⚠️ Allergens Detected:</strong><br>${data.allergens.map(a => `<span style="display:inline-block;background:#fff;border:1px solid #fcd34d;border-radius:20px;padding:3px 10px;margin:3px;">${escapeHtml(a)}</span>`).join('')}</div>`;
  }
  
  let warningsHtml = '';
  if (data.health_warnings?.length) {
    warningsHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--red-500);">🏥 Who Should Be Careful</p>${data.health_warnings.map(w => `<div style="padding:10px 12px;background:#fff7ed;border-radius:8px;margin-bottom:6px;">⚠️ ${escapeHtml(w)}</div>`).join('')}</div>`;
  }
  
  let insHtml = '';
  if (data.ins_numbers?.length) {
    insHtml = `<div style="margin-top:20px;background:#ebf8ff;border-radius:8px;padding:12px;"><strong>🔬 INS / E-Numbers:</strong><br>${data.ins_numbers.map(i => `<span style="display:inline-block;background:#bee3f8;border-radius:20px;padding:3px 10px;margin:3px;">${escapeHtml(i.code)} — ${escapeHtml(i.name)}</span>`).join('')}</div>`;
  }
  
  container.innerHTML = `
    <div class="result-card card" style="margin-top:28px;">
      <div class="result-header" style="background:linear-gradient(135deg, ${riskColor}18, ${riskColor}06); padding:28px 32px; border-bottom:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;">
          <div>
            <h2 style="font-size:1.6rem;font-weight:400;">${escapeHtml(data.product.product_name)}</h2>
            <p style="color:var(--text-muted);">${escapeHtml(data.product.brand)}</p>
          </div>
          <div style="text-align:right;">
            <div style="margin-bottom:8px;">
              <span style="font-size:0.75rem;">Overall Risk</span>
              <div style="width:180px;height:8px;background:#e2e8f0;border-radius:10px;margin-top:4px;">
                <div style="width:${riskScore}%;height:100%;background:${riskColor};border-radius:10px;"></div>
              </div>
            </div>
            <span class="badge" style="background:${riskColor}22;color:${riskColor};border:1px solid ${riskColor}44;">${riskIcon} ${data.overall_risk} Risk</span>
          </div>
        </div>
      </div>
      <div class="result-body" style="padding:28px 32px;">
        <div>
          <p class="label-upper">📋 Ingredients</p>
          <div style="display:flex;flex-wrap:wrap;gap:8px;">${ingredientTags}</div>
        </div>
        ${highRiskHtml}
        ${moderateRiskHtml}
        ${allergenHtml}
        ${warningsHtml}
        ${insHtml}
        <div style="margin-top: 24px; border-top: 1px solid var(--border); padding-top: 20px;">
          <button class="btn btn-primary" style="width: 100%;" onclick="showInlineClaimVerification()">
            🏷️ Verify Marketing Claims for this Product
          </button>
        </div>
      </div>
    </div>
  `;
}

// ==================== CLAIMS VERIFICATION ====================
function showInlineClaimVerification() {
  const claimHtml = `
    <div id="inlineClaimBox" style="margin-top: 20px; padding: 20px; background: var(--stone-100); border-radius: var(--r-lg);">
      <h4 style="margin-bottom: 12px;">🏷️ Verify Marketing Claims</h4>
      <textarea id="inlineClaimsInput" rows="3" style="width: 100%; padding: 12px; border-radius: var(--r-md); border: 1px solid var(--border);" placeholder="Enter claims one per line&#10;e.g., No Added Sugar&#10;Gluten Free&#10;All Natural"></textarea>
      <div style="display: flex; gap: 10px; margin-top: 12px;">
        <button class="btn btn-primary" style="flex: 1;" onclick="verifyInlineClaims()">Verify Claims</button>
        <button class="btn btn-outline" style="flex: 1;" onclick="document.getElementById('inlineClaimBox')?.remove()">Cancel</button>
      </div>
      <div id="inlineClaimResult" style="margin-top: 12px;"></div>
    </div>
  `;
  
  const existingBox = document.getElementById('inlineClaimBox');
  if (existingBox) existingBox.remove();
  
  const verifyButton = document.querySelector('.btn-primary[onclick="showInlineClaimVerification()"]');
  if (verifyButton) {
    verifyButton.insertAdjacentHTML('afterend', claimHtml);
  } else {
    const results = document.getElementById('search-result');
    if (results) results.insertAdjacentHTML('beforeend', claimHtml);
  }
}

async function verifyInlineClaims() {
  const claimsInput = document.getElementById('inlineClaimsInput');
  const claims = claimsInput.value.split('\n').filter(c => c.trim());
  const resultDiv = document.getElementById('inlineClaimResult');
  
  if (!claims.length) {
    resultDiv.innerHTML = '<p style="color: var(--red-500);">Please enter at least one claim</p>';
    return;
  }
  
  resultDiv.innerHTML = '<p>⏳ Verifying...</p>';
  
  try {
    const response = await fetch(`${API_URL}/verify-claims`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claims, ingredients_text: currentIngredients })
    });
    
    const data = await response.json();
    
    let html = `<div style="margin-top: 8px;"><strong>${data.verdict}</strong></div>`;
    data.results.forEach(r => {
      const color = r.status === 'Verified' ? '#48bb78' : (r.status === 'Misleading' ? '#f56565' : '#ed8936');
      html += `<div style="margin-top: 8px; padding: 10px; background: white; border-radius: 8px; border-left: 3px solid ${color};">
        <strong>${r.status === 'Verified' ? '✅' : (r.status === 'Misleading' ? '❌' : 'ℹ️')} ${escapeHtml(r.claim)}</strong>
        <p style="font-size: 0.8rem; margin-top: 4px;">${escapeHtml(r.message)}</p>
        ${r.violating_ingredients?.length ? `<small style="color: #c53030;">Found: ${r.violating_ingredients.join(', ')}</small>` : ''}
      </div>`;
    });
    resultDiv.innerHTML = html;
    showToast('Claim verification complete!', 'success');
  } catch (error) {
    resultDiv.innerHTML = '<p style="color: var(--red-500);">Verification failed</p>';
    showToast('Verification failed', 'error');
  }
}

// ==================== UPLOAD TAB (OCR) ====================
function initUploadTab() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('file-input');
  const browseBtn = document.getElementById('browse-btn');
  const extractedArea = document.getElementById('extracted-ingredients');
  const analyzeBtn = document.getElementById('analyze-upload-btn');
  const textarea = document.getElementById('extracted-text');
  const uploadResultDiv = document.getElementById('upload-result');
  
  if (!zone) return;
  
  if (browseBtn) browseBtn.addEventListener('click', () => fileInput?.click());
  if (fileInput) fileInput.addEventListener('change', e => handleFileSelect(e.target.files[0]));
  
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => { 
    e.preventDefault(); 
    zone.classList.remove('drag-over'); 
    handleFileSelect(e.dataTransfer.files[0]); 
  });
  
  async function handleFileSelect(file) {
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp', 'image/jpg'].includes(file.type)) { 
      showToast('Please upload an image (JPG, PNG, WebP)', 'error'); 
      return; 
    }
    zone.innerHTML = `<div style="text-align:center;"><div style="font-size:2rem;">📷</div><p style="font-weight:500;">${escapeHtml(file.name)}</p><p style="font-size:0.8rem;">${(file.size/1024).toFixed(1)} KB</p></div>`;
    showToast('Processing image with OCR...', 'info');
    if (analyzeBtn) { 
      analyzeBtn.disabled = true; 
      analyzeBtn.textContent = '⏳ Extracting...'; 
    }
    const formData = new FormData(); 
    formData.append('image', file);
    try {
      const response = await fetch(`${API_URL}/ocr`, { method: 'POST', body: formData });
      const data = await response.json();
      if (data.error) { 
        showToast(data.error, 'error'); 
        if (textarea) textarea.value = `Error: ${data.error}`; 
      } else { 
        if (textarea) textarea.value = data.extracted_text; 
        if (extractedArea) extractedArea.style.display = 'block'; 
        showToast('✅ Text extracted! Click "Analyze" to continue.', 'success'); 
        if (analyzeBtn) { 
          analyzeBtn.disabled = false; 
          analyzeBtn.textContent = '🔬 Analyze Ingredients'; 
        } 
      }
    } catch (error) { 
      showToast('OCR failed. Please try again.', 'error'); 
      if (textarea) textarea.value = 'OCR failed.'; 
    }
  }
  
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', async () => {
      const text = textarea?.value;
      if (!text) { 
        showToast('No ingredients extracted', 'warning'); 
        return; 
      }
      analyzeBtn.disabled = true; 
      analyzeBtn.textContent = '⏳ Analyzing...';
      try {
        const response = await fetch(`${API_URL}/analyze-ingredients`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ingredients_text: text })
        });
        const data = await response.json();
        
        const displayData = {
          product: { product_name: 'OCR Extracted', brand: 'Uploaded Label', ingredients_text: text },
          ...data
        };
        
        renderOCRResult(displayData, uploadResultDiv);
        showToast('✅ Analysis complete!', 'success');
      } catch (error) { 
        showToast('Analysis failed', 'error'); 
      } finally { 
        analyzeBtn.disabled = false; 
        analyzeBtn.textContent = '🔬 Analyze Ingredients'; 
      }
    });
  }
}

function renderOCRResult(data, container) {
  const riskIcon = { High: '🔴', Moderate: '🟡', Low: '🟢' }[data.overall_risk] || '⚪';
  const riskColor = data.overall_risk === 'High' ? 'var(--red-500)' : (data.overall_risk === 'Moderate' ? 'var(--amber-500)' : 'var(--green-500)');
  const riskScore = data.overall_risk === 'High' ? 85 : (data.overall_risk === 'Moderate' ? 55 : 20);
  
  const hiSet = new Set((data.high_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
  const moSet = new Set((data.moderate_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
  
  let ingredientTags = '';
  let ingredientsList = [];
  
  if (data.all_ingredients && data.all_ingredients.length > 0) {
    ingredientsList = data.all_ingredients;
  } else {
    const rawIngredients = data.product.ingredients_text.split(',').map(x => ({ name: x.trim() }));
    ingredientsList = rawIngredients;
  }
  
  ingredientsList.forEach(i => {
    const name = i.name || i;
    const isHigh = hiSet.has(name.toLowerCase());
    const isMod = moSet.has(name.toLowerCase());
    const isInfo = i.risk_level === 'Info' || i.is_debunked === true;
    
    let tagClass = 'ingredient-tag';
    if (isInfo) tagClass += ' tag-info';
    else if (isHigh) tagClass += ' tag-high';
    else if (isMod) tagClass += ' tag-moderate';
    
    const title = i.explanation || i.category || '';
    ingredientTags += `<span class="${tagClass}" title="${escapeHtml(title)}">${escapeHtml(name)}</span>`;
  });
  
  let highRiskHtml = '';
  if (data.high_risk_ingredients?.length) {
    highRiskHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--red-500);">🔴 High Risk Ingredients</p>${data.high_risk_ingredients.map(i => `<div style="padding:12px;background:#fff5f5;border-left:3px solid #e53e3e;border-radius:8px;margin-bottom:8px;"><strong>⚠️ ${escapeHtml(i.ingredient)}</strong><br><span style="font-size:0.85rem;">${escapeHtml(i.explanation || i.reason)}</span><br><small style="color:#c53030;">Avoid if you have: ${escapeHtml(i.caution_for)}</small></div>`).join('')}</div>`;
  }
  
  let moderateRiskHtml = '';
  if (data.moderate_risk_ingredients?.length) {
    moderateRiskHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--amber-500);">🟡 Moderate Risk Ingredients</p>${data.moderate_risk_ingredients.map(i => `<div style="padding:12px;background:#fffaf0;border-left:3px solid #ed8936;border-radius:8px;margin-bottom:8px;"><strong>⚠️ ${escapeHtml(i.ingredient)}</strong><br><span style="font-size:0.85rem;">${escapeHtml(i.explanation || i.reason)}</span></div>`).join('')}</div>`;
  }
  
  let allergenHtml = '';
  if (data.allergens?.length) {
    allergenHtml = `<div style="margin-top:20px;background:#fff3cd;border:1px solid #fcd34d;border-radius:8px;padding:12px;"><strong>⚠️ Allergens Detected:</strong><br>${data.allergens.map(a => `<span style="display:inline-block;background:#fff;border:1px solid #fcd34d;border-radius:20px;padding:3px 10px;margin:3px;">${escapeHtml(a)}</span>`).join('')}</div>`;
  }
  
  let warningsHtml = '';
  if (data.health_warnings?.length) {
    warningsHtml = `<div style="margin-top:20px;"><p class="label-upper" style="color:var(--red-500);">🏥 Who Should Be Careful</p>${data.health_warnings.map(w => `<div style="padding:10px 12px;background:#fff7ed;border-radius:8px;margin-bottom:6px;">⚠️ ${escapeHtml(w)}</div>`).join('')}</div>`;
  }
  
  let insHtml = '';
  if (data.ins_numbers?.length) {
    insHtml = `<div style="margin-top:20px;background:#ebf8ff;border-radius:8px;padding:12px;"><strong>🔬 INS / E-Numbers:</strong><br>${data.ins_numbers.map(i => `<span style="display:inline-block;background:#bee3f8;border-radius:20px;padding:3px 10px;margin:3px;">${escapeHtml(i.code)} — ${escapeHtml(i.name)}</span>`).join('')}</div>`;
  }
  
  container.innerHTML = `
    <div class="result-card card" style="margin-top:20px;">
      <div class="result-header" style="background:linear-gradient(135deg, ${riskColor}18, ${riskColor}06); padding:20px 24px; border-bottom:1px solid var(--border);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;">
          <div>
            <h2 style="font-size:1.3rem;font-weight:400;">${escapeHtml(data.product.product_name)}</h2>
            <p style="color:var(--text-muted);">${escapeHtml(data.product.brand)}</p>
          </div>
          <div style="text-align:right;">
            <div style="margin-bottom:8px;">
              <span style="font-size:0.7rem;">Overall Risk</span>
              <div style="width:140px;height:6px;background:#e2e8f0;border-radius:10px;margin-top:4px;">
                <div style="width:${riskScore}%;height:100%;background:${riskColor};border-radius:10px;"></div>
              </div>
            </div>
            <span class="badge" style="background:${riskColor}22;color:${riskColor};border:1px solid ${riskColor}44;font-size:0.7rem;">${riskIcon} ${data.overall_risk} Risk</span>
          </div>
        </div>
      </div>
      <div class="result-body" style="padding:20px 24px;">
        <div>
          <p class="label-upper">📋 Ingredients</p>
          <div style="display:flex;flex-wrap:wrap;gap:8px;">${ingredientTags}</div>
        </div>
        ${highRiskHtml}
        ${moderateRiskHtml}
        ${allergenHtml}
        ${warningsHtml}
        ${insHtml}
        <div style="margin-top: 20px; border-top: 1px solid var(--border); padding-top: 16px;">
          <button class="btn btn-primary" style="width: 100%;" onclick="showInlineClaimVerificationOCR()">
            🏷️ Verify Marketing Claims for this Product
          </button>
        </div>
      </div>
    </div>
  `;
}

function showInlineClaimVerificationOCR() {
  const claimHtml = `
    <div id="inlineClaimBoxOCR" style="margin-top: 20px; padding: 20px; background: var(--stone-100); border-radius: var(--r-lg);">
      <h4 style="margin-bottom: 12px;">🏷️ Verify Marketing Claims</h4>
      <textarea id="inlineClaimsInputOCR" rows="3" style="width: 100%; padding: 12px; border-radius: var(--r-md); border: 1px solid var(--border);" placeholder="Enter claims one per line&#10;e.g., No Added Sugar&#10;Gluten Free&#10;All Natural"></textarea>
      <div style="display: flex; gap: 10px; margin-top: 12px;">
        <button class="btn btn-primary" style="flex: 1;" onclick="verifyInlineClaimsOCR()">Verify Claims</button>
        <button class="btn btn-outline" style="flex: 1;" onclick="document.getElementById('inlineClaimBoxOCR')?.remove()">Cancel</button>
      </div>
      <div id="inlineClaimResultOCR" style="margin-top: 12px;"></div>
    </div>
  `;
  
  const existingBox = document.getElementById('inlineClaimBoxOCR');
  if (existingBox) existingBox.remove();
  
  const resultsContainer = document.getElementById('upload-result');
  if (resultsContainer) resultsContainer.insertAdjacentHTML('beforeend', claimHtml);
}

async function verifyInlineClaimsOCR() {
  const claimsInput = document.getElementById('inlineClaimsInputOCR');
  const claims = claimsInput.value.split('\n').filter(c => c.trim());
  const resultDiv = document.getElementById('inlineClaimResultOCR');
  
  if (!claims.length) {
    resultDiv.innerHTML = '<p style="color: var(--red-500);">Please enter at least one claim</p>';
    return;
  }
  
  resultDiv.innerHTML = '<p>⏳ Verifying...</p>';
  
  try {
    const response = await fetch(`${API_URL}/verify-claims`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claims, ingredients_text: currentIngredients })
    });
    
    const data = await response.json();
    
    let html = `<div style="margin-top: 8px;"><strong>${data.verdict}</strong></div>`;
    data.results.forEach(r => {
      const color = r.status === 'Verified' ? '#48bb78' : (r.status === 'Misleading' ? '#f56565' : '#ed8936');
      html += `<div style="margin-top: 8px; padding: 10px; background: white; border-radius: 8px; border-left: 3px solid ${color};">
        <strong>${r.status === 'Verified' ? '✅' : (r.status === 'Misleading' ? '❌' : 'ℹ️')} ${escapeHtml(r.claim)}</strong>
        <p style="font-size: 0.8rem; margin-top: 4px;">${escapeHtml(r.message)}</p>
        ${r.violating_ingredients?.length ? `<small style="color: #c53030;">Found: ${r.violating_ingredients.join(', ')}</small>` : ''}
      </div>`;
    });
    resultDiv.innerHTML = html;
    showToast('Claim verification complete!', 'success');
  } catch (error) {
    resultDiv.innerHTML = '<p style="color: var(--red-500);">Verification failed</p>';
    showToast('Verification failed', 'error');
  }
}

// ==================== CLAIMS TAB ====================
function initClaimsTab() {
  const claimsInput = document.getElementById('claims-input');
  const analyzeClaimsBtn = document.getElementById('analyze-claims-btn');
  const claimsResult = document.getElementById('claims-result');
  if (!analyzeClaimsBtn) return;
  
  analyzeClaimsBtn.addEventListener('click', async () => {
    const text = claimsInput?.value.trim();
    if (!text) { showToast('Please enter marketing claims', 'warning'); return; }
    analyzeClaimsBtn.disabled = true; 
    analyzeClaimsBtn.textContent = '⏳ Analyzing...';
    try {
      const response = await fetch(`${API_URL}/verify-claims`, { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ claims: text.split('\n').filter(c => c.trim()), ingredients_text: 'placeholder' }) 
      });
      const data = await response.json();
      if (claimsResult) {
        claimsResult.style.display = 'block';
        let html = `<div style="margin-top:20px;"><strong>${data.verdict}</strong></div>`;
        data.results.forEach(r => {
          const color = r.status === 'Verified' ? '#48bb78' : (r.status === 'Misleading' ? '#f56565' : '#ed8936');
          html += `<div style="margin-top:12px;padding:12px;background:#f7fafc;border-radius:12px;border-left:3px solid ${color};"><strong>${r.status === 'Verified' ? '✅' : (r.status === 'Misleading' ? '❌' : 'ℹ️')} ${escapeHtml(r.claim)}</strong><p style="margin-top:8px;">${escapeHtml(r.message)}</p></div>`;
        });
        claimsResult.innerHTML = html;
      }
      showToast('Claim analysis complete!', 'success');
    } catch (error) { 
      showToast('Analysis failed', 'error'); 
    } finally { 
      analyzeClaimsBtn.disabled = false; 
      analyzeClaimsBtn.textContent = '🔍 Analyze Claims'; 
    }
  });
  
  document.querySelectorAll('.claims-example').forEach(ex => {
    ex.addEventListener('click', () => { if (claimsInput) claimsInput.value = ex.dataset.val; });
  });
}

// ==================== ADD PRODUCT ====================
async function addNewProduct() {
  const name = document.getElementById('newProductName')?.value.trim();
  const brand = document.getElementById('newProductBrand')?.value.trim();
  const ingredients = document.getElementById('newProductIngredients')?.value.trim();
  const resultDiv = document.getElementById('add-product-result');
  
  if (!name || !brand || !ingredients) {
    showToast('Please fill all fields', 'error');
    return;
  }
  
  if (resultDiv) resultDiv.innerHTML = '<div style="text-align:center;padding:20px;">⏳ Adding product...</div>';
  
  try {
    const response = await fetch(`${API_URL}/add-product`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_name: name, brand: brand, ingredients_text: ingredients })
    });
    
    const data = await response.json();
    
    if (data.success) {
      showToast(`✅ Product "${name}" added successfully!`, 'success');
      if (resultDiv) {
        resultDiv.innerHTML = `
          <div class="card" style="margin-top:20px; background: var(--green-50); border-color: var(--green-200);">
            <h3 style="color: var(--green-700);">✅ Product Added Successfully!</h3>
            <p><strong>${escapeHtml(name)}</strong> by ${escapeHtml(brand)}</p>
            <p>Ingredients: ${escapeHtml(ingredients.substring(0, 100))}${ingredients.length > 100 ? '...' : ''}</p>
            <button class="btn btn-primary" style="margin-top:10px;" onclick="analyzeAddedProduct('${escapeHtml(ingredients).replace(/'/g, "\\'")}', '${escapeHtml(name).replace(/'/g, "\\'")}', '${escapeHtml(brand).replace(/'/g, "\\'")}')">🔬 Analyze Now</button>
          </div>
        `;
      }
      
      document.getElementById('newProductName').value = '';
      document.getElementById('newProductBrand').value = '';
      document.getElementById('newProductIngredients').value = '';
    } else {
      showToast(data.error || 'Failed to add product', 'error');
      if (resultDiv) resultDiv.innerHTML = `<div class="card" style="margin-top:20px; background: var(--red-50);"><p style="color: var(--red-600);">❌ ${data.error || 'Failed to add product'}</p></div>`;
    }
  } catch (error) {
    console.error('Error:', error);
    showToast('Failed to add product - server not running?', 'error');
    if (resultDiv) resultDiv.innerHTML = `<div class="card" style="margin-top:20px; background: var(--red-50);"><p style="color: var(--red-600);">❌ Cannot connect to server. Make sure Flask is running on port 5000</p></div>`;
  }
}

async function analyzeAddedProduct(ingredients, productName, brand) {
  const resultArea = document.getElementById('search-result');
  resultArea.innerHTML = '<div style="text-align:center;padding:40px;">⏳ Analyzing ingredients...</div>';
  
  try {
    const response = await fetch(`${API_URL}/analyze-ingredients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ingredients_text: ingredients })
    });
    
    const data = await response.json();
    const displayData = {
      product: { product_name: productName, brand: brand, ingredients_text: ingredients },
      ...data
    };
    
    renderSearchResult(displayData, resultArea);
    showToast(`✅ Analysis complete for "${productName}"!`, 'success');
  } catch (error) {
    resultArea.innerHTML = `<div class="card" style="padding:32px;"><p style="color: var(--red-500);">❌ Analysis failed</p></div>`;
    showToast('Analysis failed', 'error');
  }
}

// ==================== OTHER PAGE INITIALIZATIONS ====================
function initReport() {
  if (!document.getElementById('report-page')) return;
  const form = document.getElementById('report-form');
  const successMsg = document.getElementById('report-success');
  const desc = document.getElementById('report-description');
  const counter = document.getElementById('desc-counter');
  if (desc && counter) desc.addEventListener('input', () => counter.textContent = `${desc.value.length}/500`);
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      if (btn) { btn.disabled = true; btn.textContent = '⏳ Submitting...'; }
      await new Promise(r => setTimeout(r, 1600));
      if (form) form.style.display = 'none';
      if (successMsg) { successMsg.style.display = 'block'; successMsg.style.animation = 'scaleIn .4s ease both'; }
      showToast('Report submitted successfully!', 'success');
    });
  }
  const attachZone = document.getElementById('attach-zone');
  if (attachZone) attachZone.addEventListener('click', () => { 
    attachZone.innerHTML = `<span class="attach-zone-icon">✅</span><div class="attach-zone-text"><strong style="color:var(--green-600);">evidence_photo.jpg</strong><br><span style="font-size:.78rem;">1 file attached · Click to change</span></div>`; 
    attachZone.style.borderColor = 'var(--green-400)'; 
    attachZone.style.background = 'var(--green-50)'; 
  });
}

function initAwareness() {
  if (!document.getElementById('awareness-page')) return;
  document.querySelectorAll('.accordion-item').forEach(item => {
    const trigger = item.querySelector('.accordion-trigger');
    const body = item.querySelector('.accordion-body');
    if (trigger && body) {
      trigger.addEventListener('click', () => {
        const isOpen = item.classList.contains('open');
        document.querySelectorAll('.accordion-item').forEach(i => { 
          i.classList.remove('open'); 
          const b = i.querySelector('.accordion-body'); 
          if (b) b.style.maxHeight = '0'; 
        });
        if (!isOpen) { 
          item.classList.add('open'); 
          body.style.maxHeight = body.scrollHeight + 'px'; 
        }
      });
    }
  });
}

const STAY_SAFE_DATA = {
  diabetes: { label: 'Diabetes', icon: '🩸', color: 'var(--amber-500)', tip: 'Focus on low-GI foods (GI < 55). Fiber slows glucose absorption.', watch: ['High Fructose Corn Syrup', 'White Sugar', 'Maltodextrin', 'Dextrose'], risky: ['Packaged juices', 'White bread', 'Breakfast cereals'], safer: ['Steel-cut oats', 'Whole grain bread', 'Unsweetened Greek yogurt'] },
  hypertension: { label: 'Hypertension', icon: '❤️', color: 'var(--red-500)', tip: 'Aim for under 2,300mg sodium/day.', watch: ['Sodium (>200mg/serving)', 'MSG', 'Sodium Nitrate'], risky: ['Canned soups', 'Processed meats', 'Instant noodles'], safer: ['Fresh vegetables', 'Bananas', 'Unsalted nuts'] },
  celiac: { label: 'Celiac / Gluten', icon: '🌾', color: 'var(--amber-600)', tip: 'Look for certified gluten-free labels.', watch: ['Wheat', 'Barley', 'Rye', 'Malt'], risky: ['Regular pasta', 'Soy sauce', 'Beer'], safer: ['Rice & quinoa', 'Certified GF oats', 'Corn tortillas'] },
  lactose: { label: 'Lactose Intolerance', icon: '🥛', color: 'var(--green-500)', tip: 'Hard cheeses like cheddar are low in lactose.', watch: ['Milk', 'Lactose', 'Whey', 'Casein'], risky: ['Regular milk', 'Soft cheeses', 'Ice cream'], safer: ['Oat/almond milk', 'Hard aged cheeses', 'Lactose-free products'] },
  heartdisease: { label: 'Heart Disease', icon: '🫀', color: 'var(--red-400)', tip: 'Check for "partially hydrogenated oil" in ingredients.', watch: ['Trans Fats', 'Partially Hydrogenated Oil', 'Saturated Fat'], risky: ['Margarine', 'Fried food', 'Processed meats'], safer: ['Olive oil', 'Fatty fish', 'Avocados'] },
  kidshealth: { label: "Children's Health", icon: '👶', color: 'var(--green-400)', tip: "Children's bodies are more sensitive to additives.", watch: ['Artificial Colors', 'BHA/BHT', 'Aspartame'], risky: ['Colorful candy', 'Flavored chips', 'Sweetened drinks'], safer: ['Fresh fruit', 'Homemade snacks', 'Plain yogurt'] }
};

function initStaySafe() {
  if (!document.getElementById('staysafe-page')) return;
  const selectors = document.querySelectorAll('.condition-card');
  const contentArea = document.getElementById('condition-content');
  
  function renderConditionContent(key) {
    const data = STAY_SAFE_DATA[key];
    if (!data || !contentArea) return;
    contentArea.style.opacity = '0'; 
    contentArea.style.transform = 'translateY(12px)';
    setTimeout(() => {
      contentArea.innerHTML = `<div class="cond-header" style="background:white;border:1px solid var(--border);border-radius:24px;padding:28px 32px;margin-bottom:20px;"><div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;"><div style="width:56px;height:56px;background:var(--green-50);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:1.8rem;">${data.icon}</div><div><div style="font-size:1.8rem;font-weight:400;">${data.label}</div></div></div><div style="padding:14px 18px;background:var(--green-50);border-radius:12px;">💡 ${data.tip}</div></div><div class="safe-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;"><div class="safe-section" style="background:white;border:1px solid var(--border);border-radius:16px;padding:22px;border-top:3px solid var(--red-400);"><div class="safe-section-title" style="color:var(--red-500);margin-bottom:16px;">⚠ Ingredients to Watch</div>${data.watch.map(w => `<div style="padding:8px 0;border-bottom:1px solid var(--border);">• ${escapeHtml(w)}</div>`).join('')}</div><div class="safe-section" style="background:white;border:1px solid var(--border);border-radius:16px;padding:22px;border-top:3px solid var(--amber-400);"><div class="safe-section-title" style="color:var(--amber-500);margin-bottom:16px;">⚡ Risky Products</div>${data.risky.map(r => `<div style="padding:8px 0;border-bottom:1px solid var(--border);">• ${escapeHtml(r)}</div>`).join('')}</div><div class="safe-section" style="background:white;border:1px solid var(--border);border-radius:16px;padding:22px;border-top:3px solid var(--green-400);"><div class="safe-section-title" style="color:var(--green-500);margin-bottom:16px;">✓ Safer Alternatives</div>${data.safer.map(s => `<div style="padding:8px 0;border-bottom:1px solid var(--border);">• ${escapeHtml(s)}</div>`).join('')}</div></div><div class="quick-scan-banner" style="margin-top:20px;padding:20px 24px;background:white;border:1px solid var(--border);border-radius:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;"><div><strong>Scan a product for ${data.label}</strong><br>Check if any packaged food is safe.</div><a href="check-product.html" class="btn btn-primary">🔬 Check Product</a></div><div class="medical-disclaimer" style="margin-top:20px;padding:16px 20px;background:#f8faff;border-radius:16px;font-size:0.8rem;display:flex;gap:12px;"><span>ℹ️</span><span>This guidance is for educational purposes only.</span></div>`;
      contentArea.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      contentArea.style.opacity = '1'; 
      contentArea.style.transform = 'translateY(0)';
    }, 200);
  }
  
  selectors.forEach(card => {
    card.addEventListener('click', () => { 
      selectors.forEach(c => c.classList.remove('active')); 
      card.classList.add('active'); 
      renderConditionContent(card.dataset.condition); 
    });
  });
  
  const firstCard = document.querySelector('.condition-card');
  if (firstCard) { 
    firstCard.classList.add('active'); 
    renderConditionContent(firstCard.dataset.condition); 
  }
  
  document.querySelectorAll('.hero-cond-chip').forEach(chip => {
    chip.addEventListener('click', e => { 
      e.preventDefault(); 
      document.getElementById('condition-selector')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); 
    });
  });
}

// Add CSS for info tags
const style = document.createElement('style');
style.textContent = `
  .tag-info {
    background: #ebf8ff !important;
    color: #2b6cb0 !important;
    border-color: #bee3f8 !important;
    font-style: italic;
  }
`;
document.head.appendChild(style);

// ==================== INITIALIZE ====================
document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initDashboard();
  initCheckProduct();
  initReport();
  initAwareness();
  initStaySafe();
  checkAuthState();
  
  const addProductBtn = document.getElementById('add-product-btn');
  if (addProductBtn) {
    addProductBtn.addEventListener('click', addNewProduct);
  }
});