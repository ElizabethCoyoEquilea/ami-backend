from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ReportType = Literal[
    "service_history",
    "service_income",
    "top_services",
    "customer_summary",
    "pending_services",
    "vehicle_history",
    "technician_productivity",
    "provider_completed_services",
    "service_status_summary",
]


class ReporteAIRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)
    id_taller: int | None = Field(default=None, gt=0)

    @field_validator("prompt")
    @classmethod
    def limpiar_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El prompt es obligatorio")
        return value


class ReporteFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    status: str | None = Field(default=None, max_length=30)
    client_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    technician_id: int | None = Field(default=None, gt=0)
    plate: str | None = Field(default=None, max_length=20)
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("status", "plate")
    @classmethod
    def limpiar_texto(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class ReporteAIResponse(BaseModel):
    report_type: ReportType
    title: str
    filters: ReporteFilters
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
