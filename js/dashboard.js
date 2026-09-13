/* =============================================
   PitayaGrade - Dashboard Module
   Canvas-based charts, stats, harvest gauge
   ============================================= */

const DashboardManager = {
  init() {
    this.refresh();
  },

  refresh() {
    const scans = this._getScans();
    this._updateStats(scans);
    this._updateGauge(scans);
    this._renderGradeChart(scans);
    this._renderRecentScans(scans);
  },

  _getScans() {
    return JSON.parse(localStorage.getItem('pg_scans') || '[]');
  },

  _updateStats(scans) {
    const totalEl = document.getElementById('statTotalScans');
    const avgEl = document.getElementById('statAvgGrade');
    const diseaseEl = document.getElementById('statDiseaseRate');
    const healthyEl = document.getElementById('statHealthy');

    if (totalEl) this._animateCounter(totalEl, scans.length);

    if (scans.length === 0) {
      if (avgEl) avgEl.textContent = '--';
      if (diseaseEl) diseaseEl.textContent = '0%';
      if (healthyEl) healthyEl.textContent = '0%';
      return;
    }

    // Average grade
    const gradeMap = { 'Grade A': 4, 'Grade B': 3, 'Grade C': 2, 'Reject': 1 };
    const gradeLabels = { 4: 'A', 3: 'B', 2: 'C', 1: 'R' };
    const avgScore = scans.reduce((sum, s) => sum + (gradeMap[s.grade.label] || 2), 0) / scans.length;
    const avgLabel = gradeLabels[Math.round(avgScore)] || 'B';
    if (avgEl) avgEl.textContent = avgLabel;

    // Disease rate
    const diseased = scans.filter(s => !s.disease.isHealthy).length;
    const diseaseRate = ((diseased / scans.length) * 100).toFixed(0);
    if (diseaseEl) diseaseEl.textContent = diseaseRate + '%';

    // Healthy rate
    const healthyRate = (((scans.length - diseased) / scans.length) * 100).toFixed(0);
    if (healthyEl) healthyEl.textContent = healthyRate + '%';

    // Analytics page stats
    const analyticsTotal = document.getElementById('analyticsTotal');
    const analyticsPremium = document.getElementById('analyticsPremium');
    if (analyticsTotal) this._animateCounter(analyticsTotal, scans.length);
    if (analyticsPremium) {
      const premiumCount = scans.filter(s => s.grade.label === 'Grade A').length;
      analyticsPremium.textContent = ((premiumCount / scans.length) * 100).toFixed(0) + '%';
    }
  },

  _animateCounter(element, target) {
    const current = parseInt(element.textContent) || 0;
    if (current === target) return;
    
    const duration = 600;
    const start = performance.now();
    
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(current + (target - current) * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  },

  _updateGauge(scans) {
    const arc = document.getElementById('gaugeArc');
    const valueEl = document.getElementById('gaugeValue');
    if (!arc || !valueEl) return;

    if (scans.length === 0) {
      arc.style.strokeDashoffset = 188.5;
      valueEl.textContent = '--%';
      return;
    }

    const gradeMap = { 'Grade A': 100, 'Grade B': 75, 'Grade C': 50, 'Reject': 10 };
    const avgReadiness = scans.reduce((sum, s) => sum + (gradeMap[s.grade.label] || 50), 0) / scans.length;
    const readiness = Math.min(Math.round(avgReadiness), 100);

    const maxDash = 188.5;
    const offset = maxDash - (maxDash * readiness / 100);
    
    setTimeout(() => {
      arc.style.transition = 'stroke-dashoffset 1.2s ease';
      arc.style.strokeDashoffset = offset;
    }, 200);

    valueEl.textContent = readiness + '%';
    valueEl.style.color = readiness > 70 ? 'var(--color-success)' : readiness > 40 ? 'var(--color-warning)' : 'var(--color-error)';
  },

  _renderGradeChart(scans) {
    const canvas = document.getElementById('gradeChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // High DPI support
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 260 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '260px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 260;

    ctx.clearRect(0, 0, w, h);

    if (scans.length === 0) {
      ctx.fillStyle = '#64748B';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No data yet. Start scanning!', w / 2, h / 2);
      return;
    }

    // Count grades
    const grades = { 'Grade A': 0, 'Grade B': 0, 'Grade C': 0, 'Reject': 0 };
    scans.forEach(s => { grades[s.grade.label] = (grades[s.grade.label] || 0) + 1; });

    const data = [
      { label: 'A', value: grades['Grade A'], color: '#22C55E' },
      { label: 'B', value: grades['Grade B'], color: '#3B82F6' },
      { label: 'C', value: grades['Grade C'], color: '#F59E0B' },
      { label: 'R', value: grades['Reject'], color: '#EF4444' }
    ];

    const total = data.reduce((s, d) => s + d.value, 0);
    if (total === 0) return;

    // Draw donut chart
    const cx = w / 2;
    const cy = h / 2 - 10;
    const radius = Math.min(w, h) / 2 - 40;
    const innerRadius = radius * 0.6;

    let startAngle = -Math.PI / 2;
    data.forEach(d => {
      if (d.value === 0) return;
      const sliceAngle = (d.value / total) * 2 * Math.PI;
      
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, startAngle + sliceAngle);
      ctx.arc(cx, cy, innerRadius, startAngle + sliceAngle, startAngle, true);
      ctx.closePath();
      ctx.fillStyle = d.color;
      ctx.fill();

      // Label
      const midAngle = startAngle + sliceAngle / 2;
      const labelR = radius + 18;
      const lx = cx + Math.cos(midAngle) * (innerRadius + (radius - innerRadius) / 2);
      const ly = cy + Math.sin(midAngle) * (innerRadius + (radius - innerRadius) / 2);
      
      if (d.value / total > 0.08) {
        ctx.fillStyle = '#FFF';
        ctx.font = 'bold 12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(((d.value / total) * 100).toFixed(0) + '%', lx, ly);
      }

      startAngle += sliceAngle;
    });

    // Center text
    ctx.fillStyle = '#F1F5F9';
    ctx.font = 'bold 28px Space Grotesk, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(total, cx, cy - 6);

    ctx.fillStyle = '#94A3B8';
    ctx.font = '12px Inter, sans-serif';
    ctx.fillText('Total', cx, cy + 14);
  },

  _renderRecentScans(scans) {
    const container = document.getElementById('dashRecentScans');
    if (!container) return;

    if (scans.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📷</div>
          <div class="empty-state-title">No scans yet</div>
          <div class="empty-state-text">Start scanning dragon fruit to see results here.</div>
        </div>
      `;
      return;
    }

    const recent = scans.slice(0, 5);
    container.innerHTML = recent.map(s => {
      const date = new Date(s.timestamp);
      const timeStr = date.toLocaleDateString('en-PH', { month: 'short', day: 'numeric' }) + ', ' + 
                      date.toLocaleTimeString('en-PH', { hour: '2-digit', minute: '2-digit' });
      return `
        <div class="scan-item" onclick="HistoryManager.showDetail('${s.id}')">
          <img class="scan-thumb" src="${s.thumbnail}" alt="Scan ${s.id}">
          <div class="scan-info">
            <div class="scan-info-title">${s.grade.label} ${s.disease.isHealthy ? '' : '- ' + s.disease.name}</div>
            <div class="scan-info-meta">
              <span>${timeStr}</span>
              <span>|</span>
              <span>${s.details.processingTime}</span>
            </div>
          </div>
          <div class="scan-grade">
            <span class="grade-badge ${s.grade.class}">${s.grade.label.replace('Grade ', '')}</span>
          </div>
        </div>
      `;
    }).join('');
  },

  // Analytics charts
  renderAnalytics() {
    const scans = this._getScans();
    this._renderDiseaseTrend(scans);
    this._renderQualityTrend(scans);
    this._renderDiseaseBreakdown(scans);
    this.generateAIInsights(scans);
  },

  _renderDiseaseTrend(scans) {
    const canvas = document.getElementById('diseaseTrendChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 220 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '220px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 220;
    ctx.clearRect(0, 0, w, h);

    // Group by day (last 7 days)
    const days = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      days.push({
        date: d.toISOString().split('T')[0],
        label: d.toLocaleDateString('en-PH', { weekday: 'short' }),
        healthy: 0,
        diseased: 0
      });
    }

    scans.forEach(s => {
      const scanDate = new Date(s.timestamp).toISOString().split('T')[0];
      const day = days.find(d => d.date === scanDate);
      if (day) {
        if (s.disease.isHealthy) day.healthy++;
        else day.diseased++;
      }
    });

    const maxVal = Math.max(...days.map(d => d.healthy + d.diseased), 1);
    const padding = { top: 20, right: 20, bottom: 40, left: 35 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    // Grid lines
    ctx.strokeStyle = 'rgba(148,163,184,0.08)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
    }

    // Bars
    const barW = chartW / days.length;
    const barGap = barW * 0.3;
    const singleBarW = (barW - barGap) / 2;

    days.forEach((d, i) => {
      const x = padding.left + i * barW + barGap / 2;

      // Healthy bar
      const hH = (d.healthy / maxVal) * chartH;
      ctx.fillStyle = '#22C55E';
      ctx.beginPath();
      ctx.roundRect(x, padding.top + chartH - hH, singleBarW, hH, [3, 3, 0, 0]);
      ctx.fill();

      // Diseased bar
      const dH = (d.diseased / maxVal) * chartH;
      ctx.fillStyle = '#EF4444';
      ctx.beginPath();
      ctx.roundRect(x + singleBarW, padding.top + chartH - dH, singleBarW, dH, [3, 3, 0, 0]);
      ctx.fill();

      // Label
      ctx.fillStyle = '#64748B';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(d.label, x + (barW - barGap) / 2, h - padding.bottom + 20);
    });

    // Y-axis labels
    ctx.fillStyle = '#64748B';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
      const val = Math.round((maxVal / 4) * (4 - i));
      const y = padding.top + (chartH / 4) * i;
      ctx.fillText(val, padding.left - 8, y + 4);
    }
  },

  _renderQualityTrend(scans) {
    const canvas = document.getElementById('qualityTrendChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 220 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '220px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 220;
    ctx.clearRect(0, 0, w, h);

    // Group by day
    const days = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      days.push({
        date: d.toISOString().split('T')[0],
        label: d.toLocaleDateString('en-PH', { weekday: 'short' }),
        scores: []
      });
    }

    const gradeMap = { 'Grade A': 4, 'Grade B': 3, 'Grade C': 2, 'Reject': 1 };
    scans.forEach(s => {
      const scanDate = new Date(s.timestamp).toISOString().split('T')[0];
      const day = days.find(d => d.date === scanDate);
      if (day) day.scores.push(gradeMap[s.grade.label] || 2);
    });

    const padding = { top: 20, right: 20, bottom: 40, left: 35 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    // Grid
    ctx.strokeStyle = 'rgba(148,163,184,0.08)';
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();
    }

    // Line data
    const points = days.map((d, i) => {
      const avg = d.scores.length > 0 ? d.scores.reduce((a, b) => a + b, 0) / d.scores.length : null;
      const x = padding.left + (i / (days.length - 1)) * chartW;
      const y = avg !== null ? padding.top + chartH - ((avg - 1) / 3) * chartH : null;
      return { x, y, label: d.label, avg };
    });

    // Draw line
    const validPoints = points.filter(p => p.y !== null);
    if (validPoints.length > 1) {
      // Gradient fill
      const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
      gradient.addColorStop(0, 'rgba(233, 30, 99, 0.2)');
      gradient.addColorStop(1, 'rgba(233, 30, 99, 0.0)');

      ctx.beginPath();
      ctx.moveTo(validPoints[0].x, padding.top + chartH);
      validPoints.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.lineTo(validPoints[validPoints.length - 1].x, padding.top + chartH);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Line
      ctx.beginPath();
      ctx.moveTo(validPoints[0].x, validPoints[0].y);
      validPoints.forEach(p => ctx.lineTo(p.x, p.y));
      ctx.strokeStyle = '#E91E63';
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Dots
      validPoints.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = '#E91E63';
        ctx.fill();
        ctx.beginPath();
        ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#FFF';
        ctx.fill();
      });
    }

    // X labels
    ctx.fillStyle = '#64748B';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';
    points.forEach(p => {
      ctx.fillText(p.label, p.x, h - padding.bottom + 20);
    });

    // Y labels
    ctx.textAlign = 'right';
    const yLabels = ['R', 'C', 'B', 'A'];
    for (let i = 0; i < 4; i++) {
      const y = padding.top + chartH - (i / 3) * chartH;
      ctx.fillText(yLabels[i], padding.left - 8, y + 4);
    }

    if (validPoints.length === 0) {
      ctx.fillStyle = '#64748B';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No quality data yet', w / 2, h / 2);
    }
  },

  _renderDiseaseBreakdown(scans) {
    const canvas = document.getElementById('diseaseBreakdownChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 260 * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '260px';
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 260;
    ctx.clearRect(0, 0, w, h);

    // Count diseases
    const diseases = {};
    scans.forEach(s => {
      const name = s.disease.name;
      diseases[name] = (diseases[name] || 0) + 1;
    });

    const colors = {
      'Healthy': '#22C55E',
      'Anthracnose': '#EF4444',
      'Stem Canker': '#F97316',
      'Soft Rot': '#A855F7',
      'Pest Damage': '#F59E0B',
      'Sunburn': '#EC4899',
      'Fungal Spots': '#6366F1'
    };

    const data = Object.entries(diseases).map(([name, count]) => ({
      label: name, value: count, color: colors[name] || '#64748B'
    })).sort((a, b) => b.value - a.value);

    const total = data.reduce((s, d) => s + d.value, 0);

    if (total === 0) {
      ctx.fillStyle = '#64748B';
      ctx.font = '14px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No disease data yet', w / 2, h / 2);
      return;
    }

    // Horizontal bar chart
    const padding = { top: 10, right: 60, bottom: 10, left: 100 };
    const chartH = h - padding.top - padding.bottom;
    const barHeight = Math.min(30, chartH / data.length - 8);
    const maxVal = Math.max(...data.map(d => d.value));

    data.forEach((d, i) => {
      const y = padding.top + i * (barHeight + 8);
      const barW = (d.value / maxVal) * (w - padding.left - padding.right);

      // Bar
      ctx.fillStyle = d.color;
      ctx.beginPath();
      ctx.roundRect(padding.left, y, barW, barHeight, [0, 4, 4, 0]);
      ctx.fill();

      // Label
      ctx.fillStyle = '#94A3B8';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      ctx.fillText(d.label, padding.left - 8, y + barHeight / 2);

      // Value
      ctx.fillStyle = '#F1F5F9';
      ctx.font = 'bold 11px Inter, sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(`${d.value} (${((d.value / total) * 100).toFixed(0)}%)`, padding.left + barW + 8, y + barHeight / 2);
    });

    // Update legend
    const legendEl = document.getElementById('diseaseLegend');
    if (legendEl) {
      legendEl.innerHTML = data.map(d => `
        <div class="legend-item">
          <span class="legend-dot" style="background:${d.color}"></span>
          ${d.label}
        </div>
      `).join('');
    }
  },

  // Generate and render aggregated AI Farm Insights
  async generateAIInsights(scans) {
    const contentEl = document.getElementById('aiInsightsContent');
    const statusEl = document.getElementById('aiInsightsStatus');
    if (!contentEl) return;

    if (!scans || scans.length === 0) {
      if (statusEl) statusEl.textContent = 'No Data';
      contentEl.innerHTML = '<p style="color:var(--text-tertiary);font-size:13px;text-align:center;padding:24px 12px;margin:0;">Start scanning dragon fruit to unlock dynamic AI farm insights.</p>';
      return;
    }

    // --- Cloud AI API Configuration ---
    // Toggle cloud LLM analysis (requires an API Key from Groq or Google Gemini)
    const CLOUD_AI_ENABLED = false; // Set to true once you configure your key and endpoint below
    const API_KEY = "YOUR_API_KEY_HERE";
    const API_URL = "https://api.groq.com/openai/v1/chat/completions"; 
    const MODEL_NAME = "llama3-8b-8192";

    // Extract aggregated statistics
    const totalScans = scans.length;
    const premiumCount = scans.filter(s => s.grade.label === 'Grade A').length;
    const premiumRate = ((premiumCount / totalScans) * 100).toFixed(0);
    const diseaseCounts = {};
    scans.forEach(s => {
      if (!s.disease.isHealthy) {
        diseaseCounts[s.disease.name] = (diseaseCounts[s.disease.name] || 0) + 1;
      }
    });

    const isOnline = navigator.onLine;

    if (CLOUD_AI_ENABLED && isOnline) {
      if (statusEl) {
        statusEl.innerHTML = '⚡ Online AI';
        statusEl.style.color = '#22C55E';
      }
      try {
        const insights = await this._fetchCloudAI(totalScans, premiumRate, diseaseCounts, API_KEY, API_URL, MODEL_NAME);
        this._renderAIWidget(insights, contentEl);
      } catch (e) {
        console.error('Cloud AI failed, falling back to Local Heuristics', e);
        this._renderOfflineInsights(totalScans, premiumRate, diseaseCounts, contentEl, statusEl);
      }
    } else {
      this._renderOfflineInsights(totalScans, premiumRate, diseaseCounts, contentEl, statusEl);
    }
  },

  // Calls the cloud LLM using OpenAI-compatible SDK
  async _fetchCloudAI(totalScans, premiumRate, diseaseCounts, apiKey, apiUrl, modelName) {
    const diseaseSummary = Object.entries(diseaseCounts).map(([name, count]) => `${name}: ${count} cases`).join(', ');

    const prompt = `Analyze this dragon fruit farm data:
    Total Scans: ${totalScans} fruits
    Premium Grade A Rate: ${premiumRate}%
    Diseases detected: [${diseaseSummary || 'None'}]
    
    Provide strategic, growth-focused agronomic advice in JSON format matching the schema below.
    CRITICAL RULE: Do not use any em dash or — in your output text.
    
    JSON Schema:
    {
      "summary": "A concise 2-sentence summary of the farm health status.",
      "statusAlert": "healthy" | "warning" | "critical",
      "keyMetrics": [{"label": "string", "value": "string", "trend": "up"|"down"|"neutral"}],
      "recommendations": [{"severity": "high"|"medium"|"low", "action": "string", "rationale": "string"}]
    }`;

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: modelName,
        messages: [{ role: 'user', content: prompt }],
        response_format: { type: 'json_object' }
      })
    });

    const data = await response.json();
    return JSON.parse(data.choices[0].message.content);
  },

  // Generates on-device rules when the user has no network connection or cloud is disabled
  _renderOfflineInsights(total, premium, diseases, contentEl, statusEl) {
    if (statusEl) {
      statusEl.innerHTML = '📁 Local Engine';
      statusEl.style.color = 'var(--text-secondary)';
    }

    // Determine farm health status
    let status = 'healthy';
    let summary = 'Your dragon fruit farm shows stable health indicators with robust growth parameters.';
    const recommendations = [];

    const totalDiseased = Object.values(diseases).reduce((a, b) => a + b, 0);
    const diseaseRate = total > 0 ? (totalDiseased / total) * 100 : 0;

    if (diseaseRate > 20) {
      status = 'critical';
      summary = 'Warning: Active pathogen spread detected. Over 20% of scanned crops exhibit symptomatic infections.';
      recommendations.push({
        severity: 'high',
        action: 'Execute chemical treatment and containment protocol.',
        rationale: 'High disease prevalence poses a systemic risk to neighboring crop clusters. Isolate affected vines immediately.'
      });
    } else if (diseaseRate > 5 || premium < 50) {
      status = 'warning';
      summary = 'Alert: Minor quality drop observed. Monitor developing spots to maintain premium export grades.';
      recommendations.push({
        severity: 'medium',
        action: 'Inspect scale spacing and apply structural shading.',
        rationale: 'Sunburn and minor pest scars are reducing your Grade A premium rate. Address environmental stressors.'
      });
    } else {
      recommendations.push({
        severity: 'low',
        action: 'Continue standard hydration and monitoring cycles.',
        rationale: 'Crop quality is performing at peak parameters. Premium yield matches optimal target thresholds.'
      });
    }

    const localInsights = {
      summary: summary,
      statusAlert: status,
      keyMetrics: [
        { label: 'Premium Rate', value: `${premium}%`, trend: premium > 75 ? 'up' : 'neutral' },
        { label: 'Pathology Index', value: `${diseaseRate.toFixed(0)}%`, trend: diseaseRate > 10 ? 'up' : 'down' }
      ],
      recommendations: recommendations
    };

    this._renderAIWidget(localInsights, contentEl);
  },

  // Renders the AI Insight JSON object into custom widgets
  _renderAIWidget(data, container) {
    const alertStatusColors = {
      healthy: 'var(--color-success)',
      warning: 'var(--color-warning)',
      critical: 'var(--color-error)'
    };

    container.innerHTML = `
      <p style="font-size:13px; color:#F1F5F9; line-height:1.5; margin:0 0 16px;">
        ${data.summary}
      </p>

      <div style="display:flex; gap:12px; margin-bottom:16px;">
        ${data.keyMetrics.map(m => {
          const trendColors = {
            up: 'var(--color-success)',
            down: 'var(--color-error)',
            neutral: 'var(--text-tertiary)'
          };
          const trendIcons = {
            up: '▲',
            down: '▼',
            neutral: '●'
          };
          return `
            <div style="flex:1; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); padding:12px; border-radius:8px; display:flex; flex-direction:column; justify-content:center;">
              <div style="font-size:10px; color:var(--text-tertiary); font-weight:600; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">${m.label}</div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:16px; font-weight:700; color:#FFF;">${m.value}</span>
                <span style="font-size:10px; font-weight:bold; color:${trendColors[m.trend] || 'var(--text-tertiary)'};">
                  ${trendIcons[m.trend] || '●'}
                </span>
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <div style="display:flex; flex-direction:column; gap:8px;">
        ${data.recommendations.map(r => {
          const sevColors = {
            high: 'var(--color-error)',
            medium: 'var(--color-warning)',
            low: 'var(--color-success)'
          };
          const sevBg = {
            high: 'rgba(239,68,68,0.05)',
            medium: 'rgba(245,158,11,0.05)',
            low: 'rgba(34,197,94,0.05)'
          };
          const color = sevColors[r.severity] || 'var(--color-success)';
          const bg = sevBg[r.severity] || 'rgba(34,197,94,0.05)';
          return `
            <div class="ai-recommendation-card" style="background:${bg}; border-left: 3px solid ${color}; padding:12px; border-radius:4px; transition: all 0.2s ease;">
              <div style="font-size:13px; font-weight:700; color:#FFF; margin-bottom:2px;">${r.action}</div>
              <div style="font-size:11px; color:var(--text-secondary); line-height:1.4;">${r.rationale}</div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }
};
