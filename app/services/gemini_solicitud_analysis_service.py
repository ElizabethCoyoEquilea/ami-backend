import base64
import json
import logging
import mimetypes
import time
from pathlib import Path

import requests

from app.core.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
logger = logging.getLogger("gemini_solicitud_analysis")


def _build_prompt(descripcion: str) -> str:
    return f"""
Eres un asistente tecnico para una plataforma de auxilio mecanico.

Analiza la descripcion del problema del vehiculo y las imagenes adjuntas si existen.
Ignora cualquier audio: no lo recibiras y no debes mencionarlo.

Descripcion del cliente:
{descripcion}

Devuelve solamente JSON valido con esta estructura exacta:
{{
  "prioridad": "baja|media|alta|urgente",
  "observaciones": "diagnostico breve para el taller",
  "recomendacion": "recomendacion breve para el cliente"
}}

Reglas:
- prioridad debe ser una sola palabra.
- observaciones debe ser un diagnostico pequeno para el taller, maximo 450 caracteres.
- recomendacion debe estar enfocada al cliente, maximo 350 caracteres.
- No des un diagnostico definitivo; usa lenguaje de posibilidad.
- Si hay riesgo para el cliente o el vehiculo, prioridad debe ser urgente.
""".strip()


def _image_part_from_path(image_url_path: str) -> dict | None:
    image_path = PROJECT_ROOT / image_url_path.lstrip("/")
    if not image_path.exists() or not image_path.is_file():
        return None

    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    image_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": image_data,
        }
    }


def _extract_text(response_data: dict) -> str | None:
    candidates = response_data.get("candidates") or []
    if not candidates:
        return None

    parts = candidates[0].get("content", {}).get("parts") or []
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip() or None


def _parse_json_response(text: str) -> dict:
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`")
        if clean_text.lower().startswith("json"):
            clean_text = clean_text[4:].strip()

    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1:
        clean_text = clean_text[start : end + 1]

    return json.loads(clean_text)


def _normalize_analysis(data: dict) -> dict:
    prioridad = str(data.get("prioridad") or "media").strip().lower().split()[0]
    if prioridad not in {"baja", "media", "alta", "urgente"}:
        prioridad = "media"

    observaciones = str(data.get("observaciones") or "").strip()
    recomendacion = str(data.get("recomendacion") or "").strip()

    return {
        "prioridad": prioridad,
        "observaciones": observaciones[:500] or None,
        "recomendacion": recomendacion[:500] or None,
    }


def _models_to_try() -> list[str]:
    models = [settings.GEMINI_MODEL]
    fallback_models = [
        model.strip()
        for model in (settings.GEMINI_FALLBACK_MODELS or "").split(",")
        if model.strip()
    ]
    for model in fallback_models:
        if model not in models:
            models.append(model)
    return models


def _request_gemini(model: str, parts: list[dict]) -> dict:
    url = GEMINI_ENDPOINT.format(model=model)
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        },
        json={
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            },
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def analyze_solicitud_with_gemini(
    descripcion: str,
    imagenes: list[str] | None = None,
) -> dict | None:
    if not settings.GEMINI_API_KEY:
        return None

    parts = [{"text": _build_prompt(descripcion)}]
    for image_url_path in imagenes or []:
        image_part = _image_part_from_path(image_url_path)
        if image_part:
            parts.append(image_part)

    last_error: Exception | None = None
    for model in _models_to_try():
        for attempt in range(2):
            try:
                response_data = _request_gemini(model, parts)
                text = _extract_text(response_data)
                if not text:
                    return None

                return _normalize_analysis(_parse_json_response(text))
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                detail = exc.response.text[:500] if exc.response is not None else str(exc)
                logger.warning(
                    "gemini_analysis_http_error model=%s attempt=%s status=%s detail=%s",
                    model,
                    attempt + 1,
                    status_code,
                    detail,
                )
                if status_code not in {429, 500, 503, 504}:
                    break
                time.sleep(1)
            except Exception as exc:
                last_error = exc
                logger.exception(
                    "gemini_analysis_error model=%s attempt=%s",
                    model,
                    attempt + 1,
                )
                break

    if last_error:
        raise last_error
    return None
