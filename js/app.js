/* ======================================   PitayaGrade - Main App Controller
   Routing, state management, initialization
   ============================================= */

const PitayaApp = {
  currentView: 'dashboard',
  settings: {
    language: 'en',
    offlineMode: false,
    scanAlerts: true,
    threshold: 25,
    detectorTuningVersion: 3,
    modelDefaultVersion: 3,
    selectedModel: 'efficientnet-b3-quality',
    selectedDiseaseModel: 'yolov8n-disease-seg'
  },

  async init() {
    await ScanStore.init();
    // Load settings
    const saved = ScanStore.read('pg_settings', {}, value => value && typeof value === 'object' && !Array.isArray(value));
    const savedTuningVersion = Number(saved.detectorTuningVersion);
    const migrateModelDefault = Number(saved.modelDefaultVersion) < 3;
    const migrateTuningVersion = savedTuningVersion !== 3;
    const migrateLegacyThreshold = (!Number.isFinite(savedTuningVersion) || savedTuningVersion < 2) && Number(saved.threshold) === 65;
    const migrateDefaultThreshold = savedTuningVersion === 2 && Number(saved.threshold) === 50;
    this.settings = { ...this.settings, ...saved };
    if (migrateModelDefault) this.settings.selectedModel = 'efficientnet-b3-quality';
    if (migrateLegacyThreshold) this.settings.threshold = 50;
    if (migrateDefaultThreshold) this.settings.threshold = 25;
    this.settings.threshold = Number.isFinite(Number(this.settings.threshold)) ? Math.max(10, Math.min(95, Number(this.settings.threshold))) : 25;
    this.settings.detectorTuningVersion = 3;
    this.settings.modelDefaultVersion = 3;
    this.settings.offlineMode = this.settings.offlineMode === true;
    this.settings.scanAlerts = this.settings.scanAlerts !== false;
    this.settings.language = this.settings.language === 'fil' ? 'fil' : 'en';
    LanguageManager.init(this.settings.language);
    ModelInference.CONF_THRESHOLD = this.settings.threshold / 100;
    if (!ModelInference.selectModel(this.settings.selectedModel)) {
      this.settings.selectedModel = ModelInference.getSelectedModel().id;
    }
    ModelInference.selectDiseaseModel(this.settings.selectedDiseaseModel);

    // Initialize modules
    NotificationManager.init();
    Scanner.init();
    LiveScanner.init();
    DashboardManager.init();
    HistoryManager.init();
    ReportsManager.init();
    if (migrateTuningVersion || migrateModelDefault) this._saveSettings();

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
    const scanAlerts = document.getElementById('scanAlerts');
    scanAlerts.checked = this.settings.scanAlerts;
    scanAlerts.addEventListener('change', () => {
      const previous = this.settings.scanAlerts;
      this.settings.scanAlerts = scanAlerts.checked;
      if (!this._saveSettings()) this.settings.scanAlerts = previous;
      scanAlerts.checked = this.settings.scanAlerts;
      NotificationManager.scheduleSessionSummary();
    });
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
        selectedModelName.textContent = model.name + ' + trained non-fruit gate';
        const accuracy = document.getElementById('modelAccuracyMetric');
        const f1 = document.getElementById('modelF1Metric');
        const training = document.getElementById('modelTrainingMetric');
        const percent = value => `${(value * 100).toFixed(2)}%`;
        if (model.evaluation) {
          const accuracyLabel = model.evaluation.scope === 'photo-scanner' ? 'photo scanner accuracy' : 'model accuracy';
          accuracy.textContent = `${percent(model.evaluation.accuracy)} ${accuracyLabel} on test photos (n=${model.evaluation.sampleCount})`;
          f1.textContent = `Macro F1 ${percent(model.evaluation.macroF1)} · Precision ${percent(model.evaluation.macroPrecision)} · Recall ${percent(model.evaluation.macroRecall)}`;
          training.textContent = model.evaluation.note || `Human-reviewed frozen split · ONNX · ${model.inputSize}×${model.inputSize}`;
        } else {
          accuracy.textContent = 'Not validated for the deployed pipeline';
          f1.textContent = 'Pending linked evaluation results';
          training.textContent = 'See retained training experiment outputs';
        }
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

    const diseaseModelSelect = document.getElementById('diseaseModelSelect');
    const selectedDiseaseModelName = document.getElementById('selectedDiseaseModelName');
    if (diseaseModelSelect && selectedDiseaseModelName && typeof ModelInference !== 'undefined') {
      const diseaseModels = ModelInference.getDiseaseModelCatalog();
      diseaseModelSelect.innerHTML = '';
      diseaseModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.disabled = !ModelInference.canSelectDiseaseModel(model);
        option.textContent = model.available ? model.name : 'YOLOv8n-Seg — pending';
        diseaseModelSelect.appendChild(option);
      });
      const active = ModelInference.getSelectedDiseaseModel();
      diseaseModelSelect.value = active?.id || diseaseModels[0]?.id || '';
      selectedDiseaseModelName.textContent = active
        ? `${active.name} (verified bundled ONNX)`
        : 'HSV fallback active; segmentation model pending';
      diseaseModelSelect.addEventListener('change', () => {
        if (!ModelInference.selectDiseaseModel(diseaseModelSelect.value)) return;
        this.settings.selectedDiseaseModel = diseaseModelSelect.value;
        if (!this._saveSettings()) return;
        selectedDiseaseModelName.textContent = `${ModelInference.getSelectedDiseaseModel().name} (verified bundled ONNX)`;
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
    const language = document.getElementById('languageSelect');
    language.value = this.settings.language;
    language.addEventListener('change', () => {
      const previous = this.settings.language;
      this.settings.language = language.value;
      if (!this._saveSettings()) this.settings.language = previous;
      language.value = this.settings.language;
      LanguageManager.setLanguage(this.settings.language);
    });

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
      clearBtn.addEventListener('click', async () => {
        if (LanguageManager.confirm('Delete all scan records and rejection testing feedback? This cannot be undone.')) {
          try {
            await ScanStore.clear();
            document.getElementById('detailModal').classList.remove('open');
            document.getElementById('modalBackdrop').classList.remove('open');
            ToastManager.show('All local testing records cleared', 'info');
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

const WebAppInstall = {
  promptEvent: null,
  init() {
    const row = document.getElementById('installAppRow');
    const button = document.getElementById('installAppBtn');
    const status = document.getElementById('installAppStatus');
    if (!row || !button || !status) return;
    const standalone = window.matchMedia?.('(display-mode: standalone)').matches || navigator.standalone === true;
    if (standalone) return;
    row.style.display = 'flex';
    window.addEventListener('beforeinstallprompt', event => {
      event.preventDefault();
      this.promptEvent = event;
      button.disabled = false;
      status.textContent = 'Install for quick access and offline app files';
    });
    button.addEventListener('click', async () => {
      if (!this.promptEvent) return;
      button.disabled = true;
      try {
        await this.promptEvent.prompt();
        const choice = await this.promptEvent.userChoice;
        this.promptEvent = null;
        status.textContent = choice.outcome === 'accepted' ? 'Installation accepted' : 'Install from the browser menu when ready';
      } catch (error) {
        button.disabled = false;
        status.textContent = 'Install from the browser menu when ready';
      }
    });
    window.addEventListener('appinstalled', () => {
      this.promptEvent = null;
      row.style.display = 'none';
      ToastManager.show('PitayaGrade installed', 'success');
    });
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  PitayaApp.init();
  WebAppInstall.init();
  const isLocalPreview = ['localhost', '127.0.0.1'].includes(window.location.hostname);
  if ('serviceWorker' in navigator && location.protocol === 'https:' && !isLocalPreview) {
    const hadController = Boolean(navigator.serviceWorker.controller);
    let refreshingForUpdate = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!hadController || refreshingForUpdate) return;
      if (Scanner.isProcessing || LiveScanner.isActive) {
        ToastManager.show('PitayaGrade updated. Reload after the current scan to use the new version.', 'info', 10000);
        return;
      }
      refreshingForUpdate = true;
      window.location.reload();
    });
    navigator.serviceWorker.register('./service-worker.js').then(registration => {
      const reportReadyUpdate = () => {
        if (registration.waiting && navigator.serviceWorker.controller) {
          ToastManager.show('A PitayaGrade update is ready. Reload the page to use it.', 'info', 8000);
        }
      };
      reportReadyUpdate();
      registration.addEventListener('updatefound', () => {
        registration.installing?.addEventListener('statechange', event => {
          if (event.target.state === 'installed') reportReadyUpdate();
        });
      });
    }).catch(error => console.warn('Offline web support could not be enabled:', error));
  }
});

/* ======================================   First-Time Tutorial
   ============================================= */
const Tutorial = {
  current: 0,

  steps: [
    {
      title: 'Welcome to PitayaGrade!',
      icon: '<svg class="tutorial-fruit-art" viewBox="0 0 48 48" role="img" aria-label="Dragon fruit" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="tutorialFruitSkin" x1="12" y1="12" x2="35" y2="43" gradientUnits="userSpaceOnUse"><stop stop-color="#ff6b9a"/><stop offset="1" stop-color="#e91e63"/></linearGradient></defs><g fill="#8bc34a" stroke="#b8e986" stroke-width=".7" stroke-linejoin="round"><path d="M20 17C16 11 16 6 18 3c4 3 7 8 8 14z"/><path d="M16 20C10 16 6 15 3 17c2 4 7 7 13 8z"/><path d="M15 29C9 28 5 30 3 33c4 3 8 3 13 1z"/><path d="M18 36c-4 4-5 8-3 11 4-2 7-6 9-11z"/><path d="M31 20c5-5 10-6 13-4-2 4-7 7-13 9z"/><path d="M33 29c6-1 10 1 12 4-4 3-8 3-13 1z"/><path d="M30 36c4 4 5 8 3 11-4-2-7-6-9-11z"/></g><path d="M24 13c8 0 13 7 13 16 0 10-6 17-13 17S11 39 11 29c0-9 5-16 13-16z" fill="url(#tutorialFruitSkin)" stroke="#ff9db8" stroke-width="1"/><g fill="#ffd2df" opacity=".8"><circle cx="19" cy="22" r=".8"/><circle cx="27" cy="20" r=".7"/><circle cx="31" cy="27" r=".8"/><circle cx="18" cy="31" r=".7"/><circle cx="25" cy="35" r=".8"/><circle cx="29" cy="40" r=".6"/></g></svg>',
      desc: 'Your AI-powered dragon fruit grading assistant. Let us show you around in just a few steps.',
      target: null,
      badge: 'Welcome',
    },
    {
      title: 'Dashboard',
      icon: '&#128200;',
      desc: 'This is your Home screen. See total scans, average grade, visible-symptom estimates, and harvest readiness at a glance.',
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
      desc: 'Track visible-symptom estimates, quality over time, and grade distribution across all your scans.',
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
    const edge = 8;
    const left = Math.max(edge, r.left - pad);
    const top = Math.max(edge, r.top - pad);
    const right = Math.min(window.innerWidth - edge, r.right + pad);
    const bottom = Math.min(window.innerHeight - edge, r.bottom + pad);
    spot.style.top = top + 'px';
    spot.style.left = left + 'px';
    spot.style.width = Math.max(0, right - left) + 'px';
    spot.style.height = Math.max(0, bottom - top) + 'px';
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
