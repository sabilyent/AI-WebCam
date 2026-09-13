"""
Ollama Local Vision Service for AI-WebCam.
Connects to local Ollama server (e.g., http://localhost:11434) for offline, privacy-first inference.
Recommended local models: moondream, llava:7b, llava-phi3.
"""

import re
import json
import base64
import requests
from typing import Dict, Any, List, Optional
from ai_services.base_provider import BaseVisionProvider

def list_ollama_models(base_url: str = "http://localhost:11434") -> List[Dict[str, Any]]:
    """Fetches list of locally installed models on the Ollama server."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            raise ValueError(f"Pelayan Ollama mengembalikan status {res.status_code}")
        data = res.json()
        models = []
        for m in data.get("models", []):
            name = m.get("name", "")
            size_gb = round(m.get("size", 0) / (1024**3), 1)
            models.append({
                "id": name,
                "name": f"{name} ({size_gb} GB)",
                "description": f"Model tempatan, saiz: {size_gb} GB"
            })
        return models
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Gagal menyambung ke Ollama di {base_url}. Pastikan 'ollama serve' aktif.")

class OllamaVisionService(BaseVisionProvider):
    def __init__(self, model_name: str = "moondream", base_url: str = "http://localhost:11434"):
        super().__init__(api_key="", model_name=model_name, base_url=base_url or "http://localhost:11434")

    def analyze(self, image_bytes: bytes, prompt: str, reference_images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/api/generate"
        b64_img = base64.b64encode(image_bytes).decode("ascii")

        formatted_prompt = (
            f"{prompt}\n\n"
            "Return valid JSON ONLY. No markdown formatting, no commentary."
        )

        all_images = [b64_img]
        if reference_images:
            for ref in reference_images:
                if ref.get("bytes"):
                    all_images.append(base64.b64encode(ref["bytes"]).decode("ascii"))

        payload = {
            "model": self.model_name or "moondream",
            "prompt": formatted_prompt,
            "images": all_images,
            "stream": False,
            "format": "json"
        }

        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code != 200:
                return {
                    "success": False,
                    "provider": "ollama",
                    "error": f"Pelayan Ollama ralat status {res.status_code}: {res.text}",
                    "data": {}
                }

            res_json = res.json()
            raw_response = res_json.get("response", "").strip()

            clean_json = raw_response
            if "```" in clean_json:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_json)
                if match:
                    clean_json = match.group(1)

            parsed = json.loads(clean_json)
            return {
                "success": True,
                "provider": "ollama",
                "model": self.model_name,
                "data": parsed,
                "raw": raw_response
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "provider": "ollama",
                "error": f"Tidak dapat menyambung ke Ollama di {self.base_url}. Pastikan 'ollama serve' sedang berjalan.",
                "data": {}
            }
        except json.JSONDecodeError:
            return {
                "success": True,
                "provider": "ollama",
                "model": self.model_name,
                "data": {"text": raw_response},
                "raw": raw_response
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "ollama",
                "error": str(e),
                "data": {}
            }
