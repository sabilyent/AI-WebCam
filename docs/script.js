/**
 * AI-WebCam: Interactive Simulator & Educational Lab
 * Fully client-side logic for demonstrations, animations, SQLite3 mock, and real camera support.
 */

// ==========================================
// 1. Mock SQLite3 Database Store (In-Memory)
// ==========================================
const SQLiteDB = {
  plates: [
    { id: 1, plate: "WXY 8899", owner: "Cikgu Sarah", role: "Guru Kelas 4 Amanah", status: "Dibenarkan" },
    { id: 2, plate: "VAB 1234", owner: "En. Roslan", role: "Pengetua Sekolah", status: "Dibenarkan" },
    { id: 3, plate: "BEE 7777", owner: "Van Katering", role: "Pelawat / Kontraktor", status: "Perhatian" },
    { id: 4, plate: "PEN 9999", owner: "Cikgu Azman", role: "Guru Disiplin", status: "Dibenarkan" }
  ],
  faces: [
    { id: 1, name: "Danial Hakim", role: "Murid 5 Arif", category: "Murid", avatar: "👦" },
    { id: 2, name: "Aina Sofea", role: "Pengawas Tingkatan 4", category: "Pengawas", avatar: "👧" },
    { id: 3, name: "Cikgu Azizan", role: "Guru Bertugas", category: "Guru", avatar: "👨‍🏫" },
    { id: 4, name: "Nurul Huda", role: "Ketua Tingkatan 3", category: "Murid", avatar: "👩" }
  ],
  logs: [
    { id: 101, time: "07:35:12 AM", mode: "Nombor Plat", result: "VAB 1234 (En. Roslan)", confidence: "99.4%", match: "Dibenarkan" },
    { id: 102, time: "07:41:05 AM", mode: "Pengecaman Wajah", result: "Danial Hakim (5 Arif)", confidence: "98.1%", match: "Hadir Ditanda" }
  ]
};

