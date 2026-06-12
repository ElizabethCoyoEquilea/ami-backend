import json
import logging
from calendar import monthrange
from datetime import date, timedelta
from typing import Any

import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.reportes_repository import (
    get_customer_summary_report,
    get_first_user_taller_id,
    get_pending_services_report,
    get_service_history_report,
    get_service_income_report,
    get_service_status_summary_report,
    get_technician_productivity_report,
    get_top_services_report,
    get_vehicle_history_report,
    user_owns_taller,
)
from app.schemas.reportes_schema import ReporteAIRequest, ReporteAIResponse, ReporteFilters, ReportType


OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
logger = logging.getLogger("reportes_ai")


REPORT_TEMPLATES: dict[ReportType, dict[str, Any]] = {
    "service_history": {
        "title": "Historial de servicios",
        "description": "Lista servicios realizados con cliente, vehiculo, tecnico, estado y costo.",
        "columns": ["fecha_inicio", "fecha_fin", "cliente", "vehiculo", "placa", "servicios", "tecnico", "estado", "total"],
        "examples": ["historial de servicios del ultimo mes", "servicios realizados esta semana"],
    },
    "service_income": {
        "title": "Ingresos por servicios",
        "description": "Agrupa ingresos, cantidad de servicios y promedio por periodo mensual.",
        "columns": ["periodo", "cantidad_servicios", "total_ingresos", "promedio_por_servicio"],
        "examples": ["cuanto generamos el mes pasado", "ingresos por servicios"],
    },
    "top_services": {
        "title": "Servicios mas solicitados",
        "description": "Ranking de detalles de servicios por frecuencia y monto generado.",
        "columns": ["servicio", "cantidad", "total_generado", "porcentaje"],
        "examples": ["servicios mas pedidos", "top 5 servicios"],
    },
    "customer_summary": {
        "title": "Resumen por cliente",
        "description": "Clientes con cantidad de servicios, total gastado y ultimo servicio.",
        "columns": ["id_cliente", "cliente", "cantidad_servicios", "total_gastado", "ultimo_servicio"],
        "examples": ["clientes con mas servicios", "cuanto gasto cada cliente"],
    },
    "pending_services": {
        "title": "Servicios pendientes o en proceso",
        "description": "Servicios que no figuran como finalizados, pagados, anulados o cancelados.",
        "columns": ["fecha_inicio", "fecha_fin", "cliente", "vehiculo", "placa", "servicios", "tecnico", "estado", "total"],
        "examples": ["servicios pendientes", "trabajos en proceso"],
    },
    "vehicle_history": {
        "title": "Historial por vehiculo",
        "description": "Servicios filtrables por vehiculo o placa.",
        "columns": ["fecha_inicio", "fecha_fin", "cliente", "vehiculo", "placa", "servicios", "tecnico", "estado", "total"],
        "examples": ["historial de mantenimiento por placa", "servicios de un vehiculo"],
    },
    "technician_productivity": {
        "title": "Productividad por tecnico",
        "description": "Cantidad de servicios y monto generado por tecnico.",
        "columns": ["tecnico", "cantidad_servicios", "servicios_completados", "servicios_pendientes", "total_generado"],
        "examples": ["productividad de tecnicos", "quien hizo mas servicios"],
    },
    "service_status_summary": {
        "title": "Resumen de estados",
        "description": "Cantidad y porcentaje de servicios por estado.",
        "columns": ["estado", "cantidad", "porcentaje"],
        "examples": ["cuantos servicios estan completados o pendientes", "resumen de estados"],
    },
}


REPORT_HANDLERS = {
    "service_history": get_service_history_report,
    "service_income": get_service_income_report,
    "top_services": get_top_services_report,
    "customer_summary": get_customer_summary_report,
    "pending_services": get_pending_services_report,
    "vehicle_history": get_vehicle_history_report,
    "technician_productivity": get_technician_productivity_report,
    "service_status_summary": get_service_status_summary_report,
}


def _last_month_range(today: date) -> tuple[date, date]:
    first_current_month = today.replace(day=1)
    last_previous_month = first_current_month - timedelta(days=1)
    first_previous_month = last_previous_month.replace(day=1)
    return first_previous_month, last_previous_month


def _this_month_range(today: date) -> tuple[date, date]:
    return today.replace(day=1), today


