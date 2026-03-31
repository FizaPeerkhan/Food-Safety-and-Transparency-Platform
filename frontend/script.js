  
    const API_URL = 'http://127.0.0.1:5000';
    let currentIngredients = '';
    const ALL_MODES = ['search', 'add', 'manual', 'ocr', 'nutrition'];

    function showToast(message, type = 'success') {
      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.innerHTML = message;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.style.animation = 'slideInToast 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    }

    function esc(str) {
      return escapeHtml(str);
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function setMode(btn, mode) {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      ALL_MODES.forEach(m => {
        const el = document.getElementById(m + 'Mode');
        if (el) el.classList[m === mode ? 'remove' : 'add']('hidden');
      });
      document.getElementById('results').innerHTML = '';
      document.getElementById('nutritionResults').innerHTML = '';
    }

    function showLoading(message) {
      document.getElementById('results').innerHTML = `
        <div class="card">
          <div class="loading">
            <div class="spinner"></div>
            <div>⏳ ${message}</div>
          </div>
        </div>
      `;
    }

    async function searchProduct() {
      const query = document.getElementById('searchInput').value.trim();
      if (!query) {
        showToast('Please enter a product name', 'error');
        return;
      }

      showLoading('Searching database...');
      
      try {
        const response = await fetch(`${API_URL}/search?name=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.error) {
          showToast(data.error, 'error');
          return;
        }
        
        currentIngredients = data.product.ingredients_text;
        displayResults(data);
        showToast(`✅ Found "${data.product.product_name}" by ${data.product.brand}`, 'success');
        
      } catch (error) {
        console.error('Error:', error);
        showToast('Cannot connect to server. Make sure Flask is running on port 5000', 'error');
      }
    }

    async function addNewProduct() {
      const name = document.getElementById('newProductName').value.trim();
      const brand = document.getElementById('newProductBrand').value.trim();
      const ingredients = document.getElementById('newProductIngredients').value.trim();
      
      if (!name || !brand || !ingredients) {
        showToast('Please fill all fields', 'error');
        return;
      }
      
      showLoading('Adding product to database...');
      
      try {
        const response = await fetch(`${API_URL}/add-product`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            product_name: name, 
            brand: brand, 
            ingredients_text: ingredients 
          })
        });
        
        const data = await response.json();
        
        if (data.success) {
          currentIngredients = ingredients;
          showToast(`✅ ${data.message}`, 'success');
          adaptAnalyzeResponse(data.analysis, ingredients, name, brand);
          document.getElementById('newProductName').value = '';
          document.getElementById('newProductBrand').value = '';
          document.getElementById('newProductIngredients').value = '';
        } else {
          showToast(data.error || 'Failed to add product', 'error');
        }
      } catch (error) {
        console.error('Error:', error);
        showToast('Failed to add product', 'error');
      }
    }

    async function analyzeManual() {
      const ingredients = document.getElementById('manualIngredients').value.trim();
      if (!ingredients) {
        showToast('Please enter ingredients to analyze', 'error');
        return;
      }
      
      currentIngredients = ingredients;
      showLoading('Analyzing ingredients...');
      
      try {
        const response = await fetch(`${API_URL}/analyze-ingredients`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ingredients_text: ingredients })
        });
        
        const data = await response.json();
        adaptAnalyzeResponse(data, ingredients);
        showToast('✅ Analysis complete!', 'success');
        
      } catch (error) {
        console.error('Error:', error);
        showToast('Failed to analyze ingredients', 'error');
      }
    }

    async function performOCR() {
      const file = document.getElementById('ocrImage').files[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append('image', file);
      
      document.getElementById('ocrResultGroup').classList.add('hidden');
      showLoading('Extracting text from image...');
      
      try {
        const response = await fetch(`${API_URL}/ocr`, {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
          showToast(data.error, 'error');
          return;
        }
        
        document.getElementById('ocrIngredients').value = data.extracted_text;
        document.getElementById('ocrResultGroup').classList.remove('hidden');
        document.getElementById('results').innerHTML = '';
        showToast('✅ Text extracted successfully! Click "Analyze" to continue.', 'success');
      } catch (error) {
        console.error('Error:', error);
        showToast('OCR failed. Please make sure Tesseract is installed.', 'error');
      }
    }

    async function analyzeOCRText() {
      const ingredients = document.getElementById('ocrIngredients').value.trim();
      if (!ingredients) {
        showToast('No ingredients to analyze', 'error');
        return;
      }
      
      currentIngredients = ingredients;
      showLoading('Analyzing ingredients...');
      
      try {
        const response = await fetch(`${API_URL}/analyze-ingredients`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ingredients_text: ingredients })
        });
        
        const data = await response.json();
        adaptAnalyzeResponse(data, ingredients);
        showToast('✅ Analysis complete!', 'success');
      } catch (error) {
        console.error('Error:', error);
        showToast('Analysis failed', 'error');
      }
    }

    function adaptAnalyzeResponse(d, ingredientsText, productName = null, brand = null) {
      d.product = d.product || { 
        product_name: productName || 'Manual Analysis', 
        brand: brand || '—', 
        ingredients_text: ingredientsText 
      };
      displayResults(d);
    }

    function displayResults(data) {
      let html = '<div class="card"><div class="card-title">📊 Analysis Results</div>';
      html += `<h2>${esc(data.product.product_name)}</h2>`;
      html += `<p style="color:#718096;margin:4px 0 12px">Brand: <strong>${esc(data.product.brand)}</strong></p>`;
     
      // Risk badge
      const r = data.overall_risk;
      const riskIcon = {High:'🔴', Moderate:'🟡', Low:'🟢'}[r] || '⚪';
      html += `<span class="risk-badge risk-${r}" style="margin-bottom:14px;display:inline-block">${riskIcon} Overall Risk: ${r}</span>`;
     
      // Tag cloud with colour coding
      const hiSet = new Set((data.high_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
      const moSet = new Set((data.moderate_risk_ingredients || []).map(i => (i.original_text || i.ingredient || '').toLowerCase()));
      html += `<div style="margin:10px 0"><strong>📋 All Ingredients</strong></div>
               <div class="ingredients-tag-cloud">`;
      (data.all_ingredients || data.product.ingredients_text.split(',').map(x => ({name: x.trim()}))).forEach(i => {
        const name = i.name || i;
        const cls = hiSet.has(name.toLowerCase()) ? 'ingredient-tag tag-high'
                   : moSet.has(name.toLowerCase()) ? 'ingredient-tag tag-moderate'
                   : 'ingredient-tag';
        html += `<span class="${cls}" title="${esc(i.category || '')}">${esc(name)}</span>`;
      });
      html += `</div>`;
     
      // Allergen box
      if (data.allergens && data.allergens.length) {
        html += `<div class="allergen-box"><strong>⚠️ Allergens Detected:</strong><br>
          ${data.allergens.map(a => `<span class="a-tag">${esc(a)}</span>`).join('')}</div>`;
      }
     
      // High risk
      if (data.high_risk_ingredients?.length) {
        html += `<h3 style="margin:16px 0 8px">🔴 High Risk Ingredients</h3>`;
        data.high_risk_ingredients.forEach(i => {
          html += `<div class="ingredient-item high-risk">
            <strong>⚠️ ${esc(i.ingredient)}</strong>
            <span style="font-size:.75rem;color:#718096;float:right">${esc(i.category || '')}</span><br>
            ${esc(i.explanation || i.reason || '')}<br>
            
            ${i.allergen ? `<span class="a-tag" style="margin-left:6px">${esc(i.allergen)}</span>` : ''}
          </div>`;
        });
      }
     
      // Moderate risk
      if (data.moderate_risk_ingredients?.length) {
        html += `<h3 style="margin:16px 0 8px">🟡 Moderate Risk Ingredients</h3>`;
        data.moderate_risk_ingredients.forEach(i => {
          html += `<div class="ingredient-item moderate-risk">
            <strong>${esc(i.ingredient)}</strong>
            <span style="font-size:.75rem;color:#718096;float:right">${esc(i.category || '')}</span><br>
            ${esc(i.explanation || i.reason || '')}<br>
            
            ${i.allergen ? `<span class="a-tag" style="margin-left:6px">${esc(i.allergen)}</span>` : ''}
          </div>`;
        });
      }
     
      // Health warnings
      if (data.health_warnings?.length) {
        html += `<h3 style="margin:16px 0 8px">🏥 Who Should Be Careful</h3>`;
        data.health_warnings.forEach(w => {
          html += `<div style="padding:8px 12px;background:#fff7ed;border-radius:8px;margin-bottom:6px;font-size:.88rem">⚠️ ${esc(w)}</div>`;
        });
      }
     
      // INS numbers
      if (data.ins_numbers?.length) {
        html += `<div style="background:#ebf8ff;border-radius:10px;padding:12px 16px;margin-top:12px">
          <strong style="color:#2b6cb0">🔬 INS / E-Numbers:</strong><br>`;
        data.ins_numbers.forEach(i => {
          html += `<span style="display:inline-block;background:#bee3f8;color:#2b6cb0;border-radius:20px;
                   padding:3px 10px;font-size:.75rem;font-weight:600;margin:3px">${esc(i.code)} — ${esc(i.name)}</span>`;
        });
        html += `</div>`;
      }
     
      html += `<button class="btn btn-outline" style="margin-top:18px;width:100%"
                onclick="showClaimVerification()">🏷️ Verify Marketing Claims</button>`;
      html += `</div>`;
      document.getElementById('results').innerHTML = html;
    }

    function showClaimVerification() {
      const claimHtml = `
        <div class="card" id="claimCard">
          <div class="card-title">🏷️ Verify Marketing Claims</div>
          <div class="form-group">
            <label>Enter claims to verify (one per line)</label>
            <textarea id="claimsInput" rows="3" placeholder="e.g.,&#10;No Added Sugar&#10;Gluten Free&#10;All Natural"></textarea>
          </div>
          <button class="btn btn-primary" onclick="verifyClaims()">Verify Claims</button>
        </div>
      `;
      document.getElementById('results').insertAdjacentHTML('beforeend', claimHtml);
    }

    async function verifyClaims() {
      const claimsText = document.getElementById('claimsInput').value;
      const claims = claimsText.split('\n').filter(c => c.trim().length > 0);
      
      if (claims.length === 0) {
        showToast('Please enter at least one claim', 'error');
        return;
      }
      
      showLoading('Verifying claims...');
      
      try {
        const response = await fetch(`${API_URL}/verify-claims`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            claims: claims, 
            ingredients_text: currentIngredients 
          })
        });
        
        const data = await response.json();
        
        let html = '<div class="card"><div class="card-title">📋 Verification Results</div>';
        
        if (data.verdict.includes('Warning')) {
          html += `<div class="risk-badge risk-Moderate" style="margin-bottom: 15px;">${data.verdict}</div>`;
        } else {
          html += `<div class="risk-badge risk-Low" style="margin-bottom: 15px; background: #e8f5e9;">${data.verdict}</div>`;
        }
        
        data.results.forEach(result => {
          const statusClass = result.status === 'Verified' ? 'claim-verified' : 'claim-misleading';
          const icon = result.status === 'Verified' ? '✅' : (result.status === 'Misleading' ? '❌' : 'ℹ️');
          html += `
            <div class="claim-box">
              <span class="${statusClass}">${icon} ${esc(result.claim)}</span>
              <p style="margin-top: 8px; color: #4a5568;">${esc(result.message)}</p>
              ${result.violating_ingredients && result.violating_ingredients.length > 0 ? 
                `<small style="color: #c53030;">Found: ${result.violating_ingredients.join(', ')}</small>` : ''}
            </div>
          `;
        });
        
        html += '</div>';
        document.getElementById('claimCard').outerHTML = html;
        showToast('Claim verification complete!', 'success');
        
      } catch (error) {
        console.error('Error:', error);
        showToast('Verification failed', 'error');
      }
    }

    // Nutrition Functions
    function showNutritionOCR() {
      document.getElementById('nutritionOCR').classList.remove('hidden');
      document.getElementById('nutritionManual').classList.add('hidden');
      document.getElementById('nutritionResults').innerHTML = '';
    }

    function showNutritionManual() {
      document.getElementById('nutritionOCR').classList.add('hidden');
      document.getElementById('nutritionManual').classList.remove('hidden');
      document.getElementById('nutritionResults').innerHTML = '';
    }

    async function analyzeNutritionOCR() {
      const file = document.getElementById('nutritionImage').files[0];
      if (!file) {
        showToast('Please select an image', 'error');
        return;
      }
      
      const formData = new FormData();
      formData.append('image', file);
      
      showLoading('Extracting nutrition facts from image...');
      
      try {
        const response = await fetch(`${API_URL}/ocr-nutrition`, {
          method: 'POST',
          body: formData
        });
        
        const data = await response.json();
        
        if (data.error) {
          showToast(data.error, 'error');
          return;
        }
        
        document.getElementById('nutritionText').value = data.extracted_text;
        document.getElementById('servingSize').value = '100g';
        showNutritionManual();
        analyzeNutrition();
        
      } catch (error) {
        console.error('Error:', error);
        showToast('OCR failed. Please try entering manually.', 'error');
      }
    }

    async function analyzeNutrition() {
      const nutritionText = document.getElementById('nutritionText').value.trim();
      const servingSize = document.getElementById('servingSize').value.trim() || '100g';
      
      if (!nutritionText) {
        showToast('Please enter nutrition facts', 'error');
        return;
      }
      
      showLoading('Analyzing nutrition facts...');
      
      try {
        const response = await fetch(`${API_URL}/nutrition-analysis`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nutrition_text: nutritionText,
            serving_size: servingSize
          })
        });
        
        const data = await response.json();
        
        if (data.error) {
          showToast(data.error, 'error');
          return;
        }
        
        displayAdvancedNutritionResults(data);
        showToast('Nutrition analysis complete!', 'success');
        
      } catch (error) {
        console.error('Error:', error);
        showToast('Analysis failed', 'error');
      }
    }

    function displayAdvancedNutritionResults(data) {
      const score = data.health_score;
      const color = data.rating_color || '#38a169';
     
      let html = `<div class="card" style="margin-top:16px">
        <div class="card-title">🥗 Nutrition Analysis — per ${esc(data.serving_size || '100g')}</div>
     
        <!-- Score bar -->
        <div style="margin-bottom:18px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:700;font-size:1.1rem;color:${color}">${esc(data.rating)}</span>
            <span style="font-weight:800;font-size:1.4rem;color:${color}">${score}/100</span>
          </div>
          <div class="score-bar-wrap">
            <div class="score-bar-fill" style="width:${score}%;background:${color}"></div>
          </div>
        </div>
     
        <!-- Verdict -->
        ${data.verdict ? `<div class="verdict-box">${esc(data.verdict)}</div>` : ''}
     
        <!-- Nutrient cards -->
        <h3 style="margin:16px 0 10px">📊 Nutrient Breakdown</h3>
        <div class="n-grid">`;
     
      (data.nutrients || []).forEach(n => {
        const vc = n.status === 'high' ? 'red' : n.status === 'low' && ['fiber','protein'].includes(n.key) ? 'red' : n.status === 'moderate' ? 'orange' : 'green';
        html += `
          <div class="n-card">
            <div class="n-card-top">
              <span class="n-label">${esc(n.label)}</span>
              <span class="n-val ${vc}">${n.value}${n.unit}</span>
            </div>
            <div class="n-msg">${esc(n.message)}</div>
            <div class="n-bar-wrap">
              <div class="n-bar-fill" style="width:${Math.min(n.percentage || 0, 100)}%;background:${n.bar_color}"></div>
            </div>
          </div>`;
      });
     
      html += `</div></div>`;
     
      // Warnings
      if (data.warnings && data.warnings.length) {
        html += `<div class="card"><div class="card-title">⚠️ Warnings</div>`;
        data.warnings.forEach(w => {
          html += `<div style="padding:10px 12px;background:#fff5f5;border-left:4px solid #e53e3e;
                   border-radius:8px;margin-bottom:8px;font-size:.88rem">${esc(w)}</div>`;
        });
        html += `</div>`;
      }
     
      document.getElementById('nutritionResults').innerHTML = html;
    }

    // Enter key support
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') searchProduct();
    });
 