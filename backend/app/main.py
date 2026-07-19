from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import run_agent
from .analytics_service import get_dashboard_data, get_student_profile, list_classes, list_students
from .db import ensure_database, reset_database
from .llm import llm_mode_payload
from .schemas import AgentQueryRequest, AgentResponse, DashboardResponse, StudentProfileResponse, SystemModeResponse

app = FastAPI(
    title="EduInsight API",
    version="2.0.0",
    description="EduInsight 教师侧自然语言学情分析 Data Agent 后端服务",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup_event() -> None:
    ensure_database()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/mode", response_model=SystemModeResponse)
def system_mode() -> SystemModeResponse:
    return SystemModeResponse(**llm_mode_payload())


@app.get("/api/classes")
def get_classes() -> list[dict[str, Any]]:
    return list_classes()


@app.get("/api/students")
def get_students(class_id: int | None = None) -> list[dict[str, Any]]:
    return list_students(class_id)


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(class_id: int | None = None, weeks: int = 8) -> DashboardResponse:
    return get_dashboard_data(class_id, weeks)


@app.get("/api/students/{student_id}", response_model=StudentProfileResponse)
def student_profile(student_id: int) -> StudentProfileResponse:
    try:
        return get_student_profile(student_id)
    except ValueError as exc:
        if str(exc) == "student_not_found":
            raise HTTPException(status_code=404, detail="未找到对应学生") from exc
        raise


@app.post("/api/agent/query", response_model=AgentResponse)
def agent_query(payload: AgentQueryRequest) -> AgentResponse:
    try:
        return run_agent(payload.question, class_id=payload.class_id, developer_mode=payload.developer_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reset-demo-data")
def reset_demo_data() -> dict[str, str]:
    reset_database()
    return {"status": "ok", "message": "Demo 数据已重置"}
