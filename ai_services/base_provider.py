"""
Base Vision Provider Interface for AI-WebCam.
All vision service implementations (Gemini, OpenAI, Ollama) inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseVisionProvider(ABC):
    def __init__(self, api_key: str = "", model_name: str = "", base_url: str = ""):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    @abstractmethod
    def analyze(self, image_bytes: bytes, prompt: str, reference_images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Sends frame bytes, specialized prompt, and optional reference images
        (for 1-to-few face or object matching) to the AI Vision model.
        Returns a parsed JSON dictionary containing detection results.
        """
        pass
