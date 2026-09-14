/* =============================================
   PitayaGrade - Main App Controller
   Routing, state management, initialization
   ============================================= */

const PitayaApp = {
  currentView: 'dashboard',
  settings: {
    language: 'en',
    offlineMode: false,
    threshold: 65,
    selectedModel: 'yolov8-nano'
  },

  init() {
    // Load settings
    const saved = ScanStore.read('pg_settings', {}, value => value && typeof value === 'object' && !Array.isArray(value));
    this.settings = { ...this.settings, ...saved };
    this.settings.threshold = Number.isFinite(Number(this.settings.threshold)) ? Math.max(10, Math.min(95, Number(this.settings.threshold))) : 65;
    this.settings.offlineMode = this.settings.offlineMode === true;
    ModelInference.CONF_THRESHOLD = this.settings.threshold / 100;
    if (!ModelInference.selectModel(this.settings.selectedModel)) {
      this.settings.selectedModel = ModelInference.getSelectedModel().id;
    }

    // Initialize modules
    Scanner.init();
    LiveScanner.init();
    DashboardManager.init();
    HistoryManager.init();
    ReportsManager.init();

    // Bind navigation
    this._bindNav();
    this._bindHeader();
    this._bindModal();
    this._bindSettings();
    const refreshData = () => {
      DashboardManager.refresh();
      HistoryManager.refresh();
      ReportsManager.invalidate();
      if (this.currentView === 'analytics') DashboardManager.renderAnalytics();
    };
    window.addEventListener('pg:scans-changed', refreshData);
    window.addEventListener('storage', event => {
      if (event.key === 'pg_scans' || event.key === null) refreshData();
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) LiveScanner.cleanup();
    });
    window.addEventListener('pagehide', () => LiveScanner.cleanup());
    window.addEventListener('online', () => this._checkConnectivity());
    window.addEventListener('offline', () => this._checkConnectivity());
    window.addEventListener('resize', () => {
      clearTimeout(this.resizeTimer);
      this.resizeTimer = setTimeout(() => {
        if (this.currentView === 'dashboard') DashboardManager.refresh();
        if (this.currentView === 'analytics') DashboardManager.renderAnalytics();
      }, 150);
    });
    if (ScanStore.warnings.size) ToastManager.show('Some saved data could not be loaded. Original data has been preserved.', 'warning', 8000);

    // Handle back button
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '') || 'dashboard';
      this.navigate(hash, false);
    });

    // Initial route
    const initialView = window.location.hash.replace('#', '') || 'dashboard';
    this.navigate(initialView, false);

    // Hide splash after load
    setTimeout(() => {
      const splash = document.getElementById('splashScreen');
      if (splash) splash.classList.add('hidden');
    }, 1800);

    // First-time tutorial
    Tutorial.init();

    // Simulate connectivity check
    this._checkConnectivity();
    setInterval(() => this._checkConnectivity(), 30000);

  },

  _bindNav() {
    const navItems = document.querySelectorAll('.bottom-nav .nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const view = item.dataset.view;
        if (view) this.navigate(view);
      });
    });
  },

  _bindHeader() {},

  _bindModal() {
    const modal = document.getElementById('detailModal');
    const backdrop = document.getElementById('modalBackdrop');
    const closeBtn = document.getElementById('modalCloseBtn');

    const closeModal = () => {
      modal.classList.remove('open');
      backdrop.classList.remove('open');
    };

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (backdrop) backdrop.addEventListener('click', closeModal);
    document.addEventListener('keydown', event => { if (event.key === 'Escape') closeModal(); });
  },

  _bindSettings() {
    const modelSelect = document.getElementById('modelSelect');
    const selectedModelName = document.getElementById('selectedModelName');
    if (modelSelect && selectedModelName && typeof ModelInference !== 'undefined') {
      const models = ModelInference.getAvailableModels();
      modelSelect.innerHTML = '';
      models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = model.name;
        modelSelect.appendChild(option);
      });
      const updateSelectedModel = () => {
        const model = ModelInference.getSelectedModel();
        modelSelect.value = model.id;
        selectedModelName.textContent = model.name + ' (bundled ONNX)';
      };
      updateSelectedModel();
      modelSelect.addEventListener('change', () => {
        const previous = this.settings.selectedModel;
        if (!ModelInference.selectModel(modelSelect.value)) {
          modelSelect.value = previous;
          return;
        }
        this.settings.selectedModel = ModelInference.getSelectedModel().id;
        if (!this._saveSettings()) {
          this.settings.selectedModel = previous;
          ModelInference.selectModel(previous);
        }
        updateSelectedModel();
      });
    }

    const threshold = document.getElementById('detectionThreshold');
    threshold.value = this.settings.threshold;
    document.getElementById('thresholdValue').textContent = this.settings.threshold + '%';
    threshold.addEventListener('input', () => {
      document.getElementById('thresholdValue').textContent = threshold.value + '%';
    });
    threshold.addEventListener('change', () => {
      const previous = this.settings.threshold;
      this.settings.threshold = Number(threshold.value);
      if (!this._saveSettings()) this.settings.threshold = previous;
      threshold.value = this.settings.threshold;
      document.getElementById('thresholdValue').textContent = this.settings.threshold + '%';
      ModelInference.CONF_THRESHOLD = this.settings.threshold / 100;
    });
    // English is the only implemented translation; the pending option is disabled.

    // Offline toggle
    const offlineToggle = document.getElementById('toggleOffline');
    if (offlineToggle) {
      if (this.settings.offlineMode) offlineToggle.classList.add('on');
      offlineToggle.setAttribute('aria-checked', String(this.settings.offlineMode));
      offlineToggle.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); offlineToggle.click(); }
      });
      offlineToggle.addEventListener('click', () => {
        this.settings.offlineMode = !this.settings.offlineMode;
        if (!this._saveSettings()) {
          this.settings.offlineMode = !this.settings.offlineMode;
          return;
        }
        offlineToggle.classList.toggle('on', this.settings.offlineMode);
        offlineToggle.setAttribute('aria-checked', String(this.settings.offlineMode));
        this._checkConnectivity();
        ToastManager.show(`Offline mode ${this.settings.offlineMode ? 'enabled' : 'disabled'}`, 'info');
      });
    }

    // Clear data
    const clearBtn = document.getElementById('clearDataBtn');
    if (clearBtn) {
      clearBtn.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); clearBtn.click(); }
      });
      clearBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete all scan records? This cannot be undone.')) {
          try {
            ScanStore.clear();
            document.getElementById('detailModal').classList.remove('open');
            document.getElementById('modalBackdrop').classList.remove('open');
            ToastManager.show('All scan records cleared', 'info');
          } catch (error) { ToastManager.show('Unable to clear scan records.', 'error'); }
        }
      });
    }
  },

  navigate(viewName, updateHash = true) {
    // Valid views
    const validViews = ['dashboard', 'scan', 'history', 'analytics', 'reports', 'settings'];
    if (!validViews.includes(viewName)) viewName = 'dashboard';

    // Hide all views
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

    // Show target view
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    // Update nav
    document.querySelectorAll('.bottom-nav .nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`[data-view="${viewName}"]`);
    if (navItem) navItem.classList.add('active');

    // Update hash
    if (updateHash) window.location.hash = viewName;

    this.currentView = viewName;

    // Cleanup live scanner when navigating away from scan
    if (viewName !== 'scan' && typeof LiveScanner !== 'undefined') {
      LiveScanner.cleanup();
    }

    // Refresh view-specific content
    if (viewName === 'dashboard') {
      DashboardManager.refresh();
    } else if (viewName === 'analytics') {
      setTimeout(() => DashboardManager.renderAnalytics(), 100);
    } else if (viewName === 'history') {
      HistoryManager.refresh();
    }

    // Scroll to top
    if (target) target.scrollTop = 0;
  },

  _saveSettings() {
    try {
      localStorage.setItem('pg_settings', JSON.stringify(this.settings));
      return true;
    } catch (error) {
      ToastManager.show('Settings could not be saved.', 'error');
      return false;
    }
  },

  _checkConnectivity() {
    const dot = document.getElementById('connectionDot');
    if (!dot) return;

    if (this.settings.offlineMode || !navigator.onLine) {
      dot.classList.add('offline');
      dot.title = 'Offline — scanning runs on this device';
    } else {
      dot.classList.remove('offline');
      dot.title = 'Connected — scanning runs on this device';
    }
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  PitayaApp.init();
});

