/**
 * AI-WebCam Client Application Script
 * Manages live feeds, camera switching, AJAX scanning, task toggles, and notifications.
 */

let activeTask = "ANPR";
let isAutoScanning = false;
let autoScanTimer = null;
let useBrowserCam = false;
let browserStream = null;
let soundEnabled = true;

// Sound Synthesizer via Web Audio API (No external assets required)
function playChime(isAlert = false) {
    if (!soundEnabled) return;
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (isAlert) {
            // Low alert tone
            osc.frequency.setValueAtTime(440, audioCtx.currentTime);
            osc.frequency.setValueAtTime(330, audioCtx.currentTime + 0.1);
            gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
            osc.start(audioCtx.currentTime);
            osc.stop(audioCtx.currentTime + 0.35);
        } else {
            // Pleasant chime
            osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
            osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.08); // A5
            gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
            osc.start(audioCtx.currentTime);
            osc.stop(audioCtx.currentTime + 0.3);
        }
    } catch (e) {
        // AudioContext may be restricted by browser policy
    }
}

// Toast Notifier
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = "toast";
    const icon = type === "success" ? "fa-circle-check" : type === "danger" ? "fa-triangle-exclamation" : "fa-circle-info";
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3500);
}

// Select Active Task
function selectTask(taskName) {
    activeTask = taskName;
    document.querySelectorAll(".task-btn").forEach(btn => {
        if (btn.dataset.task === taskName) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    const indicator = document.getElementById("current-task-indicator");
    if (indicator) indicator.textContent = taskName;
}

// Toggle Camera Source (Server OpenCV vs Browser getUserMedia)
async function toggleCameraSource() {
    const serverImg = document.getElementById("server-video-feed");
    const browserVideo = document.getElementById("browser-video");
    const btn = document.getElementById("toggle-cam-btn");

    if (!useBrowserCam) {
        // Switch to browser webcam
        try {
            browserStream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
            browserVideo.srcObject = browserStream;
            browserVideo.play();
            browserVideo.style.display = "block";
            serverImg.style.display = "none";
            useBrowserCam = true;
            if (btn) btn.innerHTML = `<i class="fa-solid fa-server"></i> Gunakan Kamera Pelayan`;
            showToast("Kamera Pelayar Web (HTML5) Aktif", "success");
        } catch (err) {
            showToast("Tidak dapat mengakses kamera pelayar: " + err.message, "danger");
        }
    } else {
        // Switch back to server MJPEG feed
        if (browserStream) {
            browserStream.getTracks().forEach(t => t.stop());
            browserStream = null;
        }
        browserVideo.style.display = "none";
        serverImg.style.display = "block";
        useBrowserCam = false;
        if (btn) btn.innerHTML = `<i class="fa-solid fa-camera"></i> Gunakan Kamera Pelayar`;
        showToast("Kamera Pelayan (OpenCV) Aktif", "success");
    }
}

// Capture current frame from browser video if active
function captureBrowserFrameBase64() {
    const browserVideo = document.getElementById("browser-video");
    if (!useBrowserCam || !browserVideo) return null;
    const canvas = document.createElement("canvas");
    canvas.width = browserVideo.videoWidth || 640;
    canvas.height = browserVideo.videoHeight || 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(browserVideo, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
    return dataUrl.split(",")[1]; // strip header
}

// Trigger AI Scan
async function triggerScan() {
    const scanBtn = document.getElementById("scan-now-btn");
    if (scanBtn) {
        scanBtn.disabled = true;
        scanBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Mengimbas...`;
    }

    const payload = {
        task: activeTask
    };


    if (useBrowserCam) {
        const b64 = captureBrowserFrameBase64();
        if (b64) payload.image_base64 = b64;
    }

    try {
        const res = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        renderScanResult(data);

        const isAlert = data.match_status === "Senarai Hitam" || data.match_status === "Perhatian";
        playChime(isAlert);
    } catch (err) {
        showToast("Ralat komunikasi dengan pelayan: " + err.message, "danger");
    } finally {
        if (scanBtn) {
            scanBtn.disabled = false;
            scanBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Imbas Sekarang`;
        }
    }
}

// Toggle Auto Scan
function toggleAutoScan() {
    const btn = document.getElementById("auto-scan-btn");
    if (isAutoScanning) {
        clearInterval(autoScanTimer);
        isAutoScanning = false;
        if (btn) {
            btn.classList.remove("btn-danger");
            btn.classList.add("btn-outline");
            btn.innerHTML = `<i class="fa-solid fa-play"></i> Imbasan Auto`;
        }
        showToast("Imbasan auto dihentikan", "info");
    } else {
        isAutoScanning = true;
        triggerScan();
        autoScanTimer = setInterval(triggerScan, 3500);
        if (btn) {
            btn.classList.remove("btn-outline");
            btn.classList.add("btn-danger");
            btn.innerHTML = `<i class="fa-solid fa-stop"></i> Berhenti Auto`;
        }
        showToast("Imbasan auto bermula (setiap 3.5s)", "success");
    }
}

// Render Results on UI
function renderScanResult(res) {
    const card = document.getElementById("scan-result-card");
    if (!card) return;

    if (!res.success) {
        card.innerHTML = `
            <div class="status-banner danger">
                <div class="status-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <div class="status-text">
                    <h3>Ralat Imbasan</h3>
                    <p>${res.error || 'Gagal menganalisis bingkai'}</p>
                </div>
            </div>
        `;
        return;
    }

    let bannerClass = "info";
    let iconClass = "fa-circle-info";
    let titleText = res.match_status || "Pengesanan Selesai";

    if (res.match_status === "Dibenarkan" || res.match_status === "Dikenali" || res.match_status === "Selamat") {
        bannerClass = "success";
        iconClass = "fa-circle-check";
    } else if (res.match_status === "Senarai Hitam") {
        bannerClass = "danger";
        iconClass = "fa-ban";
    } else if (res.match_status === "Perhatian" || res.match_status === "Tidak Berdaftar") {
        bannerClass = "warning";
        iconClass = "fa-triangle-exclamation";
    }

    let detailsHtml = "";
    if (res.task === "ANPR") {
        detailsHtml = `
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-id-card"></i> Nombor Plat</span>
                <span class="detail-val" style="font-size: 1.15rem; color: var(--primary);">${res.plate_number || 'Tiada'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-user-check"></i> Maklumat Pemilik</span>
                <span class="detail-val">${res.matched_info || 'Tiada Padanan'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-car-side"></i> Jenis Kenderaan</span>
                <span class="detail-val">${res.vehicle_type || 'N/A'} (${res.vehicle_color || ''})</span>
            </div>
        `;
    } else if (res.task === "FACE") {
        detailsHtml = `
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-user"></i> Nama Individu</span>
                <span class="detail-val" style="font-size: 1.15rem; color: var(--primary);">${res.person_name || 'Tidak Dikenali'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-tag"></i> Status Rekod</span>
                <span class="detail-val">${res.matched_info}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-face-smile"></i> Ekspresi / Anggaran Umur</span>
                <span class="detail-val">${res.expression} (${res.estimated_age})</span>
            </div>
        `;
    } else if (res.task === "OCR") {
        detailsHtml = `
            <div class="detail-item" style="flex-direction: column; align-items: flex-start; gap: 0.35rem;">
                <span class="detail-label"><i class="fa-solid fa-font"></i> Teks Yang Dibaca</span>
                <span class="detail-val" style="white-space: pre-wrap; word-break: break-word;">${res.detected_text || 'Tiada teks dapat dibaca'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-file"></i> Jenis Dokumen</span>
                <span class="detail-val">${res.document_type} (${res.language})</span>
            </div>
        `;
    } else if (res.task === "SCENE") {
        detailsHtml = `
            <div class="detail-item" style="flex-direction: column; align-items: flex-start; gap: 0.35rem;">
                <span class="detail-label"><i class="fa-solid fa-eye"></i> Huraian Senario</span>
                <span class="detail-val">${res.scene_summary}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-users"></i> Bilangan Individu</span>
                <span class="detail-val">${res.person_count} Orang</span>
            </div>
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-shield-halved"></i> Status Keselamatan</span>
                <span class="detail-val">${res.security_notes}</span>
            </div>
        `;
    } else if (res.task === "SPORTS") {
        const isBoxing = res.is_boxing || (res.sport_type && (res.sport_type.toLowerCase().includes("tinju") || res.sport_type.toLowerCase().includes("boxing")));
        if (isBoxing) {
            detailsHtml = `
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-mitten" style="color: #ef4444;"></i> Jenis Tumbukan</span>
                    <span class="detail-val" style="font-size: 1.1rem; color: #ef4444; font-weight: 700;">${res.punch_type || 'Tumbukan Terkawal'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-shoe-prints"></i> Pendirian Kaki</span>
                    <span class="detail-val">${res.stance_type || 'Orthodox'} (Lebar: ${res.stance_ratio || 1.3}x)</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-medal"></i> Skor Teknik Tinju</span>
                    <span class="detail-val" style="font-size: 1.2rem; color: var(--primary); font-weight: 700;">${res.posture_score} / 100</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-shield-halved"></i> Sudut (Siku | Guard)</span>
                    <span class="detail-val">${res.elbow_angle}° | Guard: ${res.guard_angle || 60}°</span>
                </div>
                <div class="detail-item" style="flex-direction: column; align-items: flex-start; gap: 0.35rem;">
                    <span class="detail-label"><i class="fa-solid fa-comment-dots"></i> Ulasan Teknik & Bunga</span>
                    <span class="detail-val" style="font-size: 0.85rem;">${res.punch_analysis || res.speed_diagnosis}</span>
                </div>
            `;
        } else {
            detailsHtml = `
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-person-running"></i> Atlet / Sukan</span>
                    <span class="detail-val">${res.athlete_name} (${res.sport_type})</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-medal"></i> Skor Postur Badan</span>
                    <span class="detail-val" style="font-size: 1.2rem; color: var(--primary); font-weight: 700;">${res.posture_score} / 100</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label"><i class="fa-solid fa-compass-drafting"></i> Sudut Sendi (Lutut | Torso)</span>
                    <span class="detail-val">${res.knee_angle}° | ${res.torso_angle}°</span>
                </div>
                <div class="detail-item" style="flex-direction: column; align-items: flex-start; gap: 0.35rem;">
                    <span class="detail-label"><i class="fa-solid fa-clipboard-check"></i> Analisis Kelajuan</span>
                    <span class="detail-val" style="font-size: 0.85rem;">${res.speed_diagnosis}</span>
                </div>
            `;
        }
    }

    const mockNotice = res.is_mock ? `
        <div style="margin-top: 0.85rem; padding: 0.5rem 0.75rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; font-size: 0.78rem; color: #92400e;">
            <i class="fa-solid fa-flask"></i> <strong>Mod Simulasi:</strong> Masukkan Kunci API anda di tab <em>Tetapan API</em> untuk pengesanan model sebenar.
        </div>
    ` : "";

    card.innerHTML = `
        <div class="status-banner ${bannerClass}">
            <div class="status-icon"><i class="fa-solid ${iconClass}"></i></div>
            <div class="status-text">
                <h3>${titleText}</h3>
                <p>${res.matched_info || res.task}</p>
            </div>
        </div>
        <div class="detail-list">
            ${detailsHtml}
            <div class="detail-item">
                <span class="detail-label"><i class="fa-solid fa-gauge-high"></i> Tahap Keyakinan (Confidence)</span>
                <span class="detail-val">${Math.round(res.confidence * 100)}%</span>
            </div>
        </div>
        ${mockNotice}
    `;

    // Refresh quick stats and recent logs if present
    refreshStats();
}

// Refresh Dashboard Stats
async function refreshStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        const elTotal = document.getElementById("stat-total-scans");
        if (elTotal) elTotal.textContent = data.total_logs;
        const elVehicles = document.getElementById("stat-total-vehicles");
        if (elVehicles) elVehicles.textContent = data.total_vehicles;
        const elFaces = document.getElementById("stat-total-faces");
        if (elFaces) elFaces.textContent = data.total_faces;
    } catch (e) {
        // silent
    }
}