def _current_week_range(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    return start, today


def _build_prompt(prompt: str) -> str:
    templates = [
        {
            "report_type": key,
            "description": value["description"],
            "examples": value["examples"],
        }
        for key, value in REPORT_TEMPLATES.items()
    ]
    return f"""
Eres un asistente de reportes para una plataforma de auxilio mecanico.

Fecha actual del sistema: {date.today().isoformat()}.

Elige exactamente un esqueleto de reporte y extrae filtros del pedido del usuario.

Esqueletos disponibles:
{json.dumps(templates, ensure_ascii=False)}

Pedido del usuario:
{prompt}

Reglas:
- Devuelve solo JSON valido.
- Usa date_from y date_to en formato YYYY-MM-DD cuando el usuario mencione fechas relativas o absolutas.
- Si el usuario no pide rango de fechas, deja date_from y date_to como null.
- limit debe estar entre 1 y 200. Si el usuario pide top N, usa ese N.
- No inventes ids si el usuario no los da.
""".strip()


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


def _request_openai_report(prompt: str) -> dict | None:
    if not settings.OPENAI_API_KEY:
        return None

    response = requests.post(
        OPENAI_RESPONSES_ENDPOINT,
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.OPENAI_MODEL,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": _build_prompt(prompt)}]}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "report_request",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "report_type": {"type": "string", "enum": list(REPORT_TEMPLATES.keys())},
                            "filters": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "date_from": {"type": ["string", "null"]},
                                    "date_to": {"type": ["string", "null"]},
                                    "status": {"type": ["string", "null"]},
                                    "client_id": {"type": ["integer", "null"]},
                                    "vehicle_id": {"type": ["integer", "null"]},
                                    "technician_id": {"type": ["integer", "null"]},
                                    "plate": {"type": ["string", "null"]},
                                    "limit": {"type": "integer"},
                                },
                                "required": ["date_from", "date_to", "status", "client_id", "vehicle_id", "technician_id", "plate", "limit"],
                            },
                        },
                        "required": ["report_type", "filters"],
                    },
                }
            },
            "max_output_tokens": 700,
        },
        timeout=30,
    )
    response.raise_for_status()
    text = _extract_text(response.json())
    return _parse_json_response(text) if text else None


def _fallback_report_request(prompt: str) -> dict:
    text = prompt.lower()
    today = date.today()
    filters: dict[str, Any] = {"limit": 50}

    if "ultimo mes" in text or "último mes" in text or "mes pasado" in text:
        start, end = _last_month_range(today)
        filters["date_from"] = start
        filters["date_to"] = end
    elif "este mes" in text:
        start, end = _this_month_range(today)
        filters["date_from"] = start
        filters["date_to"] = end
    elif "esta semana" in text:
        start, end = _current_week_range(today)
        filters["date_from"] = start
        filters["date_to"] = end
    elif "hoy" in text:
        filters["date_from"] = today
        filters["date_to"] = today

    for token in text.replace(",", " ").split():
        if token.isdigit() and ("top" in text or "primer" in text):
            filters["limit"] = max(1, min(int(token), 200))
            break

    if "ingreso" in text or "generamos" in text or "factur" in text:
        report_type = "service_income"
    elif "mas solicit" in text or "más solicit" in text or "mas pedido" in text or "top" in text:
        report_type = "top_services"
    elif "cliente" in text and ("resumen" in text or "gasto" in text or "mas" in text or "más" in text):
        report_type = "customer_summary"
    elif "pendiente" in text or "proceso" in text or "no finaliz" in text:
        report_type = "pending_services"
    elif "vehiculo" in text or "vehículo" in text or "placa" in text:
        report_type = "vehicle_history"
    elif "tecnico" in text or "técnico" in text or "productividad" in text:
        report_type = "technician_productivity"
    elif "estado" in text or "completados" in text or "cancelados" in text:
        report_type = "service_status_summary"
    else:
        report_type = "service_history"

    return {"report_type": report_type, "filters": filters}


def _normalize_report_request(data: dict) -> tuple[ReportType, ReporteFilters]:
    report_type = data.get("report_type")
    if report_type not in REPORT_TEMPLATES:
        report_type = "service_history"

    filters_data = data.get("filters") or {}
    filters_data = {key: value for key, value in filters_data.items() if value is not None}
    filters = ReporteFilters(**filters_data)

    if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
        filters.date_from, filters.date_to = filters.date_to, filters.date_from

    last_day = monthrange(date.today().year, date.today().month)[1]
    if filters.limit is None:
        filters.limit = min(last_day, 50)

    return report_type, filters


def generar_reporte_ai(db: Session, request: ReporteAIRequest, id_usuario: int) -> ReporteAIResponse:
    id_taller = request.id_taller or get_first_user_taller_id(db, id_usuario)
    if not id_taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario autenticado no tiene un taller activo",
        )
    if not user_owns_taller(db, id_taller, id_usuario):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado para el usuario autenticado",
        )

    try:
        analyzed = _request_openai_report(request.prompt) or _fallback_report_request(request.prompt)
    except requests.RequestException:
        logger.exception("report_ai_openai_error")
        analyzed = _fallback_report_request(request.prompt)
    except (ValueError, TypeError, json.JSONDecodeError):
        logger.exception("report_ai_parse_error")
        analyzed = _fallback_report_request(request.prompt)

    report_type, filters = _normalize_report_request(analyzed)
    handler = REPORT_HANDLERS[report_type]
    rows = handler(db, id_taller, filters)
    template = REPORT_TEMPLATES[report_type]

    return ReporteAIResponse(
        report_type=report_type,
        title=template["title"],
        filters=filters,
        columns=template["columns"],
        rows=rows,
        row_count=len(rows),
    )
