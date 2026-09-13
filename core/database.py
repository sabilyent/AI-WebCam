"""
SQLite3 Database Manager for AI-WebCam.
Handles database connection, table initialization, seed data, and CRUD operations.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.config import DATABASE_PATH, encrypt_key, decrypt_key

def get_db_connection() -> sqlite3.Connection:
    """Returns a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes tables and seeds starter data if newly created."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. API Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider TEXT NOT NULL,
        api_key TEXT,
        model_name TEXT NOT NULL,
        base_url TEXT,
        is_active INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Vehicle Watchlist (ANPR)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT UNIQUE NOT NULL,
        owner_name TEXT NOT NULL,
        status TEXT NOT NULL,
        category TEXT DEFAULT 'Staf',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Face Dataset
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS face_dataset (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_name TEXT NOT NULL,
        category TEXT NOT NULL,
        image_path TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Detection Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detection_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_type TEXT NOT NULL,
        detected_value TEXT,
        confidence REAL DEFAULT 0.0,
        match_status TEXT,
        matched_info TEXT,
        snapshot_path TEXT,
        raw_json TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Sports Analysis Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sports_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_name TEXT DEFAULT 'Murid 1',
        sport_type TEXT DEFAULT 'Larian Pecut',
        duration_seconds REAL DEFAULT 0.0,
        avg_stride_angle REAL DEFAULT 0.0,
        posture_score INTEGER DEFAULT 80,
        ai_feedback TEXT,
        ai_recommendations TEXT,
        snapshot_path TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # Check and insert seed data if empty
    cursor.execute("SELECT COUNT(*) FROM api_settings;")
    if cursor.fetchone()[0] == 0:
        # Default starter provider: Gemini 3.6 Flash
        cursor.execute("""
        INSERT INTO api_settings (provider, api_key, model_name, is_active)
        VALUES ('gemini', '', 'gemini-3.6-flash', 1);
        """)
    else:
        # Auto-migrate deprecated gemini-2.0-flash to gemini-3.6-flash
        cursor.execute("""
        UPDATE api_settings SET model_name = 'gemini-3.6-flash'
        WHERE model_name = 'gemini-2.0-flash';
        """)

    cursor.execute("SELECT COUNT(*) FROM vehicle_watchlist;")
    if cursor.fetchone()[0] == 0:
        seed_vehicles = [
            ("WXY 1234", "Cikgu Ahmad (Pengetua)", "Dibenarkan", "Pengurusan", "Tempat letak kereta Utama"),
            ("VAA 8888", "Dr. Siti Aminah", "Dibenarkan", "VIP", "Penceramah jemputan"),
            ("BKA 9999", "Kenderaan Mencurigakan", "Senarai Hitam", "Senarai Hitam", "Pernah menceroboh zon asrama"),
            ("JQR 5511", "En. Razak (Kontraktor)", "Perhatian", "Pelawat", "Perlu daftar di pondok pengawal"),
            ("PEN 2026", "Pn. Salmah (Guru Sukan)", "Dibenarkan", "Guru", "Pelekat Sekolah #2026")
        ]
        cursor.executemany("""
        INSERT INTO vehicle_watchlist (plate_number, owner_name, status, category, notes)
        VALUES (?, ?, ?, ?, ?);
        """, seed_vehicles)

    cursor.execute("SELECT COUNT(*) FROM face_dataset;")
    if cursor.fetchone()[0] == 0:
        seed_faces = [
            ("Cikgu Ahmad", "VIP", "", "Pengetua SMK Mahkota"),
            ("Pn. Salmah", "Staf", "", "Ketua Bidang Sukan & Kokurikulum"),
            ("Amirul Hakimi", "Staf", "", "Ketua Pengawas Sekolah"),
            ("Individu Dilarang", "Senarai Hitam", "", "Dilarang memasuki kawasan sekolah")
        ]
        cursor.executemany("""
        INSERT INTO face_dataset (person_name, category, image_path, notes)
        VALUES (?, ?, ?, ?);
        """, seed_faces)

    cursor.execute("SELECT COUNT(*) FROM detection_logs;")
    if cursor.fetchone()[0] == 0:
        seed_logs = [
            ("ANPR", "WXY 1234", 0.96, "Dibenarkan", "Cikgu Ahmad (Pengetua) [Pengurusan]", "", json.dumps({"plate": "WXY 1234", "state": "Kuala Lumpur"})),
            ("FACE", "Pn. Salmah", 0.94, "Dikenali", "Ketua Bidang Sukan & Kokurikulum [Staf]", "", json.dumps({"name": "Pn. Salmah"})),
            ("OCR", "SIJIL PENGHARGAAN SUKAN TAHUNAN", 0.98, "Maklumat", "Teks rasmi dokumen sekolah", "", json.dumps({"text": "SIJIL PENGHARGAAN SUKAN TAHUNAN"}))
        ]
        cursor.executemany("""
        INSERT INTO detection_logs (task_type, detected_value, confidence, match_status, matched_info, snapshot_path, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, seed_logs)

    conn.commit()
    conn.close()

# -------------------------------------------------------------
# API Settings CRUD
# -------------------------------------------------------------
def get_active_api_setting() -> Dict[str, Any]:
    """Returns the currently active API configuration with decrypted key."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM api_settings WHERE is_active = 1 LIMIT 1;").fetchone()
    conn.close()
    if row:
        return {
            "id": row["id"],
            "provider": row["provider"],
            "api_key": decrypt_key(row["api_key"] or ""),
            "has_key": bool(row["api_key"]),
            "model_name": row["model_name"],
            "base_url": row["base_url"] or "",
            "is_active": True
        }
    return {
        "id": None,
        "provider": "gemini",
        "api_key": "",
        "has_key": False,
        "model_name": "gemini-2.0-flash",
        "base_url": "",
        "is_active": True
    }

def save_api_setting(provider: str, api_key: str, model_name: str, base_url: str = "") -> None:
    """Saves and sets the active provider configuration with encrypted API key."""
    conn = get_db_connection()
    # Deactivate all
    conn.execute("UPDATE api_settings SET is_active = 0;")
    
    # Check if provider row exists
    row = conn.execute("SELECT id, api_key FROM api_settings WHERE provider = ?;", (provider,)).fetchone()
    enc_key = encrypt_key(api_key) if api_key else (row["api_key"] if row else "")

    if row:
        conn.execute("""
        UPDATE api_settings
        SET api_key = ?, model_name = ?, base_url = ?, is_active = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """, (enc_key, model_name, base_url, row["id"]))
    else:
        conn.execute("""
        INSERT INTO api_settings (provider, api_key, model_name, base_url, is_active)
        VALUES (?, ?, ?, ?, 1);
        """, (provider, enc_key, model_name, base_url))

    conn.commit()
    conn.close()

# -------------------------------------------------------------
# Watchlist CRUD (Vehicles)
# -------------------------------------------------------------
def get_vehicles(query: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if query:
        q = f"%{query}%"
        rows = conn.execute("""
        SELECT * FROM vehicle_watchlist 
        WHERE plate_number LIKE ? OR owner_name LIKE ? 
        ORDER BY id DESC;
        """, (q, q)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM vehicle_watchlist ORDER BY id DESC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_vehicle(plate_number: str, owner_name: str, status: str, category: str = "Staf", notes: str = "") -> int:
    clean_plate = plate_number.upper().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO vehicle_watchlist (plate_number, owner_name, status, category, notes)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(plate_number) DO UPDATE SET
        owner_name = excluded.owner_name,
        status = excluded.status,
        category = excluded.category,
        notes = excluded.notes;
    """, (clean_plate, owner_name.strip(), status, category, notes))
    conn.commit()
    v_id = cursor.lastrowid
    conn.close()
    return v_id

def delete_vehicle(vehicle_id: int) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM vehicle_watchlist WHERE id = ?;", (vehicle_id,))
    conn.commit()
    conn.close()
    return True

def find_vehicle(plate_number: str) -> Optional[Dict[str, Any]]:
    """Finds exact or sanitized match for a vehicle plate."""
    clean = "".join(filter(str.isalnum, plate_number.upper()))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM vehicle_watchlist;").fetchall()
    conn.close()
    for r in rows:
        db_clean = "".join(filter(str.isalnum, r["plate_number"].upper()))
        if db_clean == clean:
            return dict(r)
    return None

# -------------------------------------------------------------
# Face Dataset CRUD
# -------------------------------------------------------------
def get_faces() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM face_dataset ORDER BY id DESC;").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_face(person_name: str, category: str, image_path: str = "", notes: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO face_dataset (person_name, category, image_path, notes)
    VALUES (?, ?, ?, ?);
    """, (person_name.strip(), category, image_path, notes))
    conn.commit()
    f_id = cursor.lastrowid
    conn.close()
    return f_id

def get_face_by_id(face_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM face_dataset WHERE id = ?;", (face_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def delete_face(face_id: int) -> bool:
    conn = get_db_connection()
    conn.execute("DELETE FROM face_dataset WHERE id = ?;", (face_id,))
    conn.commit()
    conn.close()
    return True

def find_face(person_name: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM face_dataset WHERE person_name LIKE ? LIMIT 1;", (f"%{person_name}%",)).fetchone()
    conn.close()
    return dict(row) if row else None

# -------------------------------------------------------------
# Detection Logs CRUD
# -------------------------------------------------------------
def add_detection_log(task_type: str, detected_value: str, confidence: float, match_status: str, 
                       matched_info: str, snapshot_path: str = "", raw_json: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO detection_logs (task_type, detected_value, confidence, match_status, matched_info, snapshot_path, raw_json)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (task_type, detected_value, confidence, match_status, matched_info, snapshot_path, raw_json))
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def get_logs(limit: int = 50, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if task_type:
        rows = conn.execute("""
        SELECT * FROM detection_logs 
        WHERE task_type = ? 
        ORDER BY id DESC LIMIT ?;
        """, (task_type, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM detection_logs ORDER BY id DESC LIMIT ?;", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_logs() -> None:
    conn = get_db_connection()
    conn.execute("DELETE FROM detection_logs;")
    conn.commit()
    conn.close()

# -------------------------------------------------------------
# Sports Sessions CRUD
# -------------------------------------------------------------
def add_sports_session(athlete_name: str, sport_type: str, duration_seconds: float,
                       avg_stride_angle: float, posture_score: int, ai_feedback: str,
                       ai_recommendations: str, snapshot_path: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sports_sessions (athlete_name, sport_type, duration_seconds, avg_stride_angle, posture_score, ai_feedback, ai_recommendations, snapshot_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (athlete_name, sport_type, duration_seconds, avg_stride_angle, posture_score, ai_feedback, ai_recommendations, snapshot_path))
    conn.commit()
    s_id = cursor.lastrowid
    conn.close()
    return s_id

def get_sports_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM sports_sessions ORDER BY id DESC LIMIT ?;", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -------------------------------------------------------------
# Dashboard Summary Stats
# -------------------------------------------------------------
def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    total_logs = conn.execute("SELECT COUNT(*) FROM detection_logs;").fetchone()[0]
    total_vehicles = conn.execute("SELECT COUNT(*) FROM vehicle_watchlist;").fetchone()[0]
    total_faces = conn.execute("SELECT COUNT(*) FROM face_dataset;").fetchone()[0]
    total_sports = conn.execute("SELECT COUNT(*) FROM sports_sessions;").fetchone()[0]
    allowed_count = conn.execute("SELECT COUNT(*) FROM detection_logs WHERE match_status IN ('Dibenarkan', 'Dikenali');").fetchone()[0]
    alert_count = conn.execute("SELECT COUNT(*) FROM detection_logs WHERE match_status IN ('Senarai Hitam', 'Perhatian');").fetchone()[0]
    conn.close()
    return {
        "total_logs": total_logs,
        "total_vehicles": total_vehicles,
        "total_faces": total_faces,
        "total_sports": total_sports,
        "allowed_count": allowed_count,
        "alert_count": alert_count
    }
