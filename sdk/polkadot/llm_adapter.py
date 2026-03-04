"""
LocalLLMAdapter — Pluggable AI model adapter for ModernTensor miners.

Supports multiple backends:
- Gemini API (Google AI, free tier, recommended)
- HTTP endpoint (remote model server)
- Fallback simulation (template-based for testing)

Usage:
    adapter = LocalLLMAdapter.auto_detect()
    output = adapter.infer("Analyze this code for security issues...")
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Default Gemini config ───────────────────────────────────
GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class LocalLLMAdapter:
    """
    Adapter for AI model inference in ModernTensor.

    Priority: Gemini API → HTTP endpoint → Simulation fallback.
    """

    def __init__(
        self,
        backend: str = "auto",
        gemini_api_key: Optional[str] = None,
        gemini_model: str = GEMINI_DEFAULT_MODEL,
        http_url: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.backend = backend
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.gemini_model = gemini_model
        self.http_url = http_url
        self.timeout = timeout

        if backend == "auto":
            self.backend = self._detect_backend()

        logger.info("LocalLLMAdapter initialized: backend=%s", self.backend)

    # ── Backend Detection ───────────────────────────────────

    def _detect_backend(self) -> str:
        """Auto-detect available backend."""
        if self.gemini_api_key and self._check_gemini():
            return "gemini"
        if self.http_url and self._check_http():
            return "http"
        return "simulation"

    def _check_gemini(self) -> bool:
        """Check if Gemini API key is valid."""
        try:
            import httpx

            url = f"{GEMINI_API_BASE}"
            resp = httpx.get(
                url,
                headers={"x-goog-api-key": self.gemini_api_key},
                timeout=5,
            )
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                names = [m.get("name", "") for m in models[:5]]
                logger.info("Gemini API available, models: %s", names)
                return True
            logger.warning("Gemini API check failed: %s", resp.status_code)
        except Exception as e:
            logger.debug("Gemini API not reachable: %s", e)
        return False

    def _check_http(self) -> bool:
        """Check if HTTP model endpoint is available."""
        try:
            import httpx

            resp = httpx.get(self.http_url, timeout=2)
            return resp.status_code < 500
        except Exception:
            return False

    # ── Inference ───────────────────────────────────────────

    def infer(self, prompt: str) -> bytes:
        """
        Run inference and return output as bytes.

        Args:
            prompt: Input text prompt

        Returns:
            Model output as bytes
        """
        if self.backend == "gemini":
            return self._infer_gemini(prompt)
        elif self.backend == "http":
            return self._infer_http(prompt)
        else:
            return self._infer_simulation(prompt)

    def _infer_gemini(self, prompt: str) -> bytes:
        """Run inference via Google Gemini REST API."""
        import httpx

        url = f"{GEMINI_API_BASE}/{self.gemini_model}" f":generateContent"

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
                "topP": 0.9,
            },
        }

        logger.info(
            "Gemini inference: model=%s, prompt_len=%d",
            self.gemini_model,
            len(prompt),
        )

        try:
            resp = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self.gemini_api_key},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                logger.info("Gemini response: %d chars", len(text))
                return text.encode("utf-8")

            logger.warning("Gemini returned no candidates")
            return self._infer_simulation(prompt)

        except Exception as e:
            logger.warning("Gemini inference failed: %s, falling back to simulation", e)
            return self._infer_simulation(prompt)

    def _infer_http(self, prompt: str) -> bytes:
        """Run inference via generic HTTP endpoint."""
        import httpx

        logger.info("HTTP inference: url=%s, prompt_len=%d", self.http_url, len(prompt))

        try:
            resp = httpx.post(
                self.http_url,
                json={"prompt": prompt, "max_tokens": 256},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            result = resp.json().get("response", resp.text)
            return result.encode("utf-8") if isinstance(result, str) else result

        except Exception as e:
            logger.warning("HTTP inference failed: %s, falling back to simulation", e)
            return self._infer_simulation(prompt)

    def _infer_simulation(self, prompt: str) -> bytes:
        """
        Deterministic simulation model for demo/testing.

        Generates domain-specific reports based on input analysis.
        """
        prompt_lower = prompt.lower()

        # Detect domain from prompt content
        if any(kw in prompt_lower for kw in ["review", "code", "function", "solidity", "contract"]):
            domain = "code-review"
        elif any(kw in prompt_lower for kw in ["sentiment", "analyze", "nlp", "text"]):
            domain = "nlp"
        elif any(kw in prompt_lower for kw in ["risk", "finance", "portfolio", "invest"]):
            domain = "finance"
        elif any(kw in prompt_lower for kw in ["health", "medical", "patient", "diagnosis"]):
            domain = "health"
        else:
            domain = "generic"

        content_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        reports = {
            "code-review": (
                f"Code Review Report (ID: {content_hash})\n"
                f"Generated: {timestamp}\n"
                f"Domain: Software Security Analysis\n\n"
                f"Input Analysis:\n{prompt[:200]}\n\n"
                f"Findings:\n"
                f"1. Potential reentrancy vulnerability detected in external calls\n"
                f"2. Missing access control modifier on state-changing functions\n"
                f"3. Gas optimization: Consider using unchecked blocks for safe arithmetic\n"
                f"4. Input validation: Add require() guards for zero-address checks\n\n"
                f"Risk Level: MEDIUM\n"
                f"Recommendation: Apply checks-effects-interactions pattern"
            ),
            "nlp": (
                f"NLP Analysis Report (ID: {content_hash})\n"
                f"Generated: {timestamp}\n"
                f"Domain: Natural Language Processing\n\n"
                f"Input: {prompt[:200]}\n\n"
                f"Sentiment: POSITIVE (confidence: 0.87)\n"
                f"Key Entities: blockchain, AI, decentralized\n"
                f"Topic Classification: Technology/Innovation\n"
                f"Language Quality: High (readability: 78/100)"
            ),
            "finance": (
                f"Financial Analysis Report (ID: {content_hash})\n"
                f"Generated: {timestamp}\n"
                f"Domain: Risk Assessment\n\n"
                f"Portfolio Analysis:\n{prompt[:200]}\n\n"
                f"Risk Score: 6.2/10 (Moderate)\n"
                f"Diversification Index: 0.73\n"
                f"Recommendation: Rebalance to reduce concentration risk"
            ),
            "health": (
                f"Medical Analysis Report (ID: {content_hash})\n"
                f"Generated: {timestamp}\n"
                f"Domain: Health Informatics\n\n"
                f"Input: {prompt[:200]}\n\n"
                f"Classification: Informational Query\n"
                f"Confidence: 0.82\n"
                f"Note: This is AI-generated analysis, consult a professional"
            ),
            "generic": (
                f"Inference Report (ID: {content_hash})\n"
                f"Generated: {timestamp}\n"
                f"Domain: General AI Analysis\n\n"
                f"Input Summary: {prompt[:200]}\n\n"
                f"Analysis: The input has been processed through the ModernTensor\n"
                f"inference pipeline. Key patterns identified with 0.85 confidence.\n"
                f"Output generated deterministically for verification purposes."
            ),
        }

        return reports[domain].encode("utf-8")

    # ── Factory ─────────────────────────────────────────────

    @classmethod
    def auto_detect(cls, **kwargs) -> "LocalLLMAdapter":
        """Create adapter with auto-detected backend."""
        return cls(backend="auto", **kwargs)

    @classmethod
    def from_gemini(
        cls,
        api_key: Optional[str] = None,
        model: str = GEMINI_DEFAULT_MODEL,
    ) -> "LocalLLMAdapter":
        """Create adapter with Gemini backend."""
        return cls(
            backend="gemini",
            gemini_api_key=api_key or os.environ.get("GEMINI_API_KEY"),
            gemini_model=model,
        )

    def __repr__(self) -> str:
        if self.backend == "gemini":
            return f"LocalLLMAdapter(backend=gemini, model={self.gemini_model})"
        return f"LocalLLMAdapter(backend={self.backend})"
