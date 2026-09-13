"""
Camera manager for AI-WebCam.
Provides thread-safe video capture via OpenCV with synthetic test patterns if physical camera is offline.
Generates MJPEG streams for Flask and encodes frames to JPEG/Base64 for AI analysis.
"""

import cv2
import time
import base64
import threading
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from core.config import SNAPSHOTS_DIR

class CameraManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, camera_index: int = 0):
        if self._initialized:
            return
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self.last_frame = None
        self.frame_lock = threading.Lock()
        self.simulated_mode = False
        self._thread = None
        self.active_cam_id = "local_0"
        self.remote_cameras = {}
        self.remote_lock = threading.Lock()
        self._initialized = True
        self.start()

    def start(self):
        """Starts video capture background thread."""
        if self.is_running:
            return

        # Attempt opening hardware camera
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if self.cap.isOpened():
                # Set reasonable default resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    self.simulated_mode = False
                else:
                    self.simulated_mode = True
            else:
                self.simulated_mode = True
        except Exception as e:
            print(f"[Camera] Cannot open hardware camera ({e}). Switching to synthetic test feed.")
            self.simulated_mode = True

        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self):
        tick = 0
        while self.is_running:
            if not self.simulated_mode and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.frame_lock:
                        self.last_frame = frame
                    time.sleep(0.03)  # ~30 fps
                    continue
                else:
                    self.simulated_mode = True

            # Generate high-quality simulated test frame
            tick += 1
            frame = self._generate_test_pattern(tick)
            with self.frame_lock:
                self.last_frame = frame
            time.sleep(0.05)  # ~20 fps for synthetic stream

    def _generate_test_pattern(self, tick: int) -> np.ndarray:
        """Generates a dynamic test frame representing a live camera monitor."""
        w, h = 640, 480
        # Dark tech blue background
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (24, 28, 36)

        # Subtle grid
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), (38, 44, 54), 1)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), (38, 44, 54), 1)

        # Center target box with scanning beam
        box_x, box_y, box_w, box_h = 140, 100, 360, 240
        cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (15, 118, 110), 2)
        
        # Corner brackets
        corner_len = 25
        # Top-left
        cv2.line(frame, (box_x, box_y), (box_x + corner_len, box_y), (20, 184, 166), 3)
        cv2.line(frame, (box_x, box_y), (box_x, box_y + corner_len), (20, 184, 166), 3)
        # Top-right
        cv2.line(frame, (box_x + box_w, box_y), (box_x + box_w - corner_len, box_y), (20, 184, 166), 3)
        cv2.line(frame, (box_x + box_w, box_y), (box_x + box_w, box_y + corner_len), (20, 184, 166), 3)
        # Bottom-left
        cv2.line(frame, (box_x, box_y + box_h), (box_x + corner_len, box_y + box_h), (20, 184, 166), 3)
        cv2.line(frame, (box_x, box_y + box_h), (box_x, box_y + box_h - corner_len), (20, 184, 166), 3)
        # Bottom-right
        cv2.line(frame, (box_x + box_w, box_y + box_h), (box_x + box_w - corner_len, box_y + box_h), (20, 184, 166), 3)
        cv2.line(frame, (box_x + box_w, box_y + box_h), (box_x + box_w, box_y + box_h - corner_len), (20, 184, 166), 3)

        # Scanning line
        scan_pos = box_y + int((tick * 4) % box_h)
        cv2.line(frame, (box_x + 2, scan_pos), (box_x + box_w - 2, scan_pos), (52, 211, 153), 2)

        # Simulated car plate inside target box
        plate_bg_x, plate_bg_y, plate_w, plate_h = 230, 200, 180, 50
        cv2.rectangle(frame, (plate_bg_x, plate_bg_y), (plate_bg_x + plate_w, plate_bg_y + plate_h), (10, 10, 12), -1)
        cv2.rectangle(frame, (plate_bg_x, plate_bg_y), (plate_bg_x + plate_w, plate_bg_y + plate_h), (220, 220, 220), 2)
        cv2.putText(frame, "WXY 1234", (plate_bg_x + 18, plate_bg_y + 35), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)

        # Top HUD Text
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_text = "SIMULATED FEED (ACTIVE)" if self.simulated_mode else "LIVE HARDWARE WEBCAM"
        cv2.putText(frame, f"AI-WEBCAM REC  |  {now_str}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)
        cv2.putText(frame, status_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (20, 184, 166), 1)

        # Red recording dot
        if (tick // 10) % 2 == 0:
            cv2.circle(frame, (w - 30, 30), 8, (0, 0, 230), -1)

        return frame

    def register_remote_frame(self, cam_id: str, name: str, ip: str, jpeg_bytes: bytes) -> Tuple[bool, str]:
        """
        Registers an incoming JPEG frame from an external phone camera node.
        Updates frame, calculated rolling FPS, and last-seen timestamp.
        """
        if not jpeg_bytes:
            return False, "Data bingkai kosong."

        np_arr = np.frombuffer(jpeg_bytes, np.uint8)
        frame_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame_np is None:
            return False, "Format imej tidak sah."

        now = time.time()
        with self.remote_lock:
            first_time = (cam_id not in self.remote_cameras)
            if first_time:
                self.remote_cameras[cam_id] = {
                    "id": cam_id,
                    "name": name or f"Kamera Telefon ({cam_id})",
                    "ip": ip,
                    "last_seen": now,
                    "last_frame": frame_np,
                    "last_jpeg": jpeg_bytes,
                    "frame_count": 1,
                    "fps": 0.0,
                    "fps_timer": now,
                    "fps_counter": 1,
                    "first_connected": now
                }
                # Automatically switch active camera to the newly connected phone camera
                self.active_cam_id = cam_id
            else:
                node = self.remote_cameras[cam_id]
                node["last_seen"] = now
                if name:
                    node["name"] = name
                node["ip"] = ip
                node["last_frame"] = frame_np
                node["last_jpeg"] = jpeg_bytes
                node["frame_count"] += 1
                node["fps_counter"] += 1

                elapsed = now - node["fps_timer"]
                if elapsed >= 1.0:
                    node["fps"] = round(node["fps_counter"] / elapsed, 1)
                    node["fps_counter"] = 0
                    node["fps_timer"] = now

        return True, "Bingkai berjaya diterima."

    def set_active_camera(self, cam_id: str) -> bool:
        """Sets the active camera source ('local_0' or remote camera ID)."""
        if cam_id == "local_0":
            self.active_cam_id = "local_0"
            return True
        with self.remote_lock:
            if cam_id in self.remote_cameras:
                self.active_cam_id = cam_id
                return True
        return False

    def get_camera_list(self) -> list:
        """Returns a list of all known camera nodes and their current status."""
        now = time.time()
        cams = [
            {
                "id": "local_0",
                "name": "Kamera Tempatan (Webcam)" if not self.simulated_mode else "Kamera Tempatan (Simulasi)",
                "type": "local",
                "is_active": (self.active_cam_id == "local_0"),
                "status": "online",
                "ip": "127.0.0.1",
                "fps": 30.0 if not self.simulated_mode else 20.0
            }
        ]
        with self.remote_lock:
            for cid, node in self.remote_cameras.items():
                is_online = (now - node["last_seen"]) < 12.0
                cams.append({
                    "id": cid,
                    "name": node["name"],
                    "type": "remote",
                    "is_active": (self.active_cam_id == cid),
                    "status": "online" if is_online else "offline",
                    "ip": node.get("ip", ""),
                    "fps": node.get("fps", 0.0) if is_online else 0.0,
                    "last_seen_secs_ago": round(now - node["last_seen"], 1)
                })
        return cams

    def _generate_disconnected_pattern(self, name: str) -> np.ndarray:
        """Generates a standby frame when a phone camera disconnects or times out."""
        w, h = 640, 480
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (20, 24, 30)

        # Warning container box
        box_x, box_y, box_w, box_h = 80, 110, 480, 260
        cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (35, 45, 60), -1)
        cv2.rectangle(frame, (box_x, box_y), (box_x + box_w, box_y + box_h), (50, 100, 220), 2)

        cv2.putText(frame, "SAMBUNGAN KAMERA TERPUTUS", (box_x + 60, box_y + 60), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (100, 150, 255), 2)
        cv2.putText(frame, f"Nod: {name}", (box_x + 60, box_y + 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)
        cv2.putText(frame, "Sila pastikan telefon masih membuka web /phone_cam", (box_x + 40, box_y + 155), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)
        cv2.putText(frame, "Menunggu bingkai seterusnya...", (box_x + 120, box_y + 205), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (20, 184, 166), 1)

        return frame

    def get_frame(self, cam_id: Optional[str] = None) -> np.ndarray:
        """Returns the latest captured frame as a numpy array for the active or specified camera."""
        target_id = cam_id or self.active_cam_id
        if target_id != "local_0":
            with self.remote_lock:
                if target_id in self.remote_cameras:
                    node = self.remote_cameras[target_id]
                    if (time.time() - node["last_seen"]) < 12.0 and node["last_frame"] is not None:
                        return node["last_frame"].copy()
                    return self._generate_disconnected_pattern(node["name"])

        # Default local hardware/synthetic frame
        with self.frame_lock:
            if self.last_frame is not None:
                return self.last_frame.copy()
        return self._generate_test_pattern(0)

    def get_jpeg_bytes(self, cam_id: Optional[str] = None) -> bytes:
        """Encodes or returns JPEG bytes for the active or specified camera."""
        target_id = cam_id or self.active_cam_id
        if target_id != "local_0":
            with self.remote_lock:
                if target_id in self.remote_cameras:
                    node = self.remote_cameras[target_id]
                    if (time.time() - node["last_seen"]) < 12.0 and node["last_jpeg"] is not None:
                        return node["last_jpeg"]

        frame = self.get_frame(cam_id=target_id)
        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret:
            return buf.tobytes()
        return b""

    def get_base64_frame(self, cam_id: Optional[str] = None) -> str:
        """Encodes the current frame as a Base64 string."""
        raw_bytes = self.get_jpeg_bytes(cam_id=cam_id)
        return base64.b64encode(raw_bytes).decode("ascii")

    def save_snapshot(self, frame: Optional[np.ndarray] = None, prefix: str = "snap", cam_id: Optional[str] = None) -> str:
        """Saves frame to disk in data/snapshots/ and returns relative web path."""
        if frame is None:
            frame = self.get_frame(cam_id=cam_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        filename = f"{prefix}_{timestamp}.jpg"
        filepath = SNAPSHOTS_DIR / filename
        cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return f"snapshots/{filename}"

    def generate_mjpeg_stream(self, cam_id: Optional[str] = None):
        """Yields MJPEG multipart stream for HTTP video response."""
        while self.is_running:
            jpeg = self.get_jpeg_bytes(cam_id=cam_id)
            if jpeg:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            time.sleep(0.04)  # ~25 fps

    def stop(self):
        self.is_running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()

# Global singleton helper
def get_camera_manager() -> CameraManager:
    return CameraManager()
