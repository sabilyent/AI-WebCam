"""
Face Recognition Task for AI-WebCam.
Performs multimodal face verification by comparing live camera frames against
stored reference face photos and candidate profiles in the SQLite database.
"""

from typing import Dict, Any, List
from pathlib import Path
from core.config import REFERENCE_FACES_DIR
from core.database import get_faces, find_face, add_detection_log
from ai_services.base_provider import BaseVisionProvider

def process_face_recognition(image_bytes: bytes, vision_service: BaseVisionProvider, snapshot_path: str = "") -> Dict[str, Any]:
    # 1. Retrieve all registered faces from SQLite
    registered_faces = get_faces()

    # 2. Gather physical reference photos for multimodal visual matching
    ref_images: List[Dict[str, Any]] = []
    for face in registered_faces:
        img_filename = face.get("image_path")
        if img_filename:
            full_img_path = REFERENCE_FACES_DIR / img_filename
            if full_img_path.exists():
                try:
                    with open(full_img_path, "rb") as f:
                        ref_images.append({
                            "label": face["person_name"],
                            "info": f"{face.get('category', 'Staf')} ({face.get('notes', '')})".strip(" ()"),
                            "bytes": f.read()
                        })
                except Exception as e:
                    print(f"[Face] Gagal membaca foto rujukan {full_img_path}: {e}")

    # 3. Construct dynamic prompt with known candidate names
    candidates_list = [f"'{f['person_name']}' [{f.get('category', 'Staf')}]" for f in registered_faces]
    candidates_str = ", ".join(candidates_list) if candidates_list else "Tiada calon berdaftar lagi"

    prompt = f"""
Anda adalah sistem Pengecaman Wajah (Face Recognition & Biometric Verification) pintar.
Imej 1 adalah tangkapan langsung dari kamera (Live WebCam).
Foto-foto rujukan berikutnya (jika disertakan) adalah foto profil wajah individu yang berdaftar dalam pangkalan data organisasi:
Senarai individu berdaftar: [{candidates_str}]

TUGASAN ANDA:
1. Kenal pasti sama ada terdapat wajah manusia dalam Imej 1.
2. Sekiranya ada wajah, bandingkan ciri-ciri anatomi muka (mata, hidung, bibir, struktur rahang, dahi, garis rambut) dengan Foto Rujukan yang disertakan.
3. Sekiranya wajah dalam Imej 1 sepadan dengan mana-mana Foto Rujukan individu berdaftar:
   - Tetapkan "is_matched": true
   - Tetapkan "person_name" kepada NAMA TEPAT individu tersebut seperti dalam senarai.
   - Tetapkan "confidence" tahap keyakinan (cth: 0.90 - 0.99).
   - Terangkan padanan ringkas dalam "match_rationale".
4. Sekiranya wajah TIDAK sepadan dengan mana-mana Foto Rujukan berdaftar:
   - Tetapkan "is_matched": false
   - Tetapkan "person_name": "Tidak Dikenali"
   - Tetapkan "match_rationale": "Wajah individu tidak sepadan dengan mana-mana rekod rujukan."

Sila kembalikan HANYA format JSON berikut:
{{
  "detected": true,
  "is_matched": true,
  "person_name": "Nama Tepat Individu Berdaftar atau 'Tidak Dikenali'",
  "confidence": 0.95,
  "match_rationale": "Ciri wajah seperti hidung, bibir dan bentuk muka sepadan dengan foto rujukan",
  "expression": "Tersenyum/Neutral/Fokus",
  "estimated_age": "Kanak-kanak/Remaja/Dewasa/Warga Emas"
}}
Jika tiada wajah manusia kelihatan langsung dalam Imej 1:
{{
  "detected": false,
  "is_matched": false,
  "person_name": "",
  "confidence": 0.0
}}
"""

    # 4. Analyze via multimodal Vision AI (passing live frame + all reference face photos)
    response = vision_service.analyze(image_bytes, prompt, reference_images=ref_images)
    if not response.get("success"):
        return {
            "task": "FACE",
            "success": False,
            "error": response.get("error", "Ralat memproses pengecaman wajah"),
            "data": {}
        }

    data = response.get("data", {})
    detected = data.get("detected", True)
    is_matched = bool(data.get("is_matched", False))
    raw_name = (data.get("person_name") or "Tidak Dikenali").strip()
    confidence = float(data.get("confidence", 0.85))
    rationale = data.get("match_rationale", "")

    match_status = "Tidak Dikenali"
    matched_info = "Wajah tidak terdapat dalam pangkalan data (Pelawat Baharu)"
    final_name = raw_name

    if detected and raw_name and raw_name.lower() not in ["tidak dikenali", "individu", "unknown", "none", ""]:
        db_match = find_face(raw_name)
        if db_match:
            final_name = db_match["person_name"]
            category = db_match.get("category", "Staf")
            notes = db_match.get("notes", "")
            match_status = "Dikenali" if category != "Senarai Hitam" else "Senarai Hitam"
            matched_info = f"{final_name} [{category}] - {notes}" if notes else f"{final_name} [{category}]"
            if rationale:
                matched_info += f" ({rationale})"
        else:
            if is_matched:
                match_status = "Dikenali"
                matched_info = f"Padanan wajah rujukan: {raw_name}"
            else:
                match_status = "Pelawat"
                matched_info = f"Pengesanan wajah umum: {raw_name}"
    elif detected and not is_matched:
        match_status = "Pelawat"
        matched_info = "Wajah individu tidak sepadan dengan mana-mana rujukan (Pelawat / Belum Berdaftar)"

    # Log into SQLite
    add_detection_log(
        task_type="FACE",
        detected_value=final_name if final_name != "Tidak Dikenali" else "Individu Tidak Dikenali",
        confidence=confidence,
        match_status=match_status,
        matched_info=matched_info,
        snapshot_path=snapshot_path,
        raw_json=str(data)
    )

    return {
        "task": "FACE",
        "success": True,
        "is_mock": response.get("is_mock", False),
        "detected": detected,
        "is_matched": is_matched,
        "person_name": final_name,
        "match_status": match_status,
        "matched_info": matched_info,
        "match_rationale": rationale,
        "expression": data.get("expression", "Neutral"),
        "estimated_age": data.get("estimated_age", "Dewasa"),
        "confidence": confidence,
        "reference_count": len(ref_images),
        "details": data
    }
