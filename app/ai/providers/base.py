from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx


class ProviderError(Exception):
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(message)


class MultimodalError(Exception):
    """User-safe multimodal failure. `code` drives HTTP mapping."""

    def __init__(self, message: str, code: str = "provider"):
        self.code = code
        super().__init__(message)


class SpeechToTextError(MultimodalError):
    pass


class TextToSpeechError(MultimodalError):
    pass


class VisionError(MultimodalError):
    pass


class HttpProviderClient:
    def __init__(self, timeout: float, headers: Optional[Dict[str, str]] = None):
        self.timeout = timeout
        self.headers = headers or {}

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise ProviderError("http", f"Request timed out: {url}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("http", f"HTTP request failed: {exc}") from exc

    def post(self, url: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=json, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise ProviderError("http", f"Request timed out: {url}") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("http", f"HTTP request failed: {exc}") from exc


class WeatherProvider(ABC):
    @abstractmethod
    def get_forecast(self, location: str, days: int) -> Dict[str, Any]:
        raise NotImplementedError


class MapsProvider(ABC):
    @abstractmethod
    def search_places(self, query: str, location: Optional[str], limit: int) -> Dict[str, Any]:
        raise NotImplementedError


class PricingProvider(ABC):
    @abstractmethod
    def estimate(self, destination: str, days: int, budget: Optional[float], trip_style: Optional[str], travelers: int) -> Dict[str, Any]:
        raise NotImplementedError


class SpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, audio: bytes, filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError


class VisionProvider(ABC):
    @abstractmethod
    def analyze(self, image: bytes, prompt: str, content_type: Optional[str] = None, filename: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError
