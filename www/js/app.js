/* =============================================
   PitayaGrade - Main App Controller
   Routing, state management, initialization
   ============================================= */

const PitayaApp = {
  currentView: 'dashboard',
  settings: {
    language: 'en',
    offlineMode: false,
    threshold: 65
  },

  init() {
    // Load settings
    const saved = localStorage.getItem('pg_settings');
    if (saved) this.settings = { ...this.settings, ...JSON.parse(saved) };

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
  },

  _bindSettings() {
    // Language toggle
    const langBtn = document.getElementById('toggleLangBtn');
    if (langBtn) {
      langBtn.addEventListener('click', () => {
        this.settings.language = this.settings.language === 'en' ? 'fil' : 'en';
        this._saveSettings();
        const langLabel = document.getElementById('currentLang');
        if (langLabel) langLabel.textContent = this.settings.language === 'en' ? 'English' : 'Filipino';
        ToastManager.show(`Language set to ${this.settings.language === 'en' ? 'English' : 'Filipino'}`, 'info');
      });
    }

    // Offline toggle
    const offlineToggle = document.getElementById('toggleOffline');
    if (offlineToggle) {
      if (this.settings.offlineMode) offlineToggle.classList.add('on');
      offlineToggle.addEventListener('click', () => {
        this.settings.offlineMode = !this.settings.offlineMode;
        offlineToggle.classList.toggle('on');
        this._saveSettings();
        this._checkConnectivity();
        ToastManager.show(`Offline mode ${this.settings.offlineMode ? 'enabled' : 'disabled'}`, 'info');
      });
    }

    // Clear data
    const clearBtn = document.getElementById('clearDataBtn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete all scan records? This cannot be undone.')) {
          localStorage.removeItem('pg_scans');
          DashboardManager.refresh();
          HistoryManager.refresh();
          ToastManager.show('All data cleared', 'info');
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
    localStorage.setItem('pg_settings', JSON.stringify(this.settings));
  },

  _checkConnectivity() {
    const dot = document.getElementById('connectionDot');
    if (!dot) return;

    if (this.settings.offlineMode) {
      dot.classList.add('offline');
      dot.title = 'Offline Mode (TFLite)';
    } else {
      dot.classList.remove('offline');
      dot.title = 'Online (Cloud)';
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
      desc: 'Tap the Scan button to capture or upload a dragon fruit photo. The AI will grade it and detect any disease in under 2 seconds.',
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
    if (localStorage.getItem('pg_tutorial_done')) return;
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
    localStorage.setItem('pg_tutorial_done', 'true');
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