// ==========================================
// 2. Interactive Sample Datasets for Simulator
// ==========================================
const SimulatorModes = {
  plate: {
    name: "Nombor Plat Kenderaan",
    hudTitle: "MOD: NOMBOR PLAT KENDERAAN (ANPR)",
    provider: "Gemini 1.5 Flash Vision",
    samples: [
      {
        plate: "WXY 8899",
        color: "#2563eb",
        model: "Proton X50",
        confidence: 99.2,
        expectedOwner: "Cikgu Sarah (Guru Kelas 4 Amanah)",
        status: "allowed",
        actionText: "✅ Buka Palang Automatik (Servo Motor ON)",
        message: "Kenderaan Guru Dikenali! Selamat datang Cikgu Sarah.",
        json: {
          task: "license_plate_recognition",
          detected_text: "WXY 8899",
          confidence: 0.992,
          bounding_box: { ymin: 412, xmin: 350, ymax: 510, xmax: 670 },
          db_lookup: {
            table: "vehicle_watchlist",
            matched: true,
            owner: "Cikgu Sarah",
            role: "Guru Kelas 4 Amanah",
            barrier_action: "OPEN"
          }
        }
      },
      {
        plate: "VAB 1234",
        color: "#1e293b",
        model: "Honda Civic VIP",
        confidence: 98.8,
        expectedOwner: "En. Roslan (Pengetua Sekolah)",
        status: "allowed",
        actionText: "✅ Buka Palang VIP + Lampu Hijau",
        message: "Kereta Pengetua Dikesan! Palang Utama dibuka serta-merta.",
        json: {
          task: "license_plate_recognition",
          detected_text: "VAB 1234",
          confidence: 0.988,
          bounding_box: { ymin: 390, xmin: 320, ymax: 480, xmax: 640 },
          db_lookup: {
            table: "vehicle_watchlist",
            matched: true,
            owner: "En. Roslan",
            role: "Pengetua Sekolah",
            barrier_action: "OPEN_VIP"
          }
        }
      },
      {
        plate: "BEE 7777",
        color: "#d97706",
        model: "Van Katering Makanan",
        confidence: 96.5,
        expectedOwner: "Van Katering (Pelawat)",
        status: "warning",
        actionText: "⚠️ Tahan Palang: Arahkan Masuk Pondok Pengawal",
        message: "Kenderaan Kontraktor/Pelawat. Sila buat pendaftaran keselamatan.",
        json: {
          task: "license_plate_recognition",
          detected_text: "BEE 7777",
          confidence: 0.965,
          bounding_box: { ymin: 440, xmin: 380, ymax: 530, xmax: 700 },
          db_lookup: {
            table: "vehicle_watchlist",
            matched: true,
            owner: "Van Katering",
            role: "Pelawat / Kontraktor",
            barrier_action: "HOLD_ALERT"
          }
        }
      },
      {
        plate: "KDA 4040",
        color: "#dc2626",
        model: "Kereta Luar Tidak Berdaftar",
        confidence: 97.3,
        expectedOwner: "TIADA DALAM PANGKALAN DATA",
        status: "denied",
        actionText: "❌ Palang Kekal Tutup + Notis Amaran",
        message: "Nombor plat tidak berdaftar di SQLite3. Akses dinafikan.",
        json: {
          task: "license_plate_recognition",
          detected_text: "KDA 4040",
          confidence: 0.973,
          bounding_box: { ymin: 420, xmin: 340, ymax: 515, xmax: 660 },
          db_lookup: {
            table: "vehicle_watchlist",
            matched: false,
            barrier_action: "DENY_ENTRY"
          }
        }
      }
    ]
  },

  face: {
    name: "Pengecaman Wajah",
    hudTitle: "MOD: PENGECAMAN WAJAH (FACE RECOGNITION)",
    provider: "OpenAI GPT-4o Vision",
    samples: [
      {
        name: "Danial Hakim",
        classInfo: "Murid 5 Arif",
        avatar: "👦",
        confidence: 98.6,
        status: "allowed",
        actionText: "✅ Tanda Kehadiran: 07:45 AM (Tepat Waktu)",
        message: "Selamat Pagi Danial! Rekod kehadiran anda telah disimpan di SQLite3.",
        json: {
          task: "face_recognition",
          detected_person: "Danial Hakim",
          confidence: 0.986,
          facial_landmarks: { eye_left: [120, 140], eye_right: [160, 140], nose: [140, 165] },
          db_match: {
            table: "face_dataset",
            matched_id: 1,
            attendance_status: "PRESENT",
            whatsapp_alert: "SENT_TO_PARENT"
          }
        }
      },
      {
        name: "Aina Sofea",
        classInfo: "Pengawas Tingkatan 4",
        avatar: "👧",
        confidence: 99.1,
        status: "allowed",
        actionText: "✅ Kehadiran Ditanda + Buka Pintu Bilik Pengawas",
        message: "Aina Sofea dikesan. Akses bilik khas pengawas dibenarkan.",
        json: {
          task: "face_recognition",
          detected_person: "Aina Sofea",
          confidence: 0.991,
          db_match: {
            table: "face_dataset",
            matched_id: 2,
            category: "Pengawas",
            access_granted: ["Bilik Pengawas", "Pintu Utama"]
          }
        }
      },
      {
        name: "Individu Tidak Dikenali",
        classInfo: "Tiada rekod pelajar/guru",
        avatar: "🕵️‍♂️",
        confidence: 78.4,
        status: "warning",
        actionText: "⚠️ Amaran: Tetamu Tidak Dikenali di Kawasan Kelas",
        message: "Wajah ini tiada dalam dataset SQLite3. Memerlukan pas pelawat.",
        json: {
          task: "face_recognition",
          detected_person: "UNKNOWN_PERSON",
          confidence: 0.784,
          db_match: {
            table: "face_dataset",
            matched: false,
            alert_security: true
          }
        }
      }
    ]
  },

  ocr: {
    name: "Pengecaman Huruf (OCR)",
    hudTitle: "MOD: PENGERCAMAN TEKS & HURUF (OCR VISION)",
    provider: "Google Gemini Vision OCR",
    samples: [
      {
        title: "Kad Imbasan Sains",
        textSample: "Bab 3: Sistem Peredaran Darah Manusia & Jantung",
        snippet: "Darah beroksigen dipam dari jantung ke seluruh badan.",
        confidence: 99.5,
        status: "allowed",
        actionText: "✅ Teks Berjaya Dibaca & Ditukar ke Suara",
        message: "Semua perkataan pada kad imbasan berjaya diekstrak secara tepat!",
        json: {
          task: "optical_character_recognition",
          document_type: "science_flashcard",
          extracted_text: "Bab 3: Sistem Peredaran Darah Manusia & Jantung. Darah beroksigen dipam dari jantung ke seluruh badan.",
          word_count: 14,
          reading_language: "ms-MY",
          accuracy_score: 0.995
        }
      },
      {
        title: "Buku Latihan Matematik",
        textSample: "Formula Luas Segi Tiga = 1/2 x Tapak x Tinggi",
        snippet: "Jika tapak = 8cm dan tinggi = 6cm, Luas = 24 cm².",
        confidence: 98.7,
        status: "allowed",
        actionText: "✅ Teks & Formula Matematik Ditukar ke LaTeX/Digit",
        message: "Formula matematik berjaya dikesan dan disimpan ke nota digital.",
        json: {
          task: "optical_character_recognition",
          document_type: "math_notes",
          extracted_formula: "\\text{Luas} = \\frac{1}{2} \\times \\text{Tapak} \\times \\text{Tinggi}",
          calculation_verified: true,
          confidence: 0.987
        }
      },
      {
        title: "Papan Tanda Makmal Komputer",
        textSample: "DILARANG MEMBAWA MAKANAN ATAU MINUMAN",
        snippet: "Sila jaga kebersihan dan keselamatan perkakasan komputer.",
        confidence: 99.8,
        status: "warning",
        actionText: "⚠️ Amaran Keselamatan Makmal Dikesan",
        message: "AI mengecam tanda amaran larangan makanan di makmal.",
        json: {
          task: "optical_character_recognition",
          document_type: "warning_sign",
          extracted_text: "DILARANG MEMBAWA MAKANAN ATAU MINUMAN",
          is_safety_warning: true,
          confidence: 0.998
        }
      }
    ]
  },

  scene: {
    name: "Mata Pintar AI",
    hudTitle: "MOD: MATA PINTAR AI (SCENE & OBJECT DETECTION)",
    provider: "Multimodal LLM Reasoning",
    samples: [
      {
        sceneTitle: "Makmal Sains Sekolah",
        icon: "🔬",
        description: "2 murid sedang mengkaji spesimen menggunakan mikroskop, 1 tabung uji kaca di atas meja rak.",
        confidence: 96.8,
        status: "allowed",
        actionText: "✅ Aktiviti Makmal Normal & Selamat Dikenalpasti",
        message: "AI mengenalpasti peralatan sains dan aktiviti pembelajaran aktif.",
        json: {
          task: "multimodal_scene_understanding",
          scene: "School Science Laboratory",
          detected_objects: [
            { label: "student", count: 2, activity: "studying" },
            { label: "microscope", count: 1, condition: "in_use" },
            { label: "test_tube", count: 3, safe: true }
          ],
          safety_status: "NORMAL"
        }
      },
      {
        sceneTitle: "Pusat Kitar Semula Sekolah",
        icon: "♻️",
        description: "Botol plastik minuman dikesan di hadapan kamera.",
        confidence: 97.4,
        status: "allowed",
        actionText: "✅ Panduan Kitar Semula: Masukkan ke Tong Jingga (Plastik)",
        message: "AI mengenalpasti botol polietilena (PET) dan mengaktifkan lampu tong jingga!",
        json: {
          task: "recycle_item_sorter",
          item: "Plastic Water Bottle",
          material: "PET (Polyethylene terephthalate)",
          designated_bin_color: "Orange (Plastik & Tin)",
          confidence: 0.974
        }
      }
    ]
  }
};

