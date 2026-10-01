/* =============================================
   PitayaGrade - Notification System
   ============================================= */

const NotificationManager = {
  notifications: [],

  init() {
    this.load();
    const dialog = document.getElementById('notificationDialog');
    document.getElementById('notificationsBtn')?.addEventListener('click', () => {
      this.load();
      this.renderList();
      dialog.showModal();
    });
    document.getElementById('notificationsClose')?.addEventListener('click', () => dialog.close());
    document.getElementById('notificationsRead')?.addEventListener('click', () => this.markAllRead());
    document.getElementById('notificationsClear')?.addEventListener('click', () => {
      const message = 'Clear all saved notifications?';
      if (typeof LanguageManager !== 'undefined' ? LanguageManager.confirm(message) : confirm(message)) this.clearAll();
    });
    window.addEventListener('storage', event => {
      if (event.key === 'pg_notifications' || event.key === null) this.load();
    });
    window.addEventListener('pg:scans-changed', () => this.scheduleSessionSummary());
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) this.scheduleSessionSummary();
    });
    this.scheduleSessionSummary();
  },

  load() {
    this.storageReadable = true;
    try {
      const value = JSON.parse(localStorage.getItem('pg_notifications') || '[]');
      if (!Array.isArray(value) || !value.every(n => n && Number.isFinite(n.id) &&
        typeof n.title === 'string' && typeof n.body === 'string' &&
        ['low', 'medium', 'high', 'success'].includes(n.severity) &&
        typeof n.icon === 'string' && typeof n.read === 'boolean' &&
        Number.isFinite(Date.parse(n.time)))) throw new Error('Invalid notifications');
      this.notifications = value;
    } catch {
      this.notifications = [];
      this.storageReadable = false;
    }
    this.updateBadge();
    this.renderList();
  },

  _commit(next) {
    if (!this.storageReadable) {
      ToastManager.show('Saved notifications could not be read. Original data has been preserved.', 'warning');
      return false;
    }
    try { localStorage.setItem('pg_notifications', JSON.stringify(next)); }
    catch {
      ToastManager.show('Notifications could not be saved. Existing alerts are unchanged.', 'warning');
      return false;
    }
    this.notifications = next;
    this.updateBadge();
    this.renderList();
    return true;
  },

  add(notification) {
    this.load();
    const notif = {
      id: Date.now() + Math.random(),
      title: notification.title,
      body: notification.body,
      severity: notification.severity || 'low', // low, medium, high, success
      icon: notification.icon || '🔔',
      time: new Date().toISOString(),
      read: false
    };
    if (notification.sessionKey) notif.sessionKey = notification.sessionKey;
    const saved = this._commit([notif, ...this.notifications].slice(0, 50));
    
    // Show toast
    ToastManager.show(notif.title, notif.severity === 'high' ? 'error' : notif.severity === 'medium' ? 'warning' : 'success');
    
    return saved ? notif : null;
  },

  remove(id) {
    this.load();
    return this._commit(this.notifications.filter(n => n.id !== id));
  },

  clearAll() {
    this.load();
    return this._commit([]);
  },

  markAllRead() {
    this.load();
    return this._commit(this.notifications.map(n => ({ ...n, read: true })));
  },

  getUnreadCount() {
    return this.notifications.filter(n => !n.read).length;
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

    if (!this.storageReadable) {
      list.textContent = 'Saved notifications could not be read. Original data has been preserved.';
      return;
    }

    if (this.notifications.length === 0) {
      list.innerHTML = '';
      list.appendChild(empty || this._createEmptyState());
      return;
    }

    list.innerHTML = this.notifications.map(n => {
      const timeAgo = this._timeAgo(n.time);
      return `
        <div class="notif-item severity-${n.severity}" data-id="${n.id}">
          <div class="notif-icon">${this._escape(n.icon)}</div>
          <div class="notif-content">
            <div class="notif-title">${n.read ? '' : '<span aria-hidden="true">● </span>'}<span>${this._escape(n.title)}</span></div>
            <div class="notif-body">${this._escape(n.body)}</div>
            <div class="notif-time">${timeAgo}</div>
          </div>
        </div>
      `;
    }).join('');
  },

  _escape(value) {
    return String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  },

  // Sessions use fixed 60-minute windows anchored at their first saved scan.
  _latestSession(scans) {
    let session = [];
    const sorted = [...scans].sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
    for (const scan of sorted) {
      if (!session.length || Date.parse(scan.timestamp) - Date.parse(session[0].timestamp) >= 3600000) session = [];
      session.push(scan);
    }
    return session;
  },

  scheduleSessionSummary(now = Date.now()) {
    clearTimeout(this.sessionTimer);
    if (typeof PitayaApp !== 'undefined' && PitayaApp.settings.scanAlerts === false) return;
    const session = this._latestSession(ScanStore.getScans());
    if (!session.length) return;
    const start = Date.parse(session[0].timestamp);
    if (!Number.isFinite(start) || start > now) return;
    const remaining = start + 3600000 - now;
    if (remaining > 0) {
      this.sessionTimer = setTimeout(() => this.scheduleSessionSummary(), remaining);
      return;
    }
    const key = String(session[0].id) + ':' + session[0].timestamp;
    this.load();
    try {
      if (localStorage.getItem('pg_last_session_summary') === key) return;
      if (!this.notifications.some(n => n.sessionKey === key)) {
        const counts = ['Grade A', 'Grade B', 'Grade C', 'Reject'].map(label =>
          `${label}: ${session.filter(s => s.grade.label === label).length}`).join(', ');
        const flagged = session.filter(s => s.disease && s.disease.name !== 'Healthy').length;
        const saved = this.add({ title: 'Session Summary',
          body: `${session.length} scans saved. ${counts}. ${flagged} with image-based disease flags; these are estimates.`,
          severity: flagged ? 'medium' : 'success', icon: '📊', sessionKey: key });
        if (!saved) return;
      }
      localStorage.setItem('pg_last_session_summary', key);
    } catch {
      // Saved notification itself is a duplicate guard if writing the marker fails.
      ToastManager.show('Session summary state could not be saved.', 'warning');
    }
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
    if (typeof PitayaApp !== 'undefined' && PitayaApp.settings.scanAlerts === false) return;
    const { grade, disease, confidence } = scanResult;

    // Disease alert
    if (disease && disease.name !== 'Healthy') {
      const severity = disease.confidence > 0.85 ? 'high' : disease.confidence > 0.65 ? 'medium' : 'low';
      this.add({
        title: `Possible ${disease.name}`,
        body: 'Image-based estimate, not a confirmed diagnosis. Inspect the fruit and consult an agricultural officer for confirmation.',
        severity: severity,
        icon: severity === 'high' ? '🚨' : '⚠️'
      });
    }

    // Reject alert
    if (grade.label === 'Reject') {
      this.add({
        title: 'Fruit Rejected',
        body: `Fruit classified as Reject with ${(grade.confidence * 100).toFixed(1)}% confidence. Verify the fruit against grading criteria before deciding its use.`,
        severity: 'high',
        icon: '❌'
      });
    }

    // Grade A celebration
    if (grade.label === 'Grade A' && grade.confidence > 0.9) {
      this.add({
        title: 'Premium Quality Detected',
        body: `Grade A fruit with ${(grade.confidence * 100).toFixed(1)}% confidence. Verify physical grading criteria before making market decisions.`,
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
    toast.innerHTML = `<span>${icons[type] || ''}</span><span>${NotificationManager._escape(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('leaving');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }
};
