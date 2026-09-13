"""
Google Gemini Vision Service for AI-WebCam.
Uses the modern google-genai SDK with graceful fallback.
Supports Gemini 3.6 Flash, 2.5 Flash, 1.5 Flash, and dynamic model listing.
"""

import re
import json
import warnings
from typing import Dict, Any, List, Optional

warnings.filterwarnings("ignore", category=FutureWarning)

def list_gemini_models(api_key: str) -> List[Dict[str, Any]]:
    """Fetches all accessible generative models for this Gemini API key."""
    if not api_key:
        raise ValueError("Kunci API Gemini diperlukan untuk memuat turun senarai model.")

    models = []
    last_error = None

    # Try modern google.genai first
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m in client.models.list():
            model_id = m.name.replace("models/", "") if m.name else ""
            display = getattr(m, "display_name", "") or model_id
            desc = getattr(m, "description", "") or ""
            # Filter to relevant multimodal/gemini models
            if any(k in model_id.lower() for k in ["gemini", "flash", "pro"]):
                models.append({
                    "id": model_id,
                    "name": f"{display} ({model_id})" if display != model_id else model_id,
                    "description": desc[:120]
                })
        if models:
            # Sort: put 3.6-flash and flash models on top
            models.sort(key=lambda x: (not ("3.6" in x["id"] or "flash" in x["id"]), x["id"]))
            return models
    except Exception as e:
        last_error = e

    # Fallback to google.generativeai
    try:
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key)
        for m in legacy_genai.list_models():
            methods = getattr(m, "supported_generation_methods", [])
            if "generateContent" in methods:
                model_id = m.name.replace("models/", "")
                display = getattr(m, "display_name", "") or model_id
                models.append({
                    "id": model_id,
                    "name": f"{display} ({model_id})" if display != model_id else model_id,
                    "description": (getattr(m, "description", "") or "")[:120]
                })
        if models:
            models.sort(key=lambda x: (not ("3.6" in x["id"] or "flash" in x["id"]), x["id"]))
            return models
    except Exception as e:
        last_error = e

    if last_error:
        raise last_error

    return models

class GeminiVisionService:
    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.api_key = api_key
        # Clean potential models/ prefix
        clean_name = (model_name or "gemini-3.6-flash").strip()
        if clean_name.startswith("models/"):
            clean_name = clean_name.replace("models/", "")
        self.model_name = clean_name
        self.client = None

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                self.use_modern = True
            except Exception:
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self.legacy_model = legacy_genai.GenerativeModel(self.model_name)
                    self.use_modern = False
                except Exception as e:
                    self.client = None
                    self.error_init = str(e)

    def analyze(self, image_bytes: bytes, prompt: str, reference_images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.api_key:
            return {
                "success": False,
                "error": "Kunci API Google Gemini belum dimasukkan. Sila isi di halaman Tetapan API.",
                "data": {}
            }

        formatted_prompt = (
            f"{prompt}\n\n"
            "PENTING: Berikan jawapan HANYA dalam format JSON tulen tanpa sebarang blok Markdown atau penerangan luar."
        )

        try:
            if getattr(self, "use_modern", True) and self.client:
                from google.genai import types
                contents = []
                # 1. Primary Live Image
                contents.append("--- IMEJ 1: SUAPAN LANGSUNG KAMERA (LIVE WEBCAM STREAM) ---")
                contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))

                # 2. Reference Images if provided
                if reference_images:
                    for idx, ref in enumerate(reference_images, start=1):
                        ref_bytes = ref.get("bytes")
                        label = ref.get("label", f"Rujukan {idx}")
                        info = ref.get("info", "")
                        if ref_bytes:
                            contents.append(f"--- FOTO RUJUKAN {idx}: {label} ({info}) ---")
                            contents.append(types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg"))

                # 3. Prompt
                contents.append(formatted_prompt)

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )
                raw_text = response.text.strip()
            else:
                import io
                from PIL import Image
                contents = []
                contents.append(formatted_prompt)
                contents.append(Image.open(io.BytesIO(image_bytes)))
                if reference_images:
                    for ref in reference_images:
                        if ref.get("bytes"):
                            contents.append(Image.open(io.BytesIO(ref["bytes"])))
                resp = self.legacy_model.generate_content(contents)
                raw_text = resp.text.strip()

            clean_json = raw_text
            if "```" in clean_json:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json)
                if match:
                    clean_json = match.group(1).strip()

            parsed = json.loads(clean_json)
            return {
                "success": True,
                "provider": "gemini",
                "model": self.model_name,
                "data": parsed,
                "raw": raw_text
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "provider": "gemini",
                "model": self.model_name,
                "data": {"text": raw_text},
                "raw": raw_text
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "gemini",
                "error": str(e),
                "data": {}
            }
