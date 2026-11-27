"""Image generation support for VoxMate.

The voice gateway uses this small provider adapter so image generation does not
interfere with the existing text/voice pipeline. Pollinations' current API is
preferred when POLLINATIONS_API_KEY is configured; the legacy image endpoint is
kept as a compatibility fallback for existing VoxMate setups.
"""

import base64
import hashlib
import os
import re
from urllib.parse import quote

import httpx
from loguru import logger


POLLINATIONS_API = "https://gen.pollinations.ai"
LEGACY_POLLINATIONS_API = "https://image.pollinations.ai/prompt"
DEFAULT_MODEL = os.getenv("POLLINATIONS_IMAGE_MODEL", "flux")


def _filename(prompt: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", prompt.strip()).strip("-").lower()
    slug = slug[:48] or "voxmate-image"
    digest = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:8]
    return f"voxmate-{slug}-{digest}.jpg"


def _mime_from_bytes(data: bytes, content_type: str = "") -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return content_type.split(";", 1)[0].strip().lower() or "image/jpeg"


async def _fetch_legacy(prompt: str, width: int, height: int) -> tuple[bytes, str]:
    url = (
        f"{LEGACY_POLLINATIONS_API}/{quote(prompt, safe='')}"
        f"?model={quote(DEFAULT_MODEL)}&width={width}&height={height}&nologo=true"
    )
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content, _mime_from_bytes(response.content, response.headers.get("content-type", ""))


async def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """Generate one image and return binary data as base64 for the mobile client."""
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("Image prompt cannot be empty.")

    api_key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    data: bytes | None = None
    mime_type = "image/jpeg"
    provider = "pollinations-legacy"

    # Current authenticated Pollinations API.
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{POLLINATIONS_API}/v1/images/generations",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": DEFAULT_MODEL,
                        "prompt": prompt,
                        "n": 1,
                        "size": f"{width}x{height}",
                        "response_format": "b64_json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                item = (payload.get("data") or [{}])[0]
                encoded = item.get("b64_json")
                if encoded:
                    data = base64.b64decode(encoded)
                    provider = "pollinations"
                else:
                    image_url = item.get("url")
                    if image_url:
                        image_response = await client.get(image_url)
                        image_response.raise_for_status()
                        data = image_response.content
                    else:
                        raise RuntimeError("Pollinations returned no image data.")
                mime_type = _mime_from_bytes(data, response.headers.get("content-type", ""))
        except Exception as exc:
            logger.warning("Authenticated Pollinations image generation failed: {}", exc)
            # Keep the old endpoint as a compatibility fallback.

    if data is None:
        try:
            data, mime_type = await _fetch_legacy(prompt, width, height)
        except Exception as exc:
            logger.error("All Pollinations image generation paths failed: {}", exc)
            if api_key:
                raise RuntimeError(
                    "Image generation failed through Pollinations. Check POLLINATIONS_API_KEY, "
                    "model access/quota, and backend network connectivity."
                ) from exc
            raise RuntimeError(
                "Image generation is unavailable. Add POLLINATIONS_API_KEY to the backend "
                "environment, or use a legacy Pollinations endpoint that is still accessible."
            ) from exc

    if not data:
        raise RuntimeError("Image provider returned an empty image.")

    extension = "jpg" if mime_type == "image/jpeg" else ("png" if mime_type == "image/png" else "jpg")
    filename = _filename(prompt).rsplit(".", 1)[0] + f".{extension}"
    return {
        "data": base64.b64encode(data).decode("ascii"),
        "mime_type": mime_type,
        "filename": filename,
        "provider": provider,
        "prompt": prompt,
    }