/* =============================================
   First-Time Tutorial
   ============================================= */
const Tutorial = {
  current: 0,

  steps: [
    {
      title: 'Welcome to PitayaGrade!',
      icon: '&#127815;',
      desc: 'Your AI-powered dragon fruit grading assistant. Let us show you around in just a few steps.',
      target: null,
      badge: 'Welcome',
    },
    {
      title: 'Dashboard',
      icon: '&#128200;',
      desc: 'This is your Home screen. See your total scans, average grade, disease rate, and harvest readiness at a glance.',
      target: '#nav-dashboard',
      badge: 'Step 1 of 5',
    },
    {
      title: 'Scan a Fruit',
      icon: '&#128247;',
      desc: 'Tap Scan to capture or upload a dragon fruit photo. The app grades the image and estimates visible symptoms. Processing time depends on your device.',
      target: '#nav-scan',
      badge: 'Step 2 of 5',
    },
    {
      title: 'Scan History',
      icon: '&#128203;',
      desc: 'Every scan is saved here automatically. Filter by grade, search by notes, and view full details for any past assessment.',
      target: '#nav-history',
      badge: 'Step 3 of 5',
    },
    {
      title: 'Analytics',
      icon: '&#128202;',
      desc: 'Track disease trends, quality over time, and grade distribution across all your scans. Great for farm-level decision making.',
      target: '#nav-analytics',
      badge: 'Step 4 of 5',
    },
    {
      title: 'Settings',
      icon: '&#9881;',
      desc: 'Configure your language, detection threshold, and offline mode here. You can also clear all scan data from this page.',
      target: '#nav-settings',
      badge: 'Step 5 of 5',
    },
  ],

  init() {
    try { if (localStorage.getItem('pg_tutorial_done')) return; } catch (error) { return; }
    setTimeout(() => this.show(), 2200);
  },

  show() {
    const overlay = document.getElementById('tutorialOverlay');
    if (!overlay) return;
    this.current = 0;
    this._buildDots();
    this._renderStep();
    overlay.classList.add('active');

    document.getElementById('tutorialNext').addEventListener('click', () => this.next());
    document.getElementById('tutorialSkip').addEventListener('click', () => this.done());
  },

  next() {
    this.current++;
    if (this.current >= this.steps.length) {
      this.done();
    } else {
      this._renderStep();
    }
  },

  done() {
    const overlay = document.getElementById('tutorialOverlay');
    overlay.classList.remove('active', 'spotlight-mode');
    try { localStorage.setItem('pg_tutorial_done', 'true'); } catch (error) { /* Tutorial can still close without storage. */ }
    this._clearSpotlight();
  },

  _renderStep() {
    const step = this.steps[this.current];
    const isLast = this.current === this.steps.length - 1;
    const isFirst = this.current === 0;

    document.getElementById('tutorialBadge').textContent = step.badge;
    document.getElementById('tutorialIcon').innerHTML = step.icon;
    document.getElementById('tutorialTitle').textContent = step.title;
    document.getElementById('tutorialDesc').textContent = step.desc;
    document.getElementById('tutorialNext').innerHTML =
      (isLast ? 'Done &#10003;' : 'Next') +
      (isLast ? '' : ' <svg viewBox="0 0 24 24" style="width:16px;height:16px;stroke:white;fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round"><polyline points="9 18 15 12 9 6"/></svg>');
    document.getElementById('tutorialSkip').style.display = isFirst ? 'none' : 'block';

    this._updateDots();

    const overlay = document.getElementById('tutorialOverlay');
    if (step.target) {
      overlay.classList.add('spotlight-mode');
      this._spotlightEl(step.target);
    } else {
      overlay.classList.remove('spotlight-mode');
      this._clearSpotlight();
    }
  },

  _spotlightEl(selector) {
    const el = document.querySelector(selector);
    const spot = document.getElementById('tutorialSpotlight');
    if (!el || !spot) return;
    const r = el.getBoundingClientRect();
    const pad = 6;
    spot.style.top    = (r.top    - pad) + 'px';
    spot.style.left   = (r.left   - pad) + 'px';
    spot.style.width  = (r.width  + pad * 2) + 'px';
    spot.style.height = (r.height + pad * 2) + 'px';
  },

  _clearSpotlight() {
    const spot = document.getElementById('tutorialSpotlight');
    if (spot) { spot.style.width = '0'; spot.style.height = '0'; }
  },

  _buildDots() {
    const container = document.getElementById('tutorialDots');
    container.innerHTML = '';
    this.steps.forEach((_, i) => {
      const d = document.createElement('div');
      d.className = 'tutorial-dot' + (i === 0 ? ' active' : '');
      container.appendChild(d);
    });
  },

  _updateDots() {
    document.querySelectorAll('.tutorial-dot').forEach((d, i) => {
      d.classList.toggle('active', i === this.current);
    });
  },
};