// ==========================================
// 3. Audio Effects Synthesizer (Web Audio API)
// ==========================================
class SoundFX {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  init() {
    if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
    }
  }

  playBlip(freq = 600, duration = 0.08) {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch (e) {
      console.warn("Audio error", e);
    }
  }

  playSuccess() {
    if (!this.enabled) return;
    this.playBlip(523.25, 0.1); // C5
    setTimeout(() => this.playBlip(659.25, 0.12), 100); // E5
    setTimeout(() => this.playBlip(783.99, 0.18), 200); // G5
  }

  playWarning() {
    if (!this.enabled) return;
    this.playBlip(320, 0.15);
    setTimeout(() => this.playBlip(280, 0.2), 160);
  }
}

const soundManager = new SoundFX();

// ==========================================
// 4. Application State & Controller
// ==========================================
class AppController {
  constructor() {
    this.currentMode = "plate";
    this.sampleIndices = { plate: 0, face: 0, ocr: 0, scene: 0 };
    this.isScanning = false;
    this.isRealCameraActive = false;
    this.videoStream = null;

    this.initDOMElements();
    this.bindEvents();
    this.renderSimulatorDisplay();
    this.renderTables();
  }

  initDOMElements() {
    // Buttons & Toggles
    this.modeTabs = document.querySelectorAll(".mode-tab");
    this.triggerScanBtn = document.getElementById("trigger-scan-btn");
    this.nextSampleBtn = document.getElementById("next-sample-btn");
    this.soundToggleBtn = document.getElementById("sound-toggle-btn");
    this.soundIcon = document.getElementById("sound-icon");
    this.realWebcamBtn = document.getElementById("real-webcam-btn");
    this.copyJsonBtn = document.getElementById("copy-json-btn");

    // Simulator Elements
    this.laserLine = document.getElementById("laser-line");
    this.simDisplay = document.getElementById("sim-display");
    this.realVideoFeed = document.getElementById("real-video-feed");
    this.realCanvasOverlay = document.getElementById("real-canvas-overlay");
    this.cameraStatusText = document.getElementById("camera-status-text");
    this.hudModeDisplay = document.getElementById("hud-mode-display");
    this.hudFps = document.getElementById("hud-fps");

    // Analysis Panel
    this.apiProviderBadge = document.getElementById("api-provider-badge");
    this.resultBanner = document.getElementById("result-banner");
    this.resultIconBox = document.getElementById("result-icon-box");
    this.resultTitle = document.getElementById("result-title");
    this.resultSubtitle = document.getElementById("result-subtitle");
    this.infoValue = document.getElementById("info-value");
    this.confidenceBar = document.getElementById("confidence-bar");
    this.confidenceText = document.getElementById("confidence-text");
    this.infoMatch = document.getElementById("info-match");
    this.infoAction = document.getElementById("info-action");
    this.jsonCode = document.getElementById("json-code");

    // Pipeline Steps
    this.stepCam = document.getElementById("step-cam");
    this.stepAi = document.getElementById("step-ai");
    this.stepDb = document.getElementById("step-db");
    this.stepAction = document.getElementById("step-action");

    // Database Lab
    this.dbTabBtns = document.querySelectorAll(".db-tab-btn");
    this.dbPanels = document.querySelectorAll(".db-panel");
    this.platesTableBody = document.getElementById("plates-table-body");
    this.facesTableBody = document.getElementById("faces-table-body");
    this.logsTableBody = document.getElementById("logs-table-body");
    this.clearLogsBtn = document.getElementById("clear-logs-btn");

    // Modals
    this.plateModal = document.getElementById("plate-modal");
    this.faceModal = document.getElementById("face-modal");
    this.addPlateModalBtn = document.getElementById("add-plate-modal-btn");
    this.addFaceModalBtn = document.getElementById("add-face-modal-btn");
    this.closePlateModalBtn = document.getElementById("close-plate-modal");
    this.cancelPlateModalBtn = document.getElementById("cancel-plate-modal");
    this.closeFaceModalBtn = document.getElementById("close-face-modal");
    this.cancelFaceModalBtn = document.getElementById("cancel-face-modal");
    this.addPlateForm = document.getElementById("add-plate-form");
    this.addFaceForm = document.getElementById("add-face-form");

    // Mobile Menu
    this.mobileMenuBtn = document.getElementById("mobile-menu-btn");
    this.navLinks = document.querySelector(".nav-links");
  }