// ==========================================
// Multi-Camera & "Scan to Add Camera" Logic
// ==========================================
let qrCodeInstance = null;
let knownCameraIds = new Set(["local_0"]);

function getDynamicConnectUrl() {
    const origin = window.location.origin;
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;

    const isIpOrLocal = /^(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/.test(hostname);

    // 1. If currently accessed on HTTPS (e.g. reverse proxy like https://rimau.kpst.my/ or direct HTTPS):
    if (protocol === "https:") {
        return `${origin}/phone_cam?id=phone_1`;
    }

    // 2. If accessed via a public domain name (e.g. rimau.kpst.my, not a raw LAN IP / localhost):
    if (!isIpOrLocal && hostname) {
        return `https://${hostname}/phone_cam?id=phone_1`;
    }

    // 3. Local LAN IP over HTTP (e.g. http://192.168.1.21:5000):
    // Mobile browsers require HTTPS for getUserMedia camera access, so use local HTTPS port 5001
    const targetIp = (hostname === "localhost" || hostname === "127.0.0.1") ? (window.SERVER_LOCAL_IP || hostname) : hostname;
    return `https://${targetIp}:5001/phone_cam?id=phone_1`;
}

function updateQrCode(url) {
    const qrContainer = document.getElementById("phone-qr-code");
    if (!qrContainer || typeof QRCode === "undefined") return;

    if (!qrCodeInstance) {
        qrContainer.innerHTML = "";
        qrCodeInstance = new QRCode(qrContainer, {
            text: url,
            width: 180,
            height: 180,
            colorDark: "#0f172a",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M
        });
    } else {
        qrCodeInstance.makeCode(url);
    }
}

function initPhoneCameraModal() {
    const btnOpen = document.getElementById("btn-open-qr-modal");
    const modal = document.getElementById("qr-camera-modal");
    const btnClose = document.getElementById("btn-close-qr-modal");
    const urlInput = document.getElementById("phone-connect-url-input");
    const btnCopy = document.getElementById("btn-copy-phone-url");

    if (!btnOpen || !modal) return;

    btnOpen.addEventListener("click", () => {
        modal.style.display = "flex";
        
        // Auto-detect dynamic URL based on current address bar
        const dynamicUrl = getDynamicConnectUrl();
        if (urlInput) {
            urlInput.value = dynamicUrl;
        }

        updateQrCode(dynamicUrl);
    });

    if (urlInput) {
        // Allow user to customize/type domain, and update QR in real time
        urlInput.addEventListener("input", () => {
            const customUrl = urlInput.value.trim();
            if (customUrl) {
                updateQrCode(customUrl);
            }
        });
    }

    if (btnClose) {
        btnClose.addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.style.display = "none";
        }
    });

    if (btnCopy && urlInput) {
        btnCopy.addEventListener("click", () => {
            navigator.clipboard.writeText(urlInput.value).then(() => {
                showToast("Pautan kamera telefon berjaya disalin!", "success");
            }).catch(() => {
                urlInput.select();
                document.execCommand("copy");
                showToast("Pautan kamera telefon berjaya disalin!", "success");
            });
        });
    }
}

