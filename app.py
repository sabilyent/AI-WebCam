"""
AI-WebCam Main Application Server (Flask).
Research-oriented Computer Vision & AI Vision kit with BYOK multi-provider support.
"""

import os
import socket
import base64
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, send_from_directory

from core.config import BASE_DIR, DATA_DIR, REFERENCE_FACES_DIR, SNAPSHOTS_DIR, SUPPORTED_PROVIDERS
from core.database import (
    init_db, get_active_api_setting, save_api_setting,
    get_vehicles, add_vehicle, delete_vehicle,
    get_faces, get_face_by_id, add_face, delete_face,
    get_logs, clear_logs,
    get_sports_sessions, get_dashboard_stats
)
from core.camera import get_camera_manager
from ai_services.factory import get_vision_service
from tasks.license_plate import process_license_plate
from tasks.face_recognition import process_face_recognition
from tasks.ocr_reader import process_ocr_reader
from tasks.scene_analyzer import process_scene_analysis
from tasks.sports_analysis import process_sports_analysis

app = Flask(__name__, 
            template_folder=str(BASE_DIR / "templates"),
            static_folder=str(BASE_DIR / "static"))
app.secret_key = os.environ.get("FLASK_SECRET", "ai-webcam-secret-key-2026")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

# Initialize database schema and seeds on startup
init_db()

# Camera instance
camera = get_camera_manager()

