"""
License Plate Recognition Task (ANPR) for AI-WebCam.
Extracts vehicle license plate numbers and matches them against the SQLite watchlist.
"""

from typing import Dict, Any, Optional
from core.database import find_vehicle, add_detection_log
from ai_services.base_provider import BaseVisionProvider

ANPR_PROMPT = """
Analisis imej ini untuk nombor pendaftaran kenderaan (plat lesen kereta atau motosikal).
Sila kembalikan HANYA format JSON berikut:
{
  "detected": true,
  "plate_number": "ABC 1234",
  "state_or_country": "Negeri atau negara jika dapat dikesan",
  "vehicle_type": "Sedan/SUV/Motosikal/Lori",
  "vehicle_color": "Warna anggaran kenderaan",
  "confidence": 0.95
}
Jika tiada kenderaan atau plat dikesan:
{
  "detected": false,
  "plate_number": "",
  "confidence": 0.0
}
"""

def process_license_plate(image_bytes: bytes, vision_service: BaseVisionProvider, snapshot_path: str = "") -> Dict[str, Any]:
    response = vision_service.analyze(image_bytes, ANPR_PROMPT)
    if not response.get("success"):
        return {
            "task": "ANPR",
            "success": False,
            "error": response.get("error", "Ralat memproses plat kenderaan"),
            "data": {}
        }

    data = response.get("data", {})
    plate = (data.get("plate_number") or "").strip().upper()
    confidence = float(data.get("confidence", 0.85))

    match_status = "Tidak Dikesan"
    matched_info = ""

    if plate:
        db_match = find_vehicle(plate)
        if db_match:
            match_status = db_match.get("status", "Dibenarkan")
            owner = db_match.get("owner_name", "Tidak Dikenali")
            category = db_match.get("category", "Staf")
            notes = db_match.get("notes", "")
            matched_info = f"{owner} ({category}) - {notes}" if notes else f"{owner} ({category})"
        else:
            match_status = "Tidak Berdaftar"
            matched_info = "Kenderaan tiada dalam senarai pangkalan data (Pelawat / Luar)"

        # Save to database logs
        add_detection_log(
            task_type="ANPR",
            detected_value=plate,
            confidence=confidence,
            match_status=match_status,
            matched_info=matched_info,
            snapshot_path=snapshot_path,
            raw_json=str(data)
        )

    return {
        "task": "ANPR",
        "success": True,
        "is_mock": response.get("is_mock", False),
        "plate_number": plate,
        "match_status": match_status,
        "matched_info": matched_info,
        "vehicle_type": data.get("vehicle_type", "Tidak Dinyatakan"),
        "vehicle_color": data.get("vehicle_color", "Tidak Dinyatakan"),
        "confidence": confidence,
        "details": data
    }
