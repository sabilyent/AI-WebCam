"""
AI Provider Factory for AI-WebCam.
Instantiates active vision service based on SQLite settings.
Provides MockVisionService fallback for instant zero-config testing.
"""

from typing import Dict, Any
from core.database import get_active_api_setting
from ai_services.base_provider import BaseVisionProvider
from ai_services.gemini_service import GeminiVisionService
from ai_services.openai_service import OpenAIVisionService
from ai_services.ollama_service import OllamaVisionService

class MockVisionService(BaseVisionProvider):
    """Fallback mock engine for instant offline testing before user enters an API key."""
    def __init__(self, reason: str = "Tiada kunci API aktif"):
        super().__init__()
        self.reason = reason

    def analyze(self, image_bytes: bytes, prompt: str, reference_images=None) -> Dict[str, Any]:
        # Intelligent fallback response matching the prompt context
        lower_p = prompt.lower()
        if "plat" in lower_p or "plate" in lower_p or "anpr" in lower_p:
            data = {
                "plate_number": "WXY 1234",
                "state": "Kuala Lumpur",
                "confidence": 0.95,
                "vehicle_type": "Sedan Hitam",
                "is_mock": True
            }
        elif "wajah" in lower_p or "face" in lower_p:
            matched_name = reference_images[0]["label"] if reference_images else "Cikgu Ahmad"
            data = {
                "detected": True,
                "is_matched": True,
                "person_name": matched_name,
                "confidence": 0.94,
                "expression": "Tersenyum",
                "is_mock": True
            }
        elif "ocr" in lower_p or "teks" in lower_p or "huruf" in lower_p:
            data = {
                "detected_text": "BORANG KEBENARAN PROGRAM KOKURIKULUM SMK MAHKOTA",
                "language": "ms",
                "confidence": 0.94,
                "is_mock": True
            }
        elif "senario" in lower_p or "scene" in lower_p:
            data = {
                "scene_description": "Kamera menghadap ruang dalaman bilik dengan pencahayaan yang mencukupi.",
                "person_count": 1,
                "objects_detected": ["kerusi", "meja", "komputer riba"],
                "security_alert": False,
                "is_mock": True
            }
        elif "sukan" in lower_p or "sports" in lower_p or "pose" in lower_p:
            data = {
                "athlete_posture": "Larian fasa pecutan awal (acceleration phase)",
                "knee_angle": 135,
                "torso_angle": 18,
                "posture_score": 88,
                "speed_analysis": "Laju sederhana; fasa tolakan kaki belakang kuat.",
                "weakness": "Hayunan lengan kiri sedikit ke dalam menyebabkan sedikit kehilangan momentum hadapan.",
                "recommendation": "Fokuskan hayunan tangan lurus ke hadapan selari dengan garisan bahu dan tegakkan sedikit torso selepas langkah ke-10.",
                "is_mock": True
            }
        else:
            data = {
                "summary": "Pengesanan visual berjaya dijalankan (Mod Simulasi).",
                "confidence": 0.90,
                "is_mock": True
            }

        return {
            "success": True,
            "provider": "mock",
            "model": "simulated-engine",
            "is_mock": True,
            "message": "Hasil simulasi (Sila masukkan kunci API anda di tab Tetapan untuk kecerdasan AI sebenar).",
            "data": data,
            "raw": ""
        }

def get_vision_service() -> BaseVisionProvider:
    """Factory function returning the configured vision provider."""
    setting = get_active_api_setting()
    provider = setting.get("provider", "gemini")
    api_key = setting.get("api_key", "").strip()
    model_name = setting.get("model_name", "").strip()
    base_url = setting.get("base_url", "").strip()

    if provider == "gemini":
        if not api_key:
            return MockVisionService(reason="Kunci API Gemini belum dimasukkan")
        return GeminiVisionService(api_key=api_key, model_name=model_name or "gemini-2.0-flash")

    elif provider == "openai":
        if not api_key:
            return MockVisionService(reason="Kunci API OpenAI belum dimasukkan")
        return OpenAIVisionService(api_key=api_key, model_name=model_name or "gpt-4o-mini")

    elif provider == "ollama":
        return OllamaVisionService(model_name=model_name or "moondream", base_url=base_url or "http://localhost:11434")

    return MockVisionService()