def get_local_ip() -> str:
    """Returns host LAN IP address for QR code / phone connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_connect_url(req=None) -> str:
    """
    Constructs the connect_url dynamically based on incoming request headers:
    - X-Forwarded-Host or Host
    - X-Forwarded-Proto or scheme
    If accessed through a public domain or reverse proxy (e.g. rimau.kpst.my), avoids hardcoding port 5001.
    """
    local_ip = get_local_ip()
    if not req:
        return f"https://{local_ip}:5001/phone_cam?id=phone_1"

    # Inspect headers (supports NGINX, Cloudflare, Caddy, Apache proxies)
    forwarded_host = req.headers.get("X-Forwarded-Host")
    raw_host = forwarded_host or req.headers.get("Host") or req.host or ""
    proto = (req.headers.get("X-Forwarded-Proto") or req.scheme or "http").lower()

    # Determine hostname and port
    if ":" in raw_host:
        hostname = raw_host.split(":")[0].strip()
        host_port = raw_host.split(":")[1].strip()
    else:
        hostname = raw_host.strip()
        host_port = ""

    is_ip_or_local = (
        hostname in ("localhost", "127.0.0.1", "") or
        hostname.startswith("192.168.") or
        hostname.startswith("10.") or
        (hostname.startswith("172.") and len(hostname.split(".")) > 1 and hostname.split(".")[1].isdigit() and 16 <= int(hostname.split(".")[1]) <= 31)
    )

    # 1. If accessed over HTTPS or via a public domain (e.g. https://rimau.kpst.my/):
    if proto == "https" or not is_ip_or_local:
        port_part = f":{host_port}" if host_port and host_port not in ("80", "443", "5000") else ""
        return f"https://{hostname}{port_part}/phone_cam?id=phone_1"

    # 2. Local LAN IP accessed via HTTP (e.g. http://192.168.1.21:5000):
    # Mobile browsers require HTTPS for camera permission (getUserMedia), so use local HTTPS port 5001
    target_ip = local_ip if hostname in ("localhost", "127.0.0.1", "") else hostname
    return f"https://{target_ip}:5001/phone_cam?id=phone_1"

def get_provider_display_name(setting: dict) -> str:
    provider = setting.get("provider", "gemini")
    model = setting.get("model_name", "")
    info = SUPPORTED_PROVIDERS.get(provider, {})
    name = info.get("name", provider.capitalize())
    if model:
        return f"{name} ({model})"
    return name

# -------------------------------------------------------------
# Web Page Routes
# -------------------------------------------------------------
@app.route("/")
def dashboard():
    setting = get_active_api_setting()
    stats = get_dashboard_stats()
    recent_logs = get_logs(limit=8)
    local_ip = get_local_ip()
    connect_url = get_connect_url(request)

    return render_template(
        "index.html",
        active_page="dashboard",
        stats=stats,
        recent_logs=recent_logs,
        active_provider=setting.get("provider"),
        active_provider_name=get_provider_display_name(setting),
        has_api_key=setting.get("has_key", False),
        local_ip=local_ip,
        connect_url=connect_url
    )

@app.route("/phone_cam")
def phone_cam_page():
    """Mobile-first camera streaming interface for smartphones."""
    cam_id = request.args.get("id", "phone_1")
    cam_name = request.args.get("name", "Kamera Telefon")
    local_ip = get_local_ip()
    port = request.host.split(":")[-1] if ":" in request.host else "5000"
    return render_template(
        "phone_cam.html",
        cam_id=cam_id,
        cam_name=cam_name,
        local_ip=local_ip,
        port=port
    )

@app.route("/video_feed")
def video_feed():
    """MJPEG streaming endpoint for camera feed."""
    return Response(
        camera.generate_mjpeg_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/settings")
def settings_page():
    setting = get_active_api_setting()
    return render_template(
        "settings.html",
        active_page="settings",
        current_setting=setting,
        active_provider_name=get_provider_display_name(setting)
    )

@app.route("/watchlist")
def watchlist_page():
    setting = get_active_api_setting()
    vehicles = get_vehicles()
    faces = get_faces()
    return render_template(
        "watchlist.html",
        active_page="watchlist",
        vehicles=vehicles,
        faces=faces,
        active_provider_name=get_provider_display_name(setting)
    )

@app.route("/logs")
def logs_page():
    setting = get_active_api_setting()
    task_filter = request.args.get("task")
    logs = get_logs(limit=100, task_type=task_filter)
    return render_template(
        "logs.html",
        active_page="logs",
        logs=logs,
        current_filter=task_filter,
        active_provider_name=get_provider_display_name(setting)
    )

@app.route("/sports")
def sports_page():
    setting = get_active_api_setting()
    sessions = get_sports_sessions(limit=15)
    return render_template(
        "sports.html",
        active_page="sports",
        past_sessions=sessions,
        active_provider_name=get_provider_display_name(setting)
    )

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.route("/api/current_frame")
def api_current_frame():
    """Returns current live frame as Base64 for instant client-side preview/capture."""
    b64 = camera.get_base64_frame()
    if b64:
        return jsonify({"success": True, "image_base64": b64})
    return jsonify({"success": False, "error": "Kamera tidak menghasilkan bingkai."}), 400

@app.route("/api/scan", methods=["POST"])
def api_scan():
    """
    Triggers AI vision scan on current camera frame (or uploaded browser frame).
    Payload: { "task": "ANPR"|"FACE"|"OCR"|"SCENE"|"SPORTS", "image_base64": "..." }
    """
    payload = request.get_json(silent=True) or {}
    task = (payload.get("task") or "ANPR").upper()
    client_b64 = payload.get("image_base64")

    # 1. Acquire frame image bytes
    if client_b64:
        try:
            image_bytes = base64.b64decode(client_b64)
        except Exception:
            image_bytes = camera.get_jpeg_bytes()
    else:
        image_bytes = camera.get_jpeg_bytes()

    if not image_bytes:
        return jsonify({"success": False, "error": "Gagal merakam bingkai dari kamera."}), 400

    # 2. Save snapshot
    snap_path = camera.save_snapshot(prefix=task.lower())

    # 3. Obtain vision service
    service = get_vision_service()

    # 4. Dispatch by task
    if task == "ANPR":
        result = process_license_plate(image_bytes, service, snapshot_path=snap_path)
    elif task == "FACE":
        result = process_face_recognition(image_bytes, service, snapshot_path=snap_path)
    elif task == "OCR":
        result = process_ocr_reader(image_bytes, service, snapshot_path=snap_path)
    elif task == "SCENE":
        result = process_scene_analysis(image_bytes, service, snapshot_path=snap_path)
    elif task == "SPORTS":
        athlete = payload.get("athlete_name", "Murid 1")
        sport_type = payload.get("sport_type", "Larian Pecut")
        result = process_sports_analysis(image_bytes, service, athlete_name=athlete, sport_type=sport_type, snapshot_path=snap_path)
    else:
        return jsonify({"success": False, "error": f"Tugasan '{task}' tidak dikenali."}), 400

    result["snapshot_url"] = snap_path
    return jsonify(result)

@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    provider = request.form.get("provider", "gemini").strip()
    api_key = request.form.get("api_key", "").strip()
    model_name = request.form.get("model_name", "").strip()
    base_url = request.form.get("base_url", "").strip()

    save_api_setting(provider=provider, api_key=api_key, model_name=model_name, base_url=base_url)
    return redirect(url_for("settings_page"))

@app.route("/api/test_connection", methods=["POST"])
def api_test_connection():
    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider", "gemini")
    api_key = payload.get("api_key", "").strip()
    model_name = payload.get("model_name", "")
    base_url = payload.get("base_url", "")

    # Test with current camera snapshot
    image_bytes = camera.get_jpeg_bytes()
    if not image_bytes:
        return jsonify({"success": False, "error": "Kamera tidak menghasilkan bingkai."}), 400

    from ai_services.gemini_service import GeminiVisionService
    from ai_services.openai_service import OpenAIVisionService
    from ai_services.ollama_service import OllamaVisionService

    try:
        if provider == "gemini":
            if not api_key:
                return jsonify({"success": False, "error": "Sila masukkan Kunci API Gemini."}), 400
            tester = GeminiVisionService(api_key=api_key, model_name=model_name or "gemini-3.6-flash")
            res = tester.analyze(image_bytes, "Return JSON: {'status': 'ok'}")
        elif provider == "openai":
            if not api_key:
                return jsonify({"success": False, "error": "Sila masukkan Kunci API OpenAI."}), 400
            tester = OpenAIVisionService(api_key=api_key, model_name=model_name or "gpt-4o-mini")
            res = tester.analyze(image_bytes, "Return JSON: {'status': 'ok'}")
        elif provider == "ollama":
            tester = OllamaVisionService(model_name=model_name or "moondream", base_url=base_url or "http://localhost:11434")
            res = tester.analyze(image_bytes, "Return JSON: {'status': 'ok'}")
        else:
            return jsonify({"success": False, "error": "Pembekal tidak sah."}), 400

        if res.get("success"):
            return jsonify({"success": True, "message": f"Model {model_name or 'lalai'} sedia beroperasi"})
        return jsonify({"success": False, "error": res.get("error", "Gagal menyambung ke model")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/list_models", methods=["POST"])
def api_list_models():
    """Fetches list of available models directly from the selected provider."""
    payload = request.get_json(silent=True) or {}
    provider = payload.get("provider", "gemini")
    api_key = payload.get("api_key", "").strip()
    base_url = payload.get("base_url", "").strip() or "http://localhost:11434"

    # Fallback to saved key if user didn't type one
    if not api_key and provider != "ollama":
        saved = get_active_api_setting()
        if saved.get("provider") == provider:
            api_key = saved.get("api_key", "")

    try:
        if provider == "gemini":
            if not api_key:
                return jsonify({"success": False, "error": "Sila masukkan Kunci API Google Gemini untuk melihat senarai model."}), 400
            from ai_services.gemini_service import list_gemini_models
            models = list_gemini_models(api_key=api_key)
        elif provider == "openai":
            if not api_key:
                return jsonify({"success": False, "error": "Sila masukkan Kunci API OpenAI untuk melihat senarai model."}), 400
            from ai_services.openai_service import list_openai_models
            models = list_openai_models(api_key=api_key)
        elif provider == "ollama":
            from ai_services.ollama_service import list_ollama_models
            models = list_ollama_models(base_url=base_url)
        else:
            return jsonify({"success": False, "error": "Pembekal tidak sah."}), 400

        return jsonify({
            "success": True,
            "provider": provider,
            "count": len(models),
            "models": models
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/watchlist/vehicles", methods=["POST"])
def api_add_vehicle():
    plate = request.form.get("plate_number", "")
    owner = request.form.get("owner_name", "")
    status = request.form.get("status", "Dibenarkan")
    category = request.form.get("category", "Staf")
    notes = request.form.get("notes", "")

    if plate and owner:
        add_vehicle(plate, owner, status, category, notes)
    return redirect(url_for("watchlist_page"))

@app.route("/api/watchlist/vehicles/<int:vehicle_id>/delete", methods=["POST"])
def api_delete_vehicle(vehicle_id):
    delete_vehicle(vehicle_id)
    return redirect(url_for("watchlist_page"))

@app.route("/data/reference_faces/<path:filename>")
def serve_reference_face(filename):
    return send_from_directory(str(REFERENCE_FACES_DIR), filename)

@app.route("/data/snapshots/<path:filename>")
def serve_snapshot(filename):
    return send_from_directory(str(SNAPSHOTS_DIR), filename)

@app.route("/api/watchlist/faces", methods=["POST"])
def api_add_face():
    name = request.form.get("person_name", "").strip()
    category = request.form.get("category", "Staf")
    notes = request.form.get("notes", "").strip()
    image_b64 = request.form.get("image_base64", "").strip()
    file_upload = request.files.get("face_image_file")

    image_filename = ""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]

    if image_b64:
        # User snapped photo from webcam
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
        try:
            img_bytes = base64.b64decode(image_b64)
            image_filename = f"face_{timestamp}.jpg"
            with open(REFERENCE_FACES_DIR / image_filename, "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            print("[Face] Ralat menyimpan imej base64:", e)
    elif file_upload and file_upload.filename:
        # User uploaded a file
        ext = file_upload.filename.rsplit(".", 1)[-1].lower() if "." in file_upload.filename else "jpg"
        image_filename = f"face_{timestamp}.{ext}"
        file_upload.save(str(REFERENCE_FACES_DIR / image_filename))
    else:
        # Fallback: grab current frame directly from camera
        cam_bytes = camera.get_jpeg_bytes()
        if cam_bytes:
            image_filename = f"face_{timestamp}.jpg"
            with open(REFERENCE_FACES_DIR / image_filename, "wb") as f:
                f.write(cam_bytes)

    if name:
        add_face(name, category, image_path=image_filename, notes=notes)
    return redirect(url_for("watchlist_page"))

@app.route("/api/watchlist/faces/<int:face_id>/delete", methods=["POST"])
def api_delete_face(face_id):
    face = get_face_by_id(face_id)
    if face and face.get("image_path"):
        img_file = REFERENCE_FACES_DIR / face["image_path"]
        if img_file.exists():
            try:
                img_file.unlink()
            except Exception:
                pass
    delete_face(face_id)
    return redirect(url_for("watchlist_page"))

@app.route("/api/logs/clear", methods=["POST"])
def api_clear_logs():
    clear_logs()
    return redirect(url_for("logs_page"))

@app.route("/api/stats")
def api_stats():
    return jsonify(get_dashboard_stats())

# -------------------------------------------------------------
# Multi-Camera Remote Node Endpoints
# -------------------------------------------------------------
@app.route("/api/cameras", methods=["GET"])
def api_get_cameras():
    """Returns all camera sources and their active/online status."""
    cameras = camera.get_camera_list()
    local_ip = get_local_ip()
    return jsonify({
        "success": True,
        "active_cam_id": camera.active_cam_id,
        "cameras": cameras,
        "local_ip": local_ip,
        "port": "5001",
        "connect_url": get_connect_url(request)
    })

@app.route("/api/cameras/select", methods=["POST"])
def api_select_camera():
    """Switches the active camera feed."""
    payload = request.get_json(silent=True) or {}
    cam_id = payload.get("cam_id", "local_0")
    if camera.set_active_camera(cam_id):
        return jsonify({
            "success": True,
            "active_cam_id": cam_id,
            "message": f"Kamera aktif ditukar ke {cam_id}."
        })
    return jsonify({"success": False, "error": f"Kamera '{cam_id}' tidak ditemui."}), 404

@app.route("/api/remote_camera/frame", methods=["POST"])
def api_remote_camera_frame():
    """
    Receives continuous video frames from remote phone camera node.
    Accepts multipart/form-data or JSON payload with base64 image.
    """
    cam_id = request.form.get("cam_id") or request.args.get("cam_id") or "phone_1"
    cam_name = request.form.get("cam_name") or request.args.get("cam_name") or "Kamera Telefon"
    client_ip = request.remote_addr or "127.0.0.1"

    jpeg_bytes = None
    if "frame" in request.files:
        jpeg_bytes = request.files["frame"].read()
    else:
        payload = request.get_json(silent=True)
        if payload and "image_base64" in payload:
            raw_b64 = payload["image_base64"]
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            try:
                jpeg_bytes = base64.b64decode(raw_b64)
            except Exception:
                pass
            if payload.get("cam_id"):
                cam_id = payload["cam_id"]
            if payload.get("cam_name"):
                cam_name = payload["cam_name"]

    if not jpeg_bytes:
        return jsonify({"success": False, "error": "Tiada data bingkai diterima."}), 400

    success, msg = camera.register_remote_frame(
        cam_id=cam_id,
        name=cam_name,
        ip=client_ip,
        jpeg_bytes=jpeg_bytes
    )
    if success:
        return jsonify({"success": True, "message": msg, "cam_id": cam_id, "active_cam_id": camera.active_cam_id})
    return jsonify({"success": False, "error": msg}), 400

def ensure_ssl_certs():
    cert_file = BASE_DIR / "cert.pem"
    key_file = BASE_DIR / "key.pem"
    if not cert_file.exists() or not key_file.exists():
        import subprocess
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(key_file), "-out", str(cert_file),
                "-days", "365", "-nodes", "-subj", "/CN=AI-WebCam-LAN"
            ], check=True, capture_output=True)
            print("[SSL] Sijil SSL tempatan dijana secara automatik.")
        except Exception as e:
            print("[SSL] Tidak dapat menjana sijil SSL:", e)
    return str(cert_file), str(key_file)

if __name__ == "__main__":
    from werkzeug.serving import make_server
    import threading
    import ssl
    import time

    http_port = int(os.environ.get("PORT", 5000))
    https_port = int(os.environ.get("HTTPS_PORT", 5001))
    local_ip = get_local_ip()

    cert_path, key_path = ensure_ssl_certs()

    # 1. Start HTTP server on port 5000 (standard access for PC)
    http_server = make_server("0.0.0.0", http_port, app, threaded=True)
    t_http = threading.Thread(target=http_server.serve_forever, daemon=True)
    t_http.start()

    # 2. Start HTTPS server on port 5001 (Secure Context for Phone Cameras)
    has_https = False
    try:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(cert_path, key_path)
        https_server = make_server("0.0.0.0", https_port, app, ssl_context=ssl_ctx, threaded=True)
        t_https = threading.Thread(target=https_server.serve_forever, daemon=True)
        t_https.start()
        has_https = True
    except Exception as e:
        print("[SSL] Gagal melancarkan pelayan HTTPS:", e)

    print(f"==================================================")
    print(f"🚀 AI-WebCam Pelayan Dwi-Protokol Sedang Beroperasi:")
    print(f"💻 Komputer PC (HTTP) : http://127.0.0.1:{http_port}")
    if has_https:
        print(f"📱 Telefon Pintar (HTTPS) : https://{local_ip}:{https_port}/phone_cam")
        print(f"   (HTTPS diperlukan oleh pelayar telefon untuk mengaktifkan kamera)")
    print(f"==================================================")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nMenutup pelayan...")
        http_server.shutdown()
        if has_https:
            https_server.shutdown()
