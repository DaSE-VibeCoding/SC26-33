from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    step: str
    status: Literal["done", "warning", "error"]
    detail: str


class EvidenceItem(BaseModel):
    label: str
    value: str
    change: str | None = None


class AgentAnswer(BaseModel):
    problem_understanding: str
    analysis_task: str
    headline: str
    summary: str
    key_findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class TableData(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]


class ChartData(BaseModel):
    type: Literal["bar", "line", "table", "pie"]
    title: str
    x_field: str
    y_field: str | None = None
    series: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)


class DebugInfo(BaseModel):
    sql: str | None = None
    llm_used: bool = False
    model: str | None = None
    reason: str | None = None


class AgentResponse(BaseModel):
    mode: Literal["llm", "template", "fallback"]
    intent: str
    question: str
    answer: AgentAnswer
    trace: list[TraceStep]
    table: TableData
    chart: ChartData
    debug: DebugInfo = Field(default_factory=DebugInfo)


class AgentQueryRequest(BaseModel):
    question: str
    class_id: int | None = None
    developer_mode: bool = False


class KpiCard(BaseModel):
    label: str
    value: str
    delta: str | None = None
    trend: Literal["up", "down", "flat"] = "flat"


class DashboardMeta(BaseModel):
    scope_label: str
    student_count: int
    weeks: int


class DashboardResponse(BaseModel):
    meta: DashboardMeta
    kpis: list[KpiCard]
    accuracy_trend: list[dict[str, Any]]
    submission_trend: list[dict[str, Any]]
    knowledge_mastery: list[dict[str, Any]]
    risk_students: list[dict[str, Any]]


class StudentProfileResponse(BaseModel):
    profile: dict[str, Any]
    weekly_accuracy: list[dict[str, Any]]
    submission_summary: list[dict[str, Any]]
    weak_knowledge_points: list[dict[str, Any]]
    insight: str
    recommendations: list[str]


class SystemModeResponse(BaseModel):
    mode: Literal["online", "offline"]
    label: str
    llm_available: bool
    model: str | None = None