// Poll available cameras
async function pollCameras() {
    const selectEl = document.getElementById("camera-source-select");
    if (!selectEl) return;

    try {
        const res = await fetch("/api/cameras");
        if (!res.ok) return;
        const data = await res.json();
        if (data.local_ip) {
            window.SERVER_LOCAL_IP = data.local_ip;
        }
        const cameras = data.cameras || [];
        const activeId = data.active_cam_id || "local_0";

        // Check if any new remote camera connected
        cameras.forEach(cam => {
            if (cam.type === "remote" && !knownCameraIds.has(cam.id)) {
                knownCameraIds.add(cam.id);
                showToast(`📱 Kamera Telefon Bersambung: ${cam.name}`, "success");
                playChime(false);

                // Update QR modal status if open
                const statusText = document.getElementById("qr-modal-status-text");
                if (statusText) {
                    statusText.innerHTML = `<strong>🟢 Bersambung!</strong> ${cam.name} kini aktif.`;
                }
            }
        });

        // Rebuild select options
        selectEl.innerHTML = "";
        cameras.forEach(cam => {
            const opt = document.createElement("option");
            opt.value = cam.id;
            const statusEmoji = (cam.status === "online") ? "🟢" : "⚪";
            const fpsText = (cam.status === "online" && cam.fps > 0) ? ` (${cam.fps} FPS)` : "";
            opt.textContent = `${statusEmoji} ${cam.name}${fpsText}`;
            if (cam.id === activeId) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        });

        // Update badge
        const badge = document.getElementById("cam-status-badge");
        if (badge) {
            const currentCam = cameras.find(c => c.id === activeId);
            if (currentCam && currentCam.status === "online") {
                badge.className = "badge badge-green";
                badge.textContent = (currentCam.type === "remote") ? "TELEFON LANGSUNG" : "LANGSUNG";
            } else {
                badge.className = "badge badge-amber";
                badge.textContent = "TERPUTUS";
            }
        }
    } catch (err) {
        // network error ignored
    }
}

