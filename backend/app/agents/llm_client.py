import io
import json
import os
import time
from typing import Any, Dict, List, Optional, Union
import httpx

# Safe import for gTTS to prevent ModuleNotFoundError from crashing the application
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    gTTS = None
    GTTS_AVAILABLE = False

from loguru import logger

# Active Gemini Models
# NOTE: gemini-1.5-flash was fully retired by Google (confirmed 404 NOT_FOUND on every
# request) and has been removed from the fallback chain. gemini-3.1-flash-lite is a
# separate model family from the 2.5 series, so it draws from its own daily free-tier
# quota bucket instead of competing with gemini-2.5-flash-lite / gemini-2.5-flash.
DEFAULT_TEXT_MODEL = "gemini-3.5-flash-lite"
TEXT_MODELS_FALLBACK = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite",
]
DEFAULT_EMBED_MODEL = "gemini-embedding-2"
# Keep one embedding model for stored and query vectors. Do not mix embedding spaces.
EMBEDDING_OUTPUT_DIMENSIONALITY = 768


class LLMClient:

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        max_retries: int = 2,
        retry_delay: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Construction is safe in offline/test mode; real credentials enable live Gemini.
        self.client = None
        if self.api_key:
            import google.genai as genai
            from google.genai import types
            transport = httpx.HTTPTransport(local_address="0.0.0.0", retries=2)
            custom_httpx_client = httpx.Client(transport=transport, timeout=10.0)
            client_options = types.HttpOptions(httpx_client=custom_httpx_client)
            self.client = genai.Client(api_key=self.api_key, http_options=client_options)

        self.default_model = default_model or os.getenv("GEMINI_TEXT_MODEL") or DEFAULT_TEXT_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Cache models that hit rate limits (429) to skip them temporarily (60s TTL)
        self._disabled_models: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Helper Utilities
    # ------------------------------------------------------------------

    def _extract_response_text(self, response: Any, default_fallback: str = "") -> str:
        """Safely extract text from a Gemini response while guarding against safety filters."""
        if not response:
            return default_fallback

        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason and str(finish_reason).upper() in ["SAFETY", "RECITATION", "BLOCKLIST"]:
                    logger.warning(f"Response candidate blocked by safety reason: {finish_reason}")
                    return default_fallback

            text = getattr(response, "text", None)
            if text:
                return text.strip()
        except (AttributeError, ValueError) as exc:
            logger.warning(f"Failed to extract response text directly: {exc}")

        return default_fallback

    def _clean_expired_disabled_models(self) -> None:
        """Clear model cache entries older than 60 seconds."""
        now = time.time()
        expired = [m for m, t in self._disabled_models.items() if now - t > 60]
        for m in expired:
            del self._disabled_models[m]

    def _execute_with_retry(
        self,
        func,
        model_list: List[str],
        op_name: str = "Operation",
    ) -> Any:
        """Execute operation across model fallbacks with retry logic."""
        self._clean_expired_disabled_models()
        last_error: Optional[Exception] = None

        active_models = [m for m in model_list if m not in self._disabled_models]
        if not active_models:
            active_models = model_list

        for model in active_models:
            for attempt in range(1, self.max_retries + 1):
                try:
                    return func(model)
                except APIError as exc:
                    last_error = exc
                    status_code = getattr(exc, "code", None)

                    if status_code in (400, 404):
                        logger.warning(f"[{op_name}] Model {model} returned status {status_code}: {exc}. Skipping.")
                        break

                    if status_code == 429:
                        logger.warning(f"[{op_name}] Quota exceeded (429) for model {model}. Skipping temporarily.")
                        self._disabled_models[model] = time.time()
                        break

                    logger.warning(
                        f"[{op_name}] Attempt {attempt}/{self.max_retries} failed on model {model} "
                        f"(Status: {status_code}): {exc}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                except Exception as exc:
                    last_error = exc
                    logger.error(f"[{op_name}] Non-API error on model {model}: {exc}")
                    break

            logger.warning(f"[{op_name}] Switching fallback model from '{model}'...")

        if last_error:
            raise RuntimeError(f"All configured models failed for [{op_name}]. Last error: {last_error}")
        raise RuntimeError(f"All configured models failed for [{op_name}].")

    # ------------------------------------------------------------------
    # Core Operations
    # ------------------------------------------------------------------

    def generate_content(
        self,
        prompt: Any = None,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        safety_settings: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Any]] = None,
        *,
        contents: Any = None,
        config: Optional[Any] = None,
    ) -> Any:
        """
        Generate content through the configured Gemini client.

        Supports both this wrapper's original API:
            generate_content(prompt=...)

        And the Google GenAI-style calling convention used by the
        orchestrator and integrations:
            generate_content(contents=..., config=...)
        """
        if contents is not None:
            if prompt is not None:
                raise TypeError("Pass either 'prompt' or 'contents', not both.")
            prompt = contents

        if prompt is None:
            raise ValueError("A prompt or contents value is required.")

        if self.client is None:
            raise RuntimeError(
                "Gemini is not configured. Set GEMINI_API_KEY "
                "to enable live AI generation."
            )

        from google.genai import types
        from google.genai.errors import APIError

        models_to_try = [model] if model else TEXT_MODELS_FALLBACK

        # Preserve a complete SDK config supplied by the orchestrator.
        # Otherwise build one from the wrapper's individual options.
        if config is None:
            config_args: Dict[str, Any] = {
                "automatic_function_calling":
                    types.AutomaticFunctionCallingConfig(disable=True)
            }
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            if temperature is not None:
                config_args["temperature"] = temperature
            if max_output_tokens is not None:
                config_args["max_output_tokens"] = max_output_tokens
            if safety_settings:
                config_args["safety_settings"] = safety_settings
            if tools:
                config_args["tools"] = tools

            request_config = types.GenerateContentConfig(**config_args)
        else:
            request_config = config

        def _call(target_model: str):
            return self.client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=request_config,
            )

        return self._execute_with_retry(
            _call,
            models_to_try,
            op_name="generate_content",
        )

    def embed_text(
        self,
        text: Union[str, List[str]],
        model: str = DEFAULT_EMBED_MODEL,
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate 768-dimensional embeddings using one consistent embedding model.

        IMPORTANT:
        Existing vectors created with text-embedding-004 are not semantically
        compatible with gemini-embedding-2, even if their dimensions match.
        Re-embed stored memories and document chunks before relying on semantic
        similarity search.
        """
        if self.client is None:
            raise RuntimeError(
                "Gemini is not configured. Set GEMINI_API_KEY "
                "to enable text embeddings."
            )

        from google.genai import types
        from google.genai.errors import APIError

        if isinstance(text, str):
            if not text.strip():
                return []
            contents = [text]
            is_single = True
        else:
            contents = list(text)
            if not contents:
                return []
            if any(not isinstance(item, str) for item in contents):
                raise TypeError("All embedding inputs must be strings.")
            contents = [item for item in contents if item.strip()]
            if not contents:
                return []
            is_single = False

        def _call(target_model: str):
            response = self.client.models.embed_content(
                model=target_model,
                contents=contents,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_OUTPUT_DIMENSIONALITY
                ),
            )

            returned_embeddings = getattr(response, "embeddings", None) or []
            if len(returned_embeddings) != len(contents):
                raise RuntimeError(
                    "Gemini returned an unexpected number of embeddings: "
                    f"expected {len(contents)}, got {len(returned_embeddings)}."
                )

            embeddings = []
            for item in returned_embeddings:
                values = getattr(item, "values", None)
                if values is None:
                    raise RuntimeError("Gemini returned an embedding without values.")

                vector = [float(value) for value in values]
                if len(vector) != EMBEDDING_OUTPUT_DIMENSIONALITY:
                    raise RuntimeError(
                        "Gemini returned an unexpected embedding dimension: "
                        f"expected {EMBEDDING_OUTPUT_DIMENSIONALITY}, got {len(vector)}."
                    )
                embeddings.append(vector)

            return embeddings[0] if is_single else embeddings

        # Do not fall back to a different embedding model: vectors from different
        # models must never be compared in the same semantic-search index.
        return self._execute_with_retry(
            _call,
            [model],
            op_name="embed_text",
        )

    def transcribe_audio(
        self,
        audio_data: Optional[Union[bytes, Dict[str, Any]]] = None,
        audio_bytes: Optional[Union[bytes, Dict[str, Any]]] = None,
        mime_type: str = "audio/wav",
        prompt: str = "Transcribe the following audio accurately into text.",
        model: Optional[str] = None,
    ) -> str:
        """Transcribe raw audio bytes into text using multimodal Gemini models."""
        payload = audio_data if audio_data is not None else audio_bytes
        if payload is None:
            raise ValueError("Either 'audio_data' or 'audio_bytes' must be provided to transcribe_audio.")

        if isinstance(payload, dict):
            extracted_mime = payload.get("mime_type") or payload.get("mimetype")
            if extracted_mime:
                mime_type = extracted_mime

            raw_bytes = payload.get("data") or payload.get("bytes") or payload.get("content")
            if raw_bytes is None:
                raise ValueError(f"Could not extract raw bytes from audio dict payload keys: {list(payload.keys())}")
            payload = raw_bytes

        if not isinstance(payload, bytes):
            if isinstance(payload, bytearray):
                payload = bytes(payload)
            else:
                raise TypeError(f"Audio payload must be 'bytes', got '{type(payload).__name__}'.")

        audio_part = types.Part.from_bytes(data=payload, mime_type=mime_type)
        response = self.generate_content(
            prompt=[prompt, audio_part],
            model=model,
        )
        return self._extract_response_text(response, default_fallback="")

    def synthesize_speech(
        self,
        text: str,
        voice: str = "en",
        model: Optional[str] = None,
    ) -> bytes:
        """Synthesize text into MP3 audio bytes using gTTS."""
        if not GTTS_AVAILABLE:
            logger.error("Speech synthesis requested, but 'gtts' package is not installed in the environment.")
            return b""

        try:
            if not text or not text.strip():
                return b""

            # Strip formatting symbols so LaTeX / Markdown isn't spoken verbatim
            clean_text = (
                text.replace("*", "")
                .replace("#", "")
                .replace("$", "")
                .replace("`", "")
                .strip()
            )

            tts = gTTS(text=clean_text, lang=voice, slow=False)
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            return mp3_fp.read()
        except Exception as exc:
            logger.error(f"Speech synthesis failed: {exc}")
            return b""

    def answer_from_context(
        self,
        question: str,
        context: str,
        model: Optional[str] = None,
    ) -> str:
        """Answer a user question strictly based on provided context/documents."""
        prompt = (
            f"Context Information:\n{context}\n\n"
            f"Based on the context provided above, answer the following question accurately:\n"
            f"Question: {question}"
        )
        system_instruction = "You are a helpful assistant answering user questions strictly based on provided context."
        response = self.generate_content(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
        )
        return self._extract_response_text(response, default_fallback="Could not answer based on the provided context.")

    def web_search(self, query: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Perform grounded web search, or clearly labelled offline mock in development."""
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("Search query must not be empty.")
        if self.client is None:
            if os.getenv("ENV", "development").lower() in {"production", "prod"}:
                raise RuntimeError("Live web search requires GEMINI_API_KEY in production.")
            return {
                "query": clean_query,
                "answer": (
                    f"Offline demo response for: {clean_query}. "
                    "Live web results are unavailable because GEMINI_API_KEY is not configured."
                ),
                "sources": [],
                "mode": "mock",
            }

        prompt = (
            "Search the web for current information. Summarize relevant facts, "
            "and do not invent URLs or citations.\\n\\nQuery: " + clean_query
        )
        response = self.generate_content(prompt=prompt, model=model, tools=[{"google_search": {}}])
        answer = self._extract_response_text(response, default_fallback="No search results found.")
        sources = []
        try:
            candidate = response.candidates[0]
            metadata = getattr(candidate, "grounding_metadata", None)
            for chunk in (getattr(metadata, "grounding_chunks", None) or []):
                web = getattr(chunk, "web", None)
                uri = getattr(web, "uri", None)
                if uri:
                    sources.append({"title": getattr(web, "title", None) or uri, "url": uri})
        except (AttributeError, IndexError, TypeError):
            pass
        return {"query": clean_query, "answer": answer, "sources": sources, "mode": "live"}

    def summarize_briefing(
        self,
        content: str,
        user_name: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Generate a structured daily briefing summary with an offline-safe fallback."""
        if not content or not str(content).strip() or str(content).strip() in {"[]", "{}", "null"}:
            return "You have no pending tasks. Enjoy your day!"
        greeting = f"for {user_name}" if user_name else "for the user"
        if self.client is None:
            if os.getenv("ENV", "development").lower() in {"production", "prod"}:
                raise RuntimeError("Daily briefing generation requires GEMINI_API_KEY in production.")
            return f"Here is your daily briefing {greeting}:\\n{content}"
        prompt = f"Synthesize and format the following information into a clear, engaging daily briefing {greeting}:\n\n{content}"
        system_instruction = "You are an executive assistant preparing a concise daily briefing covering key news, tasks, and updates."
        response = self.generate_content(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
        )
        return self._extract_response_text(response, default_fallback="Unable to generate briefing summary.")

    def build_system_prompt(
        self,
        role_description: str,
        guidelines: Optional[List[str]] = None,
        context: Optional[str] = None,
        assistant_name: str = "VoxMate",
        tone: str = "casual",
        extra_tool_descriptions: Optional[List[str]] = None,
    ) -> str:
        """Construct a personalized prompt without invoking the language model."""
        return _compose_system_prompt(
            role_description, guidelines, context, assistant_name, tone,
            extra_tool_descriptions,
        )


# Singleton Instance
_default_client: Optional[LLMClient] = None

def get_default_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client

get_llm_client = get_default_client


# Module-level helper functions
def embed_text(
    text: Union[str, List[str]],
    model: str = DEFAULT_EMBED_MODEL,
) -> Union[List[float], List[List[float]]]:
    return get_default_client().embed_text(text=text, model=model)

def transcribe_audio(
    audio_data: Optional[Union[bytes, Dict[str, Any]]] = None,
    audio_bytes: Optional[Union[bytes, Dict[str, Any]]] = None,
    mime_type: str = "audio/wav",
    prompt: str = "Transcribe the following audio accurately into text.",
    model: Optional[str] = None,
) -> str:
    return get_default_client().transcribe_audio(
        audio_data=audio_data,
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        prompt=prompt,
        model=model,
    )

def synthesize_speech(
    text: str,
    voice: str = "en",
    model: Optional[str] = None,
) -> bytes:
    return get_default_client().synthesize_speech(
        text=text,
        voice=voice,
        model=model,
    )

def answer_from_context(
    question: str,
    context: str,
    model: Optional[str] = None,
) -> str:
    return get_default_client().answer_from_context(
        question=question,
        context=context,
        model=model,
    )

def web_search(
    query: str,
    model: Optional[str] = None,
) -> str:
    return get_default_client().web_search(
        query=query,
        model=model,
    )

def summarize_briefing(
    content: str,
    user_name: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    return get_default_client().summarize_briefing(
        content=content,
        user_name=user_name,
        model=model,
    )

def _compose_system_prompt(
    role_description: str,
    guidelines: Optional[List[str]] = None,
    context: Optional[str] = None,
    assistant_name: str = "VoxMate",
    tone: str = "casual",
    extra_tool_descriptions: Optional[List[str]] = None,
) -> str:
    """Pure prompt builder, independent of Gemini credentials."""
    name = (assistant_name or "VoxMate").strip() or "VoxMate"
    normalized_tone = (tone or "casual").strip().lower()
    tone_instructions = {
        "formal": "Use a professional and formal tone.",
        "casual": "Use a warm, casual and friendly tone.",
        "friendly": "Use a warm, casual and friendly tone.",
        "professional": "Use a professional and formal tone.",
        "concise": "Be concise, direct and clear.",
    }
    tone_instruction = tone_instructions.get(normalized_tone, f"Use a {normalized_tone} tone.")
    parts = [
        f"You are {name}, an AI assistant.",
        tone_instruction,
        "Always respond in the same language as the user's latest message unless they request another language.",
        role_description or "Be helpful, accurate, safe and transparent.",
    ]
    if context:
        parts.append(f"Context:\\n{context}")
    if guidelines:
        parts.append("Guidelines:\\n" + "\\n".join(f"- {item}" for item in guidelines))
    if extra_tool_descriptions:
        parts.append("Additional available tools:\\n" + "\\n".join(f"- {item}" for item in extra_tool_descriptions))
    return "\\n\\n".join(parts)


def build_system_prompt(
    role_description: str,
    guidelines: Optional[List[str]] = None,
    context: Optional[str] = None,
    assistant_name: str = "VoxMate",
    tone: str = "casual",
    extra_tool_descriptions: Optional[List[str]] = None,
) -> str:
    return _compose_system_prompt(
        role_description, guidelines, context, assistant_name, tone,
        extra_tool_descriptions,
    )


# ============================================================
# BACKWARDS COMPATIBILITY
# ============================================================

def _mock_generate(user_text: str) -> str:
    """
    Lightweight deterministic mock used by routing tests.
    This helper does not initialize the Gemini client or make API calls.
    """
    text = user_text.lower()

    if "remind me" in text:
        return json.dumps({
            "tool_call": {
                "name": "create_reminder",
                "arguments": {},
            }
        })

    if "what tasks" in text or "tasks do i have" in text:
        return json.dumps({
            "tool_call": {
                "name": "list_tasks",
                "arguments": {},
            }
        })

    return user_text

