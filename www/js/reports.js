/* =============================================
   PitayaGrade - Reports Module
   Generate and export farm reports
   ============================================= */

const ReportsManager = {
  init() {
    this.bindEvents();
    this._setDefaultDates();
  },

  bindEvents() {
    ['reportFrom', 'reportTo'].forEach(id => document.getElementById(id)?.addEventListener('change', () => this.invalidate()));
    const generateBtn = document.getElementById('generateReportBtn');
    const csvBtn = document.getElementById('exportCSVBtn');

    if (generateBtn) {
      generateBtn.addEventListener('click', () => this.generateReport());
    }
    if (csvBtn) {
      csvBtn.addEventListener('click', () => this.exportCSV());
    }
  },

  _setDefaultDates() {
    const fromInput = document.getElementById('reportFrom');
    const toInput = document.getElementById('reportTo');
    if (!fromInput || !toInput) return;

    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    toInput.value = ScanStore.localDate(today);
    fromInput.value = ScanStore.localDate(thirtyDaysAgo);
  },

  invalidate() {
    const area = document.getElementById('reportPreviewArea');
    if (area) area.innerHTML = '';
  },

  _getFilteredScans() {
    const fromInput = document.getElementById('reportFrom');
    const toInput = document.getElementById('reportTo');
    const from = new Date(fromInput?.value + 'T00:00:00');
    const to = new Date(toInput?.value + 'T00:00:00');
    if (!Number.isFinite(+from) || !Number.isFinite(+to) || from > to) {
      this.invalidate();
      ToastManager.show('Choose a valid date range with From on or before To.', 'warning');
      return null;
    }
    to.setDate(to.getDate() + 1);

    const scans = ScanStore.getScans();
    return scans.filter(s => {
      const d = new Date(s.timestamp);
      return d >= from && d < to;
    });
  },

  generateReport() {
    const scans = this._getFilteredScans();
    if (!scans) return;
    const area = document.getElementById('reportPreviewArea');
    if (!area) return;

    if (scans.length === 0) {
      area.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📄</div>
          <div class="empty-state-title">No data for this period</div>
          <div class="empty-state-text">No scan records found within the selected date range.</div>
        </div>
      `;
      return;
    }

    // Generate stats
    const total = scans.length;
    const grades = { 'Grade A': 0, 'Grade B': 0, 'Grade C': 0, 'Reject': 0 };
    const diseases = {};
    let totalConfidence = 0;

    scans.forEach(s => {
      grades[s.grade.label] = (grades[s.grade.label] || 0) + 1;
      if (!s.disease.isHealthy) {
        diseases[s.disease.name] = (diseases[s.disease.name] || 0) + 1;
      }
      totalConfidence += s.grade.confidence;
    });

    const avgConfidence = (totalConfidence / total * 100).toFixed(1);
    const healthy = total - Object.values(diseases).reduce((a, b) => a + b, 0);
    const fromStr = document.getElementById('reportFrom').value;
    const toStr = document.getElementById('reportTo').value;

    area.innerHTML = `
      <div class="report-preview" id="printableReport">
        <div style="text-align:center;margin-bottom:20px">
          <div style="font-size:24px;margin-bottom:4px">🐉</div>
          <h2 style="margin-bottom:4px">PitayaGrade Farm Report</h2>
          <p style="font-size:12px;color:#666;margin:0">Period: ${fromStr} to ${toStr}</p>
          <p style="font-size:12px;color:#666;margin:0">Generated: ${new Date().toLocaleString('en-PH')}</p>
        </div>

        <h3 style="font-size:14px;margin:16px 0 8px;color:#333;border-bottom:2px solid #E91E63;padding-bottom:4px">Summary Overview</h3>
        <table>
          <tr><th>Metric</th><th>Value</th></tr>
          <tr><td>Total Scans</td><td><strong>${total}</strong></td></tr>
          <tr><td>Average Confidence</td><td>${avgConfidence}%</td></tr>
          <tr><td>Healthy Fruits</td><td>${healthy} (${((healthy/total)*100).toFixed(1)}%)</td></tr>
          <tr><td>Diseased Fruits</td><td>${total - healthy} (${(((total-healthy)/total)*100).toFixed(1)}%)</td></tr>
        </table>

        <h3 style="font-size:14px;margin:16px 0 8px;color:#333;border-bottom:2px solid #E91E63;padding-bottom:4px">Quality Grade Distribution</h3>
        <table>
          <tr><th>Grade</th><th>Count</th><th>Percentage</th></tr>
          ${Object.entries(grades).map(([g, c]) => `
            <tr>
              <td>${g}</td>
              <td>${c}</td>
              <td>${((c/total)*100).toFixed(1)}%</td>
            </tr>
          `).join('')}
        </table>

        ${Object.keys(diseases).length > 0 ? `
          <h3 style="font-size:14px;margin:16px 0 8px;color:#333;border-bottom:2px solid #E91E63;padding-bottom:4px">Disease Detection Summary</h3>
          <table>
            <tr><th>Disease</th><th>Count</th><th>Percentage</th></tr>
            ${Object.entries(diseases).sort((a,b) => b[1]-a[1]).map(([d, c]) => `
              <tr>
                <td>${d}</td>
                <td>${c}</td>
                <td>${((c/total)*100).toFixed(1)}%</td>
              </tr>
            `).join('')}
          </table>
        ` : '<p style="font-size:13px;color:#22C55E;margin:12px 0"><strong>No diseases detected in this period.</strong></p>'}

        <h3 style="font-size:14px;margin:16px 0 8px;color:#333;border-bottom:2px solid #E91E63;padding-bottom:4px">Recent Scan Log</h3>
        <table>
          <tr><th>Date</th><th>Grade</th><th>Confidence</th><th>Disease</th><th>Size</th><th>Notes</th></tr>
          ${scans.slice(0, 20).map(s => {
            const d = new Date(s.timestamp);
            return `
              <tr>
                <td>${d.toLocaleDateString('en-PH', {month:'short',day:'numeric'})} ${d.toLocaleTimeString('en-PH',{hour:'2-digit',minute:'2-digit'})}</td>
                <td>${s.grade.label}</td>
                <td>${(s.grade.confidence*100).toFixed(1)}%</td>
                <td>${s.disease.name}</td>
                <td>${s.details.size}</td>
                <td>${ScanStore.escape(s.notes)}</td>
              </tr>
            `;
          }).join('')}
          ${scans.length > 20 ? `<tr><td colspan="6" style="text-align:center;color:#999">... and ${scans.length - 20} more records</td></tr>` : ''}
        </table>

        <div style="margin-top:20px;padding-top:12px;border-top:1px solid #ddd;text-align:center">
          <p style="font-size:11px;color:#999;margin:0">Generated by PitayaGrade v1.0.0</p>
          <p style="font-size:11px;color:#999;margin:2px 0 0">Disease, maturity, and size are image-based estimates. Confirm findings through inspection.</p>
        </div>
      </div>

      <div style="display:flex;gap:8px">
        <button class="btn btn-primary btn-full" onclick="ReportsManager.printReport()">
          🖨️ Print Report
        </button>
      </div>
    `;

    ToastManager.show('Report generated successfully', 'success');
  },

  exportCSV() {
    const scans = this._getFilteredScans();
    if (!scans) return;
    if (scans.length === 0) {
      ToastManager.show('No data to export', 'warning');
      return;
    }

    const headers = ['Date', 'Time', 'Grade', 'Grade Confidence', 'Disease', 'Disease Confidence', 'Size', 'Color Uniformity', 'Surface Condition', 'Processing Mode', 'Processing Time', 'Notes'];
    
    const rows = scans.map(s => {
      const d = new Date(s.timestamp);
      return [
        d.toLocaleDateString('en-PH'),
        d.toLocaleTimeString('en-PH'),
        s.grade.label,
        (s.grade.confidence * 100).toFixed(1) + '%',
        s.disease.name,
        (s.disease.confidence * 100).toFixed(1) + '%',
        s.details.size,
        s.details.colorUniformity,
        s.details.surfaceCondition,
        s.details.processingMode,
        s.details.processingTime,
        s.notes || ''
      ];
    });

    let csv = '\uFEFF' + headers.join(',') + '\r\n';
    rows.forEach(row => {
      csv += row.map(cell => this._csvCell(cell)).join(',') + '\r\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `PitayaGrade_Report_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);

    ToastManager.show('CSV exported successfully', 'success');
  },

  _csvCell(value) {
    let text = String(value ?? '');
    if (/^[\s]*[=+@-]/.test(text)) text = "'" + text;
    return '"' + text.replace(/"/g, '""') + '"';
  },

  printReport() {
    const reportEl = document.getElementById('printableReport');
    if (!reportEl) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      ToastManager.show('Printing is unavailable or blocked. Export CSV instead.', 'warning');
      return;
    }
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>PitayaGrade Farm Report</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; color: #111; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 12px; }
          th, td { padding: 8px; border: 1px solid #ddd; text-align: left; }
          th { background: #f5f5f5; font-weight: 600; }
          h2 { font-size: 20px; margin-bottom: 4px; }
          h3 { font-size: 14px; margin: 16px 0 8px; border-bottom: 2px solid #E91E63; padding-bottom: 4px; }
        </style>
      </head>
      <body>
        ${reportEl.innerHTML}
      </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  }
};
