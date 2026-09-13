"""
Configuration module for AI-WebCam.
Handles file paths, encryption keys, and model defaults.
"""

import os
import base64
import hashlib
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
REFERENCE_FACES_DIR = DATA_DIR / "reference_faces"
DATABASE_PATH = DATA_DIR / "ai_webcam.db"

# Ensure runtime directories exist
DATA_DIR.mkdir(exist_ok=True)
SNAPSHOTS_DIR.mkdir(exist_ok=True)
REFERENCE_FACES_DIR.mkdir(exist_ok=True)

# Secret encryption key for API Key storage (derived from local machine ID / fallback)
def _get_encryption_key() -> bytes:
    machine_id = os.environ.get("MACHINE_ID", "ai-webcam-secret-salt-2025")
    return hashlib.sha256(machine_id.encode()).digest()

_KEY = _get_encryption_key()

def encrypt_key(plain_text: str) -> str:
    """Simple XOR-based reversible obfuscation + Base64 for local database storage."""
    if not plain_text:
        return ""
    plain_bytes = plain_text.encode("utf-8")
    xor_bytes = bytes([b ^ _KEY[i % len(_KEY)] for i, b in enumerate(plain_bytes)])
    return base64.b64encode(xor_bytes).decode("ascii")

def decrypt_key(encrypted_text: str) -> str:
    """Reverse XOR-based de-obfuscation."""
    if not encrypted_text:
        return ""
    try:
        xor_bytes = base64.b64decode(encrypted_text.encode("ascii"))
        plain_bytes = bytes([b ^ _KEY[i % len(_KEY)] for i, b in enumerate(xor_bytes)])
        return plain_bytes.decode("utf-8")
    except Exception:
        # Fallback if text was stored as plain text
        return encrypted_text

# Supported AI Providers & recommended models
SUPPORTED_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "default_model": "gemini-3.6-flash",
        "models": ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        "needs_key": True,
        "help_url": "https://aistudio.google.com/app/apikey"
    },
    "openai": {
        "name": "OpenAI (GPT-4o)",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "needs_key": True,
        "help_url": "https://platform.openai.com/api-keys"
    },
    "ollama": {
        "name": "Ollama (Tempatan / Luar Talian)",
        "default_model": "moondream",
        "models": ["moondream", "llava:7b", "llava-phi3", "minicpm-v"],
        "needs_key": False,
        "default_url": "http://localhost:11434",
        "help_url": "https://ollama.com/library/moondream"
    }
}

# Task Definitions
TASK_ANPR = "ANPR"
TASK_FACE = "FACE"
TASK_OCR = "OCR"
TASK_SCENE = "SCENE"
TASK_SPORTS = "SPORTS"

TASKS = [
    {"id": TASK_ANPR, "title": "Nombor Plat (ANPR)", "icon": "fa-car", "desc": "Pengecaman nombor pendaftaran kenderaan & semakan senarai."},
    {"id": TASK_FACE, "title": "Pengecaman Wajah", "icon": "fa-user-tag", "desc": "Pengesanan wajah & padanan rekod staf/pelawat/VIP."},
    {"id": TASK_OCR, "title": "Pengecaman Huruf (OCR)", "icon": "fa-file-lines", "desc": "Pembacaan teks, resit, dan dokumen fizikal."},
    {"id": TASK_SCENE, "title": "Analisis Senario", "icon": "fa-eye", "desc": "Pemerhatian situasi am, aktiviti, dan amaran keselamatan."},
    {"id": TASK_SPORTS, "title": "Analisis Sukan", "icon": "fa-person-running", "desc": "Penjejakan postur badan (Pose), kelajuan & cadangan teknik."}
]
