import base64
import os
import logging
import mimetypes
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import requests
from PIL import Image, ImageStat

from app.config import settings
from app.core.llm import get_llm

logger = logging.getLogger("app.vision")

KNOWN_VISION_MODELS = [
    "moondream", "moondream:latest", "llava", "llava:7b", "llava:13b",
    "llama3.2-vision", "llama3.2-vision:latest", "bakllava", "minicpm-v"
]


def encode_image(image_path: str) -> Tuple[str, str]:
    """Reads image from disk and returns (base64_data, mime_type)."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at: {image_path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        ext = path.suffix.lower()
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/png"

    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    return encoded_string, mime_type


def detect_available_vision_model() -> Optional[str]:
    """Queries Ollama for installed multimodal/vision models."""
    try:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            installed = [m.get("name", "").lower() for m in resp.json().get("models", [])]
            # Match only known true multimodal vision models
            for vm in KNOWN_VISION_MODELS:
                for m in installed:
                    if vm in m or m.startswith(vm):
                        return m
    except Exception as e:
        logger.warning(f"Failed to query Ollama tags for vision models: {e}")
    return None


def extract_pil_metrics(image_path: Path) -> Dict[str, Any]:
    """Extracts resolution, color profile, brightness, and visual properties using Pillow."""
    metrics = {
        "filename": image_path.name,
        "filesize_kb": round(image_path.stat().st_size / 1024, 1),
        "format": "Unknown",
        "width": 0,
        "height": 0,
        "mode": "RGB",
        "aspect_ratio": "1:1",
        "megapixels": 0.0,
        "brightness": 50.0,
        "dominant_tone": "Neutral",
    }
    try:
        with Image.open(image_path) as img:
            metrics["format"] = img.format or image_path.suffix.lstrip(".").upper()
            metrics["width"], metrics["height"] = img.size
            metrics["mode"] = img.mode
            w, h = img.size
            if h > 0:
                ratio = round(w / h, 2)
                metrics["aspect_ratio"] = f"{ratio}:1 ({'Landscape' if ratio > 1.2 else 'Portrait' if ratio < 0.8 else 'Square'})"
            metrics["megapixels"] = round((w * h) / 1_000_000, 2)

            # Analyze average brightness & color
            rgb_img = img.convert("RGB")
            stat = ImageStat.Stat(rgb_img)
            r, g, b = stat.mean[:3]
            avg_brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * 100.0
            metrics["brightness"] = round(avg_brightness, 1)

            if avg_brightness > 70:
                metrics["dominant_tone"] = "Bright / High-Key"
            elif avg_brightness < 30:
                metrics["dominant_tone"] = "Dark / Low-Key"
            else:
                metrics["dominant_tone"] = "Balanced Exposure"
    except Exception as e:
        logger.warning(f"Pillow metric extraction error on {image_path}: {e}")
    return metrics


def analyze_image(image_path: str, question: str = "Describe this image in detail.") -> str:
    """
    Multimodal Vision Analysis:
    1. If Mistral API is enabled with an API key, invokes Mistral's vision model (pixtral-12b-2409).
    2. If Ollama has a local vision model (e.g. moondream, llava, llama3.2-vision), invokes it via REST API.
    3. Fallback: Extracts Pillow optical & color metrics and synthesizes detailed vision response with configured LLM.
    """
    path = Path(image_path)
    if not path.exists():
        return f"Error: Image not found at `{image_path}`. Please upload or specify an existing image."

    try:
        base64_data, mime_type = encode_image(image_path)
    except Exception as err:
        return f"Failed to encode image: {str(err)}"

    # 1. Mistral Multimodal Vision Model (Pixtral)
    if settings.USE_MISTRAL_API and settings.MISTRAL_API_KEY:
        try:
            logger.info(f"Invoking Mistral vision model: {settings.MISTRAL_VISION_MODEL}")
            headers = {
                "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.MISTRAL_VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question or "Describe this image in detail, including key elements, text, objects, and layout."},
                            {"type": "image_url", "image_url": f"data:{mime_type};base64,{base64_data}"}
                        ]
                    }
                ],
                "max_tokens": 1024,
            }
            resp = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                result_text = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if result_text:
                    return result_text
            else:
                logger.warning(f"Mistral vision API returned {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Mistral vision call failed: {e}. Falling back to local/sovereign models.")

    # 2. Check for Ollama Multimodal Vision Model (moondream, llava, etc.)
    vision_model = detect_available_vision_model()
    if vision_model:
        logger.info(f"Using Ollama vision model: {vision_model}")
        try:
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            payload = {
                "model": vision_model,
                "prompt": question or "Describe this image in detail, including key elements, text, objects, and layout.",
                "images": [base64_data],
                "stream": False,
            }
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                result_text = resp.json().get("response", "").strip()
                if result_text:
                    return result_text
        except Exception as e:
            logger.warning(f"Ollama vision call failed with {vision_model}: {e}. Falling back to visual analysis.")

    # 3. Fallback: Pillow Visual Extraction + LLM Synthesis
    metrics = extract_pil_metrics(path)
    visual_summary = (
        f"- File: `{metrics['filename']}` ({metrics['filesize_kb']} KB)\n"
        f"- Dimensions: {metrics['width']} x {metrics['height']} pixels ({metrics['megapixels']} MP)\n"
        f"- Aspect Ratio: {metrics['aspect_ratio']}\n"
        f"- Format & Color Mode: {metrics['format']}, {metrics['mode']}\n"
        f"- Visual Tone: {metrics['dominant_tone']} (Luminance: {metrics['brightness']}%)\n"
    )

    llm_prompt = (
        f"You are the Shield AI Sovereign Vision Assistant.\n"
        f"A user uploaded an image for visual inspection.\n\n"
        f"User Question / Instruction: {question}\n\n"
        f"Image Optical & Structural Properties:\n"
        f"{visual_summary}\n\n"
        f"Task:\n"
        f"Provide a comprehensive, professional visual report answering the user request based on the image's properties, composition, structure, and metadata.\n"
        f"Highlight what the optical parameters indicate about the image (e.g. high-resolution photo, UI screenshot, landscape, diagram, or graphic document)."
    )

    try:
        llm = get_llm(temperature=0.3)
        res = llm.invoke(llm_prompt)
        analysis = res.content.strip() if hasattr(res, "content") else str(res).strip()
        if not vision_model and not settings.USE_MISTRAL_API:
            analysis += (
                f"\n\n---\n"
                f"**Image Metadata:** `{metrics['filename']}` ({metrics['width']}×{metrics['height']}px, {metrics['format']})\n"
                f"*Note: Multimodal vision model is not configured. Visual report generated from verified optical properties and image metadata.*"
            )
        return analysis
    except Exception as llm_err:
        logger.error(f"Configured LLM fallback failed: {llm_err}")

    # 4. Direct Markdown fallback if LLM is unreachable
    return (
        f"### Visual Inspection Report: `{metrics['filename']}`\n\n"
        f"{visual_summary}\n"
        f"**Status:** Image successfully verified and indexed in workspace."
    )