  bindEvents() {
    // Mode Switcher
    this.modeTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const mode = tab.getAttribute("data-mode");
        this.switchMode(mode);
      });
    });

    // Scan & Next Sample
    this.triggerScanBtn.addEventListener("click", () => this.runScanPipeline());
    this.nextSampleBtn.addEventListener("click", () => this.cycleNextSample());

    // Sound Toggle
    this.soundToggleBtn.addEventListener("click", () => {
      soundManager.enabled = !soundManager.enabled;
      this.soundIcon.textContent = soundManager.enabled ? "🔊" : "🔇";
      this.soundToggleBtn.style.color = soundManager.enabled ? "#38bdf8" : "#94a3b8";
    });

    // Real Camera Toggle
    this.realWebcamBtn.addEventListener("click", () => this.toggleRealWebcam());

    // Copy JSON
    this.copyJsonBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(this.jsonCode.textContent).then(() => {
        this.copyJsonBtn.textContent = "Disalin! ✓";
        setTimeout(() => { this.copyJsonBtn.textContent = "Salin"; }, 1800);
      });
    });

    // Database Tabs
    this.dbTabBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const tabKey = btn.getAttribute("data-dbtab");
        this.switchDbTab(tabKey);
      });
    });

    // Clear Logs
    this.clearLogsBtn.addEventListener("click", () => {
      SQLiteDB.logs = [];
      this.renderLogsTable();
    });

    // Modals
    this.addPlateModalBtn.addEventListener("click", () => this.plateModal.classList.remove("hidden"));
    this.closePlateModalBtn.addEventListener("click", () => this.plateModal.classList.add("hidden"));
    this.cancelPlateModalBtn.addEventListener("click", () => this.plateModal.classList.add("hidden"));

    this.addFaceModalBtn.addEventListener("click", () => this.faceModal.classList.remove("hidden"));
    this.closeFaceModalBtn.addEventListener("click", () => this.faceModal.classList.add("hidden"));
    this.cancelFaceModalBtn.addEventListener("click", () => this.faceModal.classList.add("hidden"));

    // Form Submissions
    this.addPlateForm.addEventListener("submit", (e) => this.handleAddPlate(e));
    this.addFaceForm.addEventListener("submit", (e) => this.handleAddFace(e));

    // Mobile Navigation Toggle
    if (this.mobileMenuBtn) {
      this.mobileMenuBtn.addEventListener("click", () => {
        this.navLinks.style.display = this.navLinks.style.display === "flex" ? "none" : "flex";
        this.navLinks.style.flexDirection = "column";
        this.navLinks.style.position = "absolute";
        this.navLinks.style.top = "100%";
        this.navLinks.style.left = "0";
        this.navLinks.style.right = "0";
        this.navLinks.style.background = "#090d16";
        this.navLinks.style.padding = "1.5rem";
        this.navLinks.style.borderBottom = "1px solid rgba(255,255,255,0.1)";
      });
    }
  }

  // ==========================================
  // Mode Switching & Rendering
  // ==========================================
  switchMode(mode) {
    if (this.isScanning) return;
    this.currentMode = mode;

    this.modeTabs.forEach(tab => {
      tab.classList.toggle("active", tab.getAttribute("data-mode") === mode);
    });

    const modeConfig = SimulatorModes[mode];
    this.hudModeDisplay.textContent = modeConfig.hudTitle;
    this.apiProviderBadge.textContent = `Pembekal: ${modeConfig.provider}`;

    this.renderSimulatorDisplay();
    this.resetPipelineUI();
  }

  cycleNextSample() {
    if (this.isScanning) return;
    const samples = SimulatorModes[this.currentMode].samples;
    this.sampleIndices[this.currentMode] = (this.sampleIndices[this.currentMode] + 1) % samples.length;
    
    soundManager.playBlip(750, 0.05);
    this.renderSimulatorDisplay();
    this.resetPipelineUI();
  }

  renderSimulatorDisplay() {
    const mode = this.currentMode;
    const idx = this.sampleIndices[mode];
    const sample = SimulatorModes[mode].samples[idx];

    let htmlContent = "";

    if (mode === "plate") {
      htmlContent = `
        <div class="sim-card">
          <div style="display:flex;flex-direction:column;align-items:center;">
            <div class="sim-car-body" style="background: linear-gradient(180deg, ${sample.color} 0%, #0f2040 100%);">
              <div class="sim-car-roof" style="background: ${sample.color}; opacity: 0.7;"></div>
              <div class="sim-plate">
                ${sample.plate}
                <div class="sim-plate-aim">
                  <span class="sim-plate-tag">${sample.plate} &bull; AI Mengimbas</span>
                </div>
              </div>
            </div>
            <div class="sim-car-wheels">
              <div class="sim-wheel"></div>
              <div class="sim-wheel"></div>
            </div>
          </div>
          <p class="sim-caption">${sample.model}</p>
        </div>
      `;
    } else if (mode === "face") {
      htmlContent = `
        <div class="sim-card">
          <div class="sim-face-box">
            <div class="sim-face-bbox">
              <span class="sim-face-label">Wajah Dikesan</span>
            </div>
            <div class="sim-face-avatar">${sample.avatar}</div>
          </div>
          <div class="sim-face-name">${sample.name}</div>
          <div class="sim-face-sub">${sample.classInfo}</div>
        </div>
      `;
    } else if (mode === "ocr") {
      htmlContent = `
        <div class="sim-card">
          <div class="sim-ocr-doc">
            <span class="sim-ocr-badge">OCR SCAN</span>
            <div class="sim-ocr-title">${sample.title}</div>
            <p class="sim-ocr-text">${sample.snippet}</p>
            <div class="sim-ocr-highlighted">${sample.textSample}</div>
          </div>
        </div>
      `;
    } else if (mode === "scene") {
      htmlContent = `
        <div class="sim-card">
          <div class="sim-scene-box">
            <div class="sim-scene-icon">${sample.icon}</div>
            <div class="sim-scene-title">${sample.sceneTitle}</div>
            <div class="sim-scene-desc">"${sample.description}"</div>
          </div>
        </div>
      `;
    }

    this.simDisplay.innerHTML = htmlContent;
  }

  resetPipelineUI() {
    this.resultBanner.className = "result-card";
    this.resultIconBox.textContent = "⏳";
    this.resultTitle.textContent = "Sedia Untuk Diimbas";
    this.resultSubtitle.textContent = 'Tekan butang "Imbas Objek Sekarang" untuk memulakan analisis AI.';

    [this.stepCam, this.stepAi, this.stepDb, this.stepAction].forEach(step => {
      step.classList.remove("active");
    });

    this.infoValue.textContent = "-";
    this.confidenceBar.style.width = "0%";
    this.confidenceText.textContent = "0%";
    this.infoMatch.textContent = "-";
    this.infoAction.textContent = "-";

    this.jsonCode.textContent = JSON.stringify({
      status: "ready",
      task: this.currentMode,
      waiting_for_scan: true
    }, null, 2);
  }

  // ==========================================
  // Scan Pipeline Execution (Simulated Animation)
  // ==========================================
  runScanPipeline() {
    if (this.isScanning) return;
    this.isScanning = true;
    this.triggerScanBtn.disabled = true;
    this.triggerScanBtn.style.opacity = "0.7";

    const mode = this.currentMode;
    const idx = this.sampleIndices[mode];
    const sample = SimulatorModes[mode].samples[idx];

    // Start laser sweep
    this.laserLine.classList.add("scanning");
    soundManager.playBlip(480, 0.1);

    // Step 1: Camera Frame Capture
    this.stepCam.classList.add("active");
    this.resultTitle.textContent = "Langkah 1: Menangkap Bingkai Kamera...";
    this.resultSubtitle.textContent = "Resolusi 1080p dihantar ke modul pemprosesan imej awal OpenCV.";

    setTimeout(() => {
      // Step 2: AI Vision Inference
      soundManager.playBlip(620, 0.1);
      this.stepAi.classList.add("active");
      this.resultTitle.textContent = `Langkah 2: Menghubungi ${SimulatorModes[mode].provider}...`;
      this.resultSubtitle.textContent = "Model AI memproses visual dan menjana data teks berstruktur (JSON).";

      setTimeout(() => {
        // Step 3: SQLite3 Database Query
        soundManager.playBlip(780, 0.1);
        this.stepDb.classList.add("active");
        this.resultTitle.textContent = "Langkah 3: Menyemak Pangkalan Data SQLite3...";
        this.resultSubtitle.textContent = "Memadankan hasil AI dengan rekod fail ai_webcam.db tempatan.";

        setTimeout(() => {
          // Step 4: Final Action & Display
          this.stepAction.classList.add("active");
          this.laserLine.classList.remove("scanning");
          this.isScanning = false;
          this.triggerScanBtn.disabled = false;
          this.triggerScanBtn.style.opacity = "1";

          this.finalizeDetectionResult(sample);
        }, 600);
      }, 700);
    }, 600);
  }

  finalizeDetectionResult(sample) {
    const isSuccess = sample.status === "allowed";
    const isWarning = sample.status === "warning";

    if (isSuccess) {
      soundManager.playSuccess();
      this.resultBanner.className = "result-card success";
      this.resultIconBox.textContent = "✅";
    } else if (isWarning) {
      soundManager.playWarning();
      this.resultBanner.className = "result-card warning";
      this.resultIconBox.textContent = "⚠️";
    } else {
      soundManager.playWarning();
      this.resultBanner.className = "result-card danger";
      this.resultIconBox.textContent = "❌";
    }

    this.resultTitle.textContent = isSuccess ? "Pengesanan Berjaya & Dikenalpasti!" : "Amaran: Perhatian Diperlukan!";
    this.resultSubtitle.textContent = sample.message;

    // Populate Match Details
    if (this.currentMode === "plate") {
      this.infoValue.textContent = sample.plate;
      this.infoMatch.textContent = sample.expectedOwner;
    } else if (this.currentMode === "face") {
      this.infoValue.textContent = sample.name;
      this.infoMatch.textContent = sample.classInfo;
    } else if (this.currentMode === "ocr") {
      this.infoValue.textContent = sample.title;
      this.infoMatch.textContent = `Teks: "${sample.textSample.substring(0, 24)}..."`;
    } else if (this.currentMode === "scene") {
      this.infoValue.textContent = sample.sceneTitle;
      this.infoMatch.textContent = "Analisis Situasi Lengkap";
    }

    this.confidenceBar.style.width = `${sample.confidence}%`;
    this.confidenceText.textContent = `${sample.confidence}%`;
    this.infoAction.textContent = sample.actionText;

    // JSON Payload
    this.jsonCode.textContent = JSON.stringify(sample.json, null, 2);

    // Append to SQLite Detection Logs
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    const newLog = {
      id: 100 + SQLiteDB.logs.length + 1,
      time: timeStr,
      mode: SimulatorModes[this.currentMode].name,
      result: this.infoValue.textContent,
      confidence: `${sample.confidence}%`,
      match: isSuccess ? "Dibenarkan" : "Ditolak / Amaran"
    };

    SQLiteDB.logs.unshift(newLog);
    this.renderLogsTable();
  }

  // ==========================================
  // Real Camera Support (getUserMedia)
  // ==========================================
  async toggleRealWebcam() {
    if (this.isRealCameraActive) {
      // Stop real camera
      if (this.videoStream) {
        this.videoStream.getTracks().forEach(track => track.stop());
      }
      this.realVideoFeed.classList.add("hidden");
      this.realCanvasOverlay.classList.add("hidden");
      this.simDisplay.classList.remove("hidden");
      this.isRealCameraActive = false;
      this.realWebcamBtn.innerHTML = "<span>📷 Cuba Kamera Saya</span>";
      this.cameraStatusText.textContent = "KAMERA AKTIF: SIMULASI 1080P";
      this.cameraStatusText.style.color = "#38bdf8";
    } else {
      // Start real camera
      try {
        this.cameraStatusText.textContent = "MEMOHON KEBENARAN KAMERA...";
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }
        });
        
        this.videoStream = stream;
        this.realVideoFeed.srcObject = stream;
        this.realVideoFeed.classList.remove("hidden");
        this.realCanvasOverlay.classList.remove("hidden");
        this.simDisplay.classList.add("hidden");
        this.isRealCameraActive = true;

        this.realWebcamBtn.innerHTML = "<span>⏹️ Kembali ke Simulator</span>";
        this.cameraStatusText.textContent = "KAMERA SEBENAR BERFUNGSI (LIVE)";
        this.cameraStatusText.style.color = "#10b981";

        this.startCanvasReticleLoop();
      } catch (err) {
        console.error("Camera access error:", err);
        alert("Kamera sebenar tidak dapat diakses atau kebenaran tidak diberikan. Simulator grafik interaktif kekal boleh digunakan sepenuhnya!");
        this.cameraStatusText.textContent = "KAMERA AKTIF: SIMULASI 1080P";
      }
    }
  }

  startCanvasReticleLoop() {
    if (!this.isRealCameraActive) return;
    const canvas = this.realCanvasOverlay;
    const ctx = canvas.getContext("2d");

    const render = () => {
      if (!this.isRealCameraActive) return;
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw subtle AI scanning box overlay on real feed
      const boxWidth = 240;
      const boxHeight = 160;
      const x = (canvas.width - boxWidth) / 2;
      const y = (canvas.height - boxHeight) / 2;

      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 4]);
      ctx.strokeRect(x, y, boxWidth, boxHeight);
      ctx.setLineDash([]);

      ctx.fillStyle = "rgba(6, 182, 212, 0.85)";
      ctx.font = "12px 'Plus Jakarta Sans', sans-serif";
      ctx.fillText("KAWASAN PENGESANAN AI", x + 10, y - 8);

      requestAnimationFrame(render);
    };

    render();
  }

  // ==========================================
  // Database Lab Rendering & Actions
  // ==========================================
  switchDbTab(tabKey) {
    this.dbTabBtns.forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-dbtab") === tabKey);
    });

    this.dbPanels.forEach(panel => {
      panel.classList.toggle("active", panel.id === `db-panel-${tabKey}`);
    });
  }

  renderTables() {
    this.renderPlatesTable();
    this.renderFacesTable();
    this.renderLogsTable();
  }

  renderPlatesTable() {
    this.platesTableBody.innerHTML = SQLiteDB.plates.map(item => `
      <tr>
        <td><strong style="color:var(--text-muted);">#${item.id}</strong></td>
        <td><strong style="font-family:var(--font-mono);color:var(--brand-primary);font-size:0.9rem;">${item.plate}</strong></td>
        <td>${item.owner}</td>
        <td>${item.role}</td>
        <td>
          <span class="badge ${item.status === 'Dibenarkan' ? 'badge-success' : item.status === 'Perhatian' ? 'badge-warning' : 'badge-danger'}">
            ${item.status}
          </span>
        </td>
        <td>
          <button class="btn btn-ghost btn-sm" onclick="app.removePlate(${item.id})">Padam</button>
        </td>
      </tr>
    `).join("");
  }

  renderFacesTable() {
    this.facesTableBody.innerHTML = SQLiteDB.faces.map(item => `
      <tr>
        <td><strong style="color:var(--text-muted);">#${item.id}</strong></td>
        <td style="font-size:1.5rem;">${item.avatar}</td>
        <td><strong>${item.name}</strong></td>
        <td>${item.role}</td>
        <td>
          <span class="badge ${item.category === 'Guru' ? 'badge-blue' : item.category === 'Pengawas' ? 'badge-purple' : 'badge-success'}">
            ${item.category}
          </span>
        </td>
        <td><span class="badge badge-success">● Aktif</span></td>
      </tr>
    `).join("");
  }

  renderLogsTable() {
    this.logsTableBody.innerHTML = SQLiteDB.logs.map(item => `
      <tr>
        <td><strong style="color:var(--text-muted);">#${item.id}</strong></td>
        <td style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);">${item.time}</td>
        <td><span class="badge badge-blue">${item.mode}</span></td>
        <td><strong>${item.result}</strong></td>
        <td style="color:var(--brand-primary);font-family:var(--font-mono);font-weight:700;">${item.confidence}</td>
        <td>
          <span class="badge ${item.match.includes('Dibenarkan') || item.match.includes('Hadir') ? 'badge-success' : 'badge-warning'}">
            ${item.match}
          </span>
        </td>
      </tr>
    `).join("");
  }

  handleAddPlate(e) {
    e.preventDefault();
    const plateNo = document.getElementById("input-plate-no").value.trim().toUpperCase();
    const ownerName = document.getElementById("input-owner-name").value.trim();
    const role = document.getElementById("input-role").value;

    if (!plateNo || !ownerName) return;

    const newId = SQLiteDB.plates.length > 0 ? Math.max(...SQLiteDB.plates.map(p => p.id)) + 1 : 1;
    const isDenied = role.includes("Dilarang");

    SQLiteDB.plates.push({
      id: newId,
      plate: plateNo,
      owner: ownerName,
      role: role,
      status: isDenied ? "Ditolak" : "Dibenarkan"
    });

    // Also inject into simulator samples so it can be scanned right away!
    SimulatorModes.plate.samples.push({
      plate: plateNo,
      color: "#059669",
      model: "Kereta Baru Ditambah",
      confidence: 99.0,
      expectedOwner: `${ownerName} (${role})`,
      status: isDenied ? "denied" : "allowed",
      actionText: isDenied ? "❌ Palang Ditolak" : "✅ Palang Automatik Dibuka",
      message: `Pengecaman berjaya untuk rekod baru: ${ownerName}`,
      json: {
        task: "license_plate_recognition",
        detected_text: plateNo,
        confidence: 0.99,
        db_lookup: {
          table: "vehicle_watchlist",
          matched: true,
          owner: ownerName,
          role: role
        }
      }
    });

    this.renderPlatesTable();
    this.plateModal.classList.add("hidden");
    this.addPlateForm.reset();

    soundManager.playSuccess();
    alert(`Nombor plat ${plateNo} (${ownerName}) berjaya disimpan ke pangkalan data SQLite3! Anda kini boleh mengimbasnya dalam simulator.`);
  }

  handleAddFace(e) {
    e.preventDefault();
    const studentName = document.getElementById("input-student-name").value.trim();
    const studentClass = document.getElementById("input-student-class").value.trim();
    const category = document.getElementById("input-student-category").value;

    if (!studentName || !studentClass) return;

    const newId = SQLiteDB.faces.length > 0 ? Math.max(...SQLiteDB.faces.map(f => f.id)) + 1 : 1;
    const avatars = ["🧑‍🎓", "👩‍🎓", "👦", "👧", "🧑‍🔬"];
    const randomAvatar = avatars[Math.floor(Math.random() * avatars.length)];

    SQLiteDB.faces.push({
      id: newId,
      name: studentName,
      role: studentClass,
      category: category,
      avatar: randomAvatar
    });

    // Inject into face simulator samples
    SimulatorModes.face.samples.push({
      name: studentName,
      classInfo: studentClass,
      avatar: randomAvatar,
      confidence: 98.9,
      status: "allowed",
      actionText: "✅ Kehadiran Ditanda Secara Automatik",
      message: `Selamat Datang, ${studentName}! Rekod anda telah dikemaskini.`,
      json: {
        task: "face_recognition",
        detected_person: studentName,
        class: studentClass,
        confidence: 0.989,
        db_match: { matched: true, table: "face_dataset", id: newId }
      }
    });

    this.renderFacesTable();
    this.faceModal.classList.add("hidden");
    this.addFaceForm.reset();

    soundManager.playSuccess();
    alert(`Rekod ${studentName} berjaya dimasukkan ke jadual face_dataset SQLite3!`);
  }

  removePlate(id) {
    SQLiteDB.plates = SQLiteDB.plates.filter(p => p.id !== id);
    this.renderPlatesTable();
    soundManager.playBlip(350, 0.08);
  }
}

// Initialize Application once DOM is loaded
let app = null;
document.addEventListener("DOMContentLoaded", () => {
  app = new AppController();
});
