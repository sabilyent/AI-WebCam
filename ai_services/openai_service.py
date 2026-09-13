"""
OpenAI Vision Service for AI-WebCam.
Supports GPT-4o and GPT-4o-mini vision models.
"""

import re
import json
import base64
from typing import Dict, Any, List, Optional
from openai import OpenAI
from ai_services.base_provider import BaseVisionProvider

def list_openai_models(api_key: str) -> List[Dict[str, Any]]:
    """Fetches all GPT vision-capable models for this OpenAI API key."""
    if not api_key:
        raise ValueError("Kunci API OpenAI diperlukan untuk memuat turun senarai model.")

    client = OpenAI(api_key=api_key)
    res = client.models.list()
    models = []
    for m in res.data:
        m_id = m.id.lower()
        if any(k in m_id for k in ["gpt-4o", "gpt-4-turbo", "gpt-4", "o1", "o3"]):
            models.append({
                "id": m.id,
                "name": m.id,
                "description": "OpenAI Multimodal Model"
            })
    # Sort: gpt-4o models on top
    models.sort(key=lambda x: (not x["id"].startswith("gpt-4o"), x["id"]))
    return models

class OpenAIVisionService(BaseVisionProvider):
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        super().__init__(api_key=api_key, model_name=model_name)
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def analyze(self, image_bytes: bytes, prompt: str, reference_images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not self.api_key or not self.client:
            return {
                "success": False,
                "error": "Kunci API OpenAI belum dimasukkan. Sila isi di halaman Tetapan API.",
                "data": {}
            }

        try:
            b64_img = base64.b64encode(image_bytes).decode("ascii")
            formatted_prompt = (
                f"{prompt}\n\n"
                "PENTING: Berikan jawapan HANYA dalam format JSON tulen tanpa sebarang teks penjelasan di luar JSON."
            )

            content_items = [
                {"type": "text", "text": "--- IMEJ 1: SUAPAN LANGSUNG KAMERA ---"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]

            if reference_images:
                for idx, ref in enumerate(reference_images, start=1):
                    ref_bytes = ref.get("bytes")
                    label = ref.get("label", f"Rujukan {idx}")
                    info = ref.get("info", "")
                    if ref_bytes:
                        ref_b64 = base64.b64encode(ref_bytes).decode("ascii")
                        content_items.append({"type": "text", "text": f"--- FOTO RUJUKAN {idx}: {label} ({info}) ---"})
                        content_items.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ref_b64}"}})

            content_items.append({"type": "text", "text": formatted_prompt})

            response = self.client.chat.completions.create(
                model=self.model_name or "gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": content_items
                    }
                ],
                max_tokens=600,
                response_format={"type": "json_object"}
            )

            raw_text = response.choices[0].message.content.strip()
            parsed = json.loads(raw_text)
            return {
                "success": True,
                "provider": "openai",
                "model": self.model_name,
                "data": parsed,
                "raw": raw_text
            }
        except Exception as e:
            return {
                "success": False,
                "provider": "openai",
                "error": str(e),
                "data": {}
            }
