/* =============================================
   PitayaGrade - Notification System
   ============================================= */

const NotificationManager = {
  notifications: [],

  init() {
    this.notifications = JSON.parse(localStorage.getItem('pg_notifications') || '[]');
    this.updateBadge();
  },

  add(notification) {
    const notif = {
      id: Date.now() + Math.random(),
      title: notification.title,
      body: notification.body,
      severity: notification.severity || 'low', // low, medium, high, success
      icon: notification.icon || '🔔',
      time: new Date().toISOString(),
      read: false
    };
    this.notifications.unshift(notif);
    if (this.notifications.length > 50) this.notifications.pop();
    this.save();
    this.updateBadge();
    this.renderList();
    
    // Show toast
    ToastManager.show(notif.title, notif.severity === 'high' ? 'error' : notif.severity === 'medium' ? 'warning' : 'success');
    
    return notif;
  },

  remove(id) {
    this.notifications = this.notifications.filter(n => n.id !== id);
    this.save();
    this.updateBadge();
    this.renderList();
  },

  clearAll() {
    this.notifications = [];
    this.save();
    this.updateBadge();
    this.renderList();
  },

  markAllRead() {
    this.notifications.forEach(n => n.read = true);
    this.save();
    this.updateBadge();
  },

  getUnreadCount() {
    return this.notifications.filter(n => !n.read).length;
  },

  save() {
    localStorage.setItem('pg_notifications', JSON.stringify(this.notifications));
  },

  updateBadge() {
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    const count = this.getUnreadCount();
    if (count > 0) {
      badge.textContent = count > 9 ? '9+' : count;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  },

  renderList() {
    const list = document.getElementById('notifList');
    const empty = document.getElementById('notifEmpty');
    if (!list) return;

    if (this.notifications.length === 0) {
      list.innerHTML = '';
      list.appendChild(empty || this._createEmptyState());
      return;
    }

    list.innerHTML = this.notifications.map(n => {
      const timeAgo = this._timeAgo(n.time);
      return `
        <div class="notif-item severity-${n.severity}" data-id="${n.id}">
          <div class="notif-icon">${n.icon}</div>
          <div class="notif-content">
            <div class="notif-title">${n.title}</div>
            <div class="notif-body">${n.body}</div>
            <div class="notif-time">${timeAgo}</div>
          </div>
        </div>
      `;
    }).join('');
  },

  _createEmptyState() {
    const div = document.createElement('div');
    div.className = 'empty-state';
    div.innerHTML = `
      <div class="empty-state-icon">🔔</div>
      <div class="empty-state-title">No Notifications</div>
      <div class="empty-state-text">You're all caught up. Notifications will appear here when issues are detected.</div>
    `;
    return div;
  },

  _timeAgo(dateStr) {
    const now = new Date();
    const date = new Date(dateStr);
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },

  // Generate notifications based on scan results
  generateScanAlert(scanResult) {
    const { grade, disease, confidence } = scanResult;

    // Disease alert
    if (disease && disease.name !== 'Healthy') {
      const severity = disease.confidence > 0.85 ? 'high' : disease.confidence > 0.65 ? 'medium' : 'low';
      this.add({
        title: `${disease.name} Detected`,
        body: `Disease detected with ${(disease.confidence * 100).toFixed(1)}% confidence. ${this._getDiseaseAdvice(disease.name)}`,
        severity: severity,
        icon: severity === 'high' ? '🚨' : '⚠️'
      });
    }

    // Reject alert
    if (grade.label === 'Reject') {
      this.add({
        title: 'Fruit Rejected',
        body: `Fruit classified as Reject with ${(grade.confidence * 100).toFixed(1)}% confidence. Remove from harvest batch.`,
        severity: 'high',
        icon: '❌'
      });
    }

    // Grade A celebration
    if (grade.label === 'Grade A' && grade.confidence > 0.9) {
      this.add({
        title: 'Premium Quality Detected',
        body: `Excellent! Grade A fruit with ${(grade.confidence * 100).toFixed(1)}% confidence. Ready for premium market.`,
        severity: 'success',
        icon: '🌟'
      });
    }
  },

  _getDiseaseAdvice(diseaseName) {
    const advice = {
      'Anthracnose': 'Consider applying fungicide. Monitor nearby fruits.',
      'Stem Canker': 'Isolate affected area. Consult agricultural officer.',
      'Soft Rot': 'Remove affected fruit immediately to prevent spread.',
      'Pest Damage': 'Inspect for pest colonies. Consider pest management.',
      'Sunburn': 'Provide shade protection for exposed fruits.',
      'Fungal Spots': 'Apply appropriate fungicide treatment.'
    };
    return advice[diseaseName] || 'Monitor closely and consult an expert.';
  },

  // Generate weekly summary
  generateWeeklySummary(scans) {
    if (scans.length === 0) return;

    const gradeA = scans.filter(s => s.grade.label === 'Grade A').length;
    const diseased = scans.filter(s => s.disease.name !== 'Healthy').length;
    const total = scans.length;

    this.add({
      title: 'Session Summary',
      body: `${total} fruits scanned. ${gradeA} Grade A (${((gradeA/total)*100).toFixed(0)}%). ${diseased} with issues detected.`,
      severity: diseased > total * 0.3 ? 'medium' : 'success',
      icon: '📊'
    });
  }
};

/* Toast Manager */
const ToastManager = {
  show(message, type = 'info', duration = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✅', warning: '⚠️', error: '🚨', info: 'ℹ️' };
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('leaving');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
};
