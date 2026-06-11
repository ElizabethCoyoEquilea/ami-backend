import base64
import json
import logging
import mimetypes
import time
from pathlib import Path

import requests

from app.core.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
OPENAI_TRANSCRIPTIONS_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
logger = logging.getLogger("openai_solicitud_analysis")


def _build_prompt(descripcion: str, transcripcion_audio: str | None = None) -> str:
    audio_section = (
        f"\n\nTranscripcion del audio del cliente:\n{transcripcion_audio}"
        if transcripcion_audio
        else ""
    )
    return f"""
Eres un asistente tecnico para una plataforma de auxilio mecanico.

Analiza la descripcion del problema del vehiculo, la transcripcion del audio y las imagenes adjuntas si existen.

Descripcion del cliente:
{descripcion}{audio_section}

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
        "type": "input_image",
        "image_url": f"data:{mime_type};base64,{image_data}",
    }


def _audio_path_from_url_path(audio_url_path: str) -> Path | None:
    audio_path = PROJECT_ROOT / audio_url_path.lstrip("/")
    if not audio_path.exists() or not audio_path.is_file():
        return None

    return audio_path


def _transcribe_audio(audio_url_path: str) -> str | None:
    audio_path = _audio_path_from_url_path(audio_url_path)
    if not audio_path:
        return None

    with audio_path.open("rb") as audio_file:
        response = requests.post(
            OPENAI_TRANSCRIPTIONS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            },
            data={
                "model": settings.OPENAI_TRANSCRIPTION_MODEL,
                "response_format": "json",
            },
            files={
                "file": (audio_path.name, audio_file, mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"),
            },
            timeout=60,
        )
    response.raise_for_status()

    response_data = response.json()
    text = response_data.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _extract_text(response_data: dict) -> str | None:
    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []
    for output_item in response_data.get("output") or []:
        for content_item in output_item.get("content") or []:
            text = content_item.get("text")
            if text:
                text_parts.append(text)

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


def _request_openai(content: list[dict]) -> dict:
    response = requests.post(
        OPENAI_RESPONSES_ENDPOINT,
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.OPENAI_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "solicitud_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "prioridad": {
                                "type": "string",
                                "enum": ["baja", "media", "alta", "urgente"],
                            },
                            "observaciones": {"type": "string"},
                            "recomendacion": {"type": "string"},
                        },
                        "required": ["prioridad", "observaciones", "recomendacion"],
                    },
                }
            },
            "max_output_tokens": 600,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def analyze_solicitud_with_openai(
    descripcion: str,
    audio: str | None = None,
    imagenes: list[str] | None = None,
) -> dict | None:
    if not settings.OPENAI_API_KEY:
        return None

    transcripcion_audio = None
    if audio:
        try:
            transcripcion_audio = _transcribe_audio(audio)
        except Exception:
            logger.exception("openai_audio_transcription_error audio=%s", audio)

    content = [{"type": "input_text", "text": _build_prompt(descripcion, transcripcion_audio)}]

    for image_url_path in imagenes or []:
        image_part = _image_part_from_path(image_url_path)
        if image_part:
            content.append(image_part)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response_data = _request_openai(content)
            text = _extract_text(response_data)
            if not text:
                return None

            return _normalize_analysis(_parse_json_response(text))
        except requests.HTTPError as exc:
            last_error = exc
            status_code = exc.response.status_code if exc.response is not None else None
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            logger.warning(
                "openai_analysis_http_error model=%s attempt=%s status=%s detail=%s",
                settings.OPENAI_MODEL,
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
                "openai_analysis_error model=%s attempt=%s",
                settings.OPENAI_MODEL,
                attempt + 1,
            )
            break

    if last_error:
        raise last_error
    return None
