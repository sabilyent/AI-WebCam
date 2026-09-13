"""
General Scene Analyzer Task for AI-WebCam.
Provides situational understanding: human count, activities, objects, and safety alerts.
"""

from typing import Dict, Any
from core.database import add_detection_log
from ai_services.base_provider import BaseVisionProvider

SCENE_PROMPT = """
Analisis suasana keseluruhan dalam imej ini.
Kenal pasti suasana, bilangan orang, aktiviti utama yang sedang berlaku, objek-objek penting, dan sama ada terdapat sebarang perkara mencurigakan atau bahaya keselamatan.
Sila kembalikan HANYA format JSON berikut:
{
  "scene_summary": "Ringkasan ringkas apa yang sedang berlaku (1-2 ayat)",
  "person_count": 1,
  "activities": ["Berjalan", "Duduk", "Bekerja di hadapan laptop"],
  "objects_detected": ["Meja", "Kerusi", "Komputer"],
  "environment": "Dalam bangunan (Pejabat / Bilik Darjah / Makmal / Koridor)",
  "security_alert": false,
  "security_notes": "Keadaan selamat dan terkawal",
  "confidence": 0.94
}
"""

def process_scene_analysis(image_bytes: bytes, vision_service: BaseVisionProvider, snapshot_path: str = "") -> Dict[str, Any]:
    response = vision_service.analyze(image_bytes, SCENE_PROMPT)
    if not response.get("success"):
        return {
            "task": "SCENE",
            "success": False,
            "error": response.get("error", "Ralat menganalisis senario"),
            "data": {}
        }

    data = response.get("data", {})
    summary = data.get("scene_summary", "Pemerhatian bilik dijalankan.")
    is_alert = bool(data.get("security_alert", False))
    confidence = float(data.get("confidence", 0.90))

    match_status = "Perhatian" if is_alert else "Selamat"
    matched_info = data.get("security_notes", "Keadaan normal")

    add_detection_log(
        task_type="SCENE",
        detected_value=summary[:80] + ("..." if len(summary) > 80 else ""),
        confidence=confidence,
        match_status=match_status,
        matched_info=f"{matched_info} | Orang: {data.get('person_count', 0)}",
        snapshot_path=snapshot_path,
        raw_json=str(data)
    )

    return {
        "task": "SCENE",
        "success": True,
        "is_mock": response.get("is_mock", False),
        "scene_summary": summary,
        "person_count": data.get("person_count", 0),
        "activities": data.get("activities", []),
        "objects_detected": data.get("objects_detected", []),
        "environment": data.get("environment", "Bilik"),
        "security_alert": is_alert,
        "security_notes": matched_info,
        "confidence": confidence,
        "details": data
    }
