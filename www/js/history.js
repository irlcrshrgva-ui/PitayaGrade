/* =============================================
   PitayaGrade - History Module
   Scan records, filtering, search, detail view
   ============================================= */

const HistoryManager = {
  currentFilter: 'all',
  searchQuery: '',

  init() {
    this.bindEvents();
    this.refresh();
  },

  bindEvents() {
    // Filter chips
    const filterBar = document.getElementById('historyFilters');
    if (filterBar) {
      filterBar.addEventListener('click', (e) => {
        const chip = e.target.closest('.filter-chip');
        if (!chip) return;
        filterBar.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        this.currentFilter = chip.dataset.filter;
        this.refresh();
      });
    }

    // Search
    const searchInput = document.getElementById('historySearch');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase();
        this.refresh();
      });
    }
  },

  refresh() {
    const scans = this._getFilteredScans();
    this._renderList(scans);
  },

  _getFilteredScans() {
    let scans = JSON.parse(localStorage.getItem('pg_scans') || '[]');

    // Apply filter
    switch (this.currentFilter) {
      case 'grade-a':
        scans = scans.filter(s => s.grade.label === 'Grade A');
        break;
      case 'grade-b':
        scans = scans.filter(s => s.grade.label === 'Grade B');
        break;
      case 'grade-c':
        scans = scans.filter(s => s.grade.label === 'Grade C');
        break;
      case 'reject':
        scans = scans.filter(s => s.grade.label === 'Reject');
        break;
      case 'diseased':
        scans = scans.filter(s => !s.disease.isHealthy);
        break;
    }

    // Apply search
    if (this.searchQuery) {
      scans = scans.filter(s => {
        const searchable = `${s.grade.label} ${s.disease.name} ${s.notes || ''} ${s.details.surfaceCondition}`.toLowerCase();
        return searchable.includes(this.searchQuery);
      });
    }

    return scans;
  },

  _renderList(scans) {
    const container = document.getElementById('historyList');
    if (!container) return;

    if (scans.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">
            <svg class="icon-svg" viewBox="0 0 24 24"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
          </div>
          <div class="empty-state-title">${this.currentFilter !== 'all' || this.searchQuery ? 'No matching records' : 'No records yet'}</div>
          <div class="empty-state-text">${this.currentFilter !== 'all' || this.searchQuery ? 'Try adjusting your filters or search.' : 'Scanned dragon fruit assessments will appear here.'}</div>
        </div>
      `;
      return;
    }

    // Group by date
    const grouped = {};
    scans.forEach(s => {
      const dateKey = new Date(s.timestamp).toLocaleDateString('en-PH', { 
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
      });
      if (!grouped[dateKey]) grouped[dateKey] = [];
      grouped[dateKey].push(s);
    });

    let html = '';
    Object.entries(grouped).forEach(([date, items]) => {
      html += `<div style="font-size:12px;font-weight:600;color:var(--text-tertiary);padding:12px 0 8px;text-transform:uppercase;letter-spacing:0.5px">${date}</div>`;
      items.forEach(s => {
        const time = new Date(s.timestamp).toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' });
        html += `
          <div class="scan-item" onclick="HistoryManager.showDetail('${s.id}')">
            <img class="scan-thumb" src="${s.thumbnail}" alt="Scan">
            <div class="scan-info">
              <div class="scan-info-title">${s.grade.label}${!s.disease.isHealthy ? ' - ' + s.disease.name : ''}</div>
              <div class="scan-info-meta">
                <span>${time}</span>
                <span>|</span>
                <span>${s.details.size}</span>
              </div>
            </div>
            <div class="scan-grade">
              <span class="grade-badge ${s.grade.class}">${s.grade.label.replace('Grade ', '')}</span>
            </div>
          </div>
        `;
      });
    });

    container.innerHTML = html;
  },

  showDetail(id) {
    const scans = JSON.parse(localStorage.getItem('pg_scans') || '[]');
    const scan = scans.find(s => String(s.id) === String(id));
    if (!scan) return;

    const modal = document.getElementById('detailModal');
    const backdrop = document.getElementById('modalBackdrop');
    const body = document.getElementById('modalBody');
    const title = document.getElementById('modalTitle');

    title.textContent = `${scan.grade.label} Assessment`;

    const date = new Date(scan.timestamp);
    const dateStr = date.toLocaleDateString('en-PH', { 
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });

    const confClass = scan.grade.confidence > 0.85 ? 'high' : scan.grade.confidence > 0.7 ? 'medium' : 'low';

    body.innerHTML = `
      <div style="text-align:center;margin-bottom:16px">
        <img src="${scan.thumbnail}" style="width:120px;height:120px;border-radius:16px;object-fit:cover;margin:0 auto 12px;display:block;border:2px solid var(--border-light)">
        <div class="grade-badge grade-badge-lg ${scan.grade.class}">${scan.grade.label}</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:8px">${(scan.grade.confidence * 100).toFixed(1)}% confidence</div>
        <div class="confidence-bar" style="max-width:200px;margin:6px auto 0">
          <div class="confidence-fill ${confClass}" style="width:${(scan.grade.confidence * 100)}%"></div>
        </div>
      </div>

      <div style="font-size:11px;color:var(--text-tertiary);text-align:center;margin-bottom:16px">${dateStr}</div>

      <!-- Maturity Status (New Feature) -->
      ${scan.maturity ? `
      <div class="disease-status ${scan.maturity.isHarvestable ? 'healthy' : 'warning'}" style="margin-bottom:8px">
        <span>
          ${scan.maturity.isHarvestable 
            ? '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="m9 11 3 3 3-3"/></svg>' 
            : '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M12 2v8"/><path d="m4.93 4.93 1.41 1.41"/><path d="M2 12h8"/><path d="m13 22 3-3h6l-3-3 3-3h-6l-3-3"/></svg>'}
        </span>
        <span style="flex:1">${scan.maturity.status} Stage</span>
        <span style="font-weight:700">${scan.maturity.value}% Maturity</span>
      </div>
      ` : ''}

      <div class="disease-status ${scan.disease.isHealthy ? 'healthy' : scan.disease.confidence > 0.8 ? 'critical' : 'warning'}" style="margin-bottom:16px">
        <span>
          ${scan.disease.isHealthy 
            ? '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>' 
            : '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>'}
        </span>
        <span style="flex:1">${scan.disease.name}</span>
        <span style="font-weight:700">${(scan.disease.confidence * 100).toFixed(1)}%</span>
      </div>

      ${scan.disease.symptoms && scan.disease.symptoms.length > 0 ? `
      <div class="result-section" style="margin-bottom:16px">
        <div class="result-section-title">Detected Symptoms</div>
        <div class="symptoms-list">
          ${scan.disease.symptoms.map(s => `
            <div class="symptom-item ${scan.disease.isHealthy ? 'healthy' : 'alert'}">
              <span class="symptom-dot ${scan.disease.isHealthy ? 'green' : 'red'}"></span>
              <span>${s}</span>
            </div>
          `).join('')}
        </div>
      </div>
      ` : ''}

      <div class="result-section">
        <div class="result-section-title">Details</div>
        <div class="result-detail-row">
          <span class="result-detail-label">
            <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><path d="M10 2v2"/><path d="M14 2v2"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M18 6h-12"/></svg>
            Size
          </span>
          <span class="result-detail-value">${scan.details.size}</span>
        </div>
        ${scan.details.colorDescriptor ? `
        <div class="result-detail-row">
          <span class="result-detail-label">
            <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><circle cx="13.5" cy="6.5" r="0.5"/><circle cx="17.5" cy="10.5" r="0.5"/><circle cx="8.5" cy="7.5" r="0.5"/><circle cx="6.5" cy="12.5" r="0.5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>
            Color
          </span>
          <span class="result-detail-value">${scan.details.colorDescriptor}</span>
        </div>
        ` : ''}
        <div class="result-detail-row">
          <span class="result-detail-label">
            <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
            Color Uniformity
          </span>
          <span class="result-detail-value">${scan.details.colorUniformity}</span>
        </div>
        <div class="result-detail-row">
          <span class="result-detail-label">
            <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
            Surface
          </span>
          <span class="result-detail-value">${scan.details.surfaceCondition}</span>
        </div>
        ${scan.details.modelUsed ? `
        <div class="result-detail-row">
          <span class="result-detail-label">
            <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>
            Model
          </span>
          <span class="result-detail-value">${scan.details.modelUsed}</span>
        </div>
        ` : ''}
      </div>

      ${scan.modelMetrics ? `
      <div class="result-section" style="margin-top:16px">
        <div class="result-section-title">Model Performance</div>
        <div class="metrics-card">
          <div class="metrics-subtitle">Grade: ${scan.grade.label}</div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.grade.accuracy}%</div>
              <div class="metric-label">Accuracy</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.grade.precision}%</div>
              <div class="metric-label">Precision</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.grade.recall}%</div>
              <div class="metric-label">Recall</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.grade.f1Score}%</div>
              <div class="metric-label">F1-Score</div>
            </div>
          </div>
        </div>
        <div class="metrics-card" style="margin-top:8px">
          <div class="metrics-subtitle">Disease: ${scan.disease.name}</div>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.disease.accuracy}%</div>
              <div class="metric-label">Accuracy</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.disease.precision}%</div>
              <div class="metric-label">Precision</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.disease.recall}%</div>
              <div class="metric-label">Recall</div>
            </div>
            <div class="metric-item">
              <div class="metric-value">${scan.modelMetrics.disease.f1Score}%</div>
              <div class="metric-label">F1-Score</div>
            </div>
          </div>
        </div>
      </div>
      ` : ''}

      ${scan.recommendations ? `
        <div class="result-section" style="margin-top:16px">
          <div class="result-section-title">Recommendations</div>
          ${scan.recommendations.map(r => `
            <div class="recommendation-card ${r.type}">
              <span class="recommendation-icon">${r.icon}</span>
              <span class="recommendation-text">${r.text}</span>
            </div>
          `).join('')}
        </div>
      ` : ''}

      <button class="btn btn-outline btn-full" style="margin-top:16px;color:var(--color-error);border-color:var(--color-error)" onclick="HistoryManager.deleteScan('${scan.id}')">
        <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px;color:var(--color-error)" viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
        Delete This Record
      </button>
    `;

    modal.classList.add('open');
    backdrop.classList.add('open');
  },

  deleteScan(id) {
    if (!confirm('Delete this scan record?')) return;
    
    let scans = JSON.parse(localStorage.getItem('pg_scans') || '[]');
    scans = scans.filter(s => String(s.id) !== String(id));
    localStorage.setItem('pg_scans', JSON.stringify(scans));

    // Close modal
    document.getElementById('detailModal').classList.remove('open');
    document.getElementById('modalBackdrop').classList.remove('open');

    this.refresh();
    DashboardManager.refresh();
    ToastManager.show('Record deleted', 'info');
  }
};
