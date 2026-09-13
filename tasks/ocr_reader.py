"""
Optical Character Recognition (OCR) Task for AI-WebCam.
Extracts printed or handwritten text from the camera frame (documents, books, receipts, signs).
"""

from typing import Dict, Any
from core.database import add_detection_log
from ai_services.base_provider import BaseVisionProvider

OCR_PROMPT = """
Baca dan ekstrak semua teks yang kelihatan dalam imej ini (papan tanda, buku, dokumen, sijil, skrin atau resit).
Sila kembalikan HANYA format JSON berikut:
{
  "detected_text": "Teks penuh yang dibaca",
  "key_lines": ["Baris 1", "Baris 2", "Baris 3"],
  "document_type": "Dokumen/Papan Tanda/Buku/Resit/Lain-lain",
  "language": "Bahasa Melayu/English/Lain-lain",
  "confidence": 0.95
}
Jika tiada sebarang teks yang dapat dibaca:
{
  "detected_text": "",
  "key_lines": [],
  "document_type": "Tiada teks",
  "language": "N/A",
  "confidence": 0.0
}
"""

def process_ocr_reader(image_bytes: bytes, vision_service: BaseVisionProvider, snapshot_path: str = "") -> Dict[str, Any]:
    response = vision_service.analyze(image_bytes, OCR_PROMPT)
    if not response.get("success"):
        return {
            "task": "OCR",
            "success": False,
            "error": response.get("error", "Ralat memproses OCR"),
            "data": {}
        }

    data = response.get("data", {})
    text = (data.get("detected_text") or "").strip()
    confidence = float(data.get("confidence", 0.90))

    if text:
        add_detection_log(
            task_type="OCR",
            detected_value=text[:80] + ("..." if len(text) > 80 else ""),
            confidence=confidence,
            match_status="Maklumat",
            matched_info=f"Jenis: {data.get('document_type', 'Dokumen')} ({data.get('language', 'N/A')})",
            snapshot_path=snapshot_path,
            raw_json=str(data)
        )

    return {
        "task": "OCR",
        "success": True,
        "is_mock": response.get("is_mock", False),
        "detected_text": text,
        "key_lines": data.get("key_lines", []),
        "document_type": data.get("document_type", "Dokumen"),
        "language": data.get("language", "N/A"),
        "confidence": confidence,
        "details": data
    }