function initCameraSelector() {
    const selectEl = document.getElementById("camera-source-select");
    if (!selectEl) return;

    selectEl.addEventListener("change", async () => {
        const selectedId = selectEl.value;
        try {
            const res = await fetch("/api/cameras/select", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ cam_id: selectedId })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Suapan kamera ditukar`, "info");
                const serverImg = document.getElementById("server-video-feed");
                if (serverImg && !useBrowserCam) {
                    serverImg.src = "/video_feed?t=" + Date.now();
                }
            } else {
                showToast("Gagal menukar kamera: " + (data.error || "Ralat tidak diketahui"), "danger");
            }
        } catch (e) {
            showToast("Ralat sambungan pelayan", "danger");
        }
    });

    pollCameras();
    setInterval(pollCameras, 3500);
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    // Attach Task Buttons
    document.querySelectorAll(".task-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            selectTask(btn.dataset.task);
        });
    });

    // Attach Scan Buttons
    const scanBtn = document.getElementById("scan-now-btn");
    if (scanBtn) scanBtn.addEventListener("click", triggerScan);

    const autoBtn = document.getElementById("auto-scan-btn");
    if (autoBtn) autoBtn.addEventListener("click", toggleAutoScan);

    const toggleCamBtn = document.getElementById("toggle-cam-btn");
    if (toggleCamBtn) toggleCamBtn.addEventListener("click", toggleCameraSource);

    // Multi-Camera & Phone QR modal
    initPhoneCameraModal();
    initCameraSelector();
});
